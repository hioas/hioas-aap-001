package com.hioas.aap.sync;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.detection.DetectionService;
import com.hioas.aap.detection.ProbeScoring;
import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * 上架同步闭环（ADM-S07 / ADM-S08 / ADM-S09）验收 —— M11 的**写入侧**。
 *
 * <p>为什么需要这三个端点（运行态实测证据）：`aap_newapi_endpoint` / `aap_sync_task` /
 * `aap_channel_binding` / `aap_sync_log` 四表在 dev 库**全部 0 行**，且全仓零 {@code insert into}
 * 这三张表 ⇒ 既有 S01–S06 是作用在「永远为空的表」上的运维接口，「编译确认 → 建渠道 → 写价 →
 * 回读 → 上架」没有写入侧，供应商进件流水线断在最后一步（业务闭环缺口，决策 D-SYNC-03）。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.4（ADM-S07/08/09）+
 * `.calicat/prd/11-同步与用量统计PRD.md` §3（渠道字段映射 / 幂等键 / 状态机 / 读前写后三段式 /
 * 重试退避）+ §5（回读不一致转人工，**不谎报成功**）+ `21-验收标准.md`（AC-34 回读一致、AC-50 E-1505）+
 * `01-PRD总览.md` §4（供应商生命周期末态 `PUBLISHED`）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>登记端点响应**永不回明文 api_key**（与凭证脱敏同一条红线）</li>
 *   <li>草稿/未确认的编译产物**禁止写入 new-api**（闸门③，{@code E-1407}）</li>
 *   <li>执行走**读前写后三段式**：读现值 → 写 → 回读比对；不一致 → 502 {@code E-1501}
 *       且**不把库内状态改成成功**</li>
 *   <li>幂等键按 PRD §3.2：建渠道 {@code sha256(provider_id|ADD_CHANNEL|channel_name)} ——
 *       同参数重复发起返回**既有任务**，不新增行</li>
 *   <li>端点标记 {@code readonly} 时的写操作 = {@code E-1505}（同步账号无写权限）</li>
 * </ul>
 */
class SyncPublishContractTest extends ApiTestBase {

    private static final String PHONE = "13800000141";
    private static final String ENDPOINT_KEY = "stub-sync-key-not-a-secret";
    private static final AtomicInteger KEY_SEQ = new AtomicInteger();

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    @Autowired
    private CryptoService cryptoService;

    @Autowired
    private DetectionService detectionService;

    private HttpServer upstream;
    private final List<String> upstreamCalls = Collections.synchronizedList(new ArrayList<>());
    private final List<String> upstreamBodies = Collections.synchronizedList(new ArrayList<>());
    private volatile int channelStatus = 1;
    private volatile boolean writeApplies = true;
    private volatile int writeHttpStatus = 200;
    private volatile String optionValue = "";

    @AfterEach
    void stopUpstream() {
        if (upstream != null) {
            upstream.stop(0);
            upstream = null;
        }
    }

    // ------------------------------------------------------------------ 上游桩

    /** 最小 new-api 桩：模型清单 / 建渠道 / 回读渠道 / 写 option（记录每次调用体供断言）。 */
    private String startUpstream() throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/models", exchange -> {
            upstreamCalls.add("GET /models");
            respond(exchange, 200, "{\"data\":[{\"id\":\"gpt-4o\",\"owned_by\":\"openai\"}]}");
        });
        upstream.createContext("/api/channel", exchange -> {
            String method = exchange.getRequestMethod();
            upstreamCalls.add(method + " /api/channel");
            String requested = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            if (!requested.isBlank()) {
                upstreamBodies.add(requested);
            }
            if ("GET".equalsIgnoreCase(method)) {
                respond(exchange, 200, "{\"success\":true,\"data\":{\"id\":777,\"name\":\"AAP-STUB-001\","
                        + "\"status\":" + channelStatus + "}}");
                return;
            }
            if (writeHttpStatus != 200) {
                respond(exchange, writeHttpStatus, "{\"success\":false,\"message\":\"denied\"}");
                return;
            }
            if (writeApplies && requested.contains("\"status\":2")) {
                channelStatus = 2;
            }
            respond(exchange, 200, "{\"success\":true,\"message\":\"\",\"data\":{\"id\":777}}");
        });
        upstream.createContext("/api/option", exchange -> {
            upstreamCalls.add(exchange.getRequestMethod() + " /api/option");
            String requested = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            if (!requested.isBlank()) {
                upstreamBodies.add(requested);
                optionValue = requested;
            }
            respond(exchange, 200, "{\"success\":true,\"message\":\"\"}");
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
                values (?, ?, 'x', '同步验收', ?, 'ACTIVE')
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
        return adminToken(980501L, "TECH_OPS");
    }

    private String superAdmin() {
        return adminToken(980502L, "SUPER_ADMIN");
    }

    // ------------------------------------------------------------------ 夹具（走真实链路）

    private long providerId() {
        Long id = jdbc.queryForObject("select max(id) from aap_provider", Long.class);
        return id == null ? 0L : id;
    }

    /**
     * 把一个新供应商推到「报价 APPROVED + 编译产物 CONFIRMED」——即上架的前置态。
     * 全部走真实接口/服务（与 CompilationContractTest 同路径），不放宽任何断言。
     */
    private long confirmedCompilation(String supplier, String admin) throws Exception {
        HttpResult credential = post("/credentials", """
                {"alias":"上架凭证","base_url":"%s","api_key":"«redacted:key»%06d","primary_flag":true,
                 "model_list":[{"model_name":"gpt-4o"}]}
                """.formatted(startUpstream(), KEY_SEQ.incrementAndGet()), supplier);
        assertThat(credential.status()).as(credential.body()).isEqualTo(200);
        String credentialId = credential.data().path("id").asText();

        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, supplier);
        assertThat(precheck.status()).as(precheck.body()).isEqualTo(200);
        detectionService.recordProbeResults(Long.valueOf(precheck.data().path("job_id").asText()), List.of(
                ProbeScoring.scoreTtft(List.of(200, 205, 210)),
                ProbeScoring.scoreThroughput(82.4),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 95.0, "tokenizer", 93.0,
                        "self_awareness", 90.0, "probability", 85.0, "context", 80.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=TestCA")), Map.of(), Map.of());

        HttpResult quote = post("/quotes", """
                {"name":"上架报价","credential_id":"%s","currency":"USD"}
                """.formatted(credentialId), supplier);
        assertThat(quote.status()).as(quote.body()).isEqualTo(200);
        String quoteId = quote.data().path("quote_id").asText();
        String itemId = post("/quotes/" + quoteId + "/items", """
                {"items":[{"model_name":"gpt-4o"}]}
                """, supplier).data().path("items").get(0).path("item_id").asText();
        HttpResult priced = put("/quotes/items/" + itemId, """
                {"input_price":2.5,"output_price":15}
                """, supplier);
        assertThat(priced.status()).as(priced.body()).isEqualTo(200);

        jdbc.update("update aap_quote set status = 'APPROVED' where id = ?::bigint", quoteId);
        HttpResult compiled = post("/admin/quotes/" + quoteId + "/compile", null, admin);
        assertThat(compiled.status()).as(compiled.body()).isEqualTo(200);
        String compilationId = compiled.data().path("compilation_id").asText();
        assertThat(post("/admin/compilations/" + compilationId + "/verify", null, admin).status()).isEqualTo(200);
        HttpResult confirmed = post("/admin/compilations/" + compilationId + "/confirm", null, admin);
        assertThat(confirmed.status()).as(confirmed.body()).isEqualTo(200);
        assertThat(confirmed.data().path("gate_status").asText()).isEqualTo("CONFIRMED");
        return Long.parseLong(compilationId);
    }

    private String registerEndpoint(String admin, boolean readonly) throws Exception {
        String base = startUpstream();
        HttpResult registered = post("/admin/newapi-endpoints", """
                {"name":"本地 new-api","base_url":"%s","api_key":"%s","readonly":%s}
                """.formatted(base, ENDPOINT_KEY, readonly), admin);
        assertThat(registered.status()).as(registered.body()).isEqualTo(200);
        return registered.data().path("id").asText();
    }

    // ------------------------------------------------------------------ ADM-S07

    @Test
    @DisplayName("ADM-S07 登记 new-api 端点：超管成功、响应不回明文 key、库里只存密文、运营无权（E-1901）")
    void registerEndpointStoresCipherOnly() throws Exception {
        String admin = superAdmin();
        String base = startUpstream();

        HttpResult registered = post("/admin/newapi-endpoints", """
                {"name":"本地 new-api","base_url":"%s","api_key":"%s","readonly":false}
                """.formatted(base, ENDPOINT_KEY), admin);
        assertThat(registered.status()).as(registered.body()).isEqualTo(200);
        SchemaAssert.assertModel("newapi-endpoint", json(registered.data()));
        assertThat(registered.data().path("base_url").asText()).isEqualTo(base);
        assertThat(registered.data().path("readonly").asBoolean()).isFalse();
        assertThat(registered.data().path("status").asText()).isEqualTo("ACTIVE");
        // 红线：响应体任何位置都不得出现明文 key（含 details/未知字段）
        assertThat(registered.body()).doesNotContain(ENDPOINT_KEY);
        assertThat(registered.data().path("api_key_mask").asText()).isNotBlank();

        String cipher = jdbc.queryForObject("select api_key_cipher from aap_newapi_endpoint where id = ?::bigint",
                String.class, registered.data().path("id").asText());
        assertThat(cipher).isNotNull().isNotEqualTo(ENDPOINT_KEY);
        assertThat(cryptoService.decrypt(cipher)).isEqualTo(ENDPOINT_KEY);

        // 运营（TECH_OPS）不得登记同步账号凭据
        HttpResult denied = post("/admin/newapi-endpoints", """
                {"name":"x","base_url":"%s","api_key":"%s"}
                """.formatted(base, ENDPOINT_KEY), techOps());
        assertThat(denied.status()).isEqualTo(403);
        assertThat(denied.code()).isEqualTo("E-1901");

        // 参数缺失 → E-1001（字段级定位）
        HttpResult invalid = post("/admin/newapi-endpoints", """
                {"name":"x"}
                """, admin);
        assertThat(invalid.status()).isEqualTo(400);
        assertThat(invalid.code()).isEqualTo("E-1001");
    }

    // ------------------------------------------------------------------ ADM-S08

    @Test
    @DisplayName("ADM-S08 发起上架同步：无编译产物/未确认拒绝（E-1407）、供应商不存在（E-1406）、参数缺失（E-1001）")
    void createTaskGuardsUnconfirmedCompilation() throws Exception {
        String supplier = supplierToken();
        String admin = techOps();
        long providerId = providerId();

        String base = startUpstream();
        assertThat(post("/admin/newapi-endpoints", """
                {"name":"本地 new-api","base_url":"%s","api_key":"%s","readonly":false}
                """.formatted(base, ENDPOINT_KEY), superAdmin()).status()).isEqualTo(200);

        // 参数缺失
        HttpResult missing = post("/admin/sync/tasks", """
                {}
                """, admin);
        assertThat(missing.status()).isEqualTo(400);
        assertThat(missing.code()).isEqualTo("E-1001");

        // 供应商不存在
        HttpResult noProvider = post("/admin/sync/tasks", """
                {"provider_id":"999999999"}
                """, admin);
        assertThat(noProvider.status()).isEqualTo(404);
        assertThat(noProvider.code()).isEqualTo("E-1406");

        // 该供应商尚无任何编译产物 → 未确认禁止写入
        HttpResult noCompilation = post("/admin/sync/tasks", """
                {"provider_id":"%d"}
                """.formatted(providerId), admin);
        assertThat(noCompilation.status()).isEqualTo(409);
        assertThat(noCompilation.code()).isEqualTo("E-1407");

        // 造到 CONFIRMED 之前先拦：编译完成但未确认（gate_status=COMPILED）同样拒绝
        long compilationId = confirmedCompilation(supplier, admin);
        jdbc.update("update aap_compiled_expression set gate_status = 'COMPILED', status = 'COMPILED',"
                + " publish_blocked = true, confirmed_at = null where id = ?", compilationId);
        HttpResult unconfirmed = post("/admin/sync/tasks", """
                {"provider_id":"%d"}
                """.formatted(providerId), admin);
        assertThat(unconfirmed.status()).isEqualTo(409);
        assertThat(unconfirmed.code()).isEqualTo("E-1407");
    }

    @Test
    @DisplayName("ADM-S08 发起上架同步：产出 PENDING 任务 + 明细（建渠道 + 逐模型写价），幂等重复发起复用同一任务")
    void createTaskIsIdempotentAndListsOperations() throws Exception {
        String supplier = supplierToken();
        String admin = techOps();
        long providerId = providerId();
        long compilationId = confirmedCompilation(supplier, admin);
        registerEndpoint(superAdmin(), false);

        HttpResult created = post("/admin/sync/tasks", """
                {"provider_id":"%d","compilation_id":"%d"}
                """.formatted(providerId, compilationId), admin);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        SchemaAssert.assertModel("sync-task", json(created.data()));
        assertThat(created.data().path("status").asText()).isEqualTo("PENDING");
        assertThat(created.data().path("task_no").asText()).startsWith("SY");
        assertThat(created.data().path("compilation_id").asText()).isEqualTo(String.valueOf(compilationId));
        assertThat(created.data().path("operations").size()).isEqualTo(2);
        assertThat(created.data().path("operations").get(0).path("operation").asText()).isEqualTo("ADD_CHANNEL");
        assertThat(created.data().path("operations").get(1).path("operation").asText()).isEqualTo("WRITE_EXPR");

        // 幂等：同 provider + 同渠道名（缺省生成）再发起 → 复用既有任务，不新增行
        HttpResult again = post("/admin/sync/tasks", """
                {"provider_id":"%d"}
                """.formatted(providerId), admin);
        assertThat(again.status()).as(again.body()).isEqualTo(200);
        assertThat(again.data().path("id").asText()).isEqualTo(created.data().path("id").asText());
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_task", Long.class)).isEqualTo(1L);

        // 任务载荷里不得出现明文上游 key
        String payload = jdbc.queryForObject("select payload::text from aap_sync_task limit 1", String.class);
        assertThat(payload).doesNotContain(ENDPOINT_KEY);
    }

    // ------------------------------------------------------------------ ADM-S09

    @Test
    @DisplayName("ADM-S09 执行上架：建渠道 + 写价 + 回读一致 → 任务 SYNCED、绑定 ENABLED、供应商 PUBLISHED")
    void executePublishesChannelAndProvider() throws Exception {
        String supplier = supplierToken();
        String admin = techOps();
        long providerId = providerId();
        long compilationId = confirmedCompilation(supplier, admin);
        registerEndpoint(superAdmin(), false);

        String taskId = post("/admin/sync/tasks", """
                {"provider_id":"%d","compilation_id":"%d"}
                """.formatted(providerId, compilationId), admin).data().path("id").asText();
        HttpResult executed = post("/admin/sync/tasks/" + taskId + "/execute", """
                {}
                """, admin);
        assertThat(executed.status()).as(executed.body()).isEqualTo(200);
        SchemaAssert.assertModel("sync-task", json(executed.data()));
        assertThat(executed.data().path("status").asText()).isEqualTo("SYNCED");
        assertThat(executed.data().path("readback_equal").asBoolean()).isTrue();

        // 上游确实收到了「建渠道」与「写价」
        assertThat(upstreamCalls).anyMatch(call -> call.startsWith("POST /api/channel"));
        assertThat(upstreamCalls).anyMatch(call -> call.startsWith("PUT /api/option"));
        String channelBody = upstreamBodies.stream().filter(b -> b.contains("base_url")).findFirst().orElse("");
        assertThat(channelBody).contains("AAP-").contains("gpt-4o").contains("aap-provider-" + providerId);
        String exprBody = upstreamBodies.stream().filter(b -> b.contains("billing_expr")).findFirst().orElse("");
        assertThat(exprBody).contains("billing_expr");

        // 库端：渠道绑定 + 供应商生命周期末态
        Map<String, Object> binding = jdbc.queryForMap(
                "select channel_id, channel_name, status, endpoint_id from aap_channel_binding limit 1");
        assertThat(binding.get("channel_id")).isNotNull();
        assertThat(binding.get("channel_name").toString()).startsWith("AAP-");
        assertThat(binding.get("status")).isEqualTo("ENABLED");
        assertThat(jdbc.queryForObject("select status from aap_provider where id = ?", String.class, providerId))
                .isEqualTo("PUBLISHED");
        assertThat(jdbc.queryForObject("select published_at from aap_provider where id = ?",
                OffsetDateTime.class, providerId)).isNotNull();
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_log", Long.class)).isGreaterThan(0L);

        // 幂等重跑：渠道已存在（同名）→ 不重复建渠道、任务仍 SYNCED
        HttpResult rerun = post("/admin/sync/tasks/" + taskId + "/execute", """
                {}
                """, admin);
        assertThat(rerun.status()).as(rerun.body()).isEqualTo(200);
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding", Long.class)).isEqualTo(1L);
    }

    @Test
    @DisplayName("ADM-S09 上游拒绝（401）→ E-1505 且任务转 MANUAL，不谎报成功")
    void executeMarksManualOnUpstreamDenied() throws Exception {
        String supplier = supplierToken();
        String admin = techOps();
        long providerId = providerId();
        long compilationId = confirmedCompilation(supplier, admin);
        registerEndpoint(superAdmin(), false);
        writeHttpStatus = 401;

        String taskId = post("/admin/sync/tasks", """
                {"provider_id":"%d","compilation_id":"%d"}
                """.formatted(providerId, compilationId), admin).data().path("id").asText();
        HttpResult executed = post("/admin/sync/tasks/" + taskId + "/execute", """
                {}
                """, admin);
        assertThat(executed.status()).isEqualTo(403);
        assertThat(executed.code()).isEqualTo("E-1505");
        assertThat(jdbc.queryForObject("select status from aap_sync_task where id = ?::bigint", String.class, taskId))
                .isEqualTo("MANUAL");
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding", Long.class)).isZero();
    }

    @Test
    @DisplayName("ADM-S09 回读不一致 → E-1501 且不把绑定置为成功（不谎报）")
    void executeDoesNotLieWhenReadbackDiffers() throws Exception {
        String supplier = supplierToken();
        String admin = techOps();
        long providerId = providerId();
        long compilationId = confirmedCompilation(supplier, admin);
        registerEndpoint(superAdmin(), false);
        channelStatus = 2;          // 上游回读为 DISABLED，与期望的 ENABLED 不一致

        String taskId = post("/admin/sync/tasks", """
                {"provider_id":"%d","compilation_id":"%d"}
                """.formatted(providerId, compilationId), admin).data().path("id").asText();
        HttpResult executed = post("/admin/sync/tasks/" + taskId + "/execute", """
                {}
                """, admin);
        assertThat(executed.status()).as(executed.body()).isEqualTo(502);
        assertThat(executed.code()).isEqualTo("E-1501");
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding where status = 'ENABLED'",
                Long.class)).isZero();
        assertThat(jdbc.queryForObject("select status from aap_provider where id = ?", String.class, providerId))
                .isNotEqualTo("PUBLISHED");
    }

    @Test
    @DisplayName("ADM-S09 只读端点禁止写入（E-1505）；dry_run 只回预演载荷且零上游写")
    void executeRespectsReadonlyAndDryRun() throws Exception {
        String supplier = supplierToken();
        String admin = techOps();
        long providerId = providerId();
        long compilationId = confirmedCompilation(supplier, admin);
        registerEndpoint(superAdmin(), true);   // readonly=true

        String taskId = post("/admin/sync/tasks", """
                {"provider_id":"%d","compilation_id":"%d"}
                """.formatted(providerId, compilationId), admin).data().path("id").asText();

        HttpResult dry = post("/admin/sync/tasks/" + taskId + "/execute", """
                {"dry_run":true}
                """, admin);
        assertThat(dry.status()).as(dry.body()).isEqualTo(200);
        assertThat(upstreamCalls).noneMatch(call -> call.startsWith("POST /api/channel"));
        assertThat(jdbc.queryForObject("select status from aap_sync_task where id = ?::bigint", String.class, taskId))
                .isEqualTo("PENDING");

        HttpResult denied = post("/admin/sync/tasks/" + taskId + "/execute", """
                {}
                """, admin);
        assertThat(denied.status()).isEqualTo(403);
        assertThat(denied.code()).isEqualTo("E-1505");
    }
}
