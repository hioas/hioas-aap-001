package com.hioas.aap.iam;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AdminUserViews.AdminUser;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
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
 * 运营账号管理接口（ADM-AUTH02…05；`docs/backend/02-API接口模型清单.md` §2.5）。
 *
 * <p>权限：**仅 SUPER_ADMIN**。建号/停用是提权操作，不能下放给 BIZ_OPERATOR / TECH_OPS。
 * 规则细节（唯一性、最后一个超管、不可停用自己）见 {@link AdminUserService}。
 */
@RestController
@RequestMapping("/api/v1/admin/admin-users")
@PreAuthorize("hasRole('SUPER_ADMIN')")
public class AdminUserController {

    private final AdminUserService adminUserService;

    public AdminUserController(AdminUserService adminUserService) {
        this.adminUserService = adminUserService;
    }

    /** ADM-AUTH02 运营账号列表（q：page/pageSize/role?/status?/keyword?）。 */
    @GetMapping
    public ApiEnvelope<PageResult<AdminUser>> list(@RequestParam(required = false) Integer page,
                                                  @RequestParam(required = false) Integer pageSize,
                                                  @RequestParam(required = false) String role,
                                                  @RequestParam(required = false) String status,
                                                  @RequestParam(required = false) String keyword) {
        return ApiEnvelope.ok(adminUserService.list(page, pageSize, role, status, keyword));
    }

    /** ADM-AUTH03 开运营账号（手机号即登录名）。 */
    @PostMapping
    public ApiEnvelope<AdminUser> create(@AuthenticationPrincipal AuthPrincipal principal,
                                         @Valid @RequestBody CreateRequest request) {
        return ApiEnvelope.ok(adminUserService.create(principal, new AdminUserService.CreateCommand(
                request.username(), request.display_name(), request.role(), request.phone())));
    }

    /** ADM-AUTH04 停用运营账号（必填理由）。 */
    @PostMapping("/{id}/suspend")
    public ApiEnvelope<AdminUser> suspend(@AuthenticationPrincipal AuthPrincipal principal,
                                          @PathVariable String id,
                                          @Valid @RequestBody SuspendRequest request) {
        return ApiEnvelope.ok(adminUserService.suspend(principal, parseId(id), request.reason()));
    }

    /** ADM-AUTH05 恢复运营账号。 */
    @PostMapping("/{id}/resume")
    public ApiEnvelope<AdminUser> resume(@AuthenticationPrincipal AuthPrincipal principal,
                                         @PathVariable String id) {
        return ApiEnvelope.ok(adminUserService.resume(principal, parseId(id)));
    }

    /** ADM-AUTH03 请求体（与 `admin-user-create.schema.json` 一致）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record CreateRequest(
            @NotBlank(message = "账号名必填") @Size(max = 64, message = "账号名不超过 64 字") String username,
            @Size(max = 64, message = "显示名不超过 64 字") String display_name,
            @NotBlank(message = "角色必填") String role,
            @NotBlank(message = "手机号必填") @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
            String phone) {
    }

    /** ADM-AUTH04 请求体（与 `admin-user-suspend.schema.json` 一致）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record SuspendRequest(
            @NotBlank(message = "停用必须填写理由") @Size(max = 255, message = "理由不超过 255 字") String reason) {
    }

    /** 非法 ID 一律 E-1001（不静默当 null，避免变成「查全量」）。 */
    private static Long parseId(String value) {
        if (value == null || value.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "id", "运营账号 ID 必填");
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, "id", "不是合法的雪花 ID：" + value);
        }
    }
}
