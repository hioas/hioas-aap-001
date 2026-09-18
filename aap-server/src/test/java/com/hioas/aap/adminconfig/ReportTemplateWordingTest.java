package com.hioas.aap.adminconfig;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * R-26 措辞红线（纯函数边界用例）：免责声明**字符串级**判定，不做语义理解。
 *
 * <p>为什么单列单元测试：这是合规红线，判错一次就是一次合规事故；边界（否定句、空值、
 * 大小写与空白变体）必须逐一钉死，且不能依赖 HTTP 链路才能验证。
 */
class ReportTemplateWordingTest {

    @Test
    @DisplayName("含保证性断言 → 不合规（保证为真 / 保证正品 / 官方正版 / 绝对真实）")
    void rejectsGuaranteePhrases() {
        assertThat(ReportTemplateWording.compliant("本报告保证为真模型")).isFalse();
        assertThat(ReportTemplateWording.compliant("检测结论：保证正品")).isFalse();
        assertThat(ReportTemplateWording.compliant("该渠道官方正版，可放心引用")).isFalse();
        assertThat(ReportTemplateWording.compliant("绝对真实，100% 真实")).isFalse();
        assertThat(ReportTemplateWording.compliant("已验证该模型为正品")).isFalse();
    }

    @Test
    @DisplayName("否定式表达与合规文案 → 通过（不禁止说明“不是判决”）")
    void acceptsNonGuaranteeWording() {
        assertThat(ReportTemplateWording.compliant(
                "本引擎输出的是证据与置信度，不是「真 / 假」判决，亦不得解读为对模型来源、授权或合规状态的担保。"))
                .isTrue();
        assertThat(ReportTemplateWording.compliant("未发现与宣称模型不一致的迹象（置信度：高）。")).isTrue();
        assertThat(ReportTemplateWording.compliant("")).isTrue();
        assertThat(ReportTemplateWording.compliant(null)).isTrue();
    }

    @Test
    @DisplayName("命中即失败：禁用词出现在否定句里同样判不合规（字符串级判定，不做语义豁免）")
    void negatedSentenceStillFails() {
        assertThat(ReportTemplateWording.compliant("请勿理解为本渠道保证为真。")).isFalse();
    }
}
