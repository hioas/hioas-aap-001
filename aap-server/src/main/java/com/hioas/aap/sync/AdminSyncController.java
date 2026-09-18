package com.hioas.aap.sync;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.sync.SyncViews.BindingStatusRequest;
import com.hioas.aap.sync.SyncViews.ChannelBinding;
import com.hioas.aap.sync.SyncViews.SyncTask;
import com.hioas.aap.sync.SyncViews.UpstreamModels;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端 new-api 同步运维（ADM-S01…06；清单 §2.4）。
 *
 * <p>权限：技术运营（TECH_OPS）——同步属技术侧能力（`13-管理端PRD`：运营商务看不到同步/配置/审计）；
 * 超管按能力矩阵为全量权限，故一并放行（与 `D-API-22`/`D-API-26` 同一口径，见偏差表 `D-SYNC-04`）。
 *
 * <p>`E-1505`（403「同步接口权限不足」）由服务层在**上游 new-api 侧拒绝**（端点只读 / 上游 401/403）时抛出。
 */
@RestController
@RequestMapping("/api/v1/admin")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class AdminSyncController {

    private final SyncAdminService syncAdminService;

    public AdminSyncController(SyncAdminService syncAdminService) {
        this.syncAdminService = syncAdminService;
    }

    /** ADM-S01 同步任务列表（`status`/`bindingId` 可选过滤）。 */
    @GetMapping("/sync/tasks")
    public ApiEnvelope<PageResult<SyncTask>> listTasks(@RequestParam(required = false) Integer page,
                                                       @RequestParam(required = false) Integer pageSize,
                                                       @RequestParam(required = false) String status,
                                                       @RequestParam(required = false) String bindingId) {
        return ApiEnvelope.ok(syncAdminService.listTasks(page, pageSize, status, optionalId(bindingId, "bindingId")));
    }

    /** ADM-S02 任务详情（含 operations 明细）。 */
    @GetMapping("/sync/tasks/{taskId}")
    public ApiEnvelope<SyncTask> taskDetail(@PathVariable String taskId) {
        return ApiEnvelope.ok(syncAdminService.taskDetail(parseId(taskId, "taskId")));
    }

    /** ADM-S03 重试（退避 30s/2m/8m/30m，≤5 次；鉴权类失败不重试转 MANUAL）。 */
    @PostMapping("/sync/tasks/{taskId}/retry")
    public ApiEnvelope<SyncTask> retry(@AuthenticationPrincipal AuthPrincipal principal,
                                       @PathVariable String taskId) {
        return ApiEnvelope.ok(syncAdminService.retry(principal, parseId(taskId, "taskId")));
    }

    /** ADM-S04 渠道绑定列表（分页）。 */
    @GetMapping("/channel-bindings")
    public ApiEnvelope<PageResult<ChannelBinding>> listBindings(@RequestParam(required = false) Integer page,
                                                                @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(syncAdminService.listBindings(page, pageSize));
    }

    /** ADM-S05 渠道启停（`ENABLED`/`DISABLED`，读前写后回读一致）。 */
    @PostMapping("/channel-bindings/{bindingId}/status")
    public ApiEnvelope<ChannelBinding> changeBindingStatus(@AuthenticationPrincipal AuthPrincipal principal,
                                                           @PathVariable String bindingId,
                                                           @RequestBody(required = false) BindingStatusRequest request) {
        return ApiEnvelope.ok(syncAdminService.changeBindingStatus(principal, parseId(bindingId, "bindingId"),
                request == null ? new BindingStatusRequest(null) : request));
    }

    /** ADM-S06 上游（new-api）模型清单。 */
    @GetMapping("/sync/models/upstream")
    public ApiEnvelope<UpstreamModels> upstreamModels() {
        return ApiEnvelope.ok(syncAdminService.upstreamModels());
    }

    /** 非法 ID 一律 E-1001（不静默当 null）。 */
    private static Long parseId(String value, String field) {
        try {
            return Long.valueOf(value.trim());
        } catch (RuntimeException e) {
            throw ApiException.field(ErrorCode.E_1001, field, "不是合法的雪花 ID：" + value);
        }
    }

    /** 可选过滤参数：缺省（null/空）不过滤；给了非法值则 400（不静默忽略）。 */
    private static Long optionalId(String value, String field) {
        return value == null || value.isBlank() ? null : parseId(value, field);
    }
}
