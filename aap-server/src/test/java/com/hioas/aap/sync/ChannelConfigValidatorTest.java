package com.hioas.aap.sync;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T-M4-06 · 渠道配置校验器单测（红基线 → 实现 → 绿）。
 *
 * <p>契约真源：`specs/001-intake-automation/spec.md` §6 `R-56`（PER_MODEL 下 models 恰为一个模型）、
 * `R-54`（命名确定性/同名即同一供给单元）、`R-58`（写入前必须可校验）、§7 `AC-20`。
 *
 * <p>为什么必须有：`aap_channel_binding.models` 是 **jsonb 数组**，历史上承载多模型（合并渠道）。
 * 一模型一渠道之后，若仍写入多元素数组，网关侧会把该渠道同时用于多个模型，
 * 「模型级调度」的前提直接失效 —— 这是本校验器存在的唯一理由，必须硬拦。
 */
class ChannelConfigValidatorTest {

    private static ChannelConfigValidator.Draft draft(String shortCode, String modelName, List<String> models,
                                                      String baseUrl, String tag, String granularity,
                                                      Integer weight, String channelName) {
        return new ChannelConfigValidator.Draft(shortCode, modelName, models, baseUrl, tag, granularity, weight, channelName);
    }

    private static ChannelConfigValidator.Draft validModelLevel() {
        return draft("ace", "gpt-4o", List.of("gpt-4o"), "https://api.example.com/v1",
                "aap-provider-1", "PER_MODEL", 10, "AAP-ace-gpt-4o");
    }

    @Test
    @DisplayName("合法 PER_MODEL（单模型、命名一致）→ 零违规")
    void validDraftHasNoViolation() {
        assertThat(ChannelConfigValidator.validate(validModelLevel())).isEmpty();
    }

    @Test
    @DisplayName("R-56 PER_MODEL 必须恰好一个模型：多模型即违规")
    void modelLevelWithMultipleModelsIsRejected() {
        var bad = draft("ace", "gpt-4o", List.of("gpt-4o", "gpt-4o-mini"),
                "https://api.example.com/v1", "aap-provider-1", "PER_MODEL", 10, "AAP-ace-gpt-4o");
        assertThat(ChannelConfigValidator.validate(bad))
                .anyMatch(v -> v.contains("R-56"));
    }

    @Test
    @DisplayName("R-56 空模型清单 / 含空元素 → 违规")
    void emptyModelListIsRejected() {
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of(),
                "https://api.example.com", "t", "PER_MODEL", 1, "AAP-ace-gpt-4o")))
                .isNotEmpty();
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", java.util.Arrays.asList("gpt-4o", "  "),
                "https://api.example.com", "t", "PER_MODEL", 1, "AAP-ace-gpt-4o")))
                .isNotEmpty();
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", null,
                "https://api.example.com", "t", "PER_MODEL", 1, "AAP-ace-gpt-4o")))
                .isNotEmpty();
    }

    @Test
    @DisplayName("R-56 模型清单与 modelName 不一致 → 违规（渠道只能代表它自己那个模型）")
    void modelListMustMatchModelName() {
        var bad = draft("ace", "gpt-4o", List.of("gpt-4o-mini"),
                "https://api.example.com", "t", "PER_MODEL", 1, "AAP-ace-gpt-4o");
        assertThat(ChannelConfigValidator.validate(bad)).isNotEmpty();
    }

    @Test
    @DisplayName("base_url 必须为 http(s)（SSRF 前置）")
    void nonHttpBaseUrlIsRejected() {
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                "ftp://api.example.com", "t", "PER_MODEL", 1, "AAP-ace-gpt-4o")))
                .anyMatch(v -> v.contains("base_url"));
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                "", "t", "PER_MODEL", 1, "AAP-ace-gpt-4o")))
                .isNotEmpty();
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                null, "t", "PER_MODEL", 1, "AAP-ace-gpt-4o")))
                .isNotEmpty();
    }

    @Test
    @DisplayName("weight 不得为负（网关侧为无符号权重）")
    void negativeWeightIsRejected() {
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                "https://api.example.com", "t", "PER_MODEL", -1, "AAP-ace-gpt-4o")))
                .isNotEmpty();
    }

    @Test
    @DisplayName("R-36 tag 必填（按供应商打标，批量启停的基础）")
    void blankTagIsRejected() {
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                "https://api.example.com", "  ", "PER_MODEL", 1, "AAP-ace-gpt-4o")))
                .anyMatch(v -> v.contains("tag"));
    }

    @Test
    @DisplayName("R-54/R-55 渠道名必须与命名器输出一致（防手工改名破坏可反解）")
    void channelNameMustMatchGeneratorOutput() {
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                "https://api.example.com", "t", "PER_MODEL", 1, "AAP-ace-gpt-4o-mini")))
                .anyMatch(v -> v.contains("R-54"));
    }

    @Test
    @DisplayName("R-55 渠道名长度不得超过 64（列宽硬约束）")
    void channelNameLengthIsBounded() {
        String tooLong = "AAP-" + "a".repeat(80);
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                "https://api.example.com", "t", "PER_MODEL", 1, tooLong)))
                .isNotEmpty();
    }

    @Test
    @DisplayName("granularity 仅允许 PER_MODEL / PER_PROVIDER")
    void unknownGranularityIsRejected() {
        assertThat(ChannelConfigValidator.validate(draft("ace", "gpt-4o", List.of("gpt-4o"),
                "https://api.example.com", "t", "PER_TEAM", 1, "AAP-ace-gpt-4o")))
                .isNotEmpty();
    }

    @Test
    @DisplayName("PER_PROVIDER 合并模式：多模型合法（DR-03 保留既有能力）")
    void providerLevelAllowsMultipleModels() {
        var merged = draft("ace", null, List.of("gpt-4o", "gpt-4o-mini"),
                "https://api.example.com", "t", "PER_PROVIDER", 1, "AAP-ace-0001");
        assertThat(ChannelConfigValidator.validate(merged)).isEmpty();
    }
}
