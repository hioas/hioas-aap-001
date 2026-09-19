package com.hioas.aap.iam;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.AuditContext;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.config.AppProperties;
import com.hioas.aap.iam.dto.LoginResult;
import com.hioas.aap.iam.dto.MeResult;
import com.hioas.aap.iam.dto.SmsSendResult;
import com.hioas.aap.provider.ProviderEntity;
import com.hioas.aap.provider.ProviderMapper;
import com.hioas.aap.support.AuditService;
import com.mybatisflex.core.query.QueryWrapper;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 账号接入（接口 AUTH-01…06）。
 *
 * <p>注册语义（AC-01）：手机号首次登录即注册 {@code role=SUPPLIER}，并自动建供应商主体
 * （{@code provider_code=AAP-P-{6位}}、状态 {@code PENDING_CREDENTIAL}）——供应商端后续所有
 * 页面都挂在 providerId 上，不建主体会让前端一路占位。
 *
 * <p>微信登录（AC-05）：同一 openid 命中同一账号并绑定；与手机号账号互不覆盖。
 */
@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /**
     * {@code aap_auth_token} 的列宽（见 {@code V1__baseline.sql}）。
     *
     * <p>请求头长度<b>不可控</b>，必须按列宽截断后再落库：实测微信开发者工具
     * （开着自动化会话）发出的 UA 长 279 字符，超过 {@code user_agent varchar(255)}
     * → {@code INSERT} 报 {@code value too long for type character varying(255)}
     * → 全局异常处理器按 E-2001 返回 → <b>微信端完全无法登录</b>。
     * H5 的 UA 只有 111 字符，所以这个缺陷在 H5 侧永远暴露不出来。
     */
    private static final int USER_AGENT_MAX = 255;

    /** {@code aap_auth_token.client_ip varchar(64)}；{@code X-Forwarded-For} 首段同样不可控。 */
    private static final int CLIENT_IP_MAX = 64;

    /** 截到列宽以内；{@code null} 原样返回（列可空）。 */
    private static String fitToColumn(String value, int max) {
        if (value == null || value.length() <= max) {
            return value;
        }
        return value.substring(0, max);
    }

    private final ProviderAccountMapper accountMapper;
    private final ProviderMapper providerMapper;
    private final AuthTokenMapper authTokenMapper;
    private final SmsService smsService;
    private final JwtService jwtService;
    private final CryptoService crypto;
    private final WechatClient wechatClient;
    private final DocNoGenerator docNoGenerator;
    private final AuditService auditService;
    private final AppProperties properties;

    public AuthService(ProviderAccountMapper accountMapper, ProviderMapper providerMapper,
                       AuthTokenMapper authTokenMapper, SmsService smsService, JwtService jwtService,
                       CryptoService crypto, WechatClient wechatClient, DocNoGenerator docNoGenerator,
                       AuditService auditService, AppProperties properties) {
        this.accountMapper = accountMapper;
        this.providerMapper = providerMapper;
        this.authTokenMapper = authTokenMapper;
        this.smsService = smsService;
        this.jwtService = jwtService;
        this.crypto = crypto;
        this.wechatClient = wechatClient;
        this.docNoGenerator = docNoGenerator;
        this.auditService = auditService;
        this.properties = properties;
    }

    public SmsSendResult sendSms(String phone, String clientIp) {
        SmsService.SentCode sent = smsService.send(phone, clientIp);
        return new SmsSendResult(sent.ttl(),
                RFC3339.format(sent.expireAt().withOffsetSameInstant(ZoneOffset.UTC)),
                sent.devCode());
    }

    @Transactional
    public LoginResult smsLogin(String phone, String smsCode, String userAgent, String clientIp) {
        smsService.verify(phone, smsCode);

        String phoneHash = crypto.sha256Hex(phone);
        ProviderAccountEntity account = findByPhoneHash(phoneHash).orElseGet(() -> createAccount(phone, phoneHash));
        account.setLastLoginAt(OffsetDateTime.now(ZoneOffset.UTC));
        accountMapper.update(account);

        ProviderEntity provider = ensureProvider(account);
        return issueTokens(account, provider, smsCode == null ? null : crypto.maskPhone(phone), userAgent, clientIp);
    }

    @Transactional
    public LoginResult wechatLogin(String code, String userAgent, String clientIp) {
        String openid = wechatClient.exchangeOpenid(code);
        Optional<ProviderAccountEntity> existing = Optional.ofNullable(accountMapper.selectOneByQuery(QueryWrapper.create()
                .where("wx_openid = ?", openid)
                .limit(1)));
        ProviderAccountEntity account = existing.orElseGet(() -> {
            ProviderAccountEntity created = new ProviderAccountEntity();
            created.setWxOpenid(openid);
            created.setRole("SUPPLIER");
            created.setStatus("ACTIVE");
            created.setSms2fa(false);
            created.setWechatSubscribed(false);
            accountMapper.insert(created);
            return created;
        });
        account.setLastLoginAt(OffsetDateTime.now(ZoneOffset.UTC));
        accountMapper.update(account);

        ProviderEntity provider = ensureProvider(account);
        return issueTokens(account, provider, "wechat", userAgent, clientIp);
    }

    /** 用 refresh token 换发新的 access/refresh（轮换：旧 refresh 立即失效）。 */
    @Transactional
    public LoginResult refresh(String refreshToken, String userAgent, String clientIp) {
        if (refreshToken == null || refreshToken.isBlank()) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        AuthTokenEntity record = authTokenMapper.selectOneByQuery(QueryWrapper.create()
                .where("refresh_token_hash = ?", crypto.sha256Hex(refreshToken))
                .and("revoked_at is null")
                .limit(1));
        if (record == null || record.getExpireAt() == null
                || record.getExpireAt().isBefore(OffsetDateTime.now(ZoneOffset.UTC))) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        record.setRevokedAt(OffsetDateTime.now(ZoneOffset.UTC));
        authTokenMapper.update(record);

        ProviderAccountEntity account = accountMapper.selectOneById(record.getAccountId());
        if (account == null) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        ProviderEntity provider = findProvider(account.getId()).orElse(null);
        return issueTokens(account, provider, null, userAgent, clientIp);
    }

    /** 登出：撤销该 jti（access token 立即失效）。 */
    @Transactional
    public void logout(String jti) {
        AuthTokenEntity record = authTokenMapper.selectOneByQuery(QueryWrapper.create()
                .where("jti = ?", jti)
                .limit(1));
        if (record != null && record.getRevokedAt() == null) {
            record.setRevokedAt(OffsetDateTime.now(ZoneOffset.UTC));
            authTokenMapper.update(record);
        }
    }

    public MeResult me(AuthPrincipal principal) {
        ProviderAccountEntity account = accountMapper.selectOneById(principal.accountId());
        if (account == null) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        ProviderEntity provider = findProvider(account.getId()).orElse(null);
        return new MeResult(
                account.getPhoneMasked(),
                account.getRole() == null ? "SUPPLIER" : account.getRole(),
                provider == null ? null : String.valueOf(provider.getId()),
                provider == null ? null : provider.getProviderCode(),
                provider == null ? null : provider.getStatus(),
                account.getNickname(),
                account.getWxOpenid() != null,
                Boolean.TRUE.equals(account.getSms2fa()),
                Boolean.TRUE.equals(account.getWechatSubscribed()));
    }

    // ------------------------------------------------------------------ 内部

    private Optional<ProviderAccountEntity> findByPhoneHash(String phoneHash) {
        return Optional.ofNullable(accountMapper.selectOneByQuery(QueryWrapper.create()
                .where("phone_hash = ?", phoneHash)
                .limit(1)));
    }

    private ProviderAccountEntity createAccount(String phone, String phoneHash) {
        ProviderAccountEntity account = new ProviderAccountEntity();
        account.setPhoneCipher(crypto.encrypt(phone));
        account.setPhoneHash(phoneHash);
        account.setPhoneMasked(crypto.maskPhone(phone));
        account.setRole("SUPPLIER");
        account.setStatus("ACTIVE");
        account.setSms2fa(false);
        account.setWechatSubscribed(false);
        accountMapper.insert(account);
        return account;
    }

    private ProviderEntity ensureProvider(ProviderAccountEntity account) {
        return findProvider(account.getId()).orElseGet(() -> {
            ProviderEntity provider = new ProviderEntity();
            provider.setAccountId(account.getId());
            provider.setProviderCode(docNoGenerator.providerCode());
            provider.setProviderNo(docNoGenerator.providerNo());
            provider.setShortCode(provider.getProviderCode());
            provider.setStatus("PENDING_CREDENTIAL");
            provider.setRecheckIntervalDays(30);
            provider.setManualOverride(false);
            provider.setCompleteness((short) 0);
            providerMapper.insert(provider);
            log.info("注册供应商主体 provider_code={} account_id={}", provider.getProviderCode(), account.getId());
            return provider;
        });
    }

    private Optional<ProviderEntity> findProvider(Long accountId) {
        return Optional.ofNullable(providerMapper.selectOneByQuery(QueryWrapper.create()
                .where("account_id = ?", accountId)
                .limit(1)));
    }

    private LoginResult issueTokens(ProviderAccountEntity account, ProviderEntity provider, String loginName,
                                    String userAgent, String clientIp) {
        String role = account.getRole() == null ? "SUPPLIER" : account.getRole();
        Long providerId = provider == null ? null : provider.getId();
        JwtService.IssuedAccessToken access = jwtService.issueAccessToken(
                account.getId(), role, "PROVIDER", providerId);

        String refreshToken = crypto.randomToken();
        AuthTokenEntity token = new AuthTokenEntity();
        token.setAccountId(account.getId());
        token.setSubjectType("PROVIDER");
        token.setJti(access.jti());
        token.setRefreshTokenHash(crypto.sha256Hex(refreshToken));
        token.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC)
                .plusDays(properties.jwt().refreshTtlDays()));
        // 必须截断到列宽：请求头长度不可控，超长会 INSERT 溢出 → 登录直接 500。
        token.setUserAgent(fitToColumn(userAgent, USER_AGENT_MAX));
        token.setClientIp(fitToColumn(clientIp, CLIENT_IP_MAX));
        authTokenMapper.insert(token);

        AuditContext.set(new AuditContext.Actor(account.getId(), "PROVIDER", loginName, clientIp));
        auditService.record(AuditService.AuditAction.AUTH_LOGIN, "provider_account", account.getId(),
                "账号登录成功（role=" + role + "）");

        return new LoginResult(access.token(), refreshToken, role,
                providerId == null ? null : String.valueOf(providerId),
                provider == null ? null : provider.getProviderCode(),
                provider == null ? null : provider.getStatus(),
                jwtService.accessTtl().toSeconds());
    }
}
