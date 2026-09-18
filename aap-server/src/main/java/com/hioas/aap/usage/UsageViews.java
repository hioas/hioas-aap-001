package com.hioas.aap.usage;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 用量响应模型（契约真源：`docs/backend/json-schema/models/usage-*.schema.json`，
 * 由 `tools/gen-backend-models.py` 从冻结清单生成；字段一律 snake_case，与数据字典 1:1）。
 *
 * <p><b>`/usage/summary` 是超集</b>（清单 §1.8 备注）：同一次响应既满足工作台
 * （环形图/模型 Top、`prompt_tokens`…`cache_read_tokens` 六类）又满足用量概览页
 * （逐日 `daily[]`、模型占比 `models[].share`、成本构成 `cost`、更新时间 `updated_at`）——
 * 两页共用端点，不各开一个（客户端 `aap-client/src/api/usage.ts` 亦只调 `/usage/summary`）。
 *
 * <p>缺字段一律回 null（前端渲染占位符「—」），禁止用 0 冒充没有数据。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class UsageViews {

    private UsageViews() {
    }

    /** 模型明细：`models[].share` 为 0–1 小数（客户端 `sharePercent` 会把 ≤1 的值当分数 ×100）。 */
    public record Model(
            @JsonProperty("model_name") String modelName,
            @JsonProperty("request_count") Long requestCount,
            @JsonProperty("total_tokens") Long totalTokens,
            @JsonProperty("amount") BigDecimal amount,
            @JsonProperty("share") BigDecimal share,
            @JsonProperty("percent") BigDecimal percent) {
    }

    /** 逐日用量（用量概览页近 7 日趋势的数据源；`stat_date` 为 UTC 日期）。 */
    public record Daily(
            @JsonProperty("stat_date") String statDate,
            @JsonProperty("date") String date,
            @JsonProperty("day") String day,
            @JsonProperty("request_count") Long requestCount,
            @JsonProperty("total_tokens") Long totalTokens,
            @JsonProperty("tokens") Long tokens,
            @JsonProperty("amount") BigDecimal amount) {
    }

    /**
     * 成本构成。`input`/`output` 当前恒为 null：小时用量表只有**总**折算金额 `cost_usd`，
     * 按 token 类型拆实际成本在清单/PRD 中无口径 → 不臆造（待拍板 D-API-10）。
     */
    public record Cost(
            @JsonProperty("input") BigDecimal input,
            @JsonProperty("output") BigDecimal output,
            @JsonProperty("platform_fee") BigDecimal platformFee,
            @JsonProperty("platform_fee_rate") BigDecimal platformFeeRate,
            @JsonProperty("total") BigDecimal total) {
    }

    /** USE-01 供应商用量概览（本人 provider 作用域）。 */
    public record Summary(
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("stat_from") String statFrom,
            @JsonProperty("stat_to") String statTo,
            @JsonProperty("month") String month,
            @JsonProperty("request_count") Long requestCount,
            @JsonProperty("prompt_tokens") Long promptTokens,
            @JsonProperty("completion_tokens") Long completionTokens,
            @JsonProperty("total_tokens") Long totalTokens,
            @JsonProperty("cache_read_tokens") Long cacheReadTokens,
            @JsonProperty("cache_write_tokens") Long cacheWriteTokens,
            @JsonProperty("cache_write_1h_tokens") Long cacheWrite1hTokens,
            @JsonProperty("image_input_tokens") Long imageInputTokens,
            @JsonProperty("audio_input_tokens") Long audioInputTokens,
            @JsonProperty("video_input_tokens") Long videoInputTokens,
            @JsonProperty("cache_hit_rate") Double cacheHitRate,
            @JsonProperty("cache_parse_rate") Double cacheParseRate,
            @JsonProperty("quota_raw") BigDecimal quotaRaw,
            @JsonProperty("cost_usd") BigDecimal costUsd,
            @JsonProperty("amount_total") BigDecimal amountTotal,
            @JsonProperty("amount") BigDecimal amount,
            @JsonProperty("mom_rate") Double momRate,
            @JsonProperty("mom_saved_amount") BigDecimal momSavedAmount,
            @JsonProperty("actual_unit_price") BigDecimal actualUnitPrice,
            @JsonProperty("deviation_rate") Double deviationRate,
            @JsonProperty("tier_distribution") Map<String, BigDecimal> tierDistribution,
            @JsonProperty("models") List<Model> models,
            @JsonProperty("daily") List<Daily> daily,
            @JsonProperty("cost") Cost cost,
            @JsonProperty("updated_at") String updatedAt,
            @JsonProperty("refreshed_at") String refreshedAt,
            @JsonProperty("degraded") Boolean degraded) {
    }

    /** USE-02 / ADM-U01 小时桶（= `aap_usage_hourly` 字典字段，供应商端只回自己渠道）。 */
    public record Bucket(
            @JsonProperty("stat_hour") String statHour,
            @JsonProperty("channel_id") String channelId,
            @JsonProperty("channel_name") String channelName,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("model_name") String modelName,
            @JsonProperty("group_name") String groupName,
            @JsonProperty("request_count") Long requestCount,
            @JsonProperty("prompt_tokens") Long promptTokens,
            @JsonProperty("completion_tokens") Long completionTokens,
            @JsonProperty("total_tokens") Long totalTokens,
            @JsonProperty("cache_read_tokens") Long cacheReadTokens,
            @JsonProperty("cache_write_tokens") Long cacheWriteTokens,
            @JsonProperty("cache_write_1h_tokens") Long cacheWrite1hTokens,
            @JsonProperty("image_input_tokens") Long imageInputTokens,
            @JsonProperty("audio_input_tokens") Long audioInputTokens,
            @JsonProperty("video_input_tokens") Long videoInputTokens,
            @JsonProperty("quota_raw") BigDecimal quotaRaw,
            @JsonProperty("cost_usd") BigDecimal costUsd,
            @JsonProperty("cache_parse_status") String cacheParseStatus,
            @JsonProperty("source") String source,
            @JsonProperty("tier_distribution") Map<String, Object> tierDistribution,
            @JsonProperty("collected_at") String collectedAt) {
    }

    /**
     * ADM-U02 聚合批次结果。`cache_parse_status` 为本批次的聚合口径：
     * 只要有一个桶无缓存字段即 `NO_CACHE_FIELD`，全可解析为 `OK`（枚举真源 = 生成器 `CacheParseStatus`）。
     */
    public record RefreshResult(
            @JsonProperty("batch_id") String batchId,
            @JsonProperty("inserted") Integer inserted,
            @JsonProperty("updated") Integer updated,
            @JsonProperty("batch_total") Integer batchTotal,
            @JsonProperty("cache_parse_status") String cacheParseStatus,
            @JsonProperty("from") String from,
            @JsonProperty("to") String to) {
    }
}
