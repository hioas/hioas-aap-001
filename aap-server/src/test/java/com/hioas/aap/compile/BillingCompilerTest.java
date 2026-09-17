package com.hioas.aap.compile;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.quote.QuoteValidation;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T09 · 计费编译器与模拟验证（PRD 06 §3/§4.2；AC-28…31）。
 *
 * <p>重点钉死三件事：
 * <ol>
 *   <li><b>阶梯必须用 `len` 判档</b>——缓存命中把 `p` 压小也不能改变档位（用 `p` 判档是最典型的实现错）</li>
 *   <li><b>时段半开区间</b>——`09:00` 算峰、`12:00` 算非峰</li>
 *   <li><b>幂等哈希</b>——同价同规则 hash 不变，任何价格/规则改动 hash 必变</li>
 * </ol>
 */
class BillingCompilerTest {

    private static final BigDecimal IN = new BigDecimal("2.5");
    private static final BigDecimal OUT = new BigDecimal("15");
    private static final BigDecimal CR = new BigDecimal("0.25");

    private static BillingCompiler.ItemRules base(String model) {
        return new BillingCompiler.ItemRules(model, IN, OUT, CR, null, null, null, List.of());
    }

    private static BillingCompiler.ItemRules tiered(String model) {
        return new BillingCompiler.ItemRules(model, IN, OUT, CR, null, null,
                new QuoteValidation.TierRule("len", "OVERRIDE", List.of(
                        tier(0, "0", "512000", "2.5", "15"),
                        tier(1, "512000", "1024000", "5", "30"),
                        tier(2, "1024000", null, "10", "60"))), List.of());
    }

    private static QuoteValidation.Tier tier(int seq, String min, String max, String in, String out) {
        return new QuoteValidation.Tier(seq, new BigDecimal(min),
                max == null ? null : new BigDecimal(max), null,
                new BigDecimal(in), new BigDecimal(out), null, null);
    }

    private static BillingCompiler.ItemRules peak(String model) {
        return new BillingCompiler.ItemRules(model, IN, OUT, CR, null,
                new QuoteValidation.TimeRule("Asia/Shanghai", "ALL", new BigDecimal("1.5"), new BigDecimal("0.8"),
                        null, List.of(new QuoteValidation.Segment("09:00", "12:00"))),
                null, List.of());
    }

    @Test
    @DisplayName("R1 基础价：渲染文本与 PRD 示例同形，求值等于独立计算")
    void basePrice() {
        BillingCompiler.ItemRules item = base("gpt-4o");
        BillingExpr expr = BillingCompiler.compileItem(item, false);
        assertThat(expr.render()).isEqualTo("tier(\"base\", p * 2.5 + c * 15 + cr * 0.25)");

        var vector = new BillingVerifier.Vector(1000, 500, 200, 0, 1700, 10, 3);
        assertThat(expr.eval(BillingExpr.Ctx.of(1000, 500, 200, 0, 1700, 10, 3)))
                .isEqualByComparingTo(BillingVerifier.expected(item, vector));
    }

    @Test
    @DisplayName("R2 阶梯用 len 判档：缓存把 p 压到 50，len=512001 仍命中第二档（★ 用 p 判档会误判）")
    void tierUsesLenNotPromptTokens() {
        BillingCompiler.ItemRules item = tiered("gpt-4o");
        BillingExpr expr = BillingCompiler.compileItem(item, false);
        String text = expr.render();
        assertThat(text).contains("len <= 512000").contains("tier(\"t0_0_512K\"").contains("tier(\"t1_512K_1M\"");
        assertThat(text).doesNotContain("p <= ");

        // 档位 2：输入 5 / 输出 30
        var vector = new BillingVerifier.Vector(50, 500, 950, 0, 512001, 10, 3);
        BigDecimal actual = expr.eval(BillingExpr.Ctx.of(50, 500, 950, 0, 512001, 10, 3));
        BigDecimal expectedByLen = new BigDecimal("5").multiply(BigDecimal.valueOf(50))
                .add(new BigDecimal("30").multiply(BigDecimal.valueOf(500)))
                .add(CR.multiply(BigDecimal.valueOf(950)));
        assertThat(actual).isEqualByComparingTo(BillingExpr.scale(expectedByLen));
        assertThat(actual).isEqualByComparingTo(BillingVerifier.expected(item, vector));

        // 若错用 p 判档：p=50 → 会落到第一档，金额明显不同（此断言守住「不是靠运气通过」）
        BigDecimal wrongByPrompt = IN.multiply(BigDecimal.valueOf(50))
                .add(OUT.multiply(BigDecimal.valueOf(500)))
                .add(CR.multiply(BigDecimal.valueOf(950)));
        assertThat(actual).isNotEqualByComparingTo(BillingExpr.scale(wrongByPrompt));
    }

    @Test
    @DisplayName("R3 峰谷：09:00 命中峰值、12:00 与 08:00 走非峰（半开区间）")
    void peakOffPeakHalfOpen() {
        BillingCompiler.ItemRules item = peak("gpt-4o");
        BillingExpr expr = BillingCompiler.compileItem(item, false);
        assertThat(expr.render()).contains("hour(\"Asia/Shanghai\") >= 9")
                .contains("hour(\"Asia/Shanghai\") < 12").contains(".peak").contains(".offpeak");

        BigDecimal at9 = expr.eval(BillingExpr.Ctx.of(1000, 500, 0, 0, 1500, 9, 3));
        BigDecimal at12 = expr.eval(BillingExpr.Ctx.of(1000, 500, 0, 0, 1500, 12, 3));
        BigDecimal at8 = expr.eval(BillingExpr.Ctx.of(1000, 500, 0, 0, 1500, 8, 3));
        assertThat(at9).isGreaterThan(at12);
        assertThat(at12).isEqualByComparingTo(at8);

        var v9 = new BillingVerifier.Vector(1000, 500, 0, 0, 1500, 9, 3);
        assertThat(at9).isEqualByComparingTo(BillingVerifier.expected(item, v9));
    }

    @Test
    @DisplayName("R4 组合：外层分档 + 内层峰谷，档位名带 .peak/.offpeak；amount 与独立计算一致")
    void tierTimesTimeRule() {
        QuoteValidation.TierRule tierRule = new QuoteValidation.TierRule("len", "OVERRIDE", List.of(
                tier(0, "0", "512000", "2.5", "15"), tier(1, "512000", null, "5", "30")));
        BillingCompiler.ItemRules item = new BillingCompiler.ItemRules("gpt-4o", IN, OUT, CR, null,
                new QuoteValidation.TimeRule("Asia/Shanghai", "ALL", new BigDecimal("1.5"), new BigDecimal("0.8"),
                        null, List.of(new QuoteValidation.Segment("09:00", "12:00"))),
                tierRule, List.of());
        BillingExpr expr = BillingCompiler.compileItem(item, false);
        assertThat(expr.render()).contains("tier(\"t1_512K_plus.peak\"");

        var vector = new BillingVerifier.Vector(1000, 500, 0, 0, 600000, 10, 3);
        BigDecimal actual = expr.eval(BillingExpr.Ctx.of(1000, 500, 0, 0, 600000, 10, 3));
        BigDecimal expected = new BigDecimal("5").multiply(BigDecimal.valueOf(1000))
                .add(new BigDecimal("30").multiply(BigDecimal.valueOf(500)))
                .multiply(new BigDecimal("1.5"));
        assertThat(actual).isEqualByComparingTo(BillingExpr.scale(expected));
        assertThat(actual).isEqualByComparingTo(BillingVerifier.expected(item, vector));
    }

    @Test
    @DisplayName("source_hash（R-34）：同价同规则稳定；价格、倍率、时段、模型任一变化都必须变")
    void sourceHashIsSensitive() {
        String baseHash = BillingCompiler.sourceHash(List.of(base("gpt-4o")));
        assertThat(BillingCompiler.sourceHash(List.of(base("gpt-4o")))).isEqualTo(baseHash);

        assertThat(BillingCompiler.sourceHash(List.of(
                new BillingCompiler.ItemRules("gpt-4o", new BigDecimal("2.6"), OUT, CR, null, null, null, List.of()))))
                .isNotEqualTo(baseHash);
        assertThat(BillingCompiler.sourceHash(List.of(tiered("gpt-4o")))).isNotEqualTo(baseHash);
        assertThat(BillingCompiler.sourceHash(List.of(peak("gpt-4o")))).isNotEqualTo(baseHash);
        assertThat(BillingCompiler.sourceHash(List.of(base("gpt-4o-mini")))).isNotEqualTo(baseHash);
        // 顺序无关：多模型时按模型名排序后再算哈希
        assertThat(BillingCompiler.sourceHash(List.of(base("gpt-4o"), base("gpt-4o-mini"))))
                .isEqualTo(BillingCompiler.sourceHash(List.of(base("gpt-4o-mini"), base("gpt-4o"))));
    }

    @Test
    @DisplayName("模拟验证闸门：自洽的表达式全部用例通过；期望值入口与 AST 求值互相印证")
    void verifierPassesForConsistentRules() {
        BillingVerifier.Report report = BillingVerifier.verify("gpt-4o", peak("gpt-4o"),
                BillingCompiler.compileItem(peak("gpt-4o"), false));
        assertThat(report.status()).isEqualTo("PASSED");
        assertThat(report.caseTotal()).isGreaterThanOrEqualTo(6);
        assertThat(report.casePassed()).isEqualTo(report.caseTotal());
        assertThat(report.failedField()).isNull();
        assertThat(report.cases()).extracting(BillingVerifier.CaseResult::caseCode)
                .contains("V1", "V2", "V4a", "V4c", "V6");
    }

    @Test
    @DisplayName("档位标签与量纲：t0_0_512K / t1_512K_1M / t2_1M_plus；表达式按 $/1M 口径")
    void tierLabelsAndUnit() {
        assertThat(BillingCompiler.tierLabel(0, tier(0, "0", "512000", "1", "2"))).isEqualTo("t0_0_512K");
        assertThat(BillingCompiler.tierLabel(1, tier(1, "512000", "1024000", "1", "2"))).isEqualTo("t1_512K_1M");
        assertThat(BillingCompiler.tierLabel(2, tier(2, "1024000", null, "1", "2"))).isEqualTo("t2_1M_plus");
        assertThat(BillingCompiler.compact(new BigDecimal("1500"))).isEqualTo("1500");
        assertThat(BillingCompiler.compact(new BigDecimal("2000000"))).isEqualTo("2M");
    }

    @Test
    @DisplayName("R6 多模型：每个模型一条独立表达式，互不串味")
    void multiModelIndependent() {
        Map<String, BillingExpr> compiled = BillingCompiler.compile(
                List.of(base("gpt-4o"), tiered("gpt-4o-mini")), false);
        assertThat(compiled).containsOnlyKeys("gpt-4o", "gpt-4o-mini");
        assertThat(compiled.get("gpt-4o").render()).contains("tier(\"base\"");
        assertThat(compiled.get("gpt-4o-mini").render()).contains("len <= 512000");
    }
}
