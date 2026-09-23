package com.hioas.aap.iam;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.AuditContext;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.config.AppProperties;
import com.hioas.aap.iam.dto.LoginResult;
import com.hioas.aap.iam.dto.MeResult;
import com.hioas.aap.support.AuditService;
import com.mybatisflex.core.query.QueryWrapper;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 管理端账号接入（**新增**：此前管理端没有任何登录入口）。
 *
 * <p>为什么需要它（2026-09-23 运行态实测确证）：
 * <ul>
 *   <li>{@code aap-admin}（运营管理端）的登录页调的是 {@code /auth/sms/login} —— 而
 *       {@link AuthService#issueTokens} 固定签发 {@code subjectType=PROVIDER}；
 *       于是管理端拿到的是供应商身份，调 {@code /api/v1/admin/**} 一律 403 {@code E-1901}；</li>
 *   <li>全仓没有 {@code admin/login}，API 清单 41 个 {@code ADM-*} 端点里也没有任何管理端鉴权端点
 *       → **真实环境里拿不到管理端身份**，人工放行 DET-06、报价审核、配置发布全都调不动；</li>
 *   <li>而报价前置要求凭证 {@code detection_status=PASS}，PASS 又只能来自管理端人工放行
 *       → 供应商全流程断在「检测 → 报价」这一跳（实测：绕过只能靠 SQL 直改账号角色，
 *       且 role 单值 —— 改成管理端角色后该账号连供应商端接口都被 403）。</li>
 * </ul>
 *
 * <p>设计取舍：**复用短信登录链路**（{@link SmsService#verify}：一次性验证码 + 60 秒频控 +
 * 连续错码锁定），不新造密码体系；身份域用 {@code aap_admin_user}（自带 {@code phone_hash} /
 * {@code role} / {@code status}），与供应商账号（{@code aap_provider_account}）完全分离，
 * 签发 {@code subjectType=ADMIN} 的令牌，role 取自管理端账号 —— 于是管理端的
 * {@code hasAnyRole('BIZ_OPERATOR','TECH_OPS','SUPER_ADMIN')} 与 {@code isAdmin()} 语义都成立。
 *
 * <p><b>不自动注册</b>：手机号不在 {@code aap_admin_user} 里一律拒绝（供应商登录才自动注册）。
 */
@Service
public class AdminAuthService {

    private static final Logger log = LoggerFactory.getLogger(AdminAuthService.class);

    /** 与 {@link AuthService} 同一组列宽约束（见该类注释：UA 长度不可控，超长会 INSERT 溢出）。 */
    private static final int USER_AGENT_MAX = 255;
    private static final int CLIENT_IP_MAX = 64;

    private final AdminUserMapper adminUserMapper;
    private final AuthTokenMapper authTokenMapper;
    private final SmsService smsService;
    private final JwtService jwtService;
    private final CryptoService crypto;
    private final AuditService auditService;
    private final AppProperties properties;

    public AdminAuthService(AdminUserMapper adminUserMapper, AuthTokenMapper authTokenMapper,
                            SmsService smsService, JwtService jwtService, CryptoService crypto,
                            AuditService auditService, AppProperties properties) {
        this.adminUserMapper = adminUserMapper;
        this.authTokenMapper = authTokenMapper;
        this.smsService = smsService;
        this.jwtService = jwtService;
        this.crypto = crypto;
        this.auditService = auditService;
        this.properties = properties;
    }

    /**
     * 管理端短信登录：验证码校验沿用供应商侧同一套频控/锁定，命中 {@code aap_admin_user} 才签发令牌。
     *
     * @throws ApiException 验证码错误/过期 → {@code E-1001}；错码过多 → {@code E-1903}；
     *                      非管理端手机号 → {@code E-1902}；账号非 ACTIVE → {@code E-1901}
     */
    @Transactional
    public LoginResult smsLogin(String phone, String smsCode, String userAgent, String clientIp) {
        smsService.verify(phone, smsCode);

        AdminUserEntity admin = findByPhoneHash(crypto.sha256Hex(phone));
        if (admin == null) {
            // 与「未认证」同码：不告诉调用方「这个号码不是管理端账号」之外的信息（也不落任何账号）
            log.warn("管理端登录被拒：手机号未开通管理端访问 phone={}", crypto.maskPhone(phone));
            throw new ApiException(ErrorCode.E_1902, "该手机号未开通管理端访问");
        }
        if (!"ACTIVE".equals(admin.getStatus())) {
            log.warn("管理端登录被拒：账号状态 {} account_id={}", admin.getStatus(), admin.getId());
            throw new ApiException(ErrorCode.E_1901, "账号已停用，请联系超管");
        }

        admin.setLastLoginAt(OffsetDateTime.now(ZoneOffset.UTC));
        adminUserMapper.update(admin);

        String role = admin.getRole() == null || admin.getRole().isBlank() ? "BIZ_OPERATOR" : admin.getRole();
        JwtService.IssuedAccessToken access = jwtService.issueAccessToken(admin.getId(), role, "ADMIN", null);

        AuthTokenEntity token = new AuthTokenEntity();
        token.setAccountId(admin.getId());
        token.setSubjectType("ADMIN");
        token.setJti(access.jti());
        token.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(properties.jwt().refreshTtlDays()));
        token.setUserAgent(fitToColumn(userAgent, USER_AGENT_MAX));
        token.setClientIp(fitToColumn(clientIp, CLIENT_IP_MAX));
        authTokenMapper.insert(token);

        AuditContext.set(new AuditContext.Actor(admin.getId(), "ADMIN", admin.getUsername(), clientIp));
        auditService.record(AuditService.AuditAction.AUTH_LOGIN, "admin_user", admin.getId(),
                "管理端登录成功（role=" + role + "）");

        log.info("管理端登录 account_id={} role={} jti={}", admin.getId(), role, access.jti());
        // 管理端不发 refresh token（会话过期后重新短信登录；refresh 端点只认供应商账号）
        return new LoginResult(access.token(), null, role, null, null, admin.getStatus(),
                jwtService.accessTtl().toSeconds());
    }

    /** 管理端当前登录者（{@code GET /auth/me} 的管理端分支）。 */
    public MeResult me(AuthPrincipal principal) {
        AdminUserEntity admin = adminUserMapper.selectOneById(principal.accountId());
        if (admin == null) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        return new MeResult(admin.getPhoneMasked(),
                admin.getRole() == null || admin.getRole().isBlank() ? "BIZ_OPERATOR" : admin.getRole(),
                null, null, admin.getStatus(), admin.getDisplayName(),
                false, false, false);
    }

    private AdminUserEntity findByPhoneHash(String phoneHash) {
        return adminUserMapper.selectOneByQuery(QueryWrapper.create()
                .where("phone_hash = ?", phoneHash)
                .limit(1));
    }

    /** 截到列宽以内；{@code null} 原样返回（列可空）。 */
    private static String fitToColumn(String value, int max) {
        if (value == null || value.length() <= max) {
            return value;
        }
        return value.substring(0, max);
    }
}
