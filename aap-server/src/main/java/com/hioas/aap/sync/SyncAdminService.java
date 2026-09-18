package com.hioas.aap.sync;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.support.AuditService;
import com.hioas.aap.sync.SyncViews.BindingStatusRequest;
import com.hioas.aap.sync.SyncViews.ChannelBinding;
import com.hioas.aap.sync.SyncViews.ModelInfo;
import com.hioas.aap.sync.SyncViews.SyncOperation;
import com.hioas.aap.sync.SyncViews.SyncTask;
import com.hioas.aap.sync.SyncViews.UpstreamModels;
import java.nio.charset.StandardCharsets;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;

/**
 * new-api 同步运维（ADM-S01…06）。
 *
 * <p>真源：`02-API接口模型清单.md` §2.4 + `01-ER数据模型.md` §`aap_sync_task`/§`aap_sync_operation`/
 * §`aap_channel_binding`/§`aap_newapi_endpoint` + `11-同步与用量统计PRD.md` §3/§5 +
 * `21-验收标准.md`（AC-34/35/36/42/50）。
 *
 * <p>四条刻意口径：
 * <ol>
 *   <li><b>重试退避与上限（AC-35）</b>：第 1 次立即 → +30s → +2min → +8min → +30min，**≤5 次**；
 *       耗尽转 `MANUAL`（再重试 409 `E-1601`）。鉴权类（上游 401/403）**不重试**直接 `MANUAL`（A8）。</li>
 *   <li><b>{@code E-1505} = new-api 侧拒绝</b>（403「同步接口权限不足」）：端点标记 `readonly` 时的写操作，
 *       或上游返回 401/403。清单只在 S03/S05/S06 列该码——这三条正是会碰上游的接口，
 *       纯 DB 读的 S01/S02/S04 不产生它（见偏差表 `D-SYNC-01`，语义待拍板）。</li>
 *   <li><b>启停走读前写后三段式（AC-34）</b>：读现值 → 写 → 回读比对；不一致**不谎报成功**（502 `E-1501`，
 *       库里状态保持不变，等人工介入）。</li>
 *   <li><b>详情/列表都带 `operations`</b>：子集合只在一处补齐（列表复用详情映射），
 *       否则「主键有、数组空」会被误判为绿（tdd-state 踩坑 22）。</li>
 * </ol>
 *
 * <p>与 T15 的边界：本批次只做**运维接口**（查/重试/启停/读上游），不做同步任务的执行器与调度
 * （谁消费 PENDING 任务、写价如何编译落库属 T09/T15，见偏差表 `D-SYNC-03`）。
 */
@Service
public class SyncAdminService {

    private static final Logger log = LoggerFactory.getLogger(SyncAdminService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 重试上限（PRD §5：1 次立即 + 30s/2m/8m/30m）。 */
    private static final int MAX_ATTEMPTS = 5;

    /** 第 n 次尝试后的退避（n = 1..4；第 5 次耗尽转 MANUAL）。 */
    private static final Duration[] BACKOFF = {
            Duration.ofSeconds(30), Duration.ofMinutes(2), Duration.ofMinutes(8), Duration.ofMinutes(30)};

    /** 允许重试的任务状态：失败与人工介入（SUCCESS/RUNNING/PENDING 无重试语义）。 */
    private static final Set<String> RETRYABLE = Set.of("FAILED", "MANUAL");

    /** 允许启停的渠道状态（PRD §3 状态机：SYNCED → ENABLED ⇄ DISABLED）。 */
    private static final Set<String> SWITCHABLE = Set.of("SYNCED", "ENABLED", "DISABLED");

    private static final String TASK_COLUMNS = """
            id, task_no, binding_id, provider_id, compilation_id, task_type, status,
            payload::text as payload, idempotency_key, attempt_count, next_retry_at, last_error, readback_equal,
            created_at, updated_at
            """;

    private static final String OPERATION_COLUMNS = """
            id, operation, request_payload::text as request_payload, response_payload::text as response_payload,
            result, readback_equal, attempt_no, error, created_at
            """;

    private static final String BINDING_COLUMNS = """
            id, provider_id, credential_id, endpoint_id, channel_id, channel_name, tag, group_name,
            priority, weight, models::text as models, status, last_synced_at, last_readback_hash
            """;

    private final JdbcTemplate jdbc;
    private final NewApiSyncClient newApiSyncClient;
    private final SyncAttemptRecorder recorder;
    private final CryptoService cryptoService;
    private final AuditService auditService;

    public SyncAdminService(JdbcTemplate jdbc, NewApiSyncClient newApiSyncClient, SyncAttemptRecorder recorder,
                            CryptoService cryptoService, AuditService auditService) {
        this.jdbc = jdbc;
        this.newApiSyncClient = newApiSyncClient;
        this.recorder = recorder;
        this.cryptoService = cryptoService;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ ADM-S01 / S02

    /** ADM-S01 同步任务列表（`status`/`bindingId` 可选过滤；列表项同样带 operations 明细）。 */
    public PageResult<SyncTask> listTasks(Integer page, Integer pageSize, String status, Long bindingId) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> args = new ArrayList<>();
        if (status != null && !status.isBlank()) {
            where.append(" and upper(status) = upper(?)");
            args.add(status.trim());
        }
        if (bindingId != null) {
            where.append(" and binding_id = ?");
            args.add(bindingId);
        }
        Long total = jdbc.queryForObject("select count(*) from aap_sync_task" + where, Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        List<SyncTask> items = jdbc.query("select " + TASK_COLUMNS + " from aap_sync_task" + where
                + " order by created_at desc, id desc limit ? offset ?", SyncAdminService::mapTask, pageArgs.toArray());
        for (SyncTask item : items) {
            item.operations().addAll(operations(Long.valueOf(item.id())));
        }
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    /** ADM-S02 任务详情（含 operations；不存在 → 404 `E-1406`）。 */
    public SyncTask taskDetail(Long taskId) {
        List<SyncTask> rows = jdbc.query("select " + TASK_COLUMNS
                + " from aap_sync_task where id = ? and deleted = false", SyncAdminService::mapTask, taskId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "同步任务不存在");
        }
        SyncTask task = rows.get(0);
        task.operations().addAll(operations(taskId));
        return task;
    }

    // ------------------------------------------------------------------ ADM-S03

    /**
     * ADM-S03 重试：按 PRD §5 退避重排（≤5 次）。
     *
     * <p>执行顺序刻意是「先落库、再抛错」：失败必须留痕（独立事务 {@link SyncAttemptRecorder}），
     * 否则一次 502 之后任务表与操作明细都查不到这次尝试。
     */
    public SyncTask retry(AuthPrincipal principal, Long taskId) {
        SyncTask before = taskDetail(taskId);
        if (!RETRYABLE.contains(before.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "只有 FAILED / MANUAL 状态的任务可以重试（当前：" + before.status() + "）");
        }
        int attempt = before.attemptCount() + 1;
        if (attempt > MAX_ATTEMPTS) {
            throw new ApiException(ErrorCode.E_1601,
                    "重试次数已达上限 " + MAX_ATTEMPTS + " 次（退避耗尽），请人工处理或新建同步任务");
        }
        log.info("同步任务重试 task_no={} attempt={} 原状态={}", before.taskNo(), attempt, before.status());
        Long actor = principal == null ? null : principal.accountId();
        String requestPayload = JsonCodec.toJson(Map.of(
                "attempt_no", attempt, "task_type", String.valueOf(before.taskType()),
                "binding_id", String.valueOf(before.bindingId())));

        Endpoint endpoint = endpointForBinding(toId(before.bindingId()));
        if (endpoint == null) {
            // 没有可探测的 new-api 端点（如编译/用量类任务）：直接重新入队，立即执行
            return reArm(taskId, before, attempt, actor, requestPayload, null,
                    "重试已入队（无 new-api 端点可探测，立即执行）");
        }

        NewApiSyncClient.Probe probe = newApiSyncClient.get(endpoint.baseUrl(), endpoint.apiKey(), "/models");
        if (probe.ok()) {
            return reArm(taskId, before, attempt, actor, requestPayload, true,
                    "重试已入队（new-api 可达，立即执行）");
        }
        if (probe.denied()) {
            String lastError = "E-1505 new-api 拒绝同步请求（HTTP " + probe.httpStatus() + "）";
            recorder.recordAttempt(taskId, attempt, "MANUAL", null, lastError, false, "RETRY", "FAILED", "E-1505",
                    requestPayload, probePayload(probe));
            audit(actor, taskId, "同步任务 " + before.taskNo() + " 重试被上游拒绝（HTTP " + probe.httpStatus()
                    + "），已转 MANUAL");
            throw new ApiException(ErrorCode.E_1505,
                    "new-api 拒绝（HTTP " + probe.httpStatus() + "）：同步账号权限不足，任务已转人工（MANUAL）");
        }

        boolean exhausted = attempt >= MAX_ATTEMPTS;
        OffsetDateTime nextRetryAt = exhausted ? null : OffsetDateTime.now(ZoneOffset.UTC).plus(BACKOFF[attempt - 1]);
        String lastError = probe.reachable()
                ? "E-1501 同步失败（new-api 返回 HTTP " + probe.httpStatus() + "）"
                : "E-1501 同步失败（new-api 不可达）";
        recorder.recordAttempt(taskId, attempt, exhausted ? "MANUAL" : "FAILED", nextRetryAt, lastError, false,
                "RETRY", "FAILED", "E-1501", requestPayload, probePayload(probe));
        audit(actor, taskId, "同步任务 " + before.taskNo() + " 第 " + attempt + " 次重试失败：" + lastError
                + (exhausted ? "，退避耗尽转 MANUAL" : "，下次重试 " + nextRetryAt));
        throw new ApiException(ErrorCode.E_1501, lastError + "（第 " + attempt + " 次尝试，"
                + (exhausted ? "已转人工 MANUAL）" : "下次重试 " + nextRetryAt + "）"));
    }

    private SyncTask reArm(Long taskId, SyncTask before, int attempt, Long actor, String requestPayload,
                           Boolean readbackEqual, String summary) {
        recorder.recordAttempt(taskId, attempt, "PENDING", null, null, readbackEqual, "RETRY", "PENDING", null,
                requestPayload, readbackEqual == null ? null : "{\"http_status\":200}");
        audit(actor, taskId, "同步任务 " + before.taskNo() + "：" + summary);
        return taskDetail(taskId);
    }

    private void audit(Long actor, Long taskId, String summary) {
        auditService.record(AuditService.AuditAction.SYNC_EXECUTE, "sync_task", taskId, summary);
    }

    private static String probePayload(NewApiSyncClient.Probe probe) {
        return JsonCodec.toJson(Map.of(
                "reachable", probe.reachable(),
                "http_status", probe.httpStatus()));
    }

    // ------------------------------------------------------------------ ADM-S04 / S05

    /** ADM-S04 渠道绑定列表（分页）。 */
    public PageResult<ChannelBinding> listBindings(Integer page, Integer pageSize) {
        PageQuery query = PageQuery.of(page, pageSize);
        Long total = jdbc.queryForObject("select count(*) from aap_channel_binding where deleted = false", Long.class);
        List<ChannelBinding> items = jdbc.query("select " + BINDING_COLUMNS
                + " from aap_channel_binding where deleted = false order by created_at desc, id desc limit ? offset ?",
                SyncAdminService::mapBinding, query.pageSize(), query.offset());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    /** 渠道绑定详情（不存在 → 404 `E-1406`）。 */
    public ChannelBinding bindingDetail(Long bindingId) {
        List<ChannelBinding> rows = jdbc.query("select " + BINDING_COLUMNS
                + " from aap_channel_binding where id = ? and deleted = false",
                SyncAdminService::mapBinding, bindingId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "渠道绑定不存在");
        }
        return rows.get(0);
    }

    /**
     * ADM-S05 渠道启停（读前写后三段式 + 回读一致，AC-34/42）。
     *
     * <p>幂等：目标状态与现值相同 → 直接返回，不打上游（PRD §3 幂等键 {@code TAG_STATUS|目标状态}）。
     */
    public ChannelBinding changeBindingStatus(AuthPrincipal principal, Long bindingId, BindingStatusRequest request) {
        String target = validateTargetStatus(request);
        ChannelBinding before = bindingDetail(bindingId);
        if (!SWITCHABLE.contains(before.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "渠道绑定当前状态不允许启停（" + before.status() + "）：需先同步成功（SYNCED）");
        }
        if (target.equals(before.status())) {
            return before;
        }
        Long actor = principal == null ? null : principal.accountId();
        Endpoint endpoint = endpointForBindingRecord(toId(before.endpointId()));
        if (endpoint == null) {
            // 未接 new-api（本地/联调模式）：只改本地状态，不假装做过回读
            updateBinding(bindingId, target, actor, null);
            audit(actor, bindingId, "渠道绑定 " + before.channelName() + " 本地置为 " + target + "（无 new-api 端点）");
            return bindingDetail(bindingId);
        }
        if (endpoint.readonly()) {
            throw new ApiException(ErrorCode.E_1505,
                    "new-api 端点 " + endpoint.id() + " 标记为只读，同步账号无写权限");
        }
        if (before.channelId() == null) {
            throw new ApiException(ErrorCode.E_1601, "渠道尚未同步到 new-api（缺少 channel_id），无法启停");
        }

        String path = "/api/channel/" + before.channelId();
        NewApiSyncClient.Probe readBefore = newApiSyncClient.get(endpoint.baseUrl(), endpoint.apiKey(), path);
        requireUpstreamReadable(readBefore, "读取渠道现值");
        NewApiSyncClient.Probe write = newApiSyncClient.put(endpoint.baseUrl(), endpoint.apiKey(), "/api/channel/",
                JsonCodec.toJson(Map.of("id", before.channelId(), "status", "ENABLED".equals(target) ? 1 : 2)));
        requireUpstreamWrite(write);
        NewApiSyncClient.Probe readAfter = newApiSyncClient.get(endpoint.baseUrl(), endpoint.apiKey(), path);
        requireUpstreamReadable(readAfter, "回读渠道状态");

        String online = channelStatusOf(readAfter.body());
        if (!target.equals(online)) {
            // 回读不一致绝不谎报成功（PRD §5：告警 + 转人工）；
            // 但回读摘要落库，便于运维对比（不把库里状态改成成功）
            updateReadbackHash(bindingId, readAfter.body(), actor);
            audit(actor, bindingId, "渠道绑定 " + before.channelName() + " 回读不一致（目标 " + target
                    + "，上游 " + online + "），已停止置态");
            throw new ApiException(ErrorCode.E_1501,
                    "回读不一致：目标 " + target + "，上游现值 " + (online == null ? "无法解析" : online)
                            + "；已保持库内状态并等待人工介入");
        }
        updateBinding(bindingId, target, actor, readAfter.body());
        audit(actor, bindingId, "渠道绑定 " + before.channelName() + " 置为 " + target + "（读前写后回读一致）");
        return bindingDetail(bindingId);
    }

    private void requireUpstreamReadable(NewApiSyncClient.Probe probe, String action) {
        if (probe.denied()) {
            throw new ApiException(ErrorCode.E_1505,
                    "new-api 拒绝" + action + "（HTTP " + probe.httpStatus() + "）：同步账号权限不足");
        }
        if (!probe.ok()) {
            throw new ApiException(ErrorCode.E_1501, "new-api " + action + "失败（"
                    + (probe.reachable() ? "HTTP " + probe.httpStatus() : "不可达") + "）");
        }
    }

    private void requireUpstreamWrite(NewApiSyncClient.Probe probe) {
        if (probe.denied()) {
            throw new ApiException(ErrorCode.E_1505,
                    "new-api 拒绝渠道启停写入（HTTP " + probe.httpStatus() + "）：同步账号权限不足");
        }
        if (!probe.ok()) {
            throw new ApiException(ErrorCode.E_1501, "new-api 渠道启停失败（"
                    + (probe.reachable() ? "HTTP " + probe.httpStatus() : "不可达") + "）");
        }
    }

    private void updateBinding(Long bindingId, String status, Long actor, String readbackBody) {
        jdbc.update("""
                update aap_channel_binding
                   set status = ?, last_synced_at = now(), last_readback_hash = ?,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and deleted = false
                """, status, readbackBody == null ? null : cryptoService.sha256Hex(readbackBody), actor, bindingId);
    }

    private void updateReadbackHash(Long bindingId, String readbackBody, Long actor) {
        jdbc.update("""
                update aap_channel_binding
                   set last_readback_hash = ?, updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and deleted = false
                """, readbackBody == null ? null : cryptoService.sha256Hex(readbackBody), actor, bindingId);
    }

    /** 上游渠道状态：`{"data":{"status":1|2}}` → ENABLED/DISABLED（无法解析返回 null → 视为不一致）。 */
    private static String channelStatusOf(String body) {
        JsonNode root = JsonCodec.readTree(body);
        if (root == null) {
            return null;
        }
        JsonNode status = root.path("data").path("status");
        if (status.isMissingNode() || status.isNull()) {
            status = root.path("status");
        }
        if (!status.isInt() && !status.isTextual()) {
            return null;
        }
        String value = status.isInt() ? String.valueOf(status.asInt()) : status.asText();
        return switch (value) {
            case "1", "ENABLED" -> "ENABLED";
            case "2", "DISABLED" -> "DISABLED";
            default -> null;
        };
    }

    private static String validateTargetStatus(BindingStatusRequest request) {
        String raw = request == null ? null : request.targetStatus();
        if (raw == null || raw.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "target_status", "目标状态必填（ENABLED 或 DISABLED）");
        }
        String value = raw.trim().toUpperCase(Locale.ROOT);
        if (!"ENABLED".equals(value) && !"DISABLED".equals(value)) {
            throw ApiException.field(ErrorCode.E_1001, "target_status",
                    "目标状态只能是 ENABLED 或 DISABLED：收到 " + raw);
        }
        return value;
    }

    // ------------------------------------------------------------------ ADM-S06

    /** ADM-S06 上游模型清单（读启用中的 new-api 端点；未配置端点 → 502 `E-1501`）。 */
    public UpstreamModels upstreamModels() {
        Endpoint endpoint = activeEndpoint();
        if (endpoint == null) {
            throw new ApiException(ErrorCode.E_1501,
                    "未配置可用的 new-api 端点（aap_newapi_endpoint 无 ACTIVE 记录），无法读取上游模型清单");
        }
        NewApiSyncClient.Probe probe = newApiSyncClient.get(endpoint.baseUrl(), endpoint.apiKey(), "/models");
        if (probe.denied()) {
            throw new ApiException(ErrorCode.E_1505,
                    "new-api 拒绝读取模型清单（HTTP " + probe.httpStatus() + "）：同步账号权限不足");
        }
        if (!probe.ok()) {
            throw new ApiException(ErrorCode.E_1501, "读取上游模型清单失败（"
                    + (probe.reachable() ? "HTTP " + probe.httpStatus() : "不可达") + "）");
        }
        return new UpstreamModels(parseModels(probe.body()));
    }

    /** 上游 `data[]` → ModelInfo（`id` → `model_name`；`owned_by` 同时作为 `vendor` 初值）。 */
    private static List<ModelInfo> parseModels(String body) {
        JsonNode root = JsonCodec.readTree(body);
        JsonNode data = root == null ? null : root.path("data");
        List<ModelInfo> models = new ArrayList<>();
        if (data == null || !data.isArray()) {
            return models;
        }
        for (JsonNode item : data) {
            String name = item.path("id").asText(null);
            if (name == null || name.isBlank()) {
                continue;
            }
            String ownedBy = item.path("owned_by").asText(null);
            JsonNode enabled = item.path("enabled");
            models.add(new ModelInfo(name, ownedBy, ownedBy, enabled.isBoolean() ? enabled.asBoolean() : Boolean.TRUE));
        }
        return models;
    }

    // ------------------------------------------------------------------ 端点解析

    /** 端点快照（base_url + 解密后的 api_key）；api_key 只在本类内部流转，不外泄到视图与日志。 */
    private record Endpoint(Long id, String baseUrl, String apiKey, boolean readonly) {
    }

    /** 由任务反查端点：task.binding_id → binding.endpoint_id → 端点（无绑定/无端点返回 null）。 */
    private Endpoint endpointForBinding(Long bindingId) {
        if (bindingId == null) {
            return null;
        }
        List<Long> endpointIds = jdbc.queryForList(
                "select endpoint_id from aap_channel_binding where id = ? and deleted = false",
                Long.class, bindingId);
        return endpointIds.isEmpty() ? null : endpointForBindingRecord(endpointIds.get(0));
    }

    private Endpoint endpointForBindingRecord(Long endpointId) {
        return endpointId == null ? null : endpoint(endpointId);
    }

    private Endpoint endpoint(Long endpointId) {
        List<Endpoint> rows = jdbc.query("""
                select id, base_url, api_key_cipher, readonly from aap_newapi_endpoint
                 where id = ? and deleted = false and status = 'ACTIVE'
                """, (rs, rowNum) -> new Endpoint(
                rs.getObject("id", Long.class),
                rs.getString("base_url"),
                cryptoService.decrypt(rs.getString("api_key_cipher")),
                rs.getBoolean("readonly")), endpointId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    /** 启用中的 new-api 端点（ADM-S06 用最近一条 ACTIVE）。 */
    private Endpoint activeEndpoint() {
        List<Endpoint> rows = jdbc.query("""
                select id, base_url, api_key_cipher, readonly from aap_newapi_endpoint
                 where deleted = false and status = 'ACTIVE'
                 order by id desc limit 1
                """, (rs, rowNum) -> new Endpoint(
                rs.getObject("id", Long.class),
                rs.getString("base_url"),
                cryptoService.decrypt(rs.getString("api_key_cipher")),
                rs.getBoolean("readonly")));
        return rows.isEmpty() ? null : rows.get(0);
    }

    // ------------------------------------------------------------------ 映射

    private List<SyncOperation> operations(Long taskId) {
        return jdbc.query("select " + OPERATION_COLUMNS
                + " from aap_sync_operation where task_id = ? and deleted = false order by attempt_no, id",
                SyncAdminService::mapOperation, taskId);
    }

    private static SyncTask mapTask(ResultSet rs, int rowNum) throws SQLException {
        Long id = rs.getObject("id", Long.class);
        return new SyncTask(
                id == null ? null : String.valueOf(id),
                id == null ? null : String.valueOf(id),
                rs.getString("task_no"),
                asString(rs.getObject("binding_id", Long.class)),
                asString(rs.getObject("provider_id", Long.class)),
                asString(rs.getObject("compilation_id", Long.class)),
                rs.getString("task_type"),
                rs.getString("status"),
                JsonCodec.readTree(rs.getString("payload")),
                rs.getString("idempotency_key"),
                rs.getObject("attempt_count", Integer.class),
                rfc3339(rs.getObject("next_retry_at", OffsetDateTime.class)),
                rs.getString("last_error"),
                rs.getObject("readback_equal", Boolean.class),
                new ArrayList<>(),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("updated_at", OffsetDateTime.class)));
    }

    private static SyncOperation mapOperation(ResultSet rs, int rowNum) throws SQLException {
        return new SyncOperation(
                asString(rs.getObject("id", Long.class)),
                rs.getString("operation"),
                JsonCodec.readTree(rs.getString("request_payload")),
                JsonCodec.readTree(rs.getString("response_payload")),
                rs.getString("result"),
                rs.getObject("readback_equal", Boolean.class),
                rs.getObject("attempt_no", Integer.class),
                rs.getString("error"),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)));
    }

    private static ChannelBinding mapBinding(ResultSet rs, int rowNum) throws SQLException {
        Long id = rs.getObject("id", Long.class);
        String models = rs.getString("models");
        // channel_id 在库里是 bigint（ER：new-api 渠道号），视图契约是 integer：按 Long 读再收窄，
        // 用 getObject(..., Integer.class) 会抛 "conversion to class java.lang.Integer from int8 not supported"
        // 并在 HTTP 层只表现为 500 E-2001（同 tdd-state 踩坑 13 的聚合 numeric 问题）
        Long channelId = rs.getObject("channel_id", Long.class);
        return new ChannelBinding(
                id == null ? null : String.valueOf(id),
                id == null ? null : String.valueOf(id),
                asString(rs.getObject("provider_id", Long.class)),
                asString(rs.getObject("credential_id", Long.class)),
                asString(rs.getObject("endpoint_id", Long.class)),
                channelId == null ? null : channelId.intValue(),
                rs.getString("channel_name"),
                rs.getString("tag"),
                rs.getString("group_name"),
                rs.getObject("priority", Integer.class),
                rs.getObject("weight", Integer.class),
                models == null ? List.of() : JsonCodec.toStringList(models),
                rs.getString("status"),
                rfc3339(rs.getObject("last_synced_at", OffsetDateTime.class)),
                rs.getString("last_readback_hash"));
    }

    private static String asString(Long value) {
        return value == null ? null : String.valueOf(value);
    }

    /** 视图里的 ID 是 string（对外契约），内部转回 Long。 */
    private static Long toId(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, "id", "不是合法的雪花 ID：" + value);
        }
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }
}
