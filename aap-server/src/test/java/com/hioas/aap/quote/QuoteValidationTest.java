package com.hioas.aap.quote;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T08 · 报价校验规则 V1–V17（纯函数单元测试，真源 10-PRD §5.1）。
 *
 * <p>这些断言是**回归护栏**：规则一旦被改坏（例如把 V5 缓存价从告警改成阻塞、把 V11 的连续性判断写反），
 * 不需要起 Spring 就能立刻发现。
 */
class QuoteValidationTest {

    private static final Set<String> DETECTED = Set.of("gpt-4o", "gpt-4o-mini");

    private static QuoteValidation.ItemDraft item(String model, String input, String output) {
        return new QuoteValidation.ItemDraft(model, null,
                input == null ? null : new BigDecimal(input), output == null ? null : new BigDecimal(output),
                null, null, null, null, null, null, null, null, null, null, null, null, null);
    }

    @Test
    @DisplayName("V1/V2/V3/V17：明细为空、模型重复、缺价、模型不在检测清单内都要报错且定位到字段")
    void submitRuleErrors() {
        var empty = QuoteValidation.validateForSubmit(List.of(), null, null, DETECTED, false);
        assertThat(empty.ok()).isFalse();
        assertThat(empty.errors()).anyMatch(e -> e.field().equals("items") && e.reason().contains("V1"));

        var dup = QuoteValidation.validateForSubmit(
                List.of(item("gpt-4o", "1.2", "3.6"), item("gpt-4o", "1.2", "3.6")),
                null, null, DETECTED, false);
        assertThat(dup.errors()).anyMatch(e -> e.field().equals("items[1].model_name")
                && e.reason().contains("V2"));

        var missingPrice = QuoteValidation.validateForSubmit(
                List.of(item("gpt-4o", "1.2", null)), null, null, DETECTED, false);
        assertThat(missingPrice.errors()).anyMatch(e -> e.field().equals("items[0].output_price")
                && e.reason().contains("V3"));

        var unknown = QuoteValidation.validateForSubmit(
                List.of(item("claude-3.7", "1.2", "3.6")), null, null, DETECTED, false);
        assertThat(unknown.errors()).anyMatch(e -> e.reason().contains("V17"));
    }

    @Test
    @DisplayName("V6：有效期止必须晚于起（相等也算错）")
    void validityRule() {
        OffsetDateTime from = OffsetDateTime.of(2026, 1, 1, 0, 0, 0, 0, ZoneOffset.UTC);
        var equal = QuoteValidation.validateForSubmit(List.of(item("gpt-4o", "1", "1")), from, from, DETECTED, false);
        assertThat(equal.errors()).anyMatch(e -> e.field().equals("valid_to") && e.reason().contains("V6"));

        var ok = QuoteValidation.validateForSubmit(List.of(item("gpt-4o", "1", "1")), from,
                from.plusDays(30), DETECTED, false);
        assertThat(ok.ok()).as(ok.errors().toString()).isTrue();
    }

    @Test
    @DisplayName("V4/V5：单价不能为负；缓存读取价高于输入价只是告警（不阻塞）")
    void priceRules() {
        var negative = QuoteValidation.validateItem(new QuoteValidation.ItemDraft("gpt-4o", null,
                new BigDecimal("-1"), new BigDecimal("3.6"), null, null, null, null, null, null, null,
                null, null, null, null, null, null), 0, false);
        assertThat(negative.ok()).isFalse();
        assertThat(negative.errors()).anyMatch(e -> e.field().equals("items[0].input_price")
                && e.reason().contains("V4"));

        var cacheHigher = QuoteValidation.validateItem(new QuoteValidation.ItemDraft("gpt-4o", null,
                new BigDecimal("1"), new BigDecimal("3"), new BigDecimal("2"), null, null, null, null,
                null, null, null, null, null, null, null, null), 0, false);
        assertThat(cacheHigher.ok()).as(cacheHigher.errors().toString()).isTrue();
        assertThat(cacheHigher.warnings()).anyMatch(w -> w.contains("V5"));
    }

    @Test
    @DisplayName("V7/V8/V9/V10：时区白名单、时段先后、时段重叠、倍率>0")
    void timeRules() {
        var badTz = QuoteValidation.validateItem(itemWithTimeRule("Mars/Olympus",
                List.of(new QuoteValidation.Segment("08:00", "12:00")), null, null), 0, false);
        assertThat(badTz.errors()).anyMatch(e -> e.reason().contains("V7"));

        var badOrder = QuoteValidation.validateItem(itemWithTimeRule("Asia/Shanghai",
                List.of(new QuoteValidation.Segment("12:00", "08:00")), null, null), 0, false);
        assertThat(badOrder.errors()).anyMatch(e -> e.reason().contains("V8"));

        var overlap = QuoteValidation.validateItem(itemWithTimeRule("Asia/Shanghai",
                List.of(new QuoteValidation.Segment("08:00", "12:00"),
                        new QuoteValidation.Segment("11:00", "14:00")), null, null), 0, false);
        assertThat(overlap.errors()).anyMatch(e -> e.reason().contains("V9") && e.reason().contains("第 1 段"));

        var zeroMultiplier = QuoteValidation.validateItem(itemWithTimeRule("Asia/Shanghai",
                List.of(new QuoteValidation.Segment("08:00", "12:00")), BigDecimal.ZERO, null), 0, false);
        assertThat(zeroMultiplier.errors()).anyMatch(e -> e.reason().contains("V10"));

        // 合法：两段不重叠
        var ok = QuoteValidation.validateItem(itemWithTimeRule("UTC",
                List.of(new QuoteValidation.Segment("08:00", "12:00"),
                        new QuoteValidation.Segment("22:00", "23:59")), new BigDecimal("1.2"), null), 0, false);
        assertThat(ok.ok()).as(ok.errors().toString()).isTrue();
    }

    @Test
    @DisplayName("V11–V14：阶梯必须连续、首档从 0、末档开放、tier_field=len、OVERRIDE 每档有价")
    void tierRules() {
        // 空洞：0–1000 与 2000–null
        var gap = QuoteValidation.validateItem(itemWithTiers(List.of(
                tier(0, "0", "1000", "1", "2"), tier(1, "2000", null, "1", "2"))), 0, false);
        assertThat(gap.errors()).anyMatch(e -> e.reason().contains("V11"));

        // 首档不从 0
        var firstNotZero = QuoteValidation.validateItem(itemWithTiers(List.of(
                tier(0, "1", null, "1", "2"))), 0, false);
        assertThat(firstNotZero.errors()).anyMatch(e -> e.reason().contains("V12"));

        // 末档封闭
        var lastClosed = QuoteValidation.validateItem(itemWithTiers(List.of(
                tier(0, "0", "1000", "1", "2"))), 0, false);
        assertThat(lastClosed.errors()).anyMatch(e -> e.reason().contains("V12"));

        // tier_field 非法
        var badField = QuoteValidation.validateItem(itemWithTiersAndField("p", List.of(
                tier(0, "0", null, "1", "2"))), 0, false);
        assertThat(badField.errors()).anyMatch(e -> e.reason().contains("V13"));

        // OVERRIDE 但缺价
        var missingTierPrice = QuoteValidation.validateItem(itemWithTiers(List.of(
                tier(0, "0", null, null, "2"))), 0, false);
        assertThat(missingTierPrice.errors()).anyMatch(e -> e.reason().contains("V14"));

        // 合法
        var ok = QuoteValidation.validateItem(itemWithTiers(List.of(
                tier(0, "0", "1000", "1", "2"), tier(1, "1000", null, "1.5", "2.5"))), 0, false);
        assertThat(ok.ok()).as(ok.errors().toString()).isTrue();
    }

    @Test
    @DisplayName("V15/V16：请求规则仅管理端；别名 ≤64 字")
    void adminAndAliasRules() {
        QuoteValidation.RequestRule rule = new QuoteValidation.RequestRule("input_len", "request", "UTC",
                ">", "1000", new BigDecimal("1.5"), null);
        var providerWrites = QuoteValidation.validateItem(new QuoteValidation.ItemDraft("gpt-4o", null,
                new BigDecimal("1"), new BigDecimal("2"), null, null, null, null, null, null, null,
                null, null, null, null, null, List.of(rule)), 0, false);
        assertThat(providerWrites.errors()).anyMatch(e -> e.field().contains("request_rules")
                && e.reason().contains("V15"));

        var adminWrites = QuoteValidation.validateItem(new QuoteValidation.ItemDraft("gpt-4o", null,
                new BigDecimal("1"), new BigDecimal("2"), null, null, null, null, null, null, null,
                null, null, null, null, null, List.of(rule)), 0, true);
        assertThat(adminWrites.ok()).as(adminWrites.errors().toString()).isTrue();

        var longAlias = QuoteValidation.validateItem(new QuoteValidation.ItemDraft("gpt-4o", "x".repeat(65),
                new BigDecimal("1"), new BigDecimal("2"), null, null, null, null, null, null, null,
                null, null, null, null, null, null), 0, false);
        assertThat(longAlias.errors()).anyMatch(e -> e.reason().contains("V16"));
    }

    @Test
    @DisplayName("校验失败一次性收集全部错误（不是 fail-fast），错误码按规则族映射")
    void collectsAllErrors() {
        var result = QuoteValidation.validateForSubmit(
                List.of(item(null, "-1", null)), null, null, DETECTED, false);
        assertThat(result.errors().size()).as("应同时报出 model_name/input_price/output_price 等").isGreaterThanOrEqualTo(3);
        assertThat(result.errors().stream().map(e -> e.field()).distinct().count()).isGreaterThanOrEqualTo(3);
    }

    // ------------------------------------------------------------------ 构造工具

    private static QuoteValidation.ItemDraft itemWithTimeRule(String tz, List<QuoteValidation.Segment> segments,
                                                              BigDecimal peakMultiplier, BigDecimal offpeak) {
        return new QuoteValidation.ItemDraft("gpt-4o", null, new BigDecimal("1"), new BigDecimal("2"),
                null, null, null, null, null, null, null, null, null, null,
                new QuoteValidation.TimeRule(tz, "ALL", peakMultiplier, offpeak, null, segments),
                null, null);
    }

    private static QuoteValidation.ItemDraft itemWithTiers(List<QuoteValidation.Tier> tiers) {
        return itemWithTiersAndField("len", tiers);
    }

    private static QuoteValidation.ItemDraft itemWithTiersAndField(String field, List<QuoteValidation.Tier> tiers) {
        return new QuoteValidation.ItemDraft("gpt-4o", null, new BigDecimal("1"), new BigDecimal("2"),
                null, null, null, null, null, null, null, null, null, null, null,
                new QuoteValidation.TierRule(field, "OVERRIDE", tiers), null);
    }

    private static QuoteValidation.Tier tier(int seq, String min, String max, String input, String output) {
        return new QuoteValidation.Tier(seq,
                min == null ? null : new BigDecimal(min), max == null ? null : new BigDecimal(max),
                "档" + seq,
                input == null ? null : new BigDecimal(input), output == null ? null : new BigDecimal(output),
                null, null);
    }

    /** 与 Map.of 无关的辅助：保证价格映射键齐全。 */
    @Test
    @DisplayName("八/九项单价键齐全（priceMap 覆盖 input/output/cache*/image*/audio*）")
    void priceMapCoversAllKeys() {
        Map<String, BigDecimal> map = QuoteValidation.priceMap(item("gpt-4o", "1", "2"));
        assertThat(map.keySet()).containsExactlyInAnyOrder("input_price", "output_price", "cache_read_price",
                "cache_write_price", "cache_write_1h_price", "image_input_price", "image_output_price",
                "audio_input_price", "audio_output_price");
    }
}
