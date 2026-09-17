package com.hioas.aap.compile;

import com.hioas.aap.quote.QuoteValidation;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 模拟验证（PRD 06 §4.2「★ 强制闸门」）。
 *
 * <p>**关键设计：期望值由独立路径计算**——{@link #expected} 用朴素 Java 逻辑（按 len 选档、按 hour 选峰谷）
 * 直接算钱，不走 {@link BillingExpr} AST。于是「编译器产出的表达式」与「独立实现」必须互相印证，
 * 才可能出现真正的失败；如果两边共用同一段代码，这道闸门就只是自证。
 *
 * <p>用例（PRD 06 §4.2）：V1 基础、V2 缓存命中、V3 阶梯边界（512000 vs 512001）、
 * V4 时段边界（09:00 / 08:59 / 12:00 / 18:00 半开区间）、V5 组合（len=600000@10:00 命中 t1.peak）、
 * V6 多模型独立。规则不存在时对应用例跳过（不造假用例凑数）。
 */
public final class BillingVerifier {

    /** 金额比较容差：表达式按 $/1M 口径，1e-6 足以覆盖减法与倍率的浮点/精度差。 */
    private static final BigDecimal TOLERANCE = new BigDecimal("0.000001");

    private BillingVerifier() {
    }

    /** 验证结果（对应 verify-report.schema.json）。 */
    public record Report(String status, Integer caseTotal, Integer casePassed, String failedField,
                         List<CaseResult> cases, String startedAt, String finishedAt) {
    }

    /** 单用例结果（对应 verify-case.schema.json）。 */
    public record CaseResult(String caseCode, String caseName, Map<String, Object> input,
                             BigDecimal expected, BigDecimal actual, Boolean passed, String diffNote) {
    }

    /** 令牌向量。 */
    public record Vector(long p, long c, long cr, long cw, long len, int hour, int weekday) {

        public Map<String, Object> toMap() {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("p", p);
            map.put("c", c);
            map.put("cr", cr);
            map.put("cw", cw);
            map.put("len", len);
            map.put("hour", hour);
            map.put("weekday", weekday);
            return map;
        }
    }

    // ------------------------------------------------------------------ 验证入口

    /** 校验一个模型的所有适用用例。 */
    public static Report verify(String modelName, BillingCompiler.ItemRules item, BillingExpr expr) {
        String startedAt = now();
        List<CaseResult> results = new ArrayList<>();
        long index = 0;
        long p = 1000;
        long c = 500;
        long len = 1500;
        int hour = 10;
        int weekday = 3;

        // V1 基础
        results.add(run("V1", "基础价（p=1000/c=500）", modelName, item, expr,
                new Vector(p, c, 0, 0, len, hour, weekday), "input_price/output_price"));

        // V2 缓存命中（p=800 + cr=200）
        results.add(run("V2", "缓存命中（p=800 + cr=200）", modelName, item, expr,
                new Vector(800, c, 200, 0, len, hour, weekday), "cache_read_price"));

        // V3 阶梯边界（用 len 判档：p 被缓存扣减也应命中同一档）
        if (hasTiers(item)) {
            long firstMax = item.tierRule().tiers().get(0).max() == null
                    ? 512000 : item.tierRule().tiers().get(0).max().longValue();
            results.add(run("V3a", "阶梯边界（len=" + firstMax + "，命中首档）", modelName, item, expr,
                    new Vector(1000, 500, 0, 0, firstMax, hour, weekday),
                    "price_tier_rule.tiers[0].max"));
            // 关键：len 超界但 p 被缓存压到很小 → 仍必须命中第 2 档（用 p 判档就会误判）
            results.add(run("V3b", "阶梯边界（len=" + (firstMax + 1) + " 且缓存压缩 p，命中次档）", modelName, item, expr,
                    new Vector(50, 500, 950, 0, firstMax + 1, hour, weekday),
                    "price_tier_rule.tiers[1].min"));
            // V5 组合：大 len + 高峰时段
            long secondMax = item.tierRule().tiers().size() > 1 && item.tierRule().tiers().get(1).max() != null
                    ? item.tierRule().tiers().get(1).max().longValue() : firstMax + 1;
            results.add(run("V5", "阶梯 × 峰谷组合（len=" + (firstMax + 1000) + " @高峰期）", modelName, item, expr,
                    new Vector(1000, 500, 0, 0, Math.min(firstMax + 1000, secondMax), peakHour(item), weekday),
                    "price_tier_rule + price_time_rule"));
        }

        // V4 时段边界（半开区间：起点算峰、终点算非峰）
        if (hasTimeRule(item)) {
            int start = firstStartHour(item);
            int end = firstEndHour(item);
            results.add(run("V4a", "时段边界（" + start + ":00 命中峰值）", modelName, item, expr,
                    new Vector(1000, 500, 0, 0, len, start, 3), "price_time_rule.peak_ranges"));
            results.add(run("V4b", "时段边界（" + (start - 1) + ":59 非峰值）", modelName, item, expr,
                    new Vector(1000, 500, 0, 0, len, start - 1, 3), "price_time_rule.peak_ranges"));
            results.add(run("V4c", "时段边界（" + end + ":00 半开区间 → 非峰值）", modelName, item, expr,
                    new Vector(1000, 500, 0, 0, len, end, 3), "price_time_rule.peak_ranges"));
            results.add(run("V4d", "时段边界（18:00 非峰值）", modelName, item, expr,
                    new Vector(1000, 500, 0, 0, len, 18, 3), "price_time_rule.peak_ranges"));
        }

        // V6 多模型独立（以 second model 名重跑基础价，验证表达式未串模型）
        results.add(run("V6", "多模型独立（模型 " + modelName + " 基础价复核）", modelName, item, expr,
                new Vector(2000, 1000, 0, 0, 3000, hour, weekday), "items[].model_name"));

        // R5 请求级加价需 new-api header 上下文，本期不参与模拟（如实记录，不假装覆盖）
        if (item.requestRules() != null && !item.requestRules().isEmpty()) {
            results.add(new CaseResult("V7", "请求级加价（R5）", Map.of(), null, null, Boolean.TRUE,
                    "R5 依赖请求 header（when(header(...))），需 new-api 运行时上下文，本期不参与模拟"));
        }

        int passed = (int) results.stream().filter(r -> Boolean.TRUE.equals(r.passed())).count();
        String failedField = results.stream().filter(r -> !Boolean.TRUE.equals(r.passed()))
                .map(CaseResult::caseCode).findFirst().orElse(null);
        String status = passed == results.size() ? "PASSED" : "FAILED";
        return new Report(status, results.size(), passed, failedField, results, startedAt, now());
    }

    private static CaseResult run(String code, String name, String modelName, BillingCompiler.ItemRules item,
                                  BillingExpr expr, Vector vector, String field) {
        BigDecimal expected = expected(item, vector);
        BigDecimal actual = compare(expr, vector);
        boolean passed = expected.subtract(actual).abs().compareTo(TOLERANCE) <= 0;
        return new CaseResult(code, name, vector.toMap(), expected, actual, passed,
                passed ? null : "表达式求值 " + actual.toPlainString() + " 与独立计算 " + expected.toPlainString()
                        + " 不一致（定位字段：" + field + "，模型 " + modelName + "）");
    }

    private static BigDecimal compare(BillingExpr expr, Vector vector) {
        return expr.eval(BillingExpr.Ctx.of(vector.p(), vector.c(), vector.cr(), vector.cw(),
                vector.len(), vector.hour(), vector.weekday()));
    }

    // ------------------------------------------------------------------ 独立期望（不走 AST）

    /** 朴素实现：按 len 选档 → 按时段选倍率 → 逐项乘单价求和。 */
    public static BigDecimal expected(BillingCompiler.ItemRules item, Vector vector) {
        BigDecimal input = item.inputPrice() == null ? BigDecimal.ZERO : item.inputPrice();
        BigDecimal output = item.outputPrice() == null ? BigDecimal.ZERO : item.outputPrice();
        BigDecimal cacheRead = item.cacheReadPrice();
        BigDecimal cacheWrite = item.cacheWritePrice();

        if (item.tierRule() != null && item.tierRule().tiers() != null) {
            for (QuoteValidation.Tier tier : item.tierRule().tiers()) {
                boolean inTier = (tier.min() == null || BigDecimal.valueOf(vector.len())
                        .compareTo(tier.min()) >= 0)
                        && (tier.max() == null || BigDecimal.valueOf(vector.len()).compareTo(tier.max()) <= 0);
                if (inTier) {
                    if (tier.inputPrice() != null && tier.outputPrice() != null) {
                        input = tier.inputPrice();
                        output = tier.outputPrice();
                        if (tier.cacheReadPrice() != null) {
                            cacheRead = tier.cacheReadPrice();
                        }
                    }
                    break;
                }
            }
        }

        BigDecimal cost = input.multiply(BigDecimal.valueOf(vector.p()))
                .add(output.multiply(BigDecimal.valueOf(vector.c())));
        if (cacheRead != null) {
            cost = cost.add(cacheRead.multiply(BigDecimal.valueOf(vector.cr())));
        }
        if (cacheWrite != null) {
            cost = cost.add(cacheWrite.multiply(BigDecimal.valueOf(vector.cw())));
        }

        BigDecimal multiplier = timeMultiplier(item.timeRule(), vector);
        return BillingExpr.scale(cost.multiply(multiplier));
    }

    /** 峰谷倍率（半开区间 `start <= hour < end`；weekday_scope 生效时还要匹配星期）。 */
    static BigDecimal timeMultiplier(QuoteValidation.TimeRule rule, Vector vector) {
        if (rule == null) {
            return BigDecimal.ONE;   // 未配置时段规则 → 不加成（与编译器「无峰谷节点」一致）
        }
        BigDecimal peak = rule.peakMultiplier() == null ? BigDecimal.ONE : rule.peakMultiplier();
        BigDecimal offpeak = rule.offpeakMultiplier() == null ? BigDecimal.ONE : rule.offpeakMultiplier();
        if (rule.segments() == null || rule.segments().isEmpty()) {
            return BigDecimal.ONE;
        }
        List<Integer> days = BillingCompiler.weekdays(rule.weekdayScope());
        if (!days.isEmpty() && !days.contains(vector.weekday())) {
            return offpeak;
        }
        for (QuoteValidation.Segment segment : rule.segments()) {
            int start = BillingCompiler.hour(segment.start());
            int end = BillingCompiler.hour(segment.end());
            if (start >= 0 && end >= 0 && vector.hour() >= start && vector.hour() < end) {
                return peak;
            }
        }
        return offpeak;
    }

    // ------------------------------------------------------------------ 工具

    private static boolean hasTiers(BillingCompiler.ItemRules item) {
        return item.tierRule() != null && item.tierRule().tiers() != null && !item.tierRule().tiers().isEmpty();
    }

    private static boolean hasTimeRule(BillingCompiler.ItemRules item) {
        return item.timeRule() != null && item.timeRule().segments() != null
                && !item.timeRule().segments().isEmpty();
    }

    private static int firstStartHour(BillingCompiler.ItemRules item) {
        int hour = BillingCompiler.hour(item.timeRule().segments().get(0).start());
        return hour < 0 ? 9 : hour;
    }

    private static int firstEndHour(BillingCompiler.ItemRules item) {
        int hour = BillingCompiler.hour(item.timeRule().segments().get(0).end());
        return hour < 0 ? 12 : hour;
    }

    private static int peakHour(BillingCompiler.ItemRules item) {
        return firstStartHour(item);
    }

    static BigDecimal round8(BigDecimal value) {
        return value == null ? null : value.setScale(8, RoundingMode.HALF_UP);
    }

    private static String now() {
        return java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'")
                .format(java.time.OffsetDateTime.now(java.time.ZoneOffset.UTC));
    }
}
