package com.hioas.aap.detection;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端检测任务列表（**ADM-DET01，2026-09-23 新增**）。
 *
 * <p>为什么新增（运行态实测）：管理端「检测中心」页原先拿不到任何任务数据 ——
 * 全仓与检测任务相关的管理端端点只有 {@code POST /detection-jobs/{jobId}/release}（按 id 放行），
 * 而 {@code DET-01…05} 全部限供应商本人（管理端调用 403 {@code E-1901}）。
 * 结果：KPI 只能显示「未知」、任务表格为空、**人工放行需要人工手输任务 ID**（运营无从得知 ID）
 * → 人工放行实际不可用，而它是凭证拿到 {@code PASS}（进而报价）的唯一路径。
 *
 * <p>权限：技术运营 + 超管（与人工放行 `DET-06` 同档；运营商务不参与检测）。
 */
@RestController
@RequestMapping("/api/v1/admin/detection-jobs")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class AdminDetectionController {

    private final DetectionService detectionService;

    public AdminDetectionController(DetectionService detectionService) {
        this.detectionService = detectionService;
    }

    /** ADM-DET01 检测任务列表（q：status?/credentialId?/providerId?/page/pageSize）。 */
    @GetMapping
    public ApiEnvelope<PageResult<DetectionViews.Job>> list(@RequestParam(required = false) String status,
                                                           @RequestParam(required = false) Long credentialId,
                                                           @RequestParam(required = false) Long providerId,
                                                           @RequestParam(required = false) Integer page,
                                                           @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(detectionService.listForAdmin(status, credentialId, providerId, page, pageSize));
    }
}
