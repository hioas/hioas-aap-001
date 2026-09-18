package com.hioas.aap.credential;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.iam.AuthPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端凭证（ADM-C01/02；清单 §2.4）。
 *
 * <p>权限：两条都限 `SUPER_ADMIN`（运营商务/技术运营不接触凭证明文语境）。非超管 403 `E-1901`、
 * 未认证 401 `E-1902`，由安全层与方法级授权统一产出。
 *
 * <p>`ADM-C02` 是 CRED-07 的**管理端入口**，直接复用 `CredentialService.reveal`：二次短信验证 +
 * `SENSITIVE` 审计只有一套实现（AC-30），避免两个入口对同一安全动作给出两套行为。
 */
@RestController
@RequestMapping("/api/v1/admin/credentials")
@PreAuthorize("hasRole('SUPER_ADMIN')")
public class AdminCredentialController {

    private final CredentialService credentialService;

    public AdminCredentialController(CredentialService credentialService) {
        this.credentialService = credentialService;
    }

    /** ADM-C02 请求体（契约：`json-schema/requests/credential-reveal.schema.json`，`smsCode` 6 位数字）。 */
    public record RevealRequest(
            @NotBlank(message = "请填写短信验证码")
            @Pattern(regexp = "^\\d{6}$", message = "验证码须为 6 位数字") String smsCode) {
    }

    /** ADM-C01 凭证详情（只回 `api_key_mask`，永不回明文）。 */
    @GetMapping("/{id}")
    public ApiEnvelope<CredentialViews.Detail> detail(@PathVariable Long id) {
        return ApiEnvelope.ok(credentialService.adminDetail(id));
    }

    /** ADM-C02 明文读取（超管 + 短信二次验证 + SENSITIVE 审计）。 */
    @PostMapping("/{id}/reveal")
    public ApiEnvelope<CredentialViews.Reveal> reveal(@AuthenticationPrincipal AuthPrincipal principal,
                                                      @PathVariable Long id,
                                                      @Valid @RequestBody RevealRequest request,
                                                      HttpServletRequest http) {
        return ApiEnvelope.ok(credentialService.reveal(principal, id, request.smsCode(), clientIp(http)));
    }

    private static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
