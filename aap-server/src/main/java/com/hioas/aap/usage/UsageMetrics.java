package com.hioas.aap.usage;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Map;

/**
 * 用量对账纯函数（AC-43 缓存字段 / AC-45 缓存缺失 / AC-46 对账指标）。
 *
 * <p><b>为什么单独成类</b>：这些比率的分母可能为 0、基期可能缺失、报价基准可能不存在 ——
 * 走 HTTP 一次只能覆盖一种输入组合，边界必须在纯函数上逐条钉死（见 {@code UsageMetricsTest}）。
 *
 * <p><b>红线</b>（`docs/api/接口字段级schema.md` §0）：**不得用 0 冒充「没有数据」**。
 * 分母为 0 / 基期缺失 / 报价缺失一律返回 {@code null}，由前端渲染占位符。
 *
 * <p>口径来源与推断标注见 `.agents/state/aap-server-tdd-state.md` R12（D-API-08/09/10）。
 */
public final class UsageMetrics {

    /** 差异率告警阈值 ±5%（11-PRD §4「对账视图指标」）。 */
    public static final double DEVIATION_ALERT_THRESHOLD = 0.05;

    private static final BigDecimal TOKENS_PER_MILLION = new BigDecimal("1000000");
    private static final int TOKEN_SCALE = 12;
    private static final int PRICE_SCALE = 6;

    private UsageMetrics() {
    }

    /** 单模型的词元结构（报价加权单价的权重来源）。 */
    public record ModelTokens(String modelName, long promptTokens, long completionTokens,
                              long cacheReadTokens, long totalTokens) {
    }

    /** 报价基准单价（USD / 1M tokens，取自 `aap_quote_item`）。 */
    public record QuotedPrice(BigDecimal inputPrice, BigDecimal outputPrice, BigDecimal cacheReadPrice) {
    }

    /** 比率；分母 ≤ 0 → null（禁止用 0 冒充无数据）。 */
    public static Double rate(long numerator, long denominator) {
        if (denominator <= 0) {
            return null;
        }
        return (double) numerator / denominator;
    }

    /** 缓存命中率 = 缓存读 /(输入 + 缓存读)（缓存读视为输入的一部分）。 */
    public static Double cacheHitRate(long cacheReadTokens, long promptTokens) {
        return rate(cacheReadTokens, cacheReadTokens + promptTokens);
    }

    /** 缓存可解析率 = OK 桶数 / 总桶数（U2/A14）。 */
    public static Double cacheParseRate(long okBuckets, long totalBuckets) {
        return rate(okBuckets, totalBuckets);
    }

    /** 实际单价 = 金额 /(词元 / 1e6)，单位 USD/1M tokens。 */
    public static BigDecimal actualUnitPrice(BigDecimal costUsd, long totalTokens) {
        if (costUsd == null || totalTokens <= 0) {
            return null;
        }
        BigDecimal millions = BigDecimal.valueOf(totalTokens)
                .divide(TOKENS_PER_MILLION, TOKEN_SCALE, RoundingMode.HALF_UP);
        return costUsd.divide(millions, PRICE_SCALE, RoundingMode.HALF_UP);
    }

    /** 环比（MoM）：基期缺失或为 0 → null（可负）。 */
    public static Double momRate(BigDecimal current, BigDecimal previous) {
        if (current == null || previous == null || previous.signum() == 0) {
            return null;
        }
        return current.subtract(previous).doubleValue() / previous.doubleValue();
    }

    /** 「较上月节省」= 基期 − 当期（可负 = 反而更贵）。 */
    public static BigDecimal momSavedAmount(BigDecimal current, BigDecimal previous) {
        if (current == null || previous == null) {
            return null;
        }
        return previous.subtract(current);
    }

    /** 差异率 = (实际单价 − 报价单价）/ 报价单价；报价缺失/为 0 → null。 */
    public static Double deviationRate(BigDecimal actualUnitPrice, BigDecimal quotedUnitPrice) {
        if (actualUnitPrice == null || quotedUnitPrice == null || quotedUnitPrice.signum() == 0) {
            return null;
        }
        return actualUnitPrice.subtract(quotedUnitPrice).doubleValue() / quotedUnitPrice.doubleValue();
    }

    /** |差异率| > 5% 触发告警（11-PRD §4）；无基准不告警。 */
    public static boolean deviationAlert(Double deviationRate) {
        return deviationRate != null && Math.abs(deviationRate) > DEVIATION_ALERT_THRESHOLD;
    }

    /**
     * 报价加权单价（USD / 1M tokens）：按各模型的输入/输出/缓存读词元结构加权，
     * 再折算到窗口总词元。缺价模型不参与加权；无任何可用报价或总词元为 0 → null。
     */
    public static BigDecimal quotedWeightedUnitPrice(List<ModelTokens> models, Map<String, QuotedPrice> prices,
                                                     long totalTokens) {
        if (models == null || models.isEmpty() || prices == null || prices.isEmpty() || totalTokens <= 0) {
            return null;
        }
        BigDecimal quotedAmount = BigDecimal.ZERO;
        boolean anyPriced = false;
        for (ModelTokens model : models) {
            QuotedPrice price = prices.get(model.modelName());
            if (price == null) {
                continue;
            }
            anyPriced = true;
            quotedAmount = quotedAmount.add(amountOf(price.inputPrice(), model.promptTokens()));
            quotedAmount = quotedAmount.add(amountOf(price.outputPrice(), model.completionTokens()));
            quotedAmount = quotedAmount.add(amountOf(price.cacheReadPrice(), model.cacheReadTokens()));
        }
        if (!anyPriced) {
            return null;
        }
        BigDecimal millions = BigDecimal.valueOf(totalTokens)
                .divide(TOKENS_PER_MILLION, TOKEN_SCALE, RoundingMode.HALF_UP);
        return quotedAmount.divide(millions, PRICE_SCALE, RoundingMode.HALF_UP);
    }

    private static BigDecimal amountOf(BigDecimal pricePerMillion, long tokens) {
        if (pricePerMillion == null || tokens <= 0) {
            return BigDecimal.ZERO;
        }
        return pricePerMillion.multiply(BigDecimal.valueOf(tokens))
                .divide(TOKENS_PER_MILLION, TOKEN_SCALE, RoundingMode.HALF_UP);
    }

    /** 6 位小数（USD / numeric(18,6)）空安全。 */
    public static BigDecimal scale6(BigDecimal value) {
        return value == null ? null : value.setScale(PRICE_SCALE, RoundingMode.HALF_UP);
    }
}
