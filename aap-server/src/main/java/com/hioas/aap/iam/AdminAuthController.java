package com.hioas.aap.iam;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.iam.dto.LoginResult;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端账号接入（**新增端点**：此前管理端没有登录入口 —— 见 {@link AdminAuthService} 的原因说明）。
 *
 * <p>端点：
 * <ul>
 *   <li>{@code POST /api/v1/admin/auth/sms/login} —— 手机号 + 短信验证码登录，
 *       签发 {@code subjectType=ADMIN} 令牌（role 取自 {@code aap_admin_user}）。
 *       验证码下发复用公共端点 {@code POST /api/v1/auth/sms/send}（同一套频控）。</li>
 * </ul>
 *
 * <p>本端点在 {@code SecurityConfig.PUBLIC_PATHS} 里放行（登录本身不能要求先登录），
 * 且**不加** {@code @PreAuthorize}：放行后能否登录由 {@code aap_admin_user} 决定。
 */
@RestController
@RequestMapping("/api/v1/admin/auth")
public class AdminAuthController {

    private final AdminAuthService adminAuthService;

    public AdminAuthController(AdminAuthService adminAuthService) {
        this.adminAuthService = adminAuthService;
    }

    /** 管理端短信登录（校验口径与供应商登录一致：手机号格式 + 6 位数字验证码）。 */
    @PostMapping("/sms/login")
    public ApiEnvelope<LoginResult> smsLogin(@Valid @RequestBody AuthController.SmsLoginRequest request,
                                            HttpServletRequest http) {
        return ApiEnvelope.ok(adminAuthService.smsLogin(request.phone(), request.smsCode(),
                http.getHeader("User-Agent"), AuthController.clientIp(http)));
    }
}
