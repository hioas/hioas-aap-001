package com.hioas.aap.adminconfig;

import com.hioas.aap.adminconfig.DetectionConfigViews.DetectionConfig;
import com.hioas.aap.adminconfig.DetectionConfigViews.SaveRequest;
import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
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
 * 管理端检测配置版本（ADM-CFG01…05；清单 §2.4）。
 *
 * <p>权限：技术运营（TECH_OPS）——检测配置属技术侧能力（`13-管理端PRD` §「运营商务看不到
 * 检测配置/报告模板/审计日志」）；超管按能力矩阵为全量权限，故一并放行。
 *
 * <p>状态推进只在 ADM-CFG05：`DRAFT → PUBLISHED`，客户端不能通过 ADM-CFG02/04 直接置生效态。
 */
@RestController
@RequestMapping("/api/v1/admin/detection-configs")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class AdminDetectionConfigController {

    private final DetectionConfigService detectionConfigService;

    public AdminDetectionConfigController(DetectionConfigService detectionConfigService) {
        this.detectionConfigService = detectionConfigService;
    }

    /** ADM-CFG01 配置列表（`status` 可选：DRAFT/PUBLISHED/SUPERSEDED）。 */
    @GetMapping
    public ApiEnvelope<PageResult<DetectionConfig>> list(@RequestParam(required = false) Integer page,
                                                         @RequestParam(required = false) Integer pageSize,
                                                         @RequestParam(required = false) String status) {
        return ApiEnvelope.ok(detectionConfigService.list(page, pageSize, status));
    }

    /** ADM-CFG02 新建配置（初始 DRAFT，新版本号）。 */
    @PostMapping
    public ApiEnvelope<DetectionConfig> create(@AuthenticationPrincipal AuthPrincipal principal,
                                               @RequestBody(required = false) SaveRequest request) {
        return ApiEnvelope.ok(detectionConfigService.create(principal, body(request)));
    }

    /** ADM-CFG03 配置详情。 */
    @GetMapping("/{configId}")
    public ApiEnvelope<DetectionConfig> detail(@PathVariable String configId) {
        return ApiEnvelope.ok(detectionConfigService.detail(parseId(configId)));
    }

    /** ADM-CFG04 修改配置（仅 DRAFT；未提供的字段保持原值）。 */
    @PutMapping("/{configId}")
    public ApiEnvelope<DetectionConfig> update(@AuthenticationPrincipal AuthPrincipal principal,
                                               @PathVariable String configId,
                                               @RequestBody(required = false) SaveRequest request) {
        return ApiEnvelope.ok(detectionConfigService.update(principal, parseId(configId), body(request)));
    }

    /** ADM-CFG05 发布配置（DRAFT → PUBLISHED；旧活版置 SUPERSEDED）。 */
    @PostMapping("/{configId}/publish")
    public ApiEnvelope<DetectionConfig> publish(@AuthenticationPrincipal AuthPrincipal principal,
                                                @PathVariable String configId) {
        return ApiEnvelope.ok(detectionConfigService.publish(principal, parseId(configId)));
    }

    private static SaveRequest body(SaveRequest request) {
        return request == null ? new SaveRequest(null, null, null, null, null) : request;
    }

    /** 非法 ID 一律 E-1001（不静默当 null）。 */
    private static Long parseId(String value) {
        try {
            return Long.valueOf(value.trim());
        } catch (RuntimeException e) {
            throw ApiException.field(ErrorCode.E_1001, "configId", "不是合法的雪花 ID：" + value);
        }
    }
}
