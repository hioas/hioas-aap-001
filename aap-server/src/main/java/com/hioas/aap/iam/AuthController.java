package com.hioas.aap.iam;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.iam.dto.LoginResult;
import com.hioas.aap.iam.dto.MeResult;
import com.hioas.aap.iam.dto.SmsSendResult;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.Map;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 账号接入接口（AUTH-01…06，见 docs/backend/02-API接口模型清单.md §1.1）。
 *
 * <p>校验规则（R-01/R-02）：手机号 {@code ^1[3-9]\d{9}$}；验证码 6 位数字；图形验证码本期只校验非空
 * （真实图形验证码服务未接入，标 `约定`）。
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    /** 管理端登录/当前登录者（{@code /admin/auth/*} 与 {@code /auth/me} 的管理端分支）。 */
    private final AdminAuthService adminAuthService;

    public AuthController(AuthService authService, AdminAuthService adminAuthService) {
        this.authService = authService;
        this.adminAuthService = adminAuthService;
    }

    public record SmsSendRequest(
            @NotBlank(message = "请输入手机号")
            @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确") String phone,
            @NotBlank(message = "请输入图形验证码") @Size(min = 2, max = 8, message = "图形验证码长度不正确") String captcha) {
    }

    public record SmsLoginRequest(
            @NotBlank @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确") String phone,
            @NotBlank @Pattern(regexp = "^\\d{6}$", message = "验证码须为 6 位数字") String smsCode) {
    }

    public record WechatLoginRequest(@NotBlank(message = "缺少微信登录 code") String code) {
    }

    public record RefreshRequest(@NotBlank(message = "缺少 refreshToken") String refreshToken) {
    }

    /** AUTH-01 下发短信验证码。 */
    @PostMapping("/sms/send")
    public ApiEnvelope<SmsSendResult> sendSms(@Valid @RequestBody SmsSendRequest request, HttpServletRequest http) {
        return ApiEnvelope.ok(authService.sendSms(request.phone(), clientIp(http)));
    }

    /** AUTH-02 短信验证码登录（首次即注册）。 */
    @PostMapping("/sms/login")
    public ApiEnvelope<LoginResult> smsLogin(@Valid @RequestBody SmsLoginRequest request, HttpServletRequest http) {
        return ApiEnvelope.ok(authService.smsLogin(request.phone(), request.smsCode(),
                http.getHeader("User-Agent"), clientIp(http)));
    }

    /** AUTH-03 微信登录（openid 绑定互认）。 */
    @PostMapping("/wechat/login")
    public ApiEnvelope<LoginResult> wechatLogin(@Valid @RequestBody WechatLoginRequest request, HttpServletRequest http) {
        return ApiEnvelope.ok(authService.wechatLogin(request.code(), http.getHeader("User-Agent"), clientIp(http)));
    }

    /** AUTH-04 换发令牌（refresh token 轮换）。 */
    @PostMapping("/refresh")
    public ApiEnvelope<LoginResult> refresh(@Valid @RequestBody RefreshRequest request, HttpServletRequest http) {
        return ApiEnvelope.ok(authService.refresh(request.refreshToken(),
                http.getHeader("User-Agent"), clientIp(http)));
    }

    /** AUTH-05 登出（撤销当前 jti）。 */
    @PostMapping("/logout")
    public ApiEnvelope<Map<String, Object>> logout(@AuthenticationPrincipal AuthPrincipal principal,
                                                   HttpServletRequest http) {
        String jti = (String) http.getAttribute(JwtAuthenticationFilter.JTI_ATTRIBUTE);
        if (principal == null || jti == null) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        authService.logout(jti);
        return ApiEnvelope.ok(Map.of("logged_out", true));
    }

    /**
     * AUTH-06 当前登录者（含「我的设置」页所需字段）。
     *
     * <p>管理端主体走**管理端档案**（{@code aap_admin_user}）：管理端账号不在
     * {@code aap_provider_account} 里，若不分支，管理端控制台登录成功后第一步调 {@code /auth/me}
     * 就会拿到 {@code E-1902}「未认证或登录已过期」（实测 aap-admin `useSession` 必调本端点）。
     */
    @GetMapping("/me")
    public ApiEnvelope<MeResult> me(@AuthenticationPrincipal AuthPrincipal principal) {
        if (principal == null) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        return ApiEnvelope.ok(principal.isAdmin()
                ? adminAuthService.me(principal)
                : authService.me(principal));
    }

    /** 取真实客户端 IP（{@code X-Forwarded-For} 首段优先）。包级可见：{@link AdminAuthController} 复用。 */
    static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
