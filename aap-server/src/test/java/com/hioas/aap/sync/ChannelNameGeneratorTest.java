package com.hioas.aap.sync;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T-M4-05 · 渠道命名器单测（红基线 → 实现 → 绿）。
 *
 * <p>契约真源：`specs/001-intake-automation/spec.md` §3.3 渠道命名规则 + §6 `R-54`（确定性生成、
 * 同名即同一供给单元）/ `R-55`（超长截断附哈希）+ `quickstart.md` 场景 1（3 条渠道命名互不相同）。
 *
 * <p>为什么必须有这些边界：模型名来自**供应商申报**，可能含 `/`（如 `anthropic/claude-…`）、
 * 空格、大写、Unicode 或超长；而 `aap_channel_binding.channel_name` 是 `varchar(64)`。
 * 若不做归一与截断，超长会在写入时直接报错、含 `/` 会在网关侧产生歧义路径。
 */
class ChannelNameGeneratorTest {

    @Test
    @DisplayName("R-54 基础命名：AAP-{shortCode}-{slug}")
    void basicName() {
        assertThat(ChannelNameGenerator.forModel("ace", "gpt-4o"))
                .isEqualTo("AAP-ace-gpt-4o");
    }

    @Test
    @DisplayName("R-55 斜杠与点号：模型名中的 / 归一为 _")
    void slashInModelName() {
        assertThat(ChannelNameGenerator.forModel("ace", "anthropic/claude-3-5-sonnet"))
                .isEqualTo("AAP-ace-anthropic_claude-3-5-sonnet");
    }

    @Test
    @DisplayName("R-55 大小写与空格：统一小写，空格段落压成单个 _")
    void caseAndSpaces() {
        assertThat(ChannelNameGenerator.forModel("ACE", "Qwen 2.5 Max"))
                .isEqualTo("AAP-ace-qwen_2_5_max");
    }

    @Test
    @DisplayName("R-54 shortCode 含 - 时归一为 _，保证反解无歧义")
    void shortCodeWithDash() {
        String name = ChannelNameGenerator.forModel("a-b", "gpt-4o");
        assertThat(name).isEqualTo("AAP-a_b-gpt-4o");
        assertThat(ChannelNameGenerator.parse(name))
                .contains(new ChannelNameGenerator.Parsed("a_b", "gpt-4o"));
    }

    @Test
    @DisplayName("R-55 超长模型名：截断后长度 ≤ 64 且确定性（两次调用一致）")
    void longModelNameIsTruncatedDeterministically() {
        String longModel = "vendor/" + "x".repeat(120) + "-turbo";
        String first = ChannelNameGenerator.forModel("ace", longModel);
        String second = ChannelNameGenerator.forModel("ace", longModel);

        assertThat(first).hasSizeLessThanOrEqualTo(ChannelNameGenerator.MAX_LENGTH);
        assertThat(first).isEqualTo(second).as("命名必须是确定性纯函数（幂等前提）");
        assertThat(first).startsWith("AAP-ace-");
    }

    @Test
    @DisplayName("R-55 不同超长模型名不得碰撞（4 位哈希区分）")
    void differentLongNamesDoNotCollide() {
        String base = "x".repeat(120);
        assertThat(ChannelNameGenerator.forModel("ace", base + "alpha"))
                .isNotEqualTo(ChannelNameGenerator.forModel("ace", base + "beta"));
    }

    @Test
    @DisplayName("字符集安全：结果仅含 [A-Za-z0-9._-]（写入外部网关的硬要求）")
    void charsetIsSafe() {
        String name = ChannelNameGenerator.forModel("ace", "模型/中文 名称: v2 (beta)");
        assertThat(name).matches("[A-Za-z0-9._-]+");
    }

    @Test
    @DisplayName("空模型名不抛异常，回落占位 slug")
    void blankModelNameFallsBack() {
        assertThat(ChannelNameGenerator.forModel("ace", ""))
                .isEqualTo("AAP-ace-model");
        assertThat(ChannelNameGenerator.forModel("ace", "   "))
                .isEqualTo("AAP-ace-model");
    }

    @Test
    @DisplayName("反解：合法命名可还原 shortCode 与 slug")
    void parseValidName() {
        assertThat(ChannelNameGenerator.parse("AAP-ace-gpt-4o"))
                .contains(new ChannelNameGenerator.Parsed("ace", "gpt-4o"));
    }

    @Test
    @DisplayName("反解：非本规则命名返回 empty（不猜测）")
    void parseInvalidNameReturnsEmpty() {
        assertThat(ChannelNameGenerator.parse("random-channel")).isEmpty();
        assertThat(ChannelNameGenerator.parse(null)).isEmpty();
        assertThat(ChannelNameGenerator.parse("")).isEmpty();
        assertThat(ChannelNameGenerator.parse("AAP-ace")).isEmpty();
    }

    @Test
    @DisplayName("往返：forModel 产物必可反解出同一 shortCode")
    void roundTrip() {
        String name = ChannelNameGenerator.forModel("prov_1", "meta-llama/Llama-3.3-70B");
        Optional<ChannelNameGenerator.Parsed> parsed = ChannelNameGenerator.parse(name);
        assertThat(parsed).isPresent();
        assertThat(parsed.get().shortCode()).isEqualTo("prov_1");
    }
}
