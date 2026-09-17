package com.hioas.aap.credential;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 测试凭证接口（CRED-01…07）。
 *
 * <p>权限：CRED-01…06 限供应商本人；CRED-07（明文读取）限超管 + 短信二次验证。
 */
@RestController
@RequestMapping("/api/v1/credentials")
public class CredentialController {

    private final CredentialService credentialService;

    public CredentialController(CredentialService credentialService) {
        this.credentialService = credentialService;
    }

    public record CredentialRequest(
            @Size(max = 64, message = "凭证名最多 64 字") String alias,
            @NotBlank(message = "请输入接口地址") String base_url,
            String api_key,
            Boolean primary_flag,
            String declared_vendor,
            Integer declared_rpm,
            Integer declared_tpm,
            Integer declared_context_window,
            List<Map<String, Object>> model_list,
            String env_tag) {
    }

    public record RevealRequest(@NotBlank @Pattern(regexp = "^\\d{6}$", message = "验证码须为 6 位数字") String smsCode) {
    }

    /** CRED-01 凭证列表（最近接入优先）。 */
    @GetMapping
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<PageResult<CredentialViews.Row>> list(@AuthenticationPrincipal AuthPrincipal principal,
                                                             @RequestParam(required = false) Integer page,
                                                             @RequestParam(required = false) Integer pageSize,
                                                             @RequestParam(required = false) String status) {
        return ApiEnvelope.ok(credentialService.list(principal, page, pageSize, status));
    }

    /** CRED-02 创建凭证。 */
    @PostMapping
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<CredentialViews.Detail> create(@AuthenticationPrincipal AuthPrincipal principal,
                                                      @Valid @RequestBody CredentialRequest request) {
        return ApiEnvelope.ok(credentialService.create(principal, toCommand(request, true)));
    }

    /** CRED-03 凭证详情。 */
    @GetMapping("/{id}")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<CredentialViews.Detail> detail(@AuthenticationPrincipal AuthPrincipal principal,
                                                      @PathVariable Long id) {
        return ApiEnvelope.ok(credentialService.detail(principal, id));
    }

    /** CRED-04 更新凭证（可轮换 api_key；支持 If-Match）。 */
    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<CredentialViews.Detail> update(@AuthenticationPrincipal AuthPrincipal principal,
                                                      @PathVariable Long id,
                                                      @Valid @RequestBody CredentialRequest request,
                                                      @RequestHeader(value = "If-Match", required = false) String ifMatch) {
        return ApiEnvelope.ok(credentialService.update(principal, id, toCommand(request, false), ifMatch));
    }

    /** CRED-05 提交检测（预检 + 建检测任务）。 */
    @PostMapping("/{id}/precheck")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<CredentialViews.PrecheckResult> precheck(@AuthenticationPrincipal AuthPrincipal principal,
                                                                @PathVariable Long id) {
        return ApiEnvelope.ok(credentialService.precheck(principal, id));
    }

    /** CRED-06 最新预检记录。 */
    @GetMapping("/{id}/precheck/latest")
    @PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
    public ApiEnvelope<CredentialViews.Precheck> latestPrecheck(@AuthenticationPrincipal AuthPrincipal principal,
                                                                @PathVariable Long id) {
        return ApiEnvelope.ok(credentialService.latestPrecheck(principal, id));
    }

    /** CRED-07 明文读取（仅超管 + 短信二次验证 + SENSITIVE 审计）。 */
    @PostMapping("/{id}/reveal")
    @PreAuthorize("hasRole('SUPER_ADMIN')")
    public ApiEnvelope<CredentialViews.Reveal> reveal(@AuthenticationPrincipal AuthPrincipal principal,
                                                      @PathVariable Long id,
                                                      @Valid @RequestBody RevealRequest request,
                                                      HttpServletRequest http) {
        return ApiEnvelope.ok(credentialService.reveal(principal, id, request.smsCode(), clientIp(http)));
    }

    private static CredentialService.CredentialCommand toCommand(CredentialRequest request, boolean create) {
        return new CredentialService.CredentialCommand(
                request.alias(), request.base_url(), request.api_key(), request.primary_flag(),
                request.declared_vendor(), request.declared_rpm(), request.declared_tpm(),
                request.declared_context_window(), request.model_list(), request.env_tag());
    }

    private static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
