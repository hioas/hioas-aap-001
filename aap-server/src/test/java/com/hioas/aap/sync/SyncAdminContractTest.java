package com.hioas.aap.sync;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

/**
 * T14 · new-api 同步运维（ADM-S01…06）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.4（`ADM-S01` 任务列表 / `ADM-S02` 任务详情（含
 * operations）/ `ADM-S03` 重试（≤5 次退避 30s/2m/8m/30m）/ `ADM-S04` 渠道绑定列表 / `ADM-S05` 渠道启停 /
 * `ADM-S06` 上游模型清单）+ `json-schema/models/{sync-task,sync-operation,channel-binding,model-info}.schema.json`
 * + `01-ER数据模型.md` §`aap_sync_task` / §`aap_sync_operation` / §`aap_channel_binding` / §`aap_newapi_endpoint`
 * + `.calicat/prd/11-同步与用量统计PRD.md` §3（渠道字段映射 / 幂等键 / 状态机 / 读前写后三段式 / 重试退避）
 * + `.calicat/prd/21-验收标准.md`（AC-34 回读一致、AC-35 退避 ≤5、AC-42 tag 批量启停、AC-50 E-1505）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>重试退避（AC-35，PRD §5）：第 1 次立即 → +30s → +2min → +8min → +30min；**≤5 次**，
 *       耗尽转 `MANUAL`（再重试 409 {@code E-1601}）；鉴权类（401/403）**不重试**直接 `MANUAL`（A8）</li>
 *   <li>{@code E-1505}（403「同步接口权限不足」）= **new-api 侧拒绝**：端点标记 `readonly` 时的写操作、
 *       或上游返回 401/403。纯 DB 读接口（S01/S02/S04）不产生该码</li>
 *   <li>启停（AC-42）走**读前写后三段式**：读现值 → 写 → 回读比对；不一致**不谎报成功**（502 {@code E-1501}）</li>
 *   <li>渠道状态机（PRD §3）：仅 `SYNCED`/`ENABLED`/`DISABLED` 可启停；同目标状态**幂等**且不打上游</li>
 *   <li>详情必须带 `operations` 子集合（列表复用同一映射，见 tdd-state 踩坑 22）</li>
 * </ul>
 */
class SyncAdminContractTest extends ApiTestBase {

    private static final String PHONE = "13800000130";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    @Autowired
    private CryptoService cryptoService;

    private HttpServer upstream;
    private final AtomicInteger upstreamCalls = new AtomicInteger();

    /** 上游桩的可编程行为：模型清单返回码 / 渠道读回状态（1=ENABLED 2=DISABLED）/ 写入是否真正生效。 */
    private volatile int modelsStatus = 200;
    private volatile int channelStatus = 1;
    private volatile boolean writeApplies = true;

    @AfterEach
    void stopUpstream() {
        if (upstream != null) {
            upstream.stop(0);
            upstream = null;
        }
    }

    /**
     * 启一个 new-api 桩（仅测试，进程内 {@code com.sun.net.httpserver}）：
     * <ul>
     *   <li>{@code GET /models} → 模型清单（{@code data[].id/owned_by/enabled}）</li>
     *   <li>{@code GET /api/channel/{id}} → 渠道现值 {@code {"data":{"id":..,"status":1|2}}}</li>
     *   <li>{@code PUT /api/channel/} → 写渠道状态（`writeApplies=false` 时忽略写入，制造回读不一致）</li>
     * </ul>
     */
    private String startUpstream() throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/models", exchange -> {
            upstreamCalls.incrementAndGet();
            String body = modelsStatus == 200
                    ? "{\"data\":[{\"id\":\"gpt-4o\",\"owned_by\":\"openai\"},"
                            + "{\"id\":\"claude-3-5-sonnet\",\"owned_by\":\"anthropic\",\"enabled\":false}]}"
                    : "{\"error\":\"upstream " + modelsStatus + "\"}";
            respond(exchange, modelsStatus, body);
        });
        upstream.createContext("/api/channel", exchange -> {
            upstreamCalls.incrementAndGet();
            String path = exchange.getRequestURI().getPath();
            if ("GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                respond(exchange, 200, "{\"data\":{\"id\":555,\"status\":" + channelStatus + "}}");
                return;
            }
            String requested = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            if (writeApplies && requested.contains("\"status\":2")) {
                channelStatus = 2;
            } else if (writeApplies && requested.contains("\"status\":1")) {
                channelStatus = 1;
            }
            respond(exchange, 200, "{\"success\":true}");
        });
        upstream.start();
        return "http://127.0.0.1:" + upstream.getAddress().getPort();
    }

    private static void respond(com.sun.net.httpserver.HttpExchange exchange, int status, String body)
            throws java.io.IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }

    // ------------------------------------------------------------------ 令牌

    private String supplierToken() {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(PHONE));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(PHONE, send.data().path("dev_code").asText()));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    private String adminToken(long accountId, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, 'x', '技术运营', ?, 'ACTIVE')
                """, accountId, role.toLowerCase() + "-" + accountId, role);
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String techOps() {
        return adminToken(970101L, "TECH_OPS");
    }

    // ------------------------------------------------------------------ 夹具

    private void insertBinding(long id, String channelName, String status, Long endpointId, Long channelId,
                               String createdAt) {
        jdbc.update("""
                insert into aap_channel_binding (id, provider_id, credential_id, endpoint_id, channel_id, channel_name,
                    tag, group_name, priority, weight, models, status, last_synced_at, created_at, updated_at,
                    deleted, version)
                values (?, 850001, 860001, ?, ?, ?, 'aap-provider-850001', 'default', 0, 1,
                        '["gpt-4o"]'::jsonb, ?, ?::timestamptz, ?::timestamptz, ?::timestamptz, false, 0)
                """, id, endpointId, channelId, channelName, status,
                "SYNCED".equals(status) || "ENABLED".equals(status) || "DISABLED".equals(status) ? createdAt : null,
                createdAt, createdAt);
    }

    private void insertTask(long id, String taskNo, Long bindingId, String taskType, String status, int attemptCount,
                            OffsetDateTime nextRetryAt, String lastError, String createdAt) {
        jdbc.update("""
                insert into aap_sync_task (id, task_no, binding_id, provider_id, task_type, status, payload,
                    idempotency_key, attempt_count, next_retry_at, last_error, created_at, updated_at, deleted, version)
                values (?, ?, ?, 850001, ?, ?, '{"key":"***"}'::jsonb, ?, ?, ?::timestamptz, ?, ?::timestamptz,
                        ?::timestamptz, false, 0)
                """, id, taskNo, bindingId, taskType, status, "idem-" + taskNo, attemptCount, nextRetryAt, lastError,
                createdAt, createdAt);
    }

    private void insertOperation(long id, long taskId, int attemptNo, String result, String error) {
        jdbc.update("""
                insert into aap_sync_operation (id, task_id, operation, request_payload, response_payload, result,
                    readback_equal, attempt_no, error, created_at, updated_at, deleted, version)
                values (?, ?, 'ADD_CHANNEL', '{"channel_name":"AAP-TEST-1"}'::jsonb, '{"ok":true}'::jsonb, ?, true, ?,
                        ?, now(), now(), false, 0)
                """, id, taskId, result, attemptNo, error);
    }

    private long insertEndpoint(long id, String baseUrl, boolean readonly, String apiKeyPlain) {
        jdbc.update("""
                insert into aap_newapi_endpoint (id, name, base_url, api_key_cipher, readonly, status,
                    created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, 'ACTIVE', now(), now(), false, 0)
                """, id, "new-api-" + id, baseUrl, cryptoService.encrypt(apiKeyPlain), readonly);
        return id;
    }

    private long taskCount() {
        Long count = jdbc.queryForObject("select count(*) from aap_sync_task", Long.class);
        return count == null ? 0L : count;
    }

    private String taskStatus(long id) {
        return jdbc.queryForObject("select status from aap_sync_task where id = ?", String.class, id);
    }

    private int taskAttempts(long id) {
        Integer value = jdbc.queryForObject("select attempt_count from aap_sync_task where id = ?", Integer.class, id);
        return value == null ? 0 : value;
    }

    private OffsetDateTime taskNextRetry(long id) {
        return jdbc.queryForObject("select next_retry_at from aap_sync_task where id = ?", OffsetDateTime.class, id);
    }

    private long secondsUntil(OffsetDateTime moment) {
        assertThat(moment).as("应排定了下次重试时间").isNotNull();
        return Duration.between(OffsetDateTime.now(ZoneOffset.UTC), moment).getSeconds();
    }

    // ------------------------------------------------------------------ ADM-S01 / S02

    @Test
    @DisplayName("ADM-S01/S02 同步任务：分页、状态/绑定过滤、详情含 operations、不存在 404 E-1406")
    void taskListAndDetail() {
        String admin = techOps();
        insertBinding(810001, "AAP-TEST-1", "SYNCED", null, null, "2026-09-18T00:00:00Z");
        insertBinding(810002, "AAP-TEST-2", "SYNCED", null, null, "2026-09-18T00:10:00Z");
        insertTask(820001, "SY202609180001", 810001L, "ADD_CHANNEL", "SUCCESS", 1, null, null,
                "2026-09-18T01:00:00Z");
        insertTask(820002, "SY202609180002", 810001L, "WRITE_PRICE", "FAILED", 2,
                OffsetDateTime.parse("2026-09-18T03:00:00Z"), "E-1501 同步 new-api 失败",
                "2026-09-18T02:00:00Z");
        insertTask(820003, "SY202609180003", 810002L, "ENABLE", "PENDING", 0, null, null,
                "2026-09-18T03:00:00Z");
        insertOperation(830001, 820001L, 1, "SUCCESS", null);
        insertOperation(830002, 820001L, 1, "SUCCESS", null);
        insertOperation(830003, 820002L, 2, "FAILED", "E-1501");

        HttpResult list = get("/admin/sync/tasks", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(list.body());
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).isEqualTo(3L);
        assertThat(list.data().path("pageSize").asInt()).isEqualTo(20);
        assertThat(list.data().path("items").size()).isEqualTo(3);
        for (JsonNode item : list.data().path("items")) {
            SchemaAssert.assertModel("sync-task", json(item));
        }
        // 列表按 created_at desc, id desc：最新的 PENDING 任务在最前
        assertThat(list.data().path("items").get(0).path("task_no").asText()).isEqualTo("SY202609180003");
        JsonNode succeeded = itemByTaskNo(list.data().path("items"), "SY202609180001");
        assertThat(succeeded.path("id").asText()).as("雪花 ID 对外 string").isEqualTo("820001");
        assertThat(succeeded.path("attempt_count").asInt()).isEqualTo(1);
        assertThat(succeeded.path("operations").size()).as("列表项也带 operations 明细").isEqualTo(2);

        assertThat(get("/admin/sync/tasks?status=FAILED", admin).data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/sync/tasks?status=failed", admin).data().path("total").asLong())
                .as("状态过滤大小写不敏感").isEqualTo(1L);
        assertThat(get("/admin/sync/tasks?bindingId=810001", admin).data().path("total").asLong()).isEqualTo(2L);
        assertThat(get("/admin/sync/tasks?bindingId=810002", admin).data().path("total").asLong()).isEqualTo(1L);
        HttpResult paged = get("/admin/sync/tasks?page=2&pageSize=2", admin);
        assertThat(paged.data().path("total").asLong()).isEqualTo(3L);
        assertThat(paged.data().path("page").asInt()).isEqualTo(2);
        assertThat(paged.data().path("items").size()).isEqualTo(1);

        HttpResult detail = get("/admin/sync/tasks/820002", admin);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertModel("sync-task", json(detail.data()));
        assertThat(detail.data().path("status").asText()).isEqualTo("FAILED");
        assertThat(detail.data().path("last_error").asText()).contains("E-1501");
        assertThat(detail.data().path("next_retry_at").asText()).startsWith("2026-09-18T03:00:00");
        assertThat(detail.data().path("operations").size()).isEqualTo(1);
        JsonNode operation = detail.data().path("operations").get(0);
        SchemaAssert.assertModel("sync-operation", json(operation));
        assertThat(operation.path("attempt_no").asInt()).isEqualTo(2);
        assertThat(operation.path("error").asText()).isEqualTo("E-1501");

        HttpResult missing = get("/admin/sync/tasks/999999", admin);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        HttpResult badId = get("/admin/sync/tasks/abc", admin);
        assertThat(badId.status()).as(badId.body()).isEqualTo(400);
        assertThat(badId.code()).isEqualTo("E-1001");
    }

    private static JsonNode itemByTaskNo(JsonNode items, String taskNo) {
        for (JsonNode item : items) {
            if (taskNo.equals(item.path("task_no").asText())) {
                return item;
            }
        }
        throw new AssertionError("列表里缺少任务 " + taskNo + "：" + items);
    }

    // ------------------------------------------------------------------ ADM-S03

    @Test
    @DisplayName("ADM-S03 重试（无端点）：立即重新入队、attempt_count 递增、逐次落 operation + SYNC_EXECUTE 审计")
    void retryWithoutEndpointRequeuesImmediately() {
        String admin = techOps();
        insertTask(820001, "SY202609180001", null, "SYNC_MODELS", "FAILED", 1, null, "上游超时",
                "2026-09-18T01:00:00Z");
        insertOperation(830001, 820001L, 1, "FAILED", "E-1501");

        HttpResult retried = post("/admin/sync/tasks/820001/retry", null, admin);
        assertThat(retried.status()).as(retried.body()).isEqualTo(200);
        SchemaAssert.assertModel("sync-task", json(retried.data()));
        assertThat(retried.data().path("status").asText()).as("无端点可探测 → 立即重新入队").isEqualTo("PENDING");
        assertThat(retried.data().path("attempt_count").asInt()).isEqualTo(2);
        assertThat(retried.data().path("next_retry_at").isNull()).as("立即执行不再排程").isTrue();
        assertThat(retried.data().path("operations").size()).isEqualTo(2);
        JsonNode last = retried.data().path("operations").get(1);
        assertThat(last.path("operation").asText()).isEqualTo("RETRY");
        assertThat(last.path("attempt_no").asInt()).isEqualTo(2);
        assertThat(last.path("result").asText()).isEqualTo("PENDING");

        assertThat(taskStatus(820001L)).isEqualTo("PENDING");
        assertThat(taskAttempts(820001L)).isEqualTo(2);
        assertThat(taskNextRetry(820001L)).isNull();
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_operation where task_id = 820001", Long.class))
                .isEqualTo(2L);

        HttpResult logs = get("/admin/audit-logs?action=SYNC_EXECUTE", admin);
        assertThat(logs.status()).as(logs.body()).isEqualTo(200);
        assertThat(logs.data().path("total").asLong()).as("同步重试必须留审计").isEqualTo(1L);
        assertThat(logs.data().path("items").get(0).path("target_type").asText()).isEqualTo("sync_task");
        assertThat(logs.data().path("items").get(0).path("target_id").asText()).isEqualTo("820001");
    }

    @Test
    @DisplayName("ADM-S03 退避序列：30s → 2m → 8m → 30m（AC-35 上限 5 次），第 5 次转 MANUAL 且再重试 409 E-1601")
    void retryBackoffScheduleAndExhaustion() throws Exception {
        String admin = techOps();
        String baseUrl = startUpstream();
        modelsStatus = 500;
        insertEndpoint(840001L, baseUrl, false, "sk-fixture-not-a-secret");
        insertBinding(810001, "AAP-TEST-1", "FAILED", 840001L, 555L, "2026-09-18T00:00:00Z");
        insertTask(820002, "SY202609180002", 810001L, "ENABLE", "FAILED", 0, null, null, "2026-09-18T01:00:00Z");

        long[] expectedSeconds = {30L, 120L, 480L, 1800L};
        for (int attempt = 1; attempt <= 4; attempt++) {
            HttpResult res = post("/admin/sync/tasks/820002/retry", null, admin);
            assertThat(res.status()).as("第 %d 次重试应报同步失败：%s", attempt, res.body()).isEqualTo(502);
            assertThat(res.code()).isEqualTo("E-1501");
            assertThat(taskStatus(820002L)).as("上游失败后任务留在 FAILED 等待退避").isEqualTo("FAILED");
            assertThat(taskAttempts(820002L)).isEqualTo(attempt);
            assertThat(secondsUntil(taskNextRetry(820002L)))
                    .as("第 %d 次重试的退避应为 %d 秒", attempt, expectedSeconds[attempt - 1])
                    .isBetween(expectedSeconds[attempt - 1] - 15, expectedSeconds[attempt - 1] + 30);
        }

        HttpResult fifth = post("/admin/sync/tasks/820002/retry", null, admin);
        assertThat(fifth.status()).as(fifth.body()).isEqualTo(502);
        assertThat(taskAttempts(820002L)).isEqualTo(5);
        assertThat(taskStatus(820002L)).as("退避耗尽转 MANUAL（等待人工介入）").isEqualTo("MANUAL");
        assertThat(taskNextRetry(820002L)).as("耗尽后不再排程").isNull();
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_operation where task_id = 820002", Long.class))
                .as("每次重试都留一行操作明细").isEqualTo(5L);
        assertThat(jdbc.queryForObject(
                "select last_error from aap_sync_task where id = 820002", String.class)).contains("E-1501");

        HttpResult exhausted = post("/admin/sync/tasks/820002/retry", null, admin);
        assertThat(exhausted.status()).as(exhausted.body()).isEqualTo(409);
        assertThat(exhausted.code()).isEqualTo("E-1601");
        assertThat(taskAttempts(820002L)).as("被拒的重试不得推进计数").isEqualTo(5);
    }

    @Test
    @DisplayName("ADM-S03 上游鉴权拒绝：401/403 不重试直接转 MANUAL 并回 E-1505（A8/AC-50）；上游可达则立即入队")
    void retryUpstreamAuthFailureGoesManual() throws Exception {
        String admin = techOps();
        String baseUrl = startUpstream();
        insertEndpoint(840001L, baseUrl, false, "sk-fixture-not-a-secret");
        insertBinding(810001, "AAP-TEST-1", "FAILED", 840001L, 555L, "2026-09-18T00:00:00Z");
        insertTask(820002, "SY202609180002", 810001L, "UPDATE_CHANNEL", "FAILED", 2, null, null,
                "2026-09-18T01:00:00Z");

        modelsStatus = 403;
        HttpResult denied = post("/admin/sync/tasks/820002/retry", null, admin);
        assertThat(denied.status()).as(denied.body()).isEqualTo(403);
        assertThat(denied.code()).isEqualTo("E-1505");
        assertThat(taskStatus(820002L)).as("鉴权失败重试无意义 → 直接 MANUAL").isEqualTo("MANUAL");
        assertThat(taskNextRetry(820002L)).isNull();
        assertThat(taskAttempts(820002L)).isEqualTo(3);
        assertThat(jdbc.queryForObject("select error from aap_sync_operation where task_id = 820002 order by id desc limit 1",
                String.class)).isEqualTo("E-1505");

        // 上游可达：立即重新入队（PENDING，不排退避）
        insertTask(820003, "SY202609180003", 810001L, "UPDATE_CHANNEL", "FAILED", 1, null, null,
                "2026-09-18T02:00:00Z");
        modelsStatus = 200;
        HttpResult ok = post("/admin/sync/tasks/820003/retry", null, admin);
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        assertThat(ok.data().path("status").asText()).isEqualTo("PENDING");
        assertThat(ok.data().path("attempt_count").asInt()).isEqualTo(2);
        assertThat(taskNextRetry(820003L)).isNull();

        // 状态机：进行中/已完成的任务不可重试；不存在 404
        insertTask(820004, "SY202609180004", null, "ENABLE", "RUNNING", 1, null, null, "2026-09-18T03:00:00Z");
        HttpResult running = post("/admin/sync/tasks/820004/retry", null, admin);
        assertThat(running.status()).as(running.body()).isEqualTo(409);
        assertThat(running.code()).isEqualTo("E-1601");
        HttpResult missing = post("/admin/sync/tasks/999999/retry", null, admin);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        assertThat(taskCount()).as("失败的重试不得凭空造任务（本轮夹具 3 条）").isEqualTo(3L);
    }

    // ------------------------------------------------------------------ ADM-S04 / S05

    @Test
    @DisplayName("ADM-S04 渠道绑定列表：分页 + 契约字段（channel_name `AAP-{简称}-{序号}`、models 数组）")
    void bindingList() {
        String admin = techOps();
        insertBinding(810001, "AAP-TEST-1", "SYNCED", 840001L, 555L, "2026-09-18T01:00:00Z");
        insertBinding(810002, "AAP-TEST-2", "ENABLED", 840001L, 556L, "2026-09-18T02:00:00Z");

        HttpResult list = get("/admin/channel-bindings", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(list.body());
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).isEqualTo(2L);
        JsonNode first = list.data().path("items").get(0);
        SchemaAssert.assertModel("channel-binding", json(first));
        assertThat(first.path("channel_name").asText()).isEqualTo("AAP-TEST-2");
        assertThat(first.path("binding_id").asText()).as("binding_id 是 id 的兼容别名").isEqualTo("810002");
        assertThat(first.path("channel_id").asInt()).isEqualTo(556);
        assertThat(first.path("models").isArray()).isTrue();
        assertThat(first.path("models").get(0).asText()).isEqualTo("gpt-4o");
        assertThat(first.path("status").asText()).isEqualTo("ENABLED");

        HttpResult paged = get("/admin/channel-bindings?page=1&pageSize=1", admin);
        assertThat(paged.data().path("items").size()).isEqualTo(1);
        assertThat(paged.data().path("total").asLong()).isEqualTo(2L);
    }

    @Test
    @DisplayName("ADM-S05 启停三段式：读前写后回读一致才置态；只读端点/上游拒绝 403 E-1505；未同步 409；同目标幂等")
    void bindingStatusChange() throws Exception {
        String admin = techOps();
        String baseUrl = startUpstream();
        insertEndpoint(840001L, baseUrl, false, "sk-fixture-not-a-secret");
        insertEndpoint(840002L, baseUrl, true, "sk-fixture-readonly-not-a-secret");
        insertBinding(810001, "AAP-TEST-1", "SYNCED", 840001L, 555L, "2026-09-18T01:00:00Z");
        insertBinding(810002, "AAP-TEST-2", "SYNCED", 840002L, 556L, "2026-09-18T01:00:00Z");
        insertBinding(810003, "AAP-TEST-3", "NOT_SYNCED", 840001L, null, "2026-09-18T01:00:00Z");
        insertBinding(810004, "AAP-TEST-4", "ENABLED", 840001L, 557L, "2026-09-18T01:00:00Z");

        // 入参校验 / 资源不存在
        HttpResult badTarget = post("/admin/channel-bindings/810001/status", """
                {"target_status":"PAUSED"}
                """, admin);
        assertThat(badTarget.status()).as(badTarget.body()).isEqualTo(400);
        assertThat(badTarget.code()).isEqualTo("E-1001");
        HttpResult noTarget = post("/admin/channel-bindings/810001/status", "{}", admin);
        assertThat(noTarget.status()).as(noTarget.body()).isEqualTo(400);
        assertThat(noTarget.code()).isEqualTo("E-1001");
        HttpResult missing = post("/admin/channel-bindings/999999/status", """
                {"target_status":"ENABLED"}
                """, admin);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        HttpResult badId = post("/admin/channel-bindings/abc/status", """
                {"target_status":"ENABLED"}
                """, admin);
        assertThat(badId.status()).as(badId.body()).isEqualTo(400);
        assertThat(badId.code()).isEqualTo("E-1001");

        // 未同步完成的渠道不可启停（PRD 状态机：PENDING/SYNCING/NOT_SYNCED → 不参与启停）
        HttpResult notSynced = post("/admin/channel-bindings/810003/status", """
                {"target_status":"ENABLED"}
                """, admin);
        assertThat(notSynced.status()).as(notSynced.body()).isEqualTo(409);
        assertThat(notSynced.code()).isEqualTo("E-1601");

        // 只读 new-api 端点：同步账号无写权限 → 403 E-1505，且库里状态不变
        upstreamCalls.set(0);
        HttpResult readonly = post("/admin/channel-bindings/810002/status", """
                {"target_status":"ENABLED"}
                """, admin);
        assertThat(readonly.status()).as(readonly.body()).isEqualTo(403);
        assertThat(readonly.code()).isEqualTo("E-1505");
        assertThat(upstreamCalls.get()).as("只读端点在本地即可判定，不该打上游").isZero();
        assertThat(jdbc.queryForObject("select status from aap_channel_binding where id = 810002", String.class))
                .isEqualTo("SYNCED");

        // 三段式成功：读前(1) + 写(1) + 回读(1) = 3 次上游调用
        upstreamCalls.set(0);
        HttpResult enabled = post("/admin/channel-bindings/810001/status", """
                {"target_status":"ENABLED"}
                """, admin);
        assertThat(enabled.status()).as(enabled.body()).isEqualTo(200);
        SchemaAssert.assertModel("channel-binding", json(enabled.data()));
        assertThat(enabled.data().path("status").asText()).isEqualTo("ENABLED");
        assertThat(enabled.data().path("last_synced_at").asText()).as("同步时间必须回填").isNotBlank();
        assertThat(enabled.data().path("last_readback_hash").asText()).as("回读摘要必须留痕").isNotBlank();
        assertThat(upstreamCalls.get()).as("读前写后三段式：3 次上游调用").isEqualTo(3);
        assertThat(jdbc.queryForObject("select status from aap_channel_binding where id = 810001", String.class))
                .isEqualTo("ENABLED");

        // 同目标状态 → 幂等，不打上游
        upstreamCalls.set(0);
        HttpResult idempotent = post("/admin/channel-bindings/810004/status", """
                {"target_status":"ENABLED"}
                """, admin);
        assertThat(idempotent.status()).as(idempotent.body()).isEqualTo(200);
        assertThat(idempotent.data().path("status").asText()).isEqualTo("ENABLED");
        assertThat(upstreamCalls.get()).as("同目标状态是幂等重放，不该打上游").isZero();

        // 回读不一致：上游写入未生效 → 502 E-1501，且不得把库里状态改成成功
        writeApplies = false;
        HttpResult mismatch = post("/admin/channel-bindings/810004/status", """
                {"target_status":"DISABLED"}
                """, admin);
        assertThat(mismatch.status()).as(mismatch.body()).isEqualTo(502);
        assertThat(mismatch.code()).isEqualTo("E-1501");
        assertThat(jdbc.queryForObject("select status from aap_channel_binding where id = 810004", String.class))
                .as("回读不一致绝不谎报成功").isEqualTo("ENABLED");
    }

    // ------------------------------------------------------------------ ADM-S06

    @Test
    @DisplayName("ADM-S06 上游模型清单：未配置端点 502 E-1501、上游 401/403 → 403 E-1505、正常返回逐条符合 model-info")
    void upstreamModels() throws Exception {
        String admin = techOps();

        HttpResult none = get("/admin/sync/models/upstream", admin);
        assertThat(none.status()).as("没有可用 new-api 端点时无法读上游：%s", none.body()).isEqualTo(502);
        assertThat(none.code()).isEqualTo("E-1501");

        String baseUrl = startUpstream();
        insertEndpoint(840001L, baseUrl, false, "sk-fixture-not-a-secret");
        modelsStatus = 403;
        HttpResult denied = get("/admin/sync/models/upstream", admin);
        assertThat(denied.status()).as(denied.body()).isEqualTo(403);
        assertThat(denied.code()).isEqualTo("E-1505");

        modelsStatus = 500;
        HttpResult broken = get("/admin/sync/models/upstream", admin);
        assertThat(broken.status()).as(broken.body()).isEqualTo(502);
        assertThat(broken.code()).isEqualTo("E-1501");

        modelsStatus = 200;
        HttpResult ok = get("/admin/sync/models/upstream", admin);
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(ok.body());
        JsonNode models = ok.data().path("models");
        assertThat(models.size()).isEqualTo(2);
        for (JsonNode model : models) {
            SchemaAssert.assertModel("model-info", json(model));
        }
        assertThat(models.get(0).path("model_name").asText()).isEqualTo("gpt-4o");
        assertThat(models.get(0).path("owned_by").asText()).isEqualTo("openai");
        assertThat(models.get(0).path("enabled").asBoolean()).isTrue();
        assertThat(models.get(1).path("model_name").asText()).isEqualTo("claude-3-5-sonnet");
        assertThat(models.get(1).path("enabled").asBoolean()).isFalse();
    }

    // ------------------------------------------------------------------ 权限

    @Test
    @DisplayName("ADM-S01…06 权限：仅 TECH_OPS/SUPER_ADMIN；运营商务与供应商 403 E-1901、未认证 401 E-1902")
    void permissions() {
        String supplier = supplierToken();
        String techOps = techOps();
        String superAdmin = adminToken(970102L, "SUPER_ADMIN");
        String bizOperator = adminToken(970103L, "BIZ_OPERATOR");
        insertBinding(810001, "AAP-TEST-1", "SYNCED", null, null, "2026-09-18T01:00:00Z");
        insertTask(820001, "SY202609180001", 810001L, "ENABLE", "FAILED", 1, null, null, "2026-09-18T01:00:00Z");

        assertThat(get("/admin/sync/tasks", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/sync/tasks", superAdmin).status()).isEqualTo(200);
        assertThat(get("/admin/channel-bindings", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/sync/models/upstream", techOps).status()).as("未配置端点 → 502 E-1501").isEqualTo(502);

        HttpResult bizList = get("/admin/sync/tasks", bizOperator);
        assertThat(bizList.status()).as("运营商务不参与同步运维").isEqualTo(403);
        assertThat(bizList.code()).isEqualTo("E-1901");
        HttpResult bizRetry = post("/admin/sync/tasks/820001/retry", null, bizOperator);
        assertThat(bizRetry.status()).isEqualTo(403);
        assertThat(bizRetry.code()).isEqualTo("E-1901");
        HttpResult bizStatus = post("/admin/channel-bindings/810001/status", """
                {"target_status":"ENABLED"}
                """, bizOperator);
        assertThat(bizStatus.status()).isEqualTo(403);
        assertThat(bizStatus.code()).isEqualTo("E-1901");

        HttpResult supplierDenied = get("/admin/channel-bindings", supplier);
        assertThat(supplierDenied.status()).as(supplierDenied.body()).isEqualTo(403);
        assertThat(supplierDenied.code()).isEqualTo("E-1901");
        assertThat(get("/admin/sync/tasks").status()).isEqualTo(401);
        assertThat(post("/admin/sync/tasks/820001/retry", null, null).status()).isEqualTo(401);
    }
}
