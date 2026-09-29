package com.hioas.aap.supply;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** T-M4-09 · 写后回读比较单测（红基线 → 实现 → 绿）。契约：spec.md R-58。 */
class ReadbackComparatorTest {

    private static ReadbackComparator.Expectation expected() {
        return new ReadbackComparator.Expectation("AAP-ace-gpt-4o", List.of("gpt-4o"),
                "aap-provider-1", "ENABLED");
    }

    @Test
    @DisplayName("完全一致 → equal，且不报任何差异")
    void identicalIsEqual() {
        var result = ReadbackComparator.compare(expected(),
                new ReadbackComparator.Readback("AAP-ace-gpt-4o", List.of("gpt-4o"),
                        "aap-provider-1", "ENABLED"));
        assertThat(result.equal()).isTrue();
        assertThat(result.differences()).isEmpty();
    }

    @Test
    @DisplayName("models 顺序/重复不同但集合相同 → 视为一致（网关会重排，不误报）")
    void modelOrderDoesNotMatter() {
        var result = ReadbackComparator.compare(
                new ReadbackComparator.Expectation("n", List.of("a", "b"), "t", "ENABLED"),
                new ReadbackComparator.Readback("n", List.of("b", "a", "a"), "t", "ENABLED"));
        assertThat(result.equal()).isTrue();
    }

    @Test
    @DisplayName("模型多一个 → 不一致，且差异描述指出 models")
    void extraModelIsMismatch() {
        var result = ReadbackComparator.compare(expected(),
                new ReadbackComparator.Readback("AAP-ace-gpt-4o", List.of("gpt-4o", "o3-mini"),
                        "aap-provider-1", "ENABLED"));
        assertThat(result.equal()).isFalse();
        assertThat(result.differences()).isNotEmpty();
        assertThat(String.join(" ", result.differences())).contains("models");
    }

    @Test
    @DisplayName("渠道名 / tag / 状态任一不同 → 不一致，且差异必须可解释")
    void eachFieldIsChecked() {
        var name = ReadbackComparator.compare(expected(),
                new ReadbackComparator.Readback("AAP-other-gpt-4o", List.of("gpt-4o"),
                        "aap-provider-1", "ENABLED"));
        assertThat(name.equal()).isFalse();
        assertThat(String.join(" ", name.differences())).contains("channelName");

        var tag = ReadbackComparator.compare(expected(),
                new ReadbackComparator.Readback("AAP-ace-gpt-4o", List.of("gpt-4o"),
                        "aap-provider-9", "ENABLED"));
        assertThat(tag.equal()).isFalse();
        assertThat(String.join(" ", tag.differences())).contains("tag");

        var status = ReadbackComparator.compare(expected(),
                new ReadbackComparator.Readback("AAP-ace-gpt-4o", List.of("gpt-4o"),
                        "aap-provider-1", "DISABLED"));
        assertThat(status.equal()).isFalse();
        assertThat(String.join(" ", status.differences())).contains("status");
    }

    @Test
    @DisplayName("空值与大小写归一：ENABLED / enabled 视为同值，空清单与 null 等价")
    void normalization() {
        assertThat(ConfigApplyRateLimiter.normalizeRate(5)).isEqualTo(5);
        var result = ReadbackComparator.compare(
                new ReadbackComparator.Expectation("n", List.of(), null, "ENABLED"),
                new ReadbackComparator.Readback("n", null, null, "enabled"));
        assertThat(result.equal()).isTrue();
    }
}
