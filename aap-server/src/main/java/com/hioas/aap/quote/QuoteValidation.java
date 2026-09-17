package com.hioas.aap.quote;

import com.hioas.aap.common.ApiErrorDetail;
import com.hioas.aap.common.ErrorCode;
import java.math.BigDecimal;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 报价校验规则（V1–V17，真源 `10-报价与合同结算PRD.md §5.1`）。
 *
 * <p>纯函数、无状态：便于单元测试逐条钉死，也便于 QT-08（保存单行）与 QT-09（提交）复用同一套规则。
 * 设计取舍：**一次性收集全部错误**（不 fail-fast）——前端要按字段高亮，只报第一条会导致用户反复提交。
 * 只有能阻塞提交的规则才进 {@code errors}；V5（缓存价 ≤ 输入价）是**告警**，进 {@code warnings} 不阻塞。
 */
public final class QuoteValidation {

    private QuoteValidation() {
    }

    /** V7 时区白名单（10-PRD §5.1 V7）。 */
    public static final Set<String> ALLOWED_TZ = Set.of(
            "Asia/Shanghai", "UTC", "Asia/Tokyo", "Asia/Singapore", "America/Los_Angeles", "Europe/London");

    /** V13 分档字段仅支持 len。 */
    public static final String TIER_FIELD_LEN = "len";

    /** 阶梯价格策略。 */
    public static final String STRATEGY_OVERRIDE = "OVERRIDE";

    /** V3 必填的输入/输出价。 */
    public static final Set<String> REQUIRED_PRICE_KEYS = Set.of("input_price", "output_price");

    // ------------------------------------------------------------------ 输入模型

    /** 时段规则。 */
    public record TimeRule(String tz, String weekdayScope, BigDecimal peakMultiplier, BigDecimal offpeakMultiplier,
                           BigDecimal peakPriceOverride, List<Segment> segments) {
    }

    /** 时段片段（HH:mm）。 */
    public record Segment(String start, String end) {
    }

    /** 阶梯规则。 */
    public record TierRule(String tierField, String priceStrategy, List<Tier> tiers) {
    }

    /** 阶梯档位。 */
    public record Tier(Integer seq, BigDecimal min, BigDecimal max, String label, BigDecimal inputPrice,
                       BigDecimal outputPrice, BigDecimal cacheReadPrice, BigDecimal multiplier) {
    }

    /** 请求规则（V15 仅管理端）。 */
    public record RequestRule(String field, String granularity, String tz, String op, String value,
                              BigDecimal multiplier, String whenExpr) {
    }

    /** 明细行草稿（八大单价 + 规则）。 */
    public record ItemDraft(String modelName, String modelAlias,
                            BigDecimal inputPrice, BigDecimal outputPrice,
                            BigDecimal cacheReadPrice, BigDecimal cacheWritePrice, BigDecimal cacheWrite1hPrice,
                            BigDecimal imageInputPrice, BigDecimal audioInputPrice,
                            BigDecimal imageOutputPrice, BigDecimal audioOutputPrice,
                            String tier, String billingMode, String note,
                            TimeRule timeRule, TierRule tierRule, List<RequestRule> requestRules) {
    }

    /** 校验结果：阻塞错误 + 非阻塞告警。 */
    public record Result(List<ApiErrorDetail> errors, List<String> warnings) {

        public boolean ok() {
            return errors.isEmpty();
        }

        public static Result empty() {
            return new Result(List.of(), List.of());
        }
    }

    // ------------------------------------------------------------------ 入口

    /** QT-09 提交：报价单级（V1/V2/V6/V17）+ 逐行（V3–V5、V7–V16）。 */
    public static Result validateForSubmit(List<ItemDraft> items, OffsetDateTime validFrom, OffsetDateTime validTo,
                                          Set<String> detectedModels, boolean admin) {
        List<ApiErrorDetail> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        // V1 明细行 ≥ 1
        if (items == null || items.isEmpty()) {
            errors.add(new ApiErrorDetail("items", "至少需要 1 条明细行（V1）"));
        } else {
            // V2 model_name 不重复
            Set<String> seen = new HashSet<>();
            for (int i = 0; i < items.size(); i++) {
                ItemDraft item = items.get(i);
                String name = trim(item.modelName());
                if (name == null || name.isEmpty()) {
                    errors.add(new ApiErrorDetail("items[" + i + "].model_name", "模型名不能为空（V2）"));
                    continue;
                }
                if (!seen.add(name)) {
                    errors.add(new ApiErrorDetail("items[" + i + "].model_name", "模型名重复：" + name + "（V2）"));
                }
                // V17 模型须在检测通过清单内
                if (detectedModels != null && !detectedModels.isEmpty() && !detectedModels.contains(name)) {
                    errors.add(new ApiErrorDetail("items[" + i + "].model_name",
                            "模型未在检测通过的清单内：" + name + "（V17）"));
                }
            }
        }

        // V6 valid_to > valid_from
        if (validFrom != null && validTo != null && !validTo.isAfter(validFrom)) {
            errors.add(new ApiErrorDetail("valid_to", "有效期止必须晚于有效期起（V6）"));
        }

        if (items != null) {
            for (int i = 0; i < items.size(); i++) {
                final int index = i;
                Result itemResult = validateItem(items.get(i), index, admin);
                errors.addAll(itemResult.errors());
                itemResult.warnings().forEach(w -> warnings.add("items[" + index + "] " + w));
            }
        }
        return new Result(errors, warnings);
    }

    /** QT-08 保存单行（不含报价单级规则）。 */
    public static Result validateItem(ItemDraft item, int index, boolean admin) {
        List<ApiErrorDetail> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        if (item == null) {
            errors.add(new ApiErrorDetail("items", "明细行不能为空"));
            return new Result(errors, warnings);
        }
        String p = index < 0 ? "" : "items[" + index + "].";

        // V16 别名 ≤ 64
        if (item.modelAlias() != null && item.modelAlias().length() > 64) {
            errors.add(new ApiErrorDetail(p + "model_alias", "别名最多 64 字（V16）"));
        }

        // V3 输入/输出价必填且 ≥0
        if (item.inputPrice() == null) {
            errors.add(new ApiErrorDetail(p + "input_price", "输入价必填（V3）"));
        }
        if (item.outputPrice() == null) {
            errors.add(new ApiErrorDetail(p + "output_price", "输出价必填（V3）"));
        }
        // V4 单价非负
        for (var entry : priceMap(item).entrySet()) {
            BigDecimal price = entry.getValue();
            if (price != null && price.signum() < 0) {
                errors.add(new ApiErrorDetail(p + entry.getKey(), "单价不能为负（V4）"));
            }
        }
        // V5 缓存读取价 ≤ 输入价（WARN，不阻塞）
        if (item.cacheReadPrice() != null && item.inputPrice() != null
                && item.cacheReadPrice().compareTo(item.inputPrice()) > 0) {
            warnings.add("缓存读取价高于输入价，请确认（V5）");
        }
        // V5 同口径：缓存写入价 ≤ 输出价
        if (item.cacheWritePrice() != null && item.outputPrice() != null
                && item.cacheWritePrice().compareTo(item.outputPrice()) > 0) {
            warnings.add("缓存写入价高于输出价，请确认（V5）");
        }

        // V15 request_rules 仅管理端
        if (!admin && item.requestRules() != null && !item.requestRules().isEmpty()) {
            errors.add(new ApiErrorDetail(p + "request_rules", "请求规则仅管理端可设置（V15）"));
        }

        // V7–V10 时段规则
        if (item.timeRule() != null) {
            TimeRule rule = item.timeRule();
            if (rule.tz() != null && !ALLOWED_TZ.contains(rule.tz())) {
                errors.add(new ApiErrorDetail(p + "price_time_rule.tz", "时区不在白名单内：" + rule.tz() + "（V7）"));
            }
            checkMultiplier(rule.peakMultiplier(), p + "price_time_rule.peak_multiplier", errors);
            checkMultiplier(rule.offpeakMultiplier(), p + "price_time_rule.offpeak_multiplier", errors);
            List<Segment> segments = rule.segments() == null ? List.of() : rule.segments();
            List<LocalTime[]> parsed = new ArrayList<>();
            for (int i = 0; i < segments.size(); i++) {
                Segment segment = segments.get(i);
                LocalTime start = parseTime(segment.start());
                LocalTime end = parseTime(segment.end());
                if (start == null || end == null) {
                    errors.add(new ApiErrorDetail(p + "price_time_rule.segments[" + i + "]",
                            "时段格式须为 HH:mm（V8）"));
                    continue;
                }
                // V8 start < end（跨零点由 E9 显式表达为两段，不允许 start >= end）
                if (!start.isBefore(end)) {
                    errors.add(new ApiErrorDetail(p + "price_time_rule.segments[" + i + "]",
                            "时段开始必须早于结束（V8）：" + segment.start() + "-" + segment.end()));
                    continue;
                }
                // V9 时段不重叠
                for (int j = 0; j < parsed.size(); j++) {
                    LocalTime[] other = parsed.get(j);
                    if (start.isBefore(other[1]) && other[0].isBefore(end)) {
                        errors.add(new ApiErrorDetail(p + "price_time_rule.segments[" + i + "]",
                                "时段与第 " + (j + 1) + " 段重叠（V9）：" + segment.start() + "-" + segment.end()));
                        break;
                    }
                }
                parsed.add(new LocalTime[] {start, end});
            }
        }

        // V11–V14 阶梯规则
        if (item.tierRule() != null) {
            TierRule rule = item.tierRule();
            // V13 tier_field 仅 len
            if (rule.tierField() != null && !TIER_FIELD_LEN.equals(rule.tierField())) {
                errors.add(new ApiErrorDetail(p + "price_tier_rule.tier_field",
                        "分档字段仅支持 len（V13）：" + rule.tierField()));
            }
            List<Tier> tiers = rule.tiers() == null ? List.of() : rule.tiers();
            if (!tiers.isEmpty()) {
                // V12 首档 min=0
                if (tiers.get(0).min() == null || tiers.get(0).min().signum() != 0) {
                    errors.add(new ApiErrorDetail(p + "price_tier_rule.tiers[0].min", "首档下界必须为 0（V12）"));
                }
                // V12 末档 max=null（开放）
                Tier last = tiers.get(tiers.size() - 1);
                if (last.max() != null) {
                    errors.add(new ApiErrorDetail(p + "price_tier_rule.tiers[" + (tiers.size() - 1) + "].max",
                            "末档上界必须开放（null）（V12）"));
                }
                // V11 连续无空洞/不重叠
                for (int i = 0; i < tiers.size() - 1; i++) {
                    BigDecimal curMax = tiers.get(i).max();
                    BigDecimal nextMin = tiers.get(i + 1).min();
                    if (curMax == null) {
                        errors.add(new ApiErrorDetail(p + "price_tier_rule.tiers[" + i + "].max",
                                "非末档上界不能开放（V11）"));
                        continue;
                    }
                    if (nextMin == null || curMax.compareTo(nextMin) != 0) {
                        errors.add(new ApiErrorDetail(p + "price_tier_rule.tiers[" + (i + 1) + "].min",
                                "阶梯区间必须连续衔接（V11）：上一档上界 " + curMax.toPlainString()
                                        + " 与下一档下界 " + (nextMin == null ? "null" : nextMin.toPlainString())
                                        + " 之间存在空洞或重叠"));
                    }
                }
                // V14 OVERRIDE 每档必须有价
                if (STRATEGY_OVERRIDE.equals(rule.priceStrategy())) {
                    for (int i = 0; i < tiers.size(); i++) {
                        Tier tier = tiers.get(i);
                        if (tier.inputPrice() == null || tier.outputPrice() == null) {
                            errors.add(new ApiErrorDetail(p + "price_tier_rule.tiers[" + i + "]",
                                    "OVERRIDE 策略下每档都必须给出输入/输出价（V14）"));
                        }
                        checkMultiplier(tier.multiplier(), p + "price_tier_rule.tiers[" + i + "].multiplier", errors);
                    }
                }
            }
        }
        return new Result(errors, warnings);
    }

    // ------------------------------------------------------------------ 工具

    private static void checkMultiplier(BigDecimal multiplier, String field, List<ApiErrorDetail> errors) {
        if (multiplier != null && multiplier.signum() <= 0) {
            errors.add(new ApiErrorDetail(field, "倍率必须大于 0（V10）"));
        }
    }

    /** 八大单价键 → 值（用于 V4 统一非负校验）。 */
    public static java.util.Map<String, BigDecimal> priceMap(ItemDraft item) {
        java.util.Map<String, BigDecimal> map = new java.util.LinkedHashMap<>();
        map.put("input_price", item.inputPrice());
        map.put("output_price", item.outputPrice());
        map.put("cache_read_price", item.cacheReadPrice());
        map.put("cache_write_price", item.cacheWritePrice());
        map.put("cache_write_1h_price", item.cacheWrite1hPrice());
        map.put("image_input_price", item.imageInputPrice());
        map.put("image_output_price", item.imageOutputPrice());
        map.put("audio_input_price", item.audioInputPrice());
        map.put("audio_output_price", item.audioOutputPrice());
        return map;
    }

    /** 校验失败统一抛 E-1001（带字段级 details），供前端逐字段高亮。 */
    public static void requireOk(Result result, ErrorCode code) {
        if (!result.ok()) {
            throw new com.hioas.aap.common.ApiException(code,
                    result.errors().isEmpty() ? "校验失败" : result.errors().get(0).reason(), result.errors());
        }
    }

    private static String trim(String value) {
        return value == null ? null : value.trim();
    }

    private static LocalTime parseTime(String value) {
        try {
            return value == null ? null : LocalTime.parse(value);
        } catch (RuntimeException e) {
            return null;
        }
    }
}
