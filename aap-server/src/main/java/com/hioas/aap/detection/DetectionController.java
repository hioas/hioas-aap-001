package com.hioas.aap.detection;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.iam.AuthPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 检测任务接口（DET-01…06）。
 *
 * <p>权限：DET-01…05 限供应商本人（任务归属校验在 Service，不可见即 404 E-1304）；
 * DET-06 人工放行限技术运营/超管，且理由必填（R-47a）。
 */
@RestController
@RequestMapping("/api/v1/detection-jobs")
public class DetectionController {

    private final DetectionService detectionService;

    public DetectionController(DetectionService detectionService) {
        this.detectionService = detectionService;
    }

    public record CreateJobRequest(
            @NotBlank(message = "缺少 credential_id") String credential_id,
            @Pattern(regexp = "^(FIRST|MANUAL|SCHEDULED)$", message = "trigger_type 不合法") String trigger_type) {
    }

    public record ReleaseRequest(@NotBlank(message = "人工放行必须填写理由") String override_reason) {
    }

    /** DET-01 新建检测任务（人工重测）。 */
    @PostMapping
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<DetectionViews.Job> create(@AuthenticationPrincipal AuthPrincipal principal,
                                                  @Valid @RequestBody CreateJobRequest request) {
        return ApiEnvelope.ok(detectionService.createJob(principal, Long.valueOf(request.credential_id()),
                request.trigger_type()));
    }

    /** DET-02 任务详情（进度页轮询）。 */
    @GetMapping("/{jobId}")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<DetectionViews.Job> job(@AuthenticationPrincipal AuthPrincipal principal,
                                               @PathVariable Long jobId) {
        return ApiEnvelope.ok(detectionService.job(principal, jobId));
    }

    /** DET-03 逐项结果。 */
    @GetMapping("/{jobId}/results")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<DetectionViews.ResultList> results(@AuthenticationPrincipal AuthPrincipal principal,
                                                          @PathVariable Long jobId) {
        return ApiEnvelope.ok(detectionService.results(principal, jobId));
    }

    /** DET-04 单个探测项结果。 */
    @GetMapping("/{jobId}/results/{probeCode}")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<DetectionViews.Result> result(@AuthenticationPrincipal AuthPrincipal principal,
                                                     @PathVariable Long jobId,
                                                     @PathVariable String probeCode) {
        return ApiEnvelope.ok(detectionService.result(principal, jobId, probeCode));
    }

    /** DET-05 取消任务。 */
    @PostMapping("/{jobId}/cancel")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<DetectionViews.Job> cancel(@AuthenticationPrincipal AuthPrincipal principal,
                                                  @PathVariable Long jobId) {
        return ApiEnvelope.ok(detectionService.cancel(principal, jobId));
    }

    /** DET-06 人工放行（技术运营/超管）。 */
    @PostMapping("/{jobId}/release")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public ApiEnvelope<DetectionViews.Job> release(@PathVariable Long jobId,
                                                   @Valid @RequestBody ReleaseRequest request,
                                                   HttpServletRequest http) {
        return ApiEnvelope.ok(detectionService.release(jobId, request.override_reason(), clientIp(http)));
    }

    private static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    /** 供内部调试使用的任务摘要（不对外暴露契约）。 */
    @GetMapping("/{jobId}/digest")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<java.util.List<Map<String, Object>>> digest(@AuthenticationPrincipal AuthPrincipal principal,
                                                                    @PathVariable Long jobId) {
        detectionService.job(principal, jobId);
        return ApiEnvelope.ok(detectionService.resultDigest(jobId));
    }
}
