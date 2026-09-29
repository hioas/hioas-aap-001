package com.hioas.aap.supply;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
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
 * 管理端批量配置批次（`ADM-CB01…05`；契约 `docs/backend/02-API接口模型清单.md` §2.6）。
 *
 * <p>权限（清单逐行）：`TECH_OPS` + `SUPER_ADMIN`；其余管理端角色（如 `BIZ_OPERATOR`）与供应商一律 403
 * `E-1901`，未认证 401 `E-1902`（由安全层拦下，方法体不重复判）。
 *
 * <p>状态码：清单 §2.6 逐行声明 —— 创建 **201**、单模型重试 **202**、单模型回滚 **202**（异步编排的受理语义，
 * 与 `ADM-SU03` 的 202 同族；零业务码的通用「业务码 0 → 200」映射不变，只是 HTTP 层用 201/202 表达
 * 「已创建 / 已受理」）。
 *
 * <p>依赖注入口径：字段名取 **类名小写首字母**（`configBatchAdminService`）—— 与仓库既有控制器一致，
 * 也是静态审计（分页夹取发生在控制器或其调用链上、状态机写点的 from 守卫等）解析接收者类型的方式；
 * 用裸 `service` 会让这些链路判定断链（把「已夹取」误报成缺口）。
 */
@RestController
@RequestMapping("/api/v1/admin/config-batches")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class AdminConfigBatchController {

    private final ConfigBatchAdminService configBatchAdminService;
    private final ConfigApplyExecutor configApplyExecutor;

    public AdminConfigBatchController(ConfigBatchAdminService configBatchAdminService,
                                      ConfigApplyExecutor configApplyExecutor) {
        this.configBatchAdminService = configBatchAdminService;
        this.configApplyExecutor = configApplyExecutor;
    }

    /** ADM-CB01 创建批次（DRY_RUN 出差异清单且生产零写入；影响面 > 20 个单元 → 409 `E-1601`）。 */
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiEnvelope<SupplyUnitViews.ConfigBatch> create(
            @AuthenticationPrincipal AuthPrincipal principal,
            @RequestBody(required = false) SupplyUnitViews.ConfigBatchCreateRequest request) {
        SupplyUnitViews.ConfigBatch batch = configBatchAdminService.create(principal, request);
        // DRY_RUN 天然零写入（AC-10）；只有 APPLY 才触发执行器把 PENDING 明细真正下发到网关。
        // 执行结果（逐项 SUCCEEDED/FAILED/MISMATCH 与回读结论）通过 ADM-CB03 详情查看 ——
        // 本响应体是「受理时刻」的快照，计数在执行前，故不在此处重算，避免与详情口径不一致。
        if (batch.mode() != null && !"DRY_RUN".equals(batch.mode())) {
            int rate = batch.rateLimitPerSec() == null
                    ? ConfigApplyRateLimiter.DEFAULT_RATE_PER_SEC : batch.rateLimitPerSec();
            configApplyExecutor.execute(ConfigBatchReader.longOf(batch.id()), rate);
        }
        return ApiEnvelope.ok(batch);
    }

    /** ADM-CB02 批次列表（分页 + `status` 可选过滤）。 */
    @GetMapping
    public ApiEnvelope<PageResult<SupplyUnitViews.ConfigBatch>> list(@RequestParam(required = false) Integer page,
                                                                     @RequestParam(required = false) Integer pageSize,
                                                                     @RequestParam(required = false) String status) {
        return ApiEnvelope.ok(configBatchAdminService.adminList(page, pageSize, status));
    }

    /** ADM-CB03 批次详情（含明细与其中的 `mismatch` 清单）。 */
    @GetMapping("/{batchId}")
    public ApiEnvelope<SupplyUnitViews.ConfigBatch> detail(@PathVariable Long batchId) {
        return ApiEnvelope.ok(configBatchAdminService.detail(batchId));
    }

    /** ADM-CB04 单模型重试（R-59：只影响该项）。 */
    @PostMapping("/{batchId}/items/{itemId}/retry")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public ApiEnvelope<SupplyUnitViews.ConfigBatchItem> retryItem(@AuthenticationPrincipal AuthPrincipal principal,
                                                                 @PathVariable Long batchId,
                                                                 @PathVariable Long itemId) {
        return ApiEnvelope.ok(configBatchAdminService.retryItem(principal, batchId, itemId));
    }

    /** ADM-CB05 单模型回滚（`reason` 必填并留痕）。 */
    @PostMapping("/{batchId}/items/{itemId}/rollback")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public ApiEnvelope<SupplyUnitViews.ConfigBatchItem> rollbackItem(
            @AuthenticationPrincipal AuthPrincipal principal,
            @PathVariable Long batchId,
            @PathVariable Long itemId,
            @RequestBody(required = false) SupplyUnitViews.RollbackRequest request) {
        return ApiEnvelope.ok(configBatchAdminService.rollbackItem(principal, batchId, itemId, request));
    }
}
