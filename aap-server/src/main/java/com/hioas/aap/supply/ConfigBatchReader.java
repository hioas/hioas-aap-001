package com.hioas.aap.supply;

import com.hioas.aap.common.JsonCodec;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * 配置批次**读模型**（`ADM-CB02`/`ADM-CB03` 与 `ADM-SU03` 共用同一读出口）。
 *
 * <p>为什么抽成一类（踩坑 22/44）：同一模型的「写后回读」若在两个服务里各写一份，形状必然分叉
 * （一边补 `items`、一边漏），而契约测试只校验**响应体**、覆盖门禁只比「方法 + 路径」
 * ⇒ 分叉对两套门禁完全不可见。这里把列清单与子集合补齐收敛到一处：
 * <ul>
 *   <li>批次行与明细一律 `deleted = false`；明细按 `id asc`（确定性，dry-run 清单可比对）；</li>
 *   <li>列表场景**一次**取回全部明细（`batch_id in (...)`，避免 N+1，同时保证同一页内形状一致）；</li>
 *   <li>时间出口一律 RFC3339 **UTC**（字面量 `Z` + 调用点先归一，与全仓口径一致）。</li>
 * </ul>
 */
final class ConfigBatchReader {

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private static final String BATCH_COLUMNS =
            "select id, batch_no, batch_type, mode, trigger_source, status, total_count, succeeded_count,"
                    + " failed_count, mismatch_count, rate_limit_per_sec, diff_payload::text as diff_payload,"
                    + " started_at, finished_at, created_at from aap_config_batch where deleted = false";

    private static final String ITEM_COLUMNS =
            "select id, batch_id, supply_unit_id, provider_id, model_name, action, status, readback_equal,"
                    + " attempt_count, last_error, created_at from aap_config_batch_item where deleted = false";

    private ConfigBatchReader() {
    }

    /** 读单个批次（含明细）；不存在或已逻辑删除返回 {@code null}。 */
    static SupplyUnitViews.ConfigBatch read(JdbcTemplate jdbc, Long batchId) {
        if (batchId == null) {
            return null;
        }
        List<SupplyUnitViews.ConfigBatch> one = readAll(jdbc, List.of(batchId));
        return one.isEmpty() ? null : one.get(0);
    }

    /** 批量读（列表用）：顺序 `created_at desc, id desc`，与列表排序一致。 */
    static List<SupplyUnitViews.ConfigBatch> readAll(JdbcTemplate jdbc, List<Long> batchIds) {
        if (batchIds == null || batchIds.isEmpty()) {
            return List.of();
        }
        String placeholders = batchIds.stream().map(id -> "?").collect(Collectors.joining(", "));
        Object[] args = batchIds.toArray();
        List<Map<String, Object>> rows = jdbc.queryForList(
                BATCH_COLUMNS + " and id in (" + placeholders + ") order by created_at desc, id desc", args);
        Map<Long, List<SupplyUnitViews.ConfigBatchItem>> itemsByBatch = new LinkedHashMap<>();
        for (Map<String, Object> item : jdbc.queryForList(
                ITEM_COLUMNS + " and batch_id in (" + placeholders + ") order by batch_id asc, id asc", args)) {
            itemsByBatch.computeIfAbsent(longOf(item.get("batch_id")), k -> new ArrayList<>()).add(itemView(item));
        }
        List<SupplyUnitViews.ConfigBatch> out = new ArrayList<>(rows.size());
        for (Map<String, Object> r : rows) {
            out.add(new SupplyUnitViews.ConfigBatch(
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
                    itemsByBatch.getOrDefault(longOf(r.get("id")), List.of())));
        }
        return out;
    }

    /** 读单个明细（必须属于该批次）；不存在或已逻辑删除返回 {@code null}（踩坑：归属校验不泄露跨批次存在性）。 */
    static SupplyUnitViews.ConfigBatchItem readItem(JdbcTemplate jdbc, Long batchId, Long itemId) {
        if (batchId == null || itemId == null) {
            return null;
        }
        List<Map<String, Object>> rows = jdbc.queryForList(
                ITEM_COLUMNS + " and batch_id = ? and id = ?", batchId, itemId);
        return rows.isEmpty() ? null : itemView(rows.get(0));
    }

    private static SupplyUnitViews.ConfigBatchItem itemView(Map<String, Object> it) {
        return new SupplyUnitViews.ConfigBatchItem(
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
                rfc3339(it.get("created_at")));
    }

    static String idOf(Object value) {
        return value == null ? null : String.valueOf(((Number) value).longValue());
    }

    static long longOf(Object value) {
        return value == null ? 0L : ((Number) value).longValue();
    }

    static Integer intOrNull(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static String rfc3339(Object value) {
        if (value == null) {
            return null;
        }
        OffsetDateTime odt = value instanceof OffsetDateTime o ? o
                : ((java.sql.Timestamp) value).toInstant().atOffset(ZoneOffset.UTC);
        return RFC3339.format(odt.withOffsetSameInstant(ZoneOffset.UTC));
    }
}
