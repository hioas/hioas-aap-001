package com.hioas.aap.supply;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 管理端批量配置批次（`ADM-CB01…05`；FR-2.5 / FR-6.2 / FR-6.3 / R-57 / R-58 / R-59）。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.6（逐行：**201** 创建 / 分页列表 / 详情含明细与
 * `mismatch` 清单 / **202** 单模型重试与回滚）+
 * `docs/backend/json-schema/models/config-batch.schema.json`、`config-batch-item.schema.json`、
 * `docs/backend/json-schema/requests/config-batch-{create,rollback}.schema.json` +
 * `specs/001-intake-automation/{spec.md（FR-2.5 部分失败、FR-6.2 控制台、FR-6.3 预演、R-57/R-58/R-59）,
 * data-model.md §9, contracts/intake-automation.openapi.yaml}` + `V16__config_batch.sql`。
 *
 * <p>硬口径（每条都对应一次真实返工）：
 * <ul>
 *   <li><b>写与随后要读回的状态同源</b>：本类全程 `JdbcTemplate`（条件 UPDATE 拿**真实影响行数**当乐观锁判定，
 *       读回也走 {@link ConfigBatchReader} 的同一 SQL 客户端）—— 踩坑 17/18：ORM 写 + JDBC 读会读出写之前的状态。</li>
 *   <li><b>dry-run 零写入是自证的</b>（AC-10）：`DRY_RUN` 的明细一律落 `SKIPPED`，落库后**回查**一遍，
 *       出现任何非 `SKIPPED` 项即失败；且不触碰 `aap_channel_binding` / `aap_sync_task`。</li>
 *   <li><b>不谎报已执行</b>（R-58）：上游执行器（T-M4-08~11：限速/写后回读/单模型隔离与回滚）尚未落地 ⇒
 *       `APPLY` 只把批次与明细登记为 `PENDING`（受理态），`succeeded_count` 恒 0。</li>
 *   <li><b>单模型隔离</b>（R-59）：重试/回滚只改**一项**（`where id = ? and batch_id = ? and status = ?`），
 *       兄弟项与其它批次的行一律不动，并要求影响行数 == 1。</li>
 *   <li><b>影响面阈值</b>（R-57「每批 ≤20」+ 规格 409「影响面超阈值需二次确认」）：命中数 > 20 → 409 `E-1601`，
 *       恰好 20 可行（AC-10 就是 20 个单元的 dry-run）。</li>
 *   <li>成功状态码按**清单**：创建 201、重试/回滚 202（与 `ADM-SU03` 的 202 同族，非 200 成功码在 md 行里已声明）。</li>
 * </ul>
 *
 * <p>与同一族 `ADM-SU03` 的关系：`ADM-SU03` 是「单单元重配置」的快捷入口（内部同样落一个批次），
 * 本类是**批量编排可观测面**（创建 / 列表 / 详情 / 逐项重试 / 逐项回滚）。两者共用
 * {@link ChannelConfigPlanner} 的差异计算与 {@link ConfigBatchReader} 的回读出口。
 */
@Service
public class ConfigBatchAdminService {

    /** R-57：每批 ≤20 个供给单元（`AC-10` 的「20 个供给单元 dry-run」恰好可行，21 个即触发影响面确认）。 */
    public static final int MAX_UNITS_PER_BATCH = 20;

    /** 可重试的明细状态（R-59：只重试**失败的那一项**；`SUCCEEDED`/`PENDING`/`ROLLED_BACK` 一律拒绝）。 */
    private static final List<String> RETRYABLE_ITEM_STATUSES = List.of("FAILED", "MISMATCH");

    /** 可回滚的明细状态：只有「已执行成功」的项才有东西可回滚（未执行 / 已回滚都无可回滚的写入）。 */
    private static final String ROLLBACKABLE_ITEM_STATUS = "SUCCEEDED";

    /** 明细 `last_error` / `reason` 是 varchar(512)：只裁自由文本，不裁用户语义（不静默截断 ID/枚举）。 */
    private static final int TEXT_LIMIT = 500;

    private final JdbcTemplate jdbc;
    private final DocNoGenerator docNoGenerator;

    public ConfigBatchAdminService(JdbcTemplate jdbc, DocNoGenerator docNoGenerator) {
        this.jdbc = jdbc;
        this.docNoGenerator = docNoGenerator;
    }

    // ------------------------------------------------------------------ ADM-CB01

    /**
     * ADM-CB01 创建批次（201；`mode=DRY_RUN` 出差异清单、零写入）。
     *
     * <p>`scope` 语义（契约把它标为可选；规格只给了内层维度 `providerIds`/`modelNames`/`supplyUnitIds`/`tags`）：
     * <ul>
     *   <li>**省略 / 全空** ⇒ 全量**未下线**供给单元（`status <> 'OFFLINE'`）；不碰已下线的单元是安全默认
     *       ——「全量」不应把被刻意下架的渠道重新拉起来。</li>
     *   <li>**显式维度** ⇒ 维度的**并集**（`supplyUnitIds` ∪ `providerIds` 的全部单元 ∪ `modelNames`（忽略大小写）
     *       ∪ `tags`（命中 `aap_channel_binding.tag` 的单元））；显式选择即明确意图，不额外按状态过滤。</li>
     *   <li>命中 0 个 ⇒ 登记一个**空批次**（`total_count=0`、无明细），而不是静默报错或伪造目标。</li>
     * </ul>
     */
    @Transactional
    public SupplyUnitViews.ConfigBatch create(AuthPrincipal principal,
                                              SupplyUnitViews.ConfigBatchCreateRequest request) {
        if (request == null) {
            throw ApiException.field(ErrorCode.E_1001, "body", "请求体必填（batch_type 与 mode 均为必填字段）");
        }
        // 必填性显式判空（契约 `requests/config-batch-create.schema.json` 的 `required = [batch_type, mode]`）：
        // 不把「缺字段」的报错只藏在解析助手里 —— 「字段 → 判空 → 拒绝」这条链要在实现里**静态可见**
        // （只读审计 `spotcheck-required` A3 的判据形态；判据看不到就会被报成「schema 说必填、实现零校验」）。
        if (request.batchType() == null || request.batchType().isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "batch_type", "缺少必填字段 batch_type");
        }
        if (request.mode() == null || request.mode().isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "mode", "缺少必填字段 mode");
        }
        ConfigBatchType type = type(request.batchType());
        ConfigBatchMode mode = mode(request.mode());
        int rateLimit = rateLimit(request.rateLimitPerSec());
        List<Long> unitIds = resolveTargets(request.scope());
        if (unitIds.size() > MAX_UNITS_PER_BATCH) {
            throw new ApiException(ErrorCode.E_1601, "影响面超阈值：本次命中 " + unitIds.size()
                    + " 个供给单元，R-57 要求每批 ≤" + MAX_UNITS_PER_BATCH + "（请按供应商/模型/标签分批，或缩小 scope）");
        }

        List<ChannelConfigPlanner.Diff> diffs = planDiffs(type, unitIds);
        Map<String, ChannelConfigPlanner.Diff> diffByUnit = new LinkedHashMap<>();
        for (ChannelConfigPlanner.Diff diff : diffs) {
            diffByUnit.put(diff.supplyUnitId(), diff);
        }
        Map<String, Long> byAction = ChannelConfigPlanner.summarize(diffs);
        long unplanned = unitIds.size() - diffs.size();

        Long actor = actorId(principal);
        long batchId = newId("seq_config_batch");
        String batchNo = docNoGenerator.configBatchNo();
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        String batchStatus = mode == ConfigBatchMode.DRY_RUN ? "SUCCEEDED" : "PENDING";
        jdbc.update("""
                insert into aap_config_batch (id, batch_no, batch_type, mode, trigger_source, status,
                    total_count, succeeded_count, failed_count, mismatch_count, rate_limit_per_sec, diff_payload,
                    operator_id, started_at, finished_at, created_at, updated_at, created_by, updated_by)
                values (?, ?, ?, ?, 'ADMIN_MANUAL', ?, ?, 0, 0, 0, ?, ?::jsonb, ?, ?::timestamptz, ?::timestamptz,
                        now(), now(), ?, ?)
                """, batchId, batchNo, type.name(), mode.name(), batchStatus, unitIds.size(), rateLimit,
                JsonCodec.toJson(diffPayload(type, mode, byAction, unplanned)), actor, now,
                mode == ConfigBatchMode.DRY_RUN ? now : null, actor, actor);

        // 明细行：把命中 0 个单元的「空批次」也如实登记（没有明细，也不伪造目标）——
        // `unitIds` 为空时**绝不能**发出 `id in ()`（那是 SQL 语法错误，HTTP 只见 500 E-2001）
        if (!unitIds.isEmpty()) {
            List<Map<String, Object>> units = jdbc.queryForList(
                    "select id, provider_id, model_name from aap_supply_unit where deleted = false"
                            + " and id in (" + placeholders(unitIds) + ") order by id asc", unitIds.toArray());
            for (Map<String, Object> unit : units) {
                long unitId = ConfigBatchReader.longOf(unit.get("id"));
                ChannelConfigPlanner.Diff diff = diffByUnit.get(String.valueOf(unitId));
                String action = diff == null ? ChannelConfigPlanner.SKIP : diff.action();
                String note = diff == null
                        ? "不可规划（PER_MODEL 下 models 必须恰为该模型）—— 待人工确认"
                        : diff.reason();
                jdbc.update("""
                        insert into aap_config_batch_item (id, batch_id, supply_unit_id, provider_id, model_name,
                            action, status, reason, idempotency_key, request_summary, attempt_count,
                            created_at, updated_at)
                        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, 0, now(), now())
                        """, newId("seq_config_batch_item"), batchId, unitId, unit.get("provider_id"),
                        unit.get("model_name"), action,
                        mode == ConfigBatchMode.DRY_RUN ? "SKIPPED" : "PENDING",
                        clip(note, TEXT_LIMIT), batchNo + ":" + unitId,
                        JsonCodec.toJson(itemRequestSummary(type, mode, action)));
            }
        }

        SupplyUnitViews.ConfigBatch view = ConfigBatchReader.read(jdbc, batchId);
        if (view == null) {
            throw new ApiException(ErrorCode.E_2001, "批次落库后回读失败（不谎报已受理）");
        }
        if (mode == ConfigBatchMode.DRY_RUN) {
            // 零写入自证（AC-10）：DRY_RUN 的批次里不允许出现任何「非 SKIPPED」的执行项
            Long executed = jdbc.queryForObject(
                    "select count(*) from aap_config_batch_item where batch_id = ? and status <> 'SKIPPED'",
                    Long.class, batchId);
            if (executed != null && executed > 0) {
                throw new ApiException(ErrorCode.E_2001, "DRY_RUN 不得产生任何写入项");
            }
        }
        return view;
    }

    // ------------------------------------------------------------------ ADM-CB02 / ADM-CB03

    /** ADM-CB02 批次列表：分页 + `status` 过滤（大小写不敏感；排序 `created_at desc, id desc`）。 */
    public PageResult<SupplyUnitViews.ConfigBatch> adminList(Integer page, Integer pageSize, String status) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> filters = new ArrayList<>();
        if (status != null && !status.isBlank()) {
            where.append(" and upper(status) = ?");
            filters.add(status.trim().toUpperCase(Locale.ROOT));
        }
        Long total = jdbc.queryForObject("select count(*) from aap_config_batch" + where, Long.class,
                filters.toArray());
        List<Object> pageParams = new ArrayList<>(filters);
        pageParams.add(query.pageSize());
        pageParams.add(query.offset());
        List<Long> ids = jdbc.queryForList("select id from aap_config_batch" + where
                + " order by created_at desc, id desc limit ? offset ?", Long.class, pageParams.toArray());
        return PageResult.of(ConfigBatchReader.readAll(jdbc, ids), query.page(), query.pageSize(),
                total == null ? 0L : total);
    }

    /** ADM-CB03 批次详情（含明细与其中的 `mismatch` 清单；不存在或已逻辑删除 → 404 `E-1406`）。 */
    public SupplyUnitViews.ConfigBatch detail(Long batchId) {
        if (batchId == null) {
            throw ApiException.field(ErrorCode.E_1001, "batchId", "批次 id 非法");
        }
        SupplyUnitViews.ConfigBatch view = ConfigBatchReader.read(jdbc, batchId);
        if (view == null) {
            throw new ApiException(ErrorCode.E_1406, "配置批次不存在");
        }
        return view;
    }

    // ------------------------------------------------------------------ ADM-CB04

    /**
     * ADM-CB04 单模型重试（202；R-59 只影响该项）。
     *
     * <p>语义：把**失败/回读不一致**的明细重新排队（`FAILED`/`MISMATCH` → `PENDING`）、`attempt_count` +1，
     * 批次回到 `RUNNING` 并重算计数；**幂等键复用**（同一条明细的 `idempotency_key` 不变 —— 重试若换键，
     * 上游会当成新渠道重复创建，C-11）。
     */
    @Transactional
    public SupplyUnitViews.ConfigBatchItem retryItem(AuthPrincipal principal, Long batchId, Long itemId) {
        requireBatch(batchId);
        Map<String, Object> item = requireItem(batchId, itemId);
        String current = (String) item.get("status");
        if (!RETRYABLE_ITEM_STATUSES.contains(current)) {
            throw new ApiException(ErrorCode.E_1601,
                    "明细现状为 " + current + "，不可重试（仅 " + String.join("/", RETRYABLE_ITEM_STATUSES) + " 可重试）");
        }
        Long actor = actorId(principal);
        int updated = jdbc.update("""
                update aap_config_batch_item
                   set status = 'PENDING', attempt_count = attempt_count + 1,
                       updated_at = now(), version = version + 1
                 where id = ? and batch_id = ? and deleted = false and status = ?
                """, itemId, batchId, current);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "明细状态已被他人改动，请刷新后重试");
        }
        refreshBatch(batchId, "RUNNING", actor);
        SupplyUnitViews.ConfigBatchItem view = ConfigBatchReader.readItem(jdbc, batchId, itemId);
        if (view == null) {
            throw new ApiException(ErrorCode.E_2001, "明细更新后回读失败（不谎报已受理）");
        }
        return view;
    }

    // ------------------------------------------------------------------ ADM-CB05

    /**
     * ADM-CB05 单模型回滚（202；`reason` 必填、留痕）。
     *
     * <p>语义：把**已执行成功**的明细置 `ROLLED_BACK` 并记下理由（`reason` 列 = 留痕，治理动作可追溯），
     * 批次转 `PARTIAL`（部分已回滚 ≠ 成功，不得继续称成功）并重算计数；兄弟项不动（R-59）。
     */
    @Transactional
    public SupplyUnitViews.ConfigBatchItem rollbackItem(AuthPrincipal principal, Long batchId, Long itemId,
                                                        SupplyUnitViews.RollbackRequest request) {
        String reason = request == null ? null : request.reason();
        if (reason == null || reason.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "reason",
                    "回滚理由必填（契约 requests/config-batch-rollback.schema.json 的 required）");
        }
        requireBatch(batchId);
        Map<String, Object> item = requireItem(batchId, itemId);
        String current = (String) item.get("status");
        if (!ROLLBACKABLE_ITEM_STATUS.equals(current)) {
            throw new ApiException(ErrorCode.E_1601,
                    "明细现状为 " + current + "，不可回滚（仅 " + ROLLBACKABLE_ITEM_STATUS + " 可回滚）");
        }
        Long actor = actorId(principal);
        int updated = jdbc.update("""
                update aap_config_batch_item
                   set status = 'ROLLED_BACK', reason = ?, updated_at = now(), version = version + 1
                 where id = ? and batch_id = ? and deleted = false and status = ?
                """, clip(reason, TEXT_LIMIT), itemId, batchId, current);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "明细状态已被他人改动，请刷新后重试");
        }
        refreshBatch(batchId, "PARTIAL", actor);
        SupplyUnitViews.ConfigBatchItem view = ConfigBatchReader.readItem(jdbc, batchId, itemId);
        if (view == null) {
            throw new ApiException(ErrorCode.E_2001, "明细回滚后回读失败（不谎报已回滚）");
        }
        return view;
    }

    // ------------------------------------------------------------------ 内部：scope / 差异

    /**
     * 解析 `scope` 为**实际存在的、未逻辑删除的**供给单元 id（升序，确定性）。
     *
     * <p>每个维度都经 SQL 落库核对（不直接信任请求里的 id：不存在的 id 不该变成明细行）。
     */
    private List<Long> resolveTargets(Object scope) {
        Map<String, Object> map = asMap(scope);
        if (map.isEmpty()) {
            return new ArrayList<>(jdbc.queryForList("""
                    select id from aap_supply_unit
                     where deleted = false and upper(status) <> 'OFFLINE'
                     order by id asc
                    """, Long.class));
        }
        Set<Long> ids = new LinkedHashSet<>();
        List<Long> unitIds = numbers(map.get("supplyUnitIds"));
        if (!unitIds.isEmpty()) {
            ids.addAll(jdbc.queryForList("select id from aap_supply_unit where deleted = false and id in ("
                    + placeholders(unitIds) + ") order by id asc", Long.class, unitIds.toArray()));
        }
        List<Long> providerIds = numbers(map.get("providerIds"));
        if (!providerIds.isEmpty()) {
            ids.addAll(jdbc.queryForList("select id from aap_supply_unit where deleted = false"
                    + " and provider_id in (" + placeholders(providerIds) + ") order by id asc",
                    Long.class, providerIds.toArray()));
        }
        List<String> modelNames = strings(map.get("modelNames"));
        if (!modelNames.isEmpty()) {
            List<String> upper = modelNames.stream().map(m -> m.toUpperCase(Locale.ROOT)).toList();
            ids.addAll(jdbc.queryForList("select id from aap_supply_unit where deleted = false"
                    + " and upper(model_name) in (" + placeholders(upper) + ") order by id asc",
                    Long.class, upper.toArray()));
        }
        List<String> tags = strings(map.get("tags"));
        if (!tags.isEmpty()) {
            // 标签维度挂在渠道绑定上（`aap_channel_binding.tag`）—— 供给单元本身没有标签列（V15 实测）
            ids.addAll(jdbc.queryForList("select distinct supply_unit_id from aap_channel_binding"
                    + " where deleted = false and supply_unit_id is not null and tag in ("
                    + placeholders(tags) + ") order by supply_unit_id asc", Long.class, tags.toArray()));
        }
        return new ArrayList<>(new TreeSet<>(ids));
    }

    /** 按下线/常规两种口径计算差异（T-M4-07 的纯逻辑核心；顺序按 unitId 升序，dry-run 清单可比对）。 */
    private List<ChannelConfigPlanner.Diff> planDiffs(ConfigBatchType type, List<Long> unitIds) {
        if (unitIds.isEmpty()) {
            return ChannelConfigPlanner.NO_DIFF;
        }
        List<Map<String, Object>> units = jdbc.queryForList("""
                select id, provider_id, model_name, granularity, routing_priority, routing_weight
                  from aap_supply_unit
                 where deleted = false and id in (""" + placeholders(unitIds) + ") order by id asc",
                unitIds.toArray());
        List<Long> providerIds = units.stream().map(u -> ConfigBatchReader.longOf(u.get("provider_id")))
                .distinct().toList();
        Map<Long, String> shortCodes = new LinkedHashMap<>();
        if (!providerIds.isEmpty()) {
            for (Map<String, Object> p : jdbc.queryForList("select id, short_code from aap_provider"
                    + " where deleted = false and id in (" + placeholders(providerIds) + ")", providerIds.toArray())) {
                shortCodes.put(ConfigBatchReader.longOf(p.get("id")), (String) p.get("short_code"));
            }
        }
        List<ChannelConfigPlanner.Target> targets = new ArrayList<>();
        for (Map<String, Object> u : units) {
            long unitId = ConfigBatchReader.longOf(u.get("id"));
            long providerId = ConfigBatchReader.longOf(u.get("provider_id"));
            String modelName = (String) u.get("model_name");
            targets.add(ChannelConfigPlanner.plan(new ChannelConfigPlanner.Input(
                    String.valueOf(unitId), providerId, shortCodes.get(providerId), modelName,
                    List.of(modelName == null ? "" : modelName), (String) u.get("granularity"),
                    intOf(u.get("routing_priority")), intOf(u.get("routing_weight")))));
        }
        List<ChannelConfigPlanner.Existing> existing = new ArrayList<>();
        for (Map<String, Object> b : jdbc.queryForList("""
                select supply_unit_id, channel_name, tag, priority, weight, models::text as models_text
                  from aap_channel_binding
                 where deleted = false and supply_unit_id in (""" + placeholders(unitIds) + ")",
                unitIds.toArray())) {
            existing.add(new ChannelConfigPlanner.Existing(
                    String.valueOf(ConfigBatchReader.longOf(b.get("supply_unit_id"))),
                    (String) b.get("channel_name"), parseStringArray((String) b.get("models_text")),
                    (String) b.get("tag"), intOf(b.get("priority")), intOf(b.get("weight")), null));
        }
        Set<String> offline = type.withdrawsChannel()
                ? unitIds.stream().map(String::valueOf).collect(Collectors.toCollection(LinkedHashSet::new))
                : Set.of();
        return ChannelConfigPlanner.diff(targets, existing, offline);
    }

    /** 差异清单（dry-run 的影响面展示；字段名与 `ADM-SU03` 的既有 payload 保持同族）。 */
    private Map<String, Object> diffPayload(ConfigBatchType type, ConfigBatchMode mode,
                                            Map<String, Long> byAction, long unplanned) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("mode", mode.name());
        payload.put("batch_type", type.name());
        payload.put("byAction", byAction);
        payload.put("unplanned", unplanned);
        payload.put("writeRequired", byAction.entrySet().stream()
                .filter(e -> ChannelConfigPlanner.isWrite(e.getKey()))
                .mapToLong(Map.Entry::getValue).sum());
        // 诚实标注：差异口径 = 渠道配置（T-M4-07）；写价与上游执行器尚未落地，不假装已规划
        payload.put("basis", "channel-config");
        payload.put("executor", "PENDING");
        return payload;
    }

    private Map<String, Object> itemRequestSummary(ConfigBatchType type, ConfigBatchMode mode, String action) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("batch_type", type.name());
        summary.put("mode", mode.name());
        summary.put("action", action);
        return summary;
    }

    // ------------------------------------------------------------------ 内部：校验 / 状态推进

    private ConfigBatchType type(String raw) {
        try {
            return ConfigBatchType.of(raw);
        } catch (IllegalArgumentException e) {
            throw ApiException.field(ErrorCode.E_1001, "batch_type", e.getMessage());
        }
    }

    private ConfigBatchMode mode(String raw) {
        try {
            return ConfigBatchMode.of(raw);
        } catch (IllegalArgumentException e) {
            throw ApiException.field(ErrorCode.E_1001, "mode", e.getMessage());
        }
    }

    /** R-57：限速默认 5，且**不接受抬高**（契约 `maximum: 5` ⇒ 上限即默认）。 */
    private int rateLimit(Integer perSec) {
        if (perSec == null) {
            return ChannelConfigPlanner.RATE_LIMIT_PER_SEC;
        }
        if (perSec < 1 || perSec > ChannelConfigPlanner.RATE_LIMIT_PER_SEC) {
            throw ApiException.field(ErrorCode.E_1001, "rate_limit_per_sec",
                    "限速必须在 1 ~ " + ChannelConfigPlanner.RATE_LIMIT_PER_SEC + " 之间（R-57）");
        }
        return perSec;
    }

    private Map<String, Object> requireBatch(Long batchId) {
        if (batchId == null) {
            throw ApiException.field(ErrorCode.E_1001, "batchId", "批次 id 非法");
        }
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select id, batch_no, status from aap_config_batch where id = ? and deleted = false", batchId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "配置批次不存在");
        }
        return rows.get(0);
    }

    private Map<String, Object> requireItem(Long batchId, Long itemId) {
        if (itemId == null) {
            throw ApiException.field(ErrorCode.E_1001, "itemId", "明细 id 非法");
        }
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select id, batch_id, status from aap_config_batch_item"
                        + " where id = ? and batch_id = ? and deleted = false", itemId, batchId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "批次明细不存在（或不属于该批次）");
        }
        return rows.get(0);
    }

    /** 批次状态与计数**重算**（状态只在明细真的变化后由本方法推进；留痕列同步刷新）。 */
    private void refreshBatch(Long batchId, String status, Long actor) {
        List<Map<String, Object>> rows = jdbc.queryForList("select status, count(*) as n"
                + " from aap_config_batch_item where batch_id = ? and deleted = false group by status", batchId);
        int succeeded = 0;
        int failed = 0;
        int mismatch = 0;
        for (Map<String, Object> row : rows) {
            int n = intOf(row.get("n"));
            switch ((String) row.get("status")) {
                case "SUCCEEDED" -> succeeded = n;
                case "FAILED" -> failed = n;
                case "MISMATCH" -> mismatch = n;
                default -> { }
            }
        }
        int updated = jdbc.update("""
                update aap_config_batch
                   set status = ?, succeeded_count = ?, failed_count = ?, mismatch_count = ?,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and deleted = false
                """, status, succeeded, failed, mismatch, actor, batchId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "批次状态推进失败，请刷新后重试");
        }
    }

    // ------------------------------------------------------------------ 内部：小工具

    private static String placeholders(List<?> values) {
        // 空列表会生成 `in ()`（SQL 语法错误 → HTTP 只见 500 E-2001，根因只在服务端日志那一行）：
        // 所有调用点都必须先判空，这里加一道**编程错误**自检，把静默的 SQL 报错变成响亮失败。
        if (values == null || values.isEmpty()) {
            throw new IllegalStateException("SQL IN 列表不得为空（调用点须先判空）");
        }
        return values.stream().map(v -> "?").collect(Collectors.joining(", "));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object scope) {
        return scope instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    private static List<Long> numbers(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        List<Long> out = new ArrayList<>();
        for (Object value : list) {
            if (value instanceof Number n) {
                out.add(n.longValue());
            } else if (value instanceof String s && !s.isBlank()) {
                try {
                    out.add(Long.parseLong(s.trim()));
                } catch (NumberFormatException ignored) {
                    // 非数字维度值直接忽略（它不可能命中任何供给单元）—— 不静默当成 0
                }
            }
        }
        return out;
    }

    private static List<String> strings(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        List<String> out = new ArrayList<>();
        for (Object value : list) {
            if (value instanceof String s && !s.isBlank()) {
                out.add(s.trim());
            }
        }
        return out;
    }

    private long newId(String sequence) {
        Long value = jdbc.queryForObject("select nextval('" + sequence + "')", Long.class);
        return value == null ? 0L : value;
    }

    private static Long actorId(AuthPrincipal principal) {
        return principal == null ? null : principal.accountId();
    }

    private static int intOf(Object value) {
        return value == null ? 0 : ((Number) value).intValue();
    }

    /** 列宽保护（自由文本最多 500 字符；不裁用户语义，只裁解释性文本）。 */
    private static String clip(String value, int max) {
        if (value == null) {
            return null;
        }
        String v = value.trim();
        return v.length() <= max ? v : v.substring(0, max);
    }

    /** jsonb 数组文本（如 {@code ["gpt-4o"]}）→ 字符串清单（PER_MODEL 下只有一个元素）。 */
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
}
