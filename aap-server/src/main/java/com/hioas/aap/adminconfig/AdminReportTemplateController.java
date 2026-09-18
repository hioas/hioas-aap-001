package com.hioas.aap.adminconfig;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.hioas.aap.adminconfig.ReportTemplateViews.Template;
import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端报告模板配置（ADM-CFG06…10；清单 §2.4）。
 *
 * <p>权限：技术运营（TECH_OPS）——检测配置/报告模板属技术侧能力（`13-管理端PRD` §「运营商务看不到
 * 检测配置/报告模板/审计日志」）；超管按能力矩阵为全量权限，故一并放行。
 *
 * <p>措辞红线（R-26）在服务层统一校验：创建与修改都过同一道 {@link ReportTemplateWording}。
 */
@RestController
@RequestMapping("/api/v1/admin/report-templates")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class AdminReportTemplateController {

    private final ReportTemplateService reportTemplateService;

    public AdminReportTemplateController(ReportTemplateService reportTemplateService) {
        this.reportTemplateService = reportTemplateService;
    }

    /** ADM-CFG06 模板列表（`status` 可选：DRAFT/PUBLISHED/SUPERSEDED）。 */
    @GetMapping
    public ApiEnvelope<PageResult<Template>> list(@RequestParam(required = false) Integer page,
                                                  @RequestParam(required = false) Integer pageSize,
                                                  @RequestParam(required = false) String status) {
        return ApiEnvelope.ok(reportTemplateService.list(page, pageSize, status));
    }

    /** ADM-CFG07 新建模板（初始 DRAFT）。 */
    @PostMapping
    public ApiEnvelope<Template> create(@AuthenticationPrincipal AuthPrincipal principal,
                                        @RequestBody(required = false) SaveRequest request) {
        SaveRequest body = request == null ? new SaveRequest(null, null, null, null) : request;
        return ApiEnvelope.ok(reportTemplateService.create(principal, body.title(), body.logoFileId(),
                body.sectionOrder(), body.disclaimer()));
    }

    /** ADM-CFG08 模板详情。 */
    @GetMapping("/{templateId}")
    public ApiEnvelope<Template> detail(@PathVariable String templateId) {
        return ApiEnvelope.ok(reportTemplateService.detail(parseId(templateId)));
    }

    /** ADM-CFG09 修改模板（仅 DRAFT；未提供的字段保持原值）。 */
    @PutMapping("/{templateId}")
    public ApiEnvelope<Template> update(@AuthenticationPrincipal AuthPrincipal principal,
                                        @PathVariable String templateId,
                                        @RequestBody(required = false) SaveRequest request) {
        SaveRequest body = request == null ? new SaveRequest(null, null, null, null) : request;
        return ApiEnvelope.ok(reportTemplateService.update(principal, parseId(templateId), body.title(),
                body.logoFileId(), body.sectionOrder(), body.disclaimer()));
    }

    /** ADM-CFG10 发布模板（DRAFT → PUBLISHED；旧活版置 SUPERSEDED）。 */
    @PostMapping("/{templateId}/publish")
    public ApiEnvelope<Template> publish(@AuthenticationPrincipal AuthPrincipal principal,
                                         @PathVariable String templateId) {
        return ApiEnvelope.ok(reportTemplateService.publish(principal, parseId(templateId)));
    }

    /** 非法 ID 一律 E-1001（不静默当 null）。 */
    private static Long parseId(String value) {
        try {
            return Long.valueOf(value.trim());
        } catch (RuntimeException e) {
            throw ApiException.field(ErrorCode.E_1001, "templateId", "不是合法的雪花 ID：" + value);
        }
    }

    /** ADM-CFG07/09 请求体（清单字段名：`title` `logo_file_id` `section_order` `disclaimer`）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record SaveRequest(
            String title,
            @JsonProperty("logo_file_id") String logoFileId,
            @JsonProperty("section_order") List<String> sectionOrder,
            String disclaimer) {
    }
}
