package com.hioas.aap.provider;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
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
 * 管理端供应商运维（ADM-P01…03；清单 §2.4）。
 *
 * <p>权限：运营商务（`BIZ_OPERATOR`）+ 技术运营（`TECH_OPS`）+ 超管（`SUPER_ADMIN`）——
 * 清单三条都列了这三个角色；供应商与未认证由安全层拦成 403 `E-1901` / 401 `E-1902`。
 *
 * <p>与供应商端 `PROV-01…05`（`/provider/**`，仅本人主体）是**两套视图**：管理端按 id 操作任意供应商，
 * 但不返回明文联系方式（`ProviderProfileResponse` 只回脱敏值）。
 */
@RestController
@RequestMapping("/api/v1/admin/providers")
@PreAuthorize("hasAnyRole('BIZ_OPERATOR','TECH_OPS','SUPER_ADMIN')")
public class AdminProviderController {

    private final ProviderService providerService;

    public AdminProviderController(ProviderService providerService) {
        this.providerService = providerService;
    }

    /** ADM-P02 请求体（契约：`json-schema/requests/provider-suspend.schema.json`，`suspend_reason` 2–500 字）。 */
    public record SuspendRequest(
            @NotBlank(message = "请填写暂停原因")
            @Size(min = 2, max = 500, message = "暂停原因需 2–500 字") String suspend_reason) {
    }

    /** ADM-P01 供应商列表（`status` / `keyword` 可选）。 */
    @GetMapping
    public ApiEnvelope<PageResult<ProviderProfileResponse>> list(@RequestParam(required = false) Integer page,
                                                                @RequestParam(required = false) Integer pageSize,
                                                                @RequestParam(required = false) String status,
                                                                @RequestParam(required = false) String keyword) {
        return ApiEnvelope.ok(providerService.adminList(page, pageSize, status, keyword));
    }

    /** ADM-P02 暂停（`suspended_at` / `suspend_reason` / 暂停前状态留痕；状态非法 409 E-1601）。 */
    @PostMapping("/{id}/suspend")
    public ApiEnvelope<ProviderProfileResponse> suspend(@AuthenticationPrincipal AuthPrincipal principal,
                                                       @PathVariable Long id,
                                                       @Valid @RequestBody SuspendRequest request) {
        return ApiEnvelope.ok(providerService.suspend(principal, id, request.suspend_reason()));
    }

    /** ADM-P03 恢复（回到暂停前状态；非暂停态 409 E-1601）。 */
    @PostMapping("/{id}/resume")
    public ApiEnvelope<ProviderProfileResponse> resume(@AuthenticationPrincipal AuthPrincipal principal,
                                                      @PathVariable Long id) {
        return ApiEnvelope.ok(providerService.resume(principal, id));
    }
}
