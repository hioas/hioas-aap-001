package com.hioas.aap.usage;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.usage.UsageMetrics.ModelTokens;
import com.hioas.aap.usage.UsageMetrics.QuotedPrice;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T12 · 用量对账纯函数单测（AC-43 缓存字段 / AC-45 缓存缺失 / AC-46 对账指标）。
 *
 * <p>为什么单测：比率、单价、环比、差异率这些**口径**决定报告数字对不对，
 * 但它们的分母可以为 0、基期可以缺失。走 HTTP 只能覆盖一种输入组合，
 * 边界（分母 0 / 基期为 0 / 缺报价）必须在纯函数上逐条钉死。
 *
 * <p>口径红线（`docs/api/接口字段级schema.md` §0）：**不得用 0 冒充「没有数据」** ——
 * 分母为 0、基期缺失、报价缺失一律回 {@code null}，由前端渲染占位符。
 */
class UsageMetricsTest {

    private static final double EPS = 1e-9;

    @Test
    @DisplayName("AC-43 缓存命中率 = 缓存读 /(输入 + 缓存读)；分母 0 → null（不臆造 0）")
    void cacheHitRate() {
        // 2000 / (1400 + 2000) = 0.5882352941176470…
        assertThat(UsageMetrics.cacheHitRate(2000L, 1400L)).isCloseTo(0.5882352941176470, org.assertj.core.data.Offset.offset(EPS));
        assertThat(UsageMetrics.cacheHitRate(0L, 0L)).isNull();
        assertThat(UsageMetrics.cacheHitRate(500L, 0L)).isEqualTo(1.0d);
        assertThat(UsageMetrics.rate(5L, 0L)).isNull();
    }

    @Test
    @DisplayName("AC-45 缓存可解析率 = OK 桶数 / 总桶数；无桶 → null")
    void cacheParseRate() {
        assertThat(UsageMetrics.cacheParseRate(1L, 2L)).isEqualTo(0.5d);
        assertThat(UsageMetrics.cacheParseRate(0L, 0L)).isNull();
        assertThat(UsageMetrics.cacheParseRate(2L, 2L)).isEqualTo(1.0d);
    }

    @Test
    @DisplayName("AC-46 实际单价 = 金额 /(词元 / 1e6)；词元 0 或金额缺失 → null")
    void actualUnitPrice() {
        // 4.0 USD / (2000 / 1e6) = 2000 USD per 1M tokens
        assertThat(UsageMetrics.actualUnitPrice(new BigDecimal("4.0"), 2000L))
                .isEqualByComparingTo(new BigDecimal("2000"));
        assertThat(UsageMetrics.actualUnitPrice(new BigDecimal("4.0"), 0L)).isNull();
        assertThat(UsageMetrics.actualUnitPrice(null, 2000L)).isNull();
    }

    @Test
    @DisplayName("AC-46 环比：基期缺失或为 0 → null；可负（(4−99)/99 ≈ −0.9596）")
    void momRate() {
        assertThat(UsageMetrics.momRate(new BigDecimal("4.0"), new BigDecimal("99.0")))
                .isCloseTo(-0.9595959595959596, org.assertj.core.data.Offset.offset(EPS));
        assertThat(UsageMetrics.momRate(new BigDecimal("4.0"), new BigDecimal("0"))).isNull();
        assertThat(UsageMetrics.momRate(new BigDecimal("4.0"), null)).isNull();
        assertThat(UsageMetrics.momSavedAmount(new BigDecimal("4.0"), new BigDecimal("99.0")))
                .isEqualByComparingTo(new BigDecimal("95.0"));
        assertThat(UsageMetrics.momSavedAmount(new BigDecimal("4.0"), null)).isNull();
    }

    @Test
    @DisplayName("AC-46 差异率 ±5% 告警：|rate| > 0.05 才告警；边界 0.05 不告警；缺基准不告警")
    void deviation() {
        assertThat(UsageMetrics.deviationRate(new BigDecimal("2.5"), new BigDecimal("2.0")))
                .isCloseTo(0.25, org.assertj.core.data.Offset.offset(EPS));
        assertThat(UsageMetrics.deviationRate(new BigDecimal("2.0"), new BigDecimal("2.0"))).isEqualTo(0.0d);
        assertThat(UsageMetrics.deviationRate(new BigDecimal("2.0"), new BigDecimal("0"))).isNull();
        assertThat(UsageMetrics.deviationRate(null, new BigDecimal("2.0"))).isNull();

        assertThat(UsageMetrics.deviationAlert(0.25d)).isTrue();
        assertThat(UsageMetrics.deviationAlert(-0.051d)).isTrue();
        assertThat(UsageMetrics.deviationAlert(0.05d)).as("阈值 ±5%：等于 5% 不告警").isFalse();
        assertThat(UsageMetrics.deviationAlert(-0.05d)).isFalse();
        assertThat(UsageMetrics.deviationAlert(null)).isFalse();
    }

    @Test
    @DisplayName("AC-46 报价加权单价：按各模型词元结构加权（含缓存读价），缺价模型不参与")
    void quotedWeightedUnitPrice() {
        List<ModelTokens> models = List.of(
                new ModelTokens("gpt-4o", 1400L, 600L, 2000L, 2000L));
        Map<String, QuotedPrice> prices = Map.of(
                "gpt-4o", new QuotedPrice(new BigDecimal("2.0"), new BigDecimal("4.0"), new BigDecimal("0.5")));
        // 报价金额 = (1400×2 + 600×4 + 2000×0.5)/1e6 = 0.0062 USD；单价 = 0.0062 / 0.002 = 3.1 USD/1M
        assertThat(UsageMetrics.quotedWeightedUnitPrice(models, prices, 2000L))
                .isEqualByComparingTo(new BigDecimal("3.1"));

        // 缺价模型 → 无基准
        assertThat(UsageMetrics.quotedWeightedUnitPrice(models, Map.of(), 2000L)).isNull();
        // 词元为 0 → 无基准
        assertThat(UsageMetrics.quotedWeightedUnitPrice(models, prices, 0L)).isNull();
    }
}
