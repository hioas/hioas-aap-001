package com.hioas.aap.compile;

import com.hioas.aap.quote.QuoteValidation;
import java.math.BigDecimal;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 计费编译器（真源 `06-报价模型与计费编译规则.md §3`）。
 *
 * <p>编译规则：
 * <ul>
 *   <li>R1 基础价：{@code p * input + c * output [+ cr * cache_read] [+ cw * cache_write]}</li>
 *   <li>R2 阶梯价：**必须用 `len` 判档**（`p` 会被缓存命中的自动排除机制扣减 → 用 p 判档会误判）</li>
 *   <li>R3 峰谷价：`hour(tz)` 半开区间抽为公共子条件，峰值 × peak_multiplier、非峰 × offpeak_multiplier</li>
 *   <li>R4 组合：外层分档（len）、内层分时段（hour），档位命名 `t{i}_{label}.{peak|offpeak}`</li>
 *   <li>R5 请求级加价：`|||when(...) * N`，本期仅管理端高级模式（**不参与模拟**，见 verify 说明）</li>
 *   <li>R6 多模型：每模型一条独立表达式，失败可单模型回滚</li>
 * </ul>
 *
 * <p>计价量纲：表达式按 **每 1M token 的美元额** 输出（PRD 原文 `p * 2.5` 即 $/1M 口径），
 * 模拟验证两侧同口径比较，避免「除以 1e6 的位置不同」造成假绿。
 */
public final class BillingCompiler {

    /** 编译器版本：表达式语义变更时必须递增（写入 aap_compiled_expression.compiler_version）。 */
    public static final String COMPILER_VERSION = "v1";

    private BillingCompiler() {
    }

    /** 单模型编译输入。 */
    public record ItemRules(String modelName,
                            BigDecimal inputPrice, BigDecimal outputPrice,
                            BigDecimal cacheReadPrice, BigDecimal cacheWritePrice,
                            QuoteValidation.TimeRule timeRule,
                            QuoteValidation.TierRule tierRule,
                            List<QuoteValidation.RequestRule> requestRules) {
    }

    // ------------------------------------------------------------------ 编译

    /** R6：多模型 → 每模型一条独立表达式。 */
    public static Map<String, BillingExpr> compile(List<ItemRules> items, boolean admin) {
        Map<String, BillingExpr> byModel = new LinkedHashMap<>();
        for (ItemRules item : items) {
            byModel.put(item.modelName(), compileItem(item, admin));
        }
        return byModel;
    }

    /** 编译单个模型。 */
    public static BillingExpr compileItem(ItemRules item, boolean admin) {
        BillingExpr base = basePrice(item);
        BillingExpr body = item.tierRule() != null && item.tierRule().tiers() != null
                && !item.tierRule().tiers().isEmpty()
                ? tiered(item, base)
                : withTimeRule(item, base, "base");
        return applyRequestRules(body, item, admin);
    }

    /** R1 基础价。 */
    private static BillingExpr.Price basePrice(ItemRules item) {
        return new BillingExpr.Price(item.inputPrice(), item.outputPrice(),
                item.cacheReadPrice(), item.cacheWritePrice(), null);
    }

    /** R2/R4 阶梯（含档内峰谷）。 */
    private static BillingExpr tiered(ItemRules item, BillingExpr base) {
        List<QuoteValidation.Tier> tiers = item.tierRule().tiers();
        BillingExpr current = null;
        for (int i = tiers.size() - 1; i >= 0; i--) {
            QuoteValidation.Tier tier = tiers.get(i);
            String tierName = tierLabel(i, tier);
            BillingExpr inner = tierPrice(tier, base);
            BillingExpr withTime = withTimeRule(item, inner, tierName);
            current = current == null
                    ? withTime
                    // 末档（max == null）不加条件，作为下降分支
                    : new BillingExpr.Cond(new BillingExpr.Condition.LenLte(tier.max().longValueExact()),
                            withTime, current);
        }
        return current;
    }

    /**
     * OVERRIDE 策略：档内有输入/输出价则用档位价，否则回落基础价。
     *
     * <p><b>缓存价回落（D-COMPILE-01）</b>：档内没给 {@code cache_read_price} 时**回落到明细行价**。
     * PRD 06 §3 R2 的示例写作 `tier("t0_0_512K", p * 2.5 + c * 15)`（省略 cr 项），
     * 但按字面照做会让缓存命中的 token **一分钱不计**（上游白送），与 15-数据字典给
     * {@code aap_price_tier.cache_read_price} 留列的设计意图冲突。取「不漏计费」的更安全一侧。
     */
    private static BillingExpr tierPrice(QuoteValidation.Tier tier, BillingExpr base) {
        if (tier.inputPrice() == null || tier.outputPrice() == null) {
            return base;
        }
        BillingExpr.Price basePrice = (BillingExpr.Price) base;
        BigDecimal cacheRead = tier.cacheReadPrice() != null
                ? tier.cacheReadPrice() : basePrice.cacheRead();
        return new BillingExpr.Price(tier.inputPrice(), tier.outputPrice(), cacheRead,
                basePrice.cacheWrite(), null);
    }

    /** R3/R4 内层峰谷：`hour` 半开区间，命中 → × peak、否则 × offpeak。 */
    private static BillingExpr withTimeRule(ItemRules item, BillingExpr inner, String tierName) {
        QuoteValidation.TimeRule rule = item.timeRule();
        if (rule == null || rule.segments() == null || rule.segments().isEmpty()) {
            return new BillingExpr.Tier(tierName, inner);
        }
        List<BillingExpr.Condition> ranges = new ArrayList<>();
        for (QuoteValidation.Segment segment : rule.segments()) {
            int start = hour(segment.start());
            int end = hour(segment.end());
            if (start < 0 || end < 0) {
                continue;
            }
            ranges.add(new BillingExpr.Condition.HourRange(
                    rule.tz() == null ? "Asia/Shanghai" : rule.tz(), start, end));
        }
        List<BillingExpr.Condition> all = new ArrayList<>(ranges);
        List<Integer> days = weekdays(rule.weekdayScope());
        if (!days.isEmpty()) {
            all.add(new BillingExpr.Condition.WeekdayIn(
                    rule.tz() == null ? "Asia/Shanghai" : rule.tz(), days));
        }
        if (all.isEmpty()) {
            return new BillingExpr.Tier(tierName, inner);
        }
        BillingExpr.Condition condition = all.size() == 1 ? all.get(0) : new BillingExpr.Condition.And(all);
        BigDecimal peak = rule.peakMultiplier() == null ? BigDecimal.ONE : rule.peakMultiplier();
        BigDecimal offpeak = rule.offpeakMultiplier() == null ? BigDecimal.ONE : rule.offpeakMultiplier();
        return new BillingExpr.Cond(
                condition,
                new BillingExpr.Tier(tierName + ".peak", new BillingExpr.Multiply(inner, peak)),
                new BillingExpr.Tier(tierName + ".offpeak", new BillingExpr.Multiply(inner, offpeak)));
    }

    /** R5 请求级加价：`|||when(...) * N`（仅管理端；不参与模拟）。 */
    private static BillingExpr applyRequestRules(BillingExpr body, ItemRules item, boolean admin) {
        if (!admin || item.requestRules() == null || item.requestRules().isEmpty()) {
            return body;
        }
        BigDecimal multiplier = item.requestRules().get(0).multiplier();
        return multiplier == null ? body : new BillingExpr.Multiply(body, multiplier);
    }

    // ------------------------------------------------------------------ source_hash（R-34）

    /** 报价内容哈希：同一份规则 → 同一 hash（幂等）；任何价格/规则变更 → hash 变化。 */
    public static String sourceHash(List<ItemRules> items) {
        StringBuilder sb = new StringBuilder(COMPILER_VERSION).append('|');
        List<ItemRules> sorted = new ArrayList<>(items);
        sorted.sort((a, b) -> String.valueOf(a.modelName()).compareTo(String.valueOf(b.modelName())));
        for (ItemRules item : sorted) {
            sb.append(item.modelName()).append('|')
                    .append(num(item.inputPrice())).append('|').append(num(item.outputPrice())).append('|')
                    .append(num(item.cacheReadPrice())).append('|').append(num(item.cacheWritePrice()));
            if (item.tierRule() != null) {
                sb.append("|T:").append(item.tierRule().tierField()).append(':')
                        .append(item.tierRule().priceStrategy());
                for (QuoteValidation.Tier tier : item.tierRule().tiers()) {
                    sb.append('[').append(num(tier.min())).append(',').append(num(tier.max())).append(',')
                            .append(num(tier.inputPrice())).append(',').append(num(tier.outputPrice()))
                            .append(']');
                }
            }
            if (item.timeRule() != null) {
                sb.append("|H:").append(item.timeRule().tz()).append(':')
                        .append(num(item.timeRule().peakMultiplier())).append(':')
                        .append(num(item.timeRule().offpeakMultiplier())).append(':')
                        .append(item.timeRule().weekdayScope());
                if (item.timeRule().segments() != null) {
                    for (QuoteValidation.Segment segment : item.timeRule().segments()) {
                        sb.append('[').append(segment.start()).append('-').append(segment.end()).append(']');
                    }
                }
            }
            sb.append('\n');
        }
        return sha256(sb.toString());
    }

    // ------------------------------------------------------------------ 工具

    /** `t{index}_{min}_{max}`：与 PRD 示例 `t0_0_512K` / `t1_512K_1M` / `t2_1M_plus` 对齐。 */
    static String tierLabel(int index, QuoteValidation.Tier tier) {
        String label = tier.label() == null || tier.label().isBlank()
                ? compact(tier.min()) + "_" + (tier.max() == null ? "plus" : compact(tier.max()))
                : tier.label();
        return "t" + index + "_" + label;
    }

    /**
     * 档位数值紧凑表述（对齐 PRD 06 §3 R2 的示例命名）：
     * 0 → "0"；512000 → "512K"；**1024000 → "1M"**（1024K 按 PRD 口径记作 1M）；2000000 → "2M"；1500 → "1500"。
     */
    static String compact(BigDecimal value) {
        if (value == null) {
            return "0";
        }
        long v = value.longValue();
        if (v >= 1_000_000L) {
            return (v / 1_000_000L) + "M";
        }
        if (v != 0 && v % 1_000L == 0) {
            return (v / 1_000L) + "K";
        }
        return String.valueOf(v);
    }

    static String num(BigDecimal value) {
        return value == null ? "" : value.stripTrailingZeros().toPlainString();
    }

    /** "09:00" → 9；"22:30" → 22（时段按小时粒度，与 hour() 语义一致）。 */
    static int hour(String time) {
        if (time == null || time.isBlank()) {
            return -1;
        }
        try {
            return java.time.LocalTime.parse(time.trim()).getHour();
        } catch (RuntimeException e) {
            return -1;
        }
    }

    /** 星期范围 → java.time.DayOfWeek 数值（1=Mon…7=Sun）。 */
    static List<Integer> weekdays(String scope) {
        if (scope == null || scope.isBlank() || "ALL".equalsIgnoreCase(scope)) {
            return List.of();
        }
        return switch (scope.toUpperCase()) {
            case "WEEKDAY", "WORKDAY" -> List.of(1, 2, 3, 4, 5);
            case "WEEKEND" -> List.of(6, 7);
            default -> List.of();
        };
    }

    private static String sha256(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(text.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 不可用", e);
        }
    }
}
