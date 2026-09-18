package com.hioas.aap.adminconfig;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * 报告模板响应模型（契约真源：`docs/backend/json-schema/models/report-template.schema.json`，
 * 由 `tools/gen-backend-models.py` 从冻结清单生成）。
 *
 * <p>雪花 ID 对外一律 string（避免 JS 精度丢失）；时间 RFC3339 UTC；缺值回 null。
 * {@code template_id} 是 {@code id} 的兼容别名（模型里两个字段都在）—— 两处同值，
 * 不引入第二套主键语义。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class ReportTemplateViews {

    private ReportTemplateViews() {
    }

    /** 单份报告模板（ADM-CFG06/07/08/09/10 的统一视图）。 */
    public record Template(
            String id,
            @JsonProperty("template_id") String templateId,
            @JsonProperty("template_no") String templateNo,
            @JsonProperty("version_no") String versionNo,
            String title,
            @JsonProperty("logo_file_id") String logoFileId,
            @JsonProperty("section_order") List<String> sectionOrder,
            String disclaimer,
            String status,
            @JsonProperty("published_at") String publishedAt,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("updated_at") String updatedAt) {
    }
}
