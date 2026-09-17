package com.hioas.aap.quote;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 报价响应模型（契约：`docs/backend/json-schema/models/quote-*.schema.json`）。
 *
 * <p>字段名与 Schema **逐字对齐**（record 组件名即序列化名），并同时提供 `id`/`quote_id`、`item_id`/`id`
 * 这类客户端容错双读键（`aap-client/src/utils/*-model.ts` 两种写法都读）。
 */
public final class QuoteViews {

    private QuoteViews() {
    }

    /** 报价单列表行（quote-row）。 */
    public record Row(String id, String quote_id, String title, String name, String quote_no, String status,
                      String currency, Integer item_count, List<?> items, String amount_total,
                      String updated_at, String created_at, String contract_id,
                      String valid_from, String valid_to, String credential_id) {
    }

    /** 时段片段（客户端与 ER 都命名为 peak_ranges 的元素）。 */
    public record Range(String start, String end) {
    }

    /** 时段规则（price-time-rule；peak_ranges 为 Schema 必填）。 */
    public record TimeRule(String tz, String weekday_scope, List<Range> peak_ranges, BigDecimal peak_multiplier,
                           BigDecimal offpeak_multiplier, BigDecimal peak_price_override) {
    }

    /** 阶梯档位（price-tier）。 */
    public record Tier(Integer seq, BigDecimal min, BigDecimal max, String label, BigDecimal input_price,
                       BigDecimal output_price, BigDecimal cache_read_price, BigDecimal multiplier) {
    }

    /** 阶梯规则（price-tier-rule）。 */
    public record TierRule(String tier_field, String price_strategy, List<Tier> tiers) {
    }

    /** 请求规则（request-rule）；客户端发 {field,granularity,tz,op,value,multiplier}，服务端归一为 when_expr。 */
    public record RequestRule(String when, String when_expr, BigDecimal multiplier, Boolean enabled,
                              String field, String granularity, String tz, String op, String value) {
    }

    /** 明细行（quote-item）。 */
    public record Item(String item_id, String id, String quote_id, String quoteId, String model_name,
                       String modelName, String model_alias,
                       BigDecimal input_price, BigDecimal output_price,
                       BigDecimal cache_read_price, BigDecimal cache_write_price, BigDecimal cache_write_1h_price,
                       BigDecimal image_input_price, BigDecimal image_output_price,
                       BigDecimal audio_input_price, BigDecimal audio_output_price,
                       String tier, String billing_mode, String compile_status, String note,
                       TimeRule time_rule, TierRule tier_rule, List<RequestRule> request_rules,
                       String created_at, String updated_at, Integer version, List<String> warnings) {
    }

    /** 明细行集合响应（QT-05/QT-06：{items:[QuoteItem],total}）。 */
    public record Items(List<Item> items, Integer total, List<String> warnings) {
    }

    /** 创建响应（QT-02：{quote_id,quote_no,status,items[]}）。 */
    public record Created(String quote_id, String id, String quote_no, String status, List<Item> items) {
    }

    /** 报价单详情（quote-detail：报价单 + 明细行）。 */
    public record Detail(String quote_id, String id, String quote_no, String name, String title,
                         String provider_id, String credential_id, String status, Integer current_version,
                         String currency, String valid_from, String valid_to, Integer item_count,
                         String remark, String reject_reason_code, String reject_reason_text,
                         String submitted_at, String reviewed_at, String contract_id, String source_hash,
                         Integer item_total, List<Item> items, String amount_total,
                         String updated_at, String created_at, Integer version,
                         List<String> warnings) {
    }

    /** 版本快照（quote-version）。 */
    public record Version(String id, String quote_id, Integer version_no, Map<String, Object> snapshot,
                          String source_hash, String created_at) {
    }
}
