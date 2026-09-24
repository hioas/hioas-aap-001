package com.hioas.aap.sync;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.OutboundUrlGuard;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.support.AuditService;
import com.hioas.aap.sync.NewApiSyncClient.Probe;
import com.hioas.aap.sync.SyncViews.NewApiEndpoint;
import com.hioas.aap.sync.SyncViews.NewApiEndpointRequest;
import com.hioas.aap.sync.SyncViews.SyncTask;
import com.hioas.aap.sync.SyncViews.SyncTaskCreateRequest;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;

/**
 * new-api 同步的**写入侧**：登记端点（ADM-S07）、发起上架同步（ADM-S08）、执行上架（ADM-S09）。
 *
 * <p>为什么需要它：既有 S01–S06 只覆盖「查任务 / 重试 / 启停 / 读上游」——作用在**永远为空的表**上。
 * 全仓零 {@code insert into aap_newapi_endpoint|aap_sync_task|aap_channel_binding} ⇒
 * 「编译确认 → 建渠道 → 写价 → 回读 → 上架」没有写入侧，供应商进件流水线断在最后一步
 * （决策 D-SYNC-03，见 `.agents/state/aap-decisions.md`）。
 *
 * <p>契约真源：`.calicat/prd/11-同步与用量统计PRD.md` §3（渠道字段映射 / 幂等键 / 状态机 /
 * 读前写后三段式 / 灰度三阶段）+ §5（回读不一致转人工；鉴权类不重试）+ `21-验收标准.md`
 * （AC-34 回读一致、AC-50 权限不足 E-1505）+ `01-PRD总览` §4（供应商生命周期末态 `PUBLISHED`）。
 *
 * <p>三个刻意的设计取舍：
 * <ol>
 *   <li>**本类不含事务**：它要做出站 HTTP（建渠道/写价/回读），事务里做外部 I/O 会拉长持锁时间
 *       （项目既有巡检项 A3）。所有落库集中在 {@link SyncPublishRecorder} 的事务方法里。</li>
 *   <li>**闸门③绝不绕过**：没有 `gate_status=CONFIRMED` 且 `publish_blocked=false` 的编译产物一律
 *       {@code E-1407} —— 这是 PRD 的红线（「编译产物未经模拟求值校验，禁止写入 new-api 生产环境」）。</li>
 *   <li>**回读不一致不谎报**：库内状态保持「未上架」，任务置 `PARTIAL` 并留对比摘要，由人工介入
 *       （PRD §5 降级动作）。</li>
 * </ol>
 */
@Service
public class SyncPublishService {

    private static final Logger log = LoggerFactory.getLogger(SyncPublishService.class);

    /** 写价落点：new-api 的 option key（PRD §3 集成路径 `billing_setting.billing_expr[model]`）。 */
    private static final String OPTION_KEY = "billing_setting.billing_expr";
    private static final String OPERATION_ADD_CHANNEL = "ADD_CHANNEL";
    private static final String OPERATION_WRITE_EXPR = "WRITE_EXPR";
    private static final String MODE_REVIEW_THEN_APPLY = "REVIEW_THEN_APPLY";
    private static final String MODE_DRY_RUN = "DRY_RUN";
    private static final DateTimeFormatter RFC3339 =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private final JdbcTemplate jdbc;
    private final NewApiSyncClient newApiSyncClient;
    private final SyncPublishRecorder recorder;
    private final SyncAdminService syncAdminService;
    private final CryptoService cryptoService;
    private final OutboundUrlGuard outboundUrlGuard;
    private final AuditService auditService;

    public SyncPublishService(JdbcTemplate jdbc, NewApiSyncClient newApiSyncClient, SyncPublishRecorder recorder,
                              SyncAdminService syncAdminService, CryptoService cryptoService,
                              OutboundUrlGuard outboundUrlGuard, AuditService auditService) {
        this.jdbc = jdbc;
        this.newApiSyncClient = newApiSyncClient;
        this.recorder = recorder;
        this.syncAdminService = syncAdminService;
        this.cryptoService = cryptoService;
        this.outboundUrlGuard = outboundUrlGuard;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ ADM-S07

    /** 登记（或追加）一个 new-api 同步端点；`api_key` 加密落库，响应只回掩码。 */
    public NewApiEndpoint registerEndpoint(AuthPrincipal principal, NewApiEndpointRequest request) {
        String name = requireText(request == null ? null : request.name(), "name", 64);
        String baseUrl = requireText(request == null ? null : request.baseUrl(), "base_url", 255);
        String apiKey = requireText(request == null ? null : request.apiKey(), "api_key", 512);
        boolean readonly = request != null && Boolean.TRUE.equals(request.readonly());
        outboundUrlGuard.verify(baseUrl);   // SSRF：登记即守（内网/非 http(s) 一律拒）
        Long actor = principal == null ? null : principal.accountId();
        long endpointId = recorder.insertEndpoint(name, baseUrl, cryptoService.encrypt(apiKey), readonly, actor);
        auditService.record(AuditService.AuditAction.CONFIG_PUBLISH, "newapi_endpoint", endpointId,
                "登记 new-api 同步端点 " + name + "（readonly=" + readonly + "）");
        log.info("new-api 端点登记 endpoint_id={} readonly={}", endpointId, readonly);
        return endpointView(endpointId);
    }

    // ------------------------------------------------------------------ ADM-S08

    /**
     * 发起上架同步：解析编译产物 → 建 `PENDING` 任务 + 待执行明细。
     *
     * <p>幂等（PRD §3.2）：键 = `sha256(provider_id|ADD_CHANNEL|channel_name)`；键相同即**返回既有任务**，
     * 不新增行（`aap_sync_task` 上有 `uq_sync_idempotency` 唯一索引兜底）。
     */
    public SyncTask createTask(AuthPrincipal principal, SyncTaskCreateRequest request) {
        Long providerId = requiredId(request == null ? null : request.providerId(), "provider_id");
        Long actor = principal == null ? null : principal.accountId();
        Map<String, Object> provider = providerRow(providerId);
        Compilation compilation = resolveCompilation(providerId, request.compilationId());
        List<ModelExpr> models = modelExpressions(compilation.id());
        if (models.isEmpty()) {
            throw new ApiException(ErrorCode.E_1407, "编译产物里没有任何模型表达式，禁止写入 new-api");
        }
        CredentialRow credential = activeCredential(providerId);

        String channelName = request.channelName() == null || request.channelName().isBlank()
                ? defaultChannelName(providerId, String.valueOf(provider.get("short_label")))
                : request.channelName().trim();
        String idempotencyKey = cryptoService.sha256Hex(
                providerId + "|" + OPERATION_ADD_CHANNEL + "|" + channelName);
        List<Long> existing = jdbc.queryForList(
                "select id from aap_sync_task where idempotency_key = ? and deleted = false order by id limit 1",
                Long.class, idempotencyKey);
        if (!existing.isEmpty()) {
            log.info("上架同步任务已存在（幂等复用）task_id={} channel={}", existing.get(0), channelName);
            return syncAdminService.taskDetail(existing.get(0));
        }

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("provider_id", String.valueOf(providerId));
        payload.put("compilation_id", String.valueOf(compilation.id()));
        payload.put("channel_name", channelName);
        payload.put("credential_id", String.valueOf(credential.id()));
        payload.put("models", models.stream().map(ModelExpr::modelName).toList());
        payload.put("source_hash", compilation.sourceHash());
        payload.put("mode", normalizeMode(request.mode()));

        long taskId = recorder.createTaskWithOperations(providerId, compilation.id(), null, OPERATION_ADD_CHANNEL,
                JsonCodec.toJson(payload), idempotencyKey,
                JsonCodec.toJson(Map.of("channel_name", channelName, "model_count", models.size())),
                List.of(OPERATION_ADD_CHANNEL, OPERATION_WRITE_EXPR), actor);
        auditService.record(AuditService.AuditAction.SYNC_EXECUTE, "sync_task", taskId,
                "发起上架同步：供应商 " + providerId + "，渠道 " + channelName + "，模型 " + models.size() + " 个");
        log.info("上架同步任务创建 task_id={} provider_id={} channel={}", taskId, providerId, channelName);
        return syncAdminService.taskDetail(taskId);
    }

    // ------------------------------------------------------------------ ADM-S09

    /**
     * 执行上架：读前写后三段式。
     *
     * <p>顺序：建渠道（`POST /api/channel/`）→ 落绑定 → 写价（合并写 `billing_setting.billing_expr`）→
     * 回读渠道（`GET /api/channel/{id}`）比对；一致才把绑定置 `ENABLED`、供应商置 `PUBLISHED`。
     */
    public SyncTask execute(AuthPrincipal principal, long taskId, boolean dryRun) {
        Map<String, Object> row = taskRow(taskId);
        Long actor = principal == null ? null : principal.accountId();
        String status = text(row.get("status"));
        if ("SYNCING".equals(status)) {
            throw new ApiException(ErrorCode.E_1601, "同步任务正在执行中，请勿并发触发");
        }
        Map<String, Object> payload = JsonCodec.toMap(text(row.get("payload")));
        Long providerId = toLong(payload.get("provider_id"));
        Long credentialId = toLong(payload.get("credential_id"));
        String channelName = text(payload.get("channel_name"));
        List<String> models = JsonCodec.toStringList(JsonCodec.toJson(payload.get("models")));
        if (providerId == null || channelName == null || models.isEmpty()) {
            throw new ApiException(ErrorCode.E_1601, "同步任务载荷不完整（缺 provider_id/channel_name/models），无法执行");
        }
        if (dryRun) {
            // 预演：零上游写、零库写（任务保持 PENDING）
            log.info("上架同步预演 task_id={} channel={} 模型 {}", taskId, channelName, models.size());
            return syncAdminService.taskDetail(taskId);
        }

        Endpoint endpoint = endpointForTask(toLong(row.get("binding_id")));
        if (endpoint == null) {
            throw new ApiException(ErrorCode.E_1501,
                    "未配置可用的 new-api 端点（aap_newapi_endpoint 无 ACTIVE 记录），无法执行上架");
        }
        if (endpoint.readonly()) {
            throw new ApiException(ErrorCode.E_1505,
                    "new-api 端点 " + endpoint.id() + " 标记为只读，同步账号无写权限");
        }
        CredentialRow credential = credentialRow(credentialId);
        List<ModelExpr> expressions = modelExpressions(toLong(row.get("compilation_id")));
        int attempt = (int) (toLong(row.get("attempt_count")) == null ? 0L : toLong(row.get("attempt_count"))) + 1;

        // ① 建渠道（PRD §3.1 字段映射）
        Map<String, Object> channel = new LinkedHashMap<>();
        channel.put("name", channelName);
        channel.put("key", credential.apiKey());
        channel.put("base_url", credential.baseUrl());
        channel.put("models", String.join(",", models));
        channel.put("group", "default");
        channel.put("tag", "aap-provider-" + providerId);
        channel.put("status", 1);
        String channelBody = JsonCodec.toJson(channel);
        Probe created = newApiSyncClient.post(endpoint.baseUrl(), endpoint.apiKey(), "/api/channel/", channelBody);
        if (created.denied()) {
            String error = "E-1505 new-api 拒绝建渠道（HTTP " + created.httpStatus() + "）";
            recorder.markTaskTerminal(taskId, "MANUAL", null, error, attempt, OPERATION_ADD_CHANNEL, "FAILED",
                    "E-1505", null, null, actor);
            auditService.record(AuditService.AuditAction.SYNC_EXECUTE, "sync_task", taskId, error + "，任务转人工");
            throw new ApiException(ErrorCode.E_1505, "new-api 拒绝建渠道（HTTP " + created.httpStatus() + "）：同步账号权限不足，任务已转人工");
        }
        if (!created.ok()) {
            String error = "E-1501 建渠道失败（" + (created.reachable() ? "HTTP " + created.httpStatus() : "不可达") + "）";
            recorder.markTaskTerminal(taskId, "FAILED", null, error, attempt, OPERATION_ADD_CHANNEL, "FAILED",
                    "E-1501", null, null, actor);
            throw new ApiException(ErrorCode.E_1501, error);
        }
        Long channelId = createdChannelId(created.body());
        if (channelId == null) {
            String error = "E-1501 建渠道响应缺少 data.id";
            recorder.markTaskTerminal(taskId, "FAILED", null, error, attempt, OPERATION_ADD_CHANNEL, "FAILED",
                    "E-1501", null, null, actor);
            throw new ApiException(ErrorCode.E_1501, error + "：无法与 new-api 对账，任务已置 FAILED");
        }
        String createdHash = cryptoService.sha256Hex(created.body() == null ? "" : created.body());
        long bindingId = recorder.upsertBinding(providerId, credentialId, endpoint.id(), channelId, channelName,
                "aap-provider-" + providerId, JsonCodec.toJson(models), createdHash, actor);

        // ② 写价（合并写，保留 new-api 上其它模型的既有表达式）
        Probe priceWritten = writeExpressions(endpoint, expressions, bindingId, actor);
        if (priceWritten != null && priceWritten.denied()) {
            String error = "E-1505 new-api 拒绝写价（HTTP " + priceWritten.httpStatus() + "）";
            recorder.markTaskTerminal(taskId, "MANUAL", false, error, attempt, OPERATION_WRITE_EXPR, "FAILED",
                    "E-1505", null, bindingId, actor);
            throw new ApiException(ErrorCode.E_1505, "new-api 拒绝写入计费表达式（HTTP " + priceWritten.httpStatus()
                    + "）：同步账号权限不足，渠道已建但价格未生效，任务已转人工");
        }
        if (priceWritten != null && !priceWritten.ok()) {
            String error = "E-1501 写价失败（" + (priceWritten.reachable() ? "HTTP " + priceWritten.httpStatus() : "不可达") + "）";
            recorder.markTaskTerminal(taskId, "PARTIAL", false, error, attempt, OPERATION_WRITE_EXPR, "FAILED",
                    "E-1501", null, bindingId, actor);
            throw new ApiException(ErrorCode.E_1501, error + "：渠道已建但价格未生效（PARTIAL），可按 ADM-S03 重试");
        }

        // ③ 回读比对（AC-34）
        Probe readback = newApiSyncClient.get(endpoint.baseUrl(), endpoint.apiKey(), "/api/channel/" + channelId);
        if (!readback.ok()) {
            String error = "E-1501 回读渠道失败（" + (readback.reachable() ? "HTTP " + readback.httpStatus() : "不可达") + "）";
            recorder.markTaskTerminal(taskId, "PARTIAL", false, error, attempt, OPERATION_ADD_CHANNEL, "FAILED",
                    "E-1501", null, bindingId, actor);
            throw new ApiException(ErrorCode.E_1501, error);
        }
        String online = channelStatusOf(readback.body());
        String readbackHash = cryptoService.sha256Hex(readback.body() == null ? "" : readback.body());
        if (!"ENABLED".equals(online)) {
            String summary = "回读不一致：期望 ENABLED，上游现值 " + (online == null ? "无法解析" : online);
            recorder.markReadbackMismatch(taskId, bindingId, readbackHash, summary, actor);
            auditService.record(AuditService.AuditAction.SYNC_EXECUTE, "sync_task", taskId,
                    "渠道 " + channelName + " " + summary + "，已保持库内状态等待人工介入");
            throw new ApiException(ErrorCode.E_1501, summary + "；已保持库内状态并等待人工介入（不置为已上架）");
        }

        recorder.markPublished(taskId, bindingId, channelId, providerId, readbackHash, OPERATION_ADD_CHANNEL,
                channelBody, readback.body(), actor);
        auditService.record(AuditService.AuditAction.SYNC_EXECUTE, "sync_task", taskId,
                "上架完成：渠道 " + channelName + "（channel_id=" + channelId + "）回读一致并置 ENABLED，供应商置 PUBLISHED");
        log.info("上架完成 task_id={} channel_id={} provider_id={}", taskId, channelId, providerId);
        return syncAdminService.taskDetail(taskId);
    }

    /** 写价：读现值 → 合并 → 写回（读失败按空起算，绝不覆盖成空对象——只在能解析出对象时才合并）。 */
    private Probe writeExpressions(Endpoint endpoint, List<ModelExpr> expressions, long bindingId, Long actor) {
        Map<String, Object> merged = new LinkedHashMap<>();
        Probe current = newApiSyncClient.get(endpoint.baseUrl(), endpoint.apiKey(), "/api/option/?key=" + OPTION_KEY);
        if (current.ok() && current.body() != null) {
            JsonNode root = JsonCodec.readTree(current.body());
            JsonNode data = root == null ? null : root.path("data");
            if (data != null && data.isTextual() && !data.asText().isBlank()) {
                try {
                    merged.putAll(JsonCodec.toMap(data.asText()));
                } catch (RuntimeException e) {
                    // 上游既有值不是 JSON 对象：不臆造、不静默清空，只记一条告警
                    log.warn("new-api 既有 billing_expr 不是 JSON 对象，改为整体写入（未覆盖空对象）");
                }
            }
        }
        for (ModelExpr expression : expressions) {
            merged.put(expression.modelName(), expression.expr());
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("key", OPTION_KEY);
        body.put("value", JsonCodec.toJson(merged));
        Probe written = newApiSyncClient.put(endpoint.baseUrl(), endpoint.apiKey(), "/api/option/",
                JsonCodec.toJson(body));
        auditService.record(AuditService.AuditAction.SYNC_WRITE_PRICE, "channel_binding", bindingId,
                "写入计费表达式 " + expressions.size() + " 条（billing_setting.billing_expr）");
        return written;
    }

    // ------------------------------------------------------------------ 内部查询

    private record Compilation(long id, String sourceHash) {
    }

    private record ModelExpr(String modelName, String expr) {
    }

    private record CredentialRow(long id, String baseUrl, String apiKey) {
    }

    private record Endpoint(long id, String baseUrl, String apiKey, boolean readonly) {
    }

    private Map<String, Object> providerRow(long providerId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, coalesce(nullif(short_name, ''), nullif(company_name, ''), provider_no, 'P' || id)
                           as short_label, status
                  from aap_provider where id = ? and deleted = false
                """, providerId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "供应商不存在：" + providerId);
        }
        return rows.get(0);
    }

    private Compilation resolveCompilation(long providerId, String compilationIdRaw) {
        if (compilationIdRaw != null && !compilationIdRaw.isBlank()) {
            long compilationId = parseId(compilationIdRaw, "compilation_id");
            List<Map<String, Object>> rows = jdbc.queryForList("""
                    select id, source_hash, gate_status, publish_blocked from aap_compiled_expression
                     where id = ? and provider_id = ? and deleted = false
                    """, compilationId, providerId);
            if (rows.isEmpty()) {
                throw new ApiException(ErrorCode.E_1406, "编译产物不存在或不属于该供应商：" + compilationId);
            }
            requireConfirmed(rows.get(0));
            return new Compilation(compilationId, text(rows.get(0).get("source_hash")));
        }
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, source_hash, gate_status, publish_blocked from aap_compiled_expression
                 where provider_id = ? and deleted = false and gate_status = 'CONFIRMED'
                 order by id desc
                """, providerId);
        for (Map<String, Object> candidate : rows) {
            if (!Boolean.TRUE.equals(candidate.get("publish_blocked"))) {
                return new Compilation(((Number) candidate.get("id")).longValue(), text(candidate.get("source_hash")));
            }
        }
        throw new ApiException(ErrorCode.E_1407,
                "该供应商没有已人工确认（CONFIRMED）的编译产物，禁止写入 new-api（闸门③）");
    }

    private void requireConfirmed(Map<String, Object> row) {
        boolean confirmed = "CONFIRMED".equals(text(row.get("gate_status")))
                && !Boolean.TRUE.equals(row.get("publish_blocked"));
        if (!confirmed) {
            throw new ApiException(ErrorCode.E_1407, "编译产物未通过人工确认（gate_status="
                    + text(row.get("gate_status")) + "，publish_blocked=" + row.get("publish_blocked")
                    + "），禁止写入 new-api");
        }
    }

    private List<ModelExpr> modelExpressions(Long compilationId) {
        if (compilationId == null) {
            return List.of();
        }
        List<ModelExpr> result = new ArrayList<>();
        jdbc.query("""
                select model_name, expr from aap_model_expression
                 where compilation_id = ? and deleted = false order by id
                """, rs -> {
            result.add(new ModelExpr(rs.getString("model_name"), rs.getString("expr")));
        }, compilationId);
        return result;
    }

    /** 建渠道用的上游 key：该供应商**检测通过**（`detection_status=PASS`）的最新凭证。 */
    private CredentialRow activeCredential(long providerId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, base_url, api_key_cipher, detection_status from aap_credential
                 where provider_id = ? and deleted = false order by id desc
                """, providerId);
        for (Map<String, Object> candidate : rows) {
            if ("PASS".equals(text(candidate.get("detection_status")))) {
                return toCredential(candidate);
            }
        }
        throw new ApiException(ErrorCode.E_1601, "该供应商没有检测通过（PASS）的凭证，无法建渠道");
    }

    private CredentialRow credentialRow(Long credentialId) {
        if (credentialId == null) {
            throw new ApiException(ErrorCode.E_1601, "同步任务缺少凭证引用（credential_id），无法建渠道");
        }
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, base_url, api_key_cipher, detection_status from aap_credential
                 where id = ? and deleted = false
                """, credentialId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1601, "同步任务引用的凭证不存在：" + credentialId);
        }
        return toCredential(rows.get(0));
    }

    private CredentialRow toCredential(Map<String, Object> row) {
        return new CredentialRow(((Number) row.get("id")).longValue(), text(row.get("base_url")),
                cryptoService.decrypt(text(row.get("api_key_cipher"))));
    }

    /** 任务无绑定时回落「启用中的端点」（首次上架必经）。 */
    private Endpoint endpointForTask(Long bindingId) {
        if (bindingId != null) {
            List<Long> endpointIds = jdbc.queryForList(
                    "select endpoint_id from aap_channel_binding where id = ? and deleted = false", Long.class, bindingId);
            if (!endpointIds.isEmpty() && endpointIds.get(0) != null) {
                Endpoint bound = endpoint(endpointIds.get(0));
                if (bound != null) {
                    return bound;
                }
            }
        }
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, base_url, api_key_cipher, readonly from aap_newapi_endpoint
                 where deleted = false and status = 'ACTIVE' order by id desc limit 1
                """);
        return rows.isEmpty() ? null : toEndpoint(rows.get(0));
    }

    private Endpoint endpoint(Long endpointId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, base_url, api_key_cipher, readonly from aap_newapi_endpoint
                 where id = ? and deleted = false and status = 'ACTIVE'
                """, endpointId);
        return rows.isEmpty() ? null : toEndpoint(rows.get(0));
    }

    private Endpoint toEndpoint(Map<String, Object> row) {
        return new Endpoint(((Number) row.get("id")).longValue(), text(row.get("base_url")),
                cryptoService.decrypt(text(row.get("api_key_cipher"))), Boolean.TRUE.equals(row.get("readonly")));
    }

    private Map<String, Object> taskRow(long taskId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select * from aap_sync_task where id = ? and deleted = false", taskId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "同步任务不存在：" + taskId);
        }
        return rows.get(0);
    }

    private NewApiEndpoint endpointView(long endpointId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, name, base_url, api_key_cipher, readonly, status, created_at, updated_at
                  from aap_newapi_endpoint where id = ?
                """, endpointId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "new-api 端点不存在：" + endpointId);
        }
        Map<String, Object> row = rows.get(0);
        return new NewApiEndpoint(String.valueOf(row.get("id")), text(row.get("name")), text(row.get("base_url")),
                Boolean.TRUE.equals(row.get("readonly")), text(row.get("status")), maskOf(text(row.get("api_key_cipher"))),
                rfc3339(row.get("created_at")), rfc3339(row.get("updated_at")));
    }

    /** 掩码是**唯一出口**：解密只为生成不可逆掩码，明文不进日志、不进响应。 */
    private String maskOf(String cipherText) {
        if (cipherText == null || cipherText.isBlank()) {
            return null;
        }
        try {
            return cryptoService.maskApiKey(cryptoService.decrypt(cipherText));
        } catch (RuntimeException e) {
            return null;   // 解密失败：宁可不显示，也不回退成任何密文片段
        }
    }

    private String defaultChannelName(long providerId, String shortLabel) {
        String label = shortLabel == null || shortLabel.isBlank() ? "P" + providerId : shortLabel.trim();
        label = label.replace(" ", "");
        if (label.length() > 12) {
            label = label.substring(0, 12);
        }
        Long count = jdbc.queryForObject(
                "select count(*) from aap_channel_binding where provider_id = ? and deleted = false", Long.class, providerId);
        long sequence = (count == null ? 0L : count) + 1;
        String name = "AAP-" + label + "-" + sequence;
        return name.length() > 64 ? name.substring(0, 64) : name;
    }

    private String normalizeMode(String mode) {
        if (mode == null || mode.isBlank()) {
            return MODE_REVIEW_THEN_APPLY;
        }
        String value = mode.trim().toUpperCase(java.util.Locale.ROOT);
        if (!MODE_REVIEW_THEN_APPLY.equals(value) && !MODE_DRY_RUN.equals(value)) {
            throw ApiException.field(ErrorCode.E_1001, "mode",
                    "只支持 REVIEW_THEN_APPLY 或 DRY_RUN：收到 " + mode);
        }
        return value;
    }

    /** 上游渠道状态解析（`{"data":{"status":1|2}}`；无法解析回 null → 视为不一致）。 */
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

    private static Long createdChannelId(String body) {
        JsonNode root = JsonCodec.readTree(body);
        JsonNode id = root == null ? null : root.path("data").path("id");
        if (id == null || id.isMissingNode() || id.isNull()) {
            return null;
        }
        long value = id.asLong(0L);
        return value > 0L ? value : null;   // 雪花 id 恒 >0；非数字/0 一律视为「拿不到渠道 id」
    }

    private static String requireText(String value, String field, int maxLength) {
        if (value == null || value.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, field, "必填");
        }
        if (value.length() > maxLength) {
            throw ApiException.field(ErrorCode.E_1001, field, "长度不得超过 " + maxLength);
        }
        return value.trim();
    }

    private static Long requiredId(String value, String field) {
        if (value == null || value.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, field, "必填");
        }
        return parseId(value, field);
    }

    private static Long parseId(String value, String field) {
        try {
            return Long.valueOf(value.trim());
        } catch (RuntimeException e) {
            throw ApiException.field(ErrorCode.E_1001, field, "不是合法的雪花 ID：" + value);
        }
    }

    private static Long toLong(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number number) {
            return number.longValue();
        }
        try {
            return Long.valueOf(String.valueOf(value).trim());
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String text(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    /**
     * 时间统一按 UTC RFC3339 输出。
     *
     * <p>为什么入参是 `Object`：`JdbcTemplate.queryForList` 对 `timestamptz` 列返回的是
     * `java.sql.Timestamp`（不是 `OffsetDateTime`），直接强转会 `ClassCastException` → `E-2001`。
     * 这里显式兼容三种真实返回形态，避免"看起来能跑、一上线就 500"的隐式约定。
     */
    private static String rfc3339(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof OffsetDateTime offsetDateTime) {
            return RFC3339.format(offsetDateTime.withOffsetSameInstant(ZoneOffset.UTC));
        }
        if (value instanceof java.sql.Timestamp timestamp) {
            return RFC3339.format(timestamp.toInstant().atOffset(ZoneOffset.UTC));
        }
        if (value instanceof java.time.Instant instant) {
            return RFC3339.format(instant.atOffset(ZoneOffset.UTC));
        }
        return String.valueOf(value);
    }
}
