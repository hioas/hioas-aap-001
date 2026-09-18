package com.hioas.aap.adminconfig;

import com.hioas.aap.report.ReportController;

/**
 * 报告模板措辞校验（R-26 红线，13-管理端PRD「保存时校验不得出现『保证为真模型』措辞」）。
 *
 * <p><b>单一真源</b>：禁用词表与判定口径直接复用 {@link ReportController#wordingCompliant(String)}
 * （该处同时服务报告正文校验与 AC-18 验收），这里**不另建一份词表** —— 两处各写一份迟早会漂移，
 * 而措辞红线是合规项。
 *
 * <p>判定是**字符串级**的：禁用词出现在否定句里同样不合规（不引入语义豁免，见 R14 踩坑记录）。
 */
public final class ReportTemplateWording {

    private ReportTemplateWording() {
    }

    /** 合规（可为空文案）→ true；命中保证性断言 → false。 */
    public static boolean compliant(String text) {
        return ReportController.wordingCompliant(text);
    }

    /** 命中的禁用词（用于错误详情，便于运营定位）。 */
    public static java.util.List<String> violations(String text) {
        if (text == null || text.isBlank()) {
            return java.util.List.of();
        }
        return ReportController.forbiddenPhrases().stream().filter(text::contains).toList();
    }
}
