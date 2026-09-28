package com.hioas.aap.supply;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.support.AuditService;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 管理端供给单元运维（`ADM-SU01…04`）。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.6（本族）+
 * `docs/backend/json-schema/models/{supply-unit,config-batch,config-batch-item}.schema.json`
 * + `specs/001-intake-automation/contracts/intake-automation.openapi.yaml`（`/admin/supply-units*` 五个 operation）
 * + `specs/001-intake-automation/spec.md` FR-2.9/FR-2.10（重配置 / 下线）与 R-65（下架前影响面校验）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>ID 对外一律 **string**（雪花超出 JS 安全整数范围）；时间 RFC3339 **UTC**；缺值回 null。</li>
 *   <li><b>写与随后要读回的状态同源</b>：本类全部走 {@code JdbcTemplate}（条件 UPDATE 拿**真实影响行数**
 *       当乐观锁判定，读回也在同一条 SQL 客户端上）—— 踩坑 17/18：ORM 写 + JDBC 读会读到写之前的状态，
 *       而且响应会变成「内存值」，出现「响应说 DOWN、库里还是 ONLINE」。</li>
 *   <li>{@code ADM-SU04} 前置校验 **R-65**：该供应商存在未结清账期（`UNSETTLED` / `PAYMENT_RECORDED`
 *       的打款记录）时拒绝下架 → 409 `E-1601`。</li>
 *   <li>{@code ADM-SU03} 的差异清单由 {@link ChannelConfigPlanner}（T-M4-07）计算；上游执行器
 *       （T-M4-08~11：限速/回读/单模型隔离/回滚）**尚未落地** ⇒ {@code mode=APPLY} 只登记批次
 *       （`PENDING`）而**不写上游**，不谎报已执行（R-58「不得静默成功」的同一纪律）。</li>
 * </ul>
 */
@Service
public class SupplyUnitAdminService {

    /** 时间出口格式（与全仓一致：字面量 `Z`，调用点一律先归一到 UTC）。 */
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 未结清账期 = 打款记录处于「已记录未确认」或「未结清」（PRD 10 §4.3 的 PaymentStatus 域）。 */
    private static final List<String> UNSETTLED_PAYMENT_STATUSES = List.of("UNSETTLED", "PAYMENT_RECORDED");

    private final JdbcTemplate jdbc;
    private final DocNoGenerator docNoGenerator;
    private final AuditService auditService;

    public SupplyUnitAdminService(JdbcTemplate jdbc, DocNoGenerator docNoGenerator, AuditService auditService) {
        this.jdbc = jdbc;
        this.docNoGenerator = docNoGenerator;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ ADM-SU01

    /** ADM-SU01 供给单元列表：分页 + `providerId`/`modelName`/`status` 过滤（排序 `created_at desc, id desc`）。 */
    public PageResult<SupplyUnitViews.SupplyUnit> adminList(Integer page, Integer pageSize, Long providerId,
                                                           String modelName, String status) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> filters = new ArrayList<>();
        if (providerId != null) {
            where.append(" and provider_id = ?");
            filters.add(providerId);
        }
        if (modelName != null && !modelName.isBlank()) {
            where.append(" and model_name ilike ?");
            filters.add("%" + modelName.trim() + "%");
        }
        if (status != null && !status.isBlank()) {
            where.append(" and upper(status) = ?");
            filters.add(status.trim().toUpperCase(Locale.ROOT));
        }
        Long total = jdbc.queryForObject("select count(*) from aap_supply_unit" + where, Long.class, filters.toArray());
        List<Object> pageParams = new ArrayList<>(filters);
        pageParams.add(query.pageSize());
        pageParams.add(query.offset());
        List<Long> ids = jdbc.queryForList("select id from aap_supply_unit" + where
                + " order by created_at desc, id desc limit ? offset ?", Long.class, pageParams.toArray());
        List<SupplyUnitViews.SupplyUnit> items = new ArrayList<>(ids.size());
        for (Long id : ids) {
            items.add(loadView(id));
        }
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    // ------------------------------------------------------------------ ADM-SU02

    /** ADM-SU02 供给单元详情（不存在或已逻辑删除 → 404 `E-1406`）。 */
    public SupplyUnitViews.SupplyUnit detail(Long id) {
        if (id == null) {
            throw new ApiException(ErrorCode.E_1001, "供给单元 id 非法");
        }
        SupplyUnitViews.SupplyUnit view = loadView(id);
        if (view == null) {
            throw new ApiException(ErrorCode.E_1406, "供给单元不存在");
        }
        return view;
    }

    // ------------------------------------------------------------------ ADM-SU03

    /**
     * ADM-SU03 重配置（INNOV-7 / FR-2.9）：凭证/价格/策略变更后重算差异。
     *
     * <p>状态守卫：仅「在架（`ONLINE`/`DEGRADED`）或暂停（`SUSPENDED`）」可重配置；`PENDING`/`CONFIGURING`/
     * `OFFLINE` 一律 409 `E-1601`（契约：「状态不允许（如未上架/已下线）」）。与 {@link SupplyUnitStatus}
     * 一致：这三种状态的目标态 `CONFIGURING` 在状态机里本就不可达（`OFFLINE` 必须先走 `CONFIGURING` 之外的
     * 重建路径，属 T-M6-07 的范围）。
     *
     * @param dryRun 契约默认 `true`（`DRY_RUN` 只出差异清单、生产零写入）；显式 `false` 才落 `APPLY`
     */
    @Transactional
    public SupplyUnitViews.ConfigBatch reconfigure(AuthPrincipal principal, Long id, Boolean dryRun, String reason) {
        Map<String, Object> row = requireRow(id);
        SupplyUnitStatus current = SupplyUnitStatus.of((String) row.get("status"));
        boolean reconfigureAllowed = current == SupplyUnitStatus.ONLINE
                || current == SupplyUnitStatus.DEGRADED
                || current == SupplyUnitStatus.SUSPENDED;
        if (!reconfigureAllowed) {
            throw new ApiException(ErrorCode.E_1601,
                    "供给单元当前状态 " + current + " 不允许重配置（未上架或已下线）");
        }
        boolean dry = !Boolean.FALSE.equals(dryRun);
        String mode = dry ? "DRY_RUN" : "APPLY";
        long providerId = ((Number) row.get("provider_id")).longValue();
        String modelName = (String) row.get("model_name");
        String granularity = (String) row.get("granularity");

        ChannelConfigPlanner.Target target = ChannelConfigPlanner.plan(new ChannelConfigPlanner.Input(
                String.valueOf(id), providerId, shortCodeOf(providerId), modelName, List.of(modelName),
                granularity, intOf(row.get("routing_priority")), intOf(row.get("routing_weight"))));
        List<ChannelConfigPlanner.Existing> existing = existingBinding(id);
        List<ChannelConfigPlanner.Diff> diffs = target == null
                ? ChannelConfigPlanner.NO_DIFF
                : ChannelConfigPlanner.diff(List.of(target), existing, Set.<String>of());
        Map<String, Long> summary = ChannelConfigPlanner.summarize(diffs);
        String diffNote = diffs.isEmpty() ? "不可规划（PER_MODEL 下 models 必须恰为该模型）" : diffs.get(0).reason();

        Long actor = actorId(principal);
        long batchId = newId("seq_config_batch");
        String batchNo = docNoGenerator.configBatchNo();
        int writeCount = (int) diffs.stream().filter(d -> ChannelConfigPlanner.isWrite(d.action())).count();
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        // DRY_RUN：零写入 ⇒ 批次立即完成、明细动作 SKIPPED；APPLY：只登记受理（执行器待 T-M4-08~11）
        String batchStatus = dry ? "COMPLETED" : "PENDING";
        jdbc.update("""
                insert into aap_config_batch (id, batch_no, batch_type, mode, trigger_source, status,
                    total_count, succeeded_count, failed_count, mismatch_count, rate_limit_per_sec, diff_payload,
                    operator_id, started_at, finished_at, created_at, updated_at, created_by, updated_by)
                values (?, ?, 'RECONFIG', ?, 'ADMIN_MANUAL', ?, 1, 0, 0, 0, ?, ?::jsonb, ?,
                        ?::timestamptz, ?::timestamptz, now(), now(), ?, ?)
                """, batchId, batchNo, mode, batchStatus, ChannelConfigPlanner.RATE_LIMIT_PER_SEC,
                JsonCodec.toJson(diffPayload(mode, summary)), actor, now, dry ? now : null, actor, actor);
        jdbc.update("""
                insert into aap_config_batch_item (id, batch_id, supply_unit_id, provider_id, model_name, action,
                    status, reason, attempt_count, created_at, updated_at)
                values (?, ?, ?, ?, ?, 'RECONFIG', ?, ?, 0, now(), now())
                """, newId("seq_config_batch_item"), batchId, id, providerId, modelName,
                dry ? "SKIPPED" : "PENDING",
                trim(reason == null || reason.isBlank() ? diffNote : reason));

        auditService.record(AuditService.AuditAction.SUPPLY_UNIT_RECONFIGURE, "supply_unit", id,
                "重配置供给单元（" + mode + "，批次 " + batchNo + "，" + (dry ? "差异清单" : "已受理") + "）",
                Map.of("status", current.name(), "granularity", granularity == null ? "" : granularity),
                Map.of("mode", mode, "batch_no", batchNo), "NORMAL");

        SupplyUnitViews.ConfigBatch view = loadBatch(batchId);
        if (view == null) {
            throw new ApiException(ErrorCode.E_2001, "批次落库后回读失败（不谎报已受理）");
        }
        if (dry && writeCount > 0) {
            // 零写入自证：DRY_RUN 的批次里不允许出现「需写上游」的完成计数
            Long executed = jdbc.queryForObject(
                    "select count(*) from aap_config_batch_item where batch_id = ? and status <> 'SKIPPED'",
                    Long.class, batchId);
            if (executed != null && executed > 0) {
                throw new ApiException(ErrorCode.E_2001, "DRY_RUN 不得产生任何写入项");
            }
        }
        return view;
    }

    // ------------------------------------------------------------------ ADM-SU04

    /**
     * ADM-SU04 下架供给单元（FR-2.10 + R-65）。
     *
     * <p>状态守卫：已是 `OFFLINE` → 409 `E-1601`（幂等由调用方按值判断，不靠状态机表达）；
     * 其余状态均允许下架（状态机里 `→ OFFLINE` 对所有非 OFFLINE 状态可达）。
     *
     * <p>影响面校验：该供应商存在未结清账期（`UNSETTLED` / `PAYMENT_RECORDED` 的打款）→ 409 `E-1601`。
     */
    @Transactional
    public SupplyUnitViews.SupplyUnit offline(AuthPrincipal principal, Long id) {
        Map<String, Object> row = requireRow(id);
        SupplyUnitStatus current = SupplyUnitStatus.of((String) row.get("status"));
        if (current == SupplyUnitStatus.OFFLINE) {
            throw new ApiException(ErrorCode.E_1601, "供给单元已下线，无需重复下架");
        }
        long providerId = ((Number) row.get("provider_id")).longValue();
        Long unsettled = jdbc.queryForObject("""
                select count(*) from aap_payment_record
                 where provider_id = ? and deleted = false and status in (?, ?)
                """, Long.class, providerId, UNSETTLED_PAYMENT_STATUSES.get(0), UNSETTLED_PAYMENT_STATUSES.get(1));
        if (unsettled != null && unsettled > 0) {
            throw new ApiException(ErrorCode.E_1601,
                    "存在未结清账期（" + unsettled + " 笔未确认打款），按 R-65 禁止下架");
        }
        Long actor = actorId(principal);
        int updated = jdbc.update("""
                update aap_supply_unit
                   set status = 'OFFLINE', updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and deleted = false and status = ?
                """, actor, id, current.name());
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "供给单元状态已被他人改动，请刷新后重试");
        }
        SupplyUnitViews.SupplyUnit view = loadView(id);
        if (view == null) {
            throw new ApiException(ErrorCode.E_1406, "供给单元不存在");
        }
        auditService.record(AuditService.AuditAction.SUPPLY_UNIT_OFFLINE, "supply_unit", id,
                "下架供给单元 " + view.modelName() + "（原状态 " + current.name() + "）",
                Map.of("status", current.name()), Map.of("status", "OFFLINE"), "NORMAL");
        return view;
    }

    // ------------------------------------------------------------------ 内部

    /** 读一行供给单元（含逻辑删除过滤）；不存在返回 null。 */
    private Map<String, Object> rowOrNull(Long id) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select * from aap_supply_unit where id = ? and deleted = false", id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Map<String, Object> requireRow(Long id) {
        if (id == null) {
            throw new ApiException(ErrorCode.E_1001, "供给单元 id 非法");
        }
        Map<String, Object> row = rowOrNull(id);
        if (row == null) {
            throw new ApiException(ErrorCode.E_1406, "供给单元不存在");
        }
        return row;
    }

    private SupplyUnitViews.SupplyUnit loadView(Long id) {
        Map<String, Object> row = rowOrNull(id);
        return row == null ? null : new SupplyUnitViews.SupplyUnit(
                idOf(row.get("id")),
                idOf(row.get("provider_id")),
                idOf(row.get("credential_id")),
                (String) row.get("model_name"),
                (String) row.get("model_slug"),
                (String) row.get("model_uid"),
                (String) row.get("status"),
                decimalOf(row.get("detect_total_score")),
                (String) row.get("detect_confidence"),
                decimalOf(row.get("quality_score")),
                intOrNull(row.get("routing_priority")),
                intOrNull(row.get("routing_weight")),
                (Boolean) row.get("auto_ban_enabled"),
                idOf(row.get("binding_id")),
                (String) row.get("granularity"),
                rfc3339(row.get("created_at")));
    }

    /** 该供给单元现存绑定（作为差异计算的「实况」；无绑定回空清单 → 差异为 CREATE）。 */
    private List<ChannelConfigPlanner.Existing> existingBinding(Long supplyUnitId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select channel_name, tag, priority, weight, models::text as models_text, status
                  from aap_channel_binding
                 where supply_unit_id = ? and deleted = false
                 order by created_at desc, id desc limit 1
                """, supplyUnitId);
        if (rows.isEmpty()) {
            return List.of();
        }
        Map<String, Object> r = rows.get(0);
        return List.of(new ChannelConfigPlanner.Existing(
                String.valueOf(supplyUnitId),
                (String) r.get("channel_name"),
                parseStringArray((String) r.get("models_text")),
                (String) r.get("tag"),
                intOf(r.get("priority")),
                intOf(r.get("weight")),
                (String) r.get("status")));
    }

    /** 批次 + 明细回读（响应与库同源；踩坑 22：子集合必须在同一处补齐）。 */
    private SupplyUnitViews.ConfigBatch loadBatch(long batchId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select id, batch_no, batch_type, mode, trigger_source, status, total_count, succeeded_count,"
                        + " failed_count, mismatch_count, rate_limit_per_sec, diff_payload::text as diff_payload,"
                        + " started_at, finished_at, created_at"
                        + " from aap_config_batch where id = ? and deleted = false", batchId);
        if (rows.isEmpty()) {
            return null;
        }
        Map<String, Object> r = rows.get(0);
        List<Map<String, Object>> itemRows = jdbc.queryForList("""
                select id, batch_id, supply_unit_id, provider_id, model_name, action, status,
                       readback_equal, attempt_count, last_error, created_at
                  from aap_config_batch_item
                 where batch_id = ? and deleted = false
                 order by id asc
                """, batchId);
        List<SupplyUnitViews.ConfigBatchItem> items = new ArrayList<>(itemRows.size());
        for (Map<String, Object> it : itemRows) {
            items.add(new SupplyUnitViews.ConfigBatchItem(
                    idOf(it.get("id")),
                    idOf(it.get("batch_id")),
                    idOf(it.get("supply_unit_id")),
                    idOf(it.get("provider_id")),
                    (String) it.get("model_name"),
                    (String) it.get("action"),
                    (String) it.get("status"),
                    (Boolean) it.get("readback_equal"),
                    intOrNull(it.get("attempt_count")),
                    (String) it.get("last_error"),
                    rfc3339(it.get("created_at"))));
        }
        return new SupplyUnitViews.ConfigBatch(
                idOf(r.get("id")),
                (String) r.get("batch_no"),
                (String) r.get("batch_type"),
                (String) r.get("mode"),
                (String) r.get("trigger_source"),
                (String) r.get("status"),
                intOrNull(r.get("total_count")),
                intOrNull(r.get("succeeded_count")),
                intOrNull(r.get("failed_count")),
                intOrNull(r.get("mismatch_count")),
                intOrNull(r.get("rate_limit_per_sec")),
                JsonCodec.readTree((String) r.get("diff_payload")),
                rfc3339(r.get("started_at")),
                rfc3339(r.get("finished_at")),
                rfc3339(r.get("created_at")),
                items);
    }

    private Map<String, Object> diffPayload(String mode, Map<String, Long> summary) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("mode", mode);
        payload.put("byAction", summary);
        payload.put("writeRequired", summary.entrySet().stream()
                .filter(e -> ChannelConfigPlanner.isWrite(e.getKey()))
                .mapToLong(Map.Entry::getValue).sum());
        return payload;
    }

    private String shortCodeOf(long providerId) {
        List<String> codes = jdbc.queryForList(
                "select short_code from aap_provider where id = ? and deleted = false", String.class, providerId);
        return codes.isEmpty() ? null : codes.get(0);
    }

    private long newId(String sequence) {
        Long value = jdbc.queryForObject("select nextval('" + sequence + "')", Long.class);
        return value == null ? 0L : value;
    }

    private static Long actorId(AuthPrincipal principal) {
        return principal == null ? null : principal.accountId();
    }

    private static String idOf(Object value) {
        return value == null ? null : String.valueOf(((Number) value).longValue());
    }

    private static Integer intOrNull(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    private static int intOf(Object value) {
        return value == null ? 0 : ((Number) value).intValue();
    }

    private static BigDecimal decimalOf(Object value) {
        if (value == null) {
            return null;
        }
        return value instanceof BigDecimal bd ? bd : new BigDecimal(value.toString());
    }

    private static String rfc3339(Object value) {
        if (value == null) {
            return null;
        }
        OffsetDateTime odt = value instanceof OffsetDateTime o ? o
                : ((java.sql.Timestamp) value).toInstant().atOffset(ZoneOffset.UTC);
        return RFC3339.format(odt.withOffsetSameInstant(ZoneOffset.UTC));
    }

    /** jsonb 数组文本（如 {@code ["gpt-4o"]}）→ 字符串清单；PER_MODEL 下只有一个元素。 */
    private static List<String> parseStringArray(String text) {
        if (text == null || text.isBlank() || "null".equals(text.trim())) {
            return List.of();
        }
        String body = text.trim();
        if (body.startsWith("[")) {
            body = body.substring(1);
        }
        if (body.endsWith("]")) {
            body = body.substring(0, body.length() - 1);
        }
        List<String> out = new ArrayList<>();
        for (String part : body.split(",")) {
            String s = part.trim();
            if (s.length() >= 2 && s.startsWith("\"") && s.endsWith("\"")) {
                s = s.substring(1, s.length() - 1);
            }
            if (!s.isBlank()) {
                out.add(s);
            }
        }
        return out;
    }

    /** 列宽保护：`last_error` 等列是 varchar(512)，超长会 500（不静默截断用户语义，只截自由文本）。 */
    private static String trim(String value) {
        if (value == null) {
            return null;
        }
        String v = value.trim();
        return v.length() <= 500 ? v : v.substring(0, 500);
    }
}
