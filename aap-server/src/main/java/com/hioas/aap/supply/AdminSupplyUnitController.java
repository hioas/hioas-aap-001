package com.hioas.aap.supply;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端供给单元运维（`ADM-SU01…04`；契约 `docs/backend/02-API接口模型清单.md` §2.6）。
 *
 * <p>权限（清单逐行）：`TECH_OPS` + `SUPER_ADMIN`；其余管理端角色（如 `BIZ_OPERATOR`）与供应商
 * 一律 403 `E-1901`，未认证 401 `E-1902`（由安全层拦下，方法体不重复判）。
 *
 * <p>与供应商端 `SET-MDL01`（`/provider/supply-units`，仅本人主体、只读）是**两套视图**：
 * 管理端可按任意维度筛全部供给单元，并把「重配置/下架」这两个治理动作暴露出来。
 *
 * <p>状态码：`ADM-SU03` 按契约返回 **202 已受理**（重配置是异步编排，差异清单在响应体里给，
 * 上游写入由 T-M4-08~11 的执行器接管）；其余 200。
 */
@RestController
@RequestMapping("/api/v1/admin/supply-units")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class AdminSupplyUnitController {

    private final SupplyUnitAdminService service;

    public AdminSupplyUnitController(SupplyUnitAdminService service) {
        this.service = service;
    }

    /** ADM-SU01 供给单元列表（`providerId`/`modelName`/`status` 可选 + 分页）。 */
    @GetMapping
    public ApiEnvelope<PageResult<SupplyUnitViews.SupplyUnit>> list(@RequestParam(required = false) Integer page,
                                                                   @RequestParam(required = false) Integer pageSize,
                                                                   @RequestParam(required = false) Long providerId,
                                                                   @RequestParam(required = false) String modelName,
                                                                   @RequestParam(required = false) String status) {
        return ApiEnvelope.ok(service.adminList(page, pageSize, providerId, modelName, status));
    }

    /** ADM-SU02 供给单元详情（含调度画像与质量分；不存在 → 404 `E-1406`）。 */
    @GetMapping("/{id}")
    public ApiEnvelope<SupplyUnitViews.SupplyUnit> detail(@PathVariable Long id) {
        return ApiEnvelope.ok(service.detail(id));
    }

    /**
     * ADM-SU03 重配置（INNOV-7 / FR-2.9）：返回 **202** 与配置批次（含 dry-run 差异清单）。
     *
     * <p>请求体可省略（契约 `dry_run` 默认 `true` → 预演、生产零写入）。
     */
    @PostMapping("/{id}/reconfigure")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public ApiEnvelope<SupplyUnitViews.ConfigBatch> reconfigure(
            @AuthenticationPrincipal AuthPrincipal principal,
            @PathVariable Long id,
            @Valid @RequestBody(required = false) SupplyUnitViews.ReconfigureRequest request) {
        Boolean dryRun = request == null ? null : request.dryRun();
        String reason = request == null ? null : request.reason();
        return ApiEnvelope.ok(service.reconfigure(principal, id, dryRun, reason));
    }

    /** ADM-SU04 下架（R-65：存在未结清账期 → 409 `E-1601`）。 */
    @PostMapping("/{id}/offline")
    public ApiEnvelope<SupplyUnitViews.SupplyUnit> offline(@AuthenticationPrincipal AuthPrincipal principal,
                                                          @PathVariable Long id) {
        return ApiEnvelope.ok(service.offline(principal, id));
    }
}
