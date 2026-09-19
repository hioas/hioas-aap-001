package com.hioas.aap.iam;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T03 · 账号接入验收（接口 AUTH-01…06；AC-01…05）。
 *
 * <p>AC 出处：`.calicat/prd/21-验收标准.md`：
 * AC-01 手机号注册（role=SUPPLIER、phone 密文+masked、返回 JWT、写审计）· AC-02 格式非法 E-1001 ·
 * AC-03 验证码频控 60s · AC-04 连续 5 次错锁 15 分钟 · AC-05 微信登录绑定互认。
 */
class AuthContractTest extends ApiTestBase {

    private static final String PHONE = "13812345678";

    /** 发验证码并取回 dev 环境暴露的验证码（`app.sms.expose-code=true`，生产关闭）。 */
    private String sendSmsAndGetCode(String phone) {
        HttpResult res = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(res.status()).as("发码应成功: %s", res.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(res.body());
        String code = res.data().path("dev_code").asText(null);
        assertThat(code).as("测试环境需能拿到验证码（生产关闭 expose-code）").isNotNull();
        return code;
    }

    private HttpResult login(String phone, String code) {
        return post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
    }

    /**
     * 缺陷 8 回归：User-Agent 超过 {@code aap_auth_token.user_agent varchar(255)} 时不得登录失败。
     *
     * <p>实测根因（2026-09-19）：微信开发者工具（开着自动化会话）发出的 UA 长 **279 字符**，
     * {@code INSERT INTO aap_auth_token} 报
     * {@code value too long for type character varying(255)} → 全局异常处理器按 E-2001 返回
     * → <b>微信端完全无法登录</b>。H5 的 UA 只有 111 字符，所以这个缺陷在 H5 侧永远暴露不出来
     * （在真实微信 runtime 里跑页面才发现的）。
     *
     * <p>期望：登录照常成功，UA 被<b>截断</b>到列宽以内落库（不因超长而丢记录、更不该 500）。
     */
    @Test
    @DisplayName("缺陷8 · 超长 User-Agent 不得导致登录失败（应截断落库）")
    void longUserAgentDoesNotBreakLogin() {
        // 真实抓包值（微信开发者工具 2.02.2608070 + 自动化会话附加的 hash/sid/winId/token 段）
        String longUa = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
                + " (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
                + " wechatdevtools/2.02.2608070 MicroMessenger/8.0.5 Language/zh_CN"
                + " webview/ hash/1882296044 sid/s0 winId/s0 token/1c11591fdea3e2ad1c17d928c1f4ebdd";
        assertThat(longUa.length()).as("这条 UA 必须真的超过 255 字符，用例才有意义").isGreaterThan(255);

        String phone = "13800009999";
        String code = sendSmsAndGetCode(phone);
        HttpResult res = send("POST", "/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code), null, java.util.Map.of("User-Agent", longUa));

        assertThat(res.status()).as("超长 UA 不应导致登录失败: %s", res.body()).isEqualTo(200);
        assertThat(res.code()).isEqualTo("0");
        assertThat(res.data().path("token").asText(null)).as("应正常签发 access token").isNotNull();
        assertThat(res.data().path("refresh_token").asText(null)).as("应正常签发 refresh token").isNotNull();

        Integer uaLen = jdbc.queryForObject(
                "select length(user_agent) from aap_auth_token order by created_at desc limit 1", Integer.class);
        assertThat(uaLen).as("UA 应被截断到 varchar(255) 以内落库").isNotNull().isLessThanOrEqualTo(255);
    }

    /** 边界：UA 恰好 255 字符应原样保留（截断不得误伤正常长度）。 */
    @Test
    @DisplayName("缺陷8 · 恰好 255 字符的 User-Agent 应原样保留")
    void exactLimitUserAgentIsKeptIntact() {
        String ua = "A".repeat(255);
        String phone = "13800009998";
        String code = sendSmsAndGetCode(phone);
        HttpResult res = send("POST", "/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code), null, java.util.Map.of("User-Agent", ua));

        assertThat(res.code()).isEqualTo("0");
        String stored = jdbc.queryForObject(
                "select user_agent from aap_auth_token order by created_at desc limit 1", String.class);
        assertThat(stored).as("255 字符是列宽上限，应原样保留").isEqualTo(ua);
    }

    @Test
    @DisplayName("AC-01 手机号注册：role=SUPPLIER、手机号密文+mask、返回 JWT、写审计、自动建供应商主体")
    void smsSignUpCreatesAccountWithMaskedPhoneAndAudit() throws Exception {
        String code = sendSmsAndGetCode(PHONE);

        HttpResult res = login(PHONE, code);
        assertThat(res.status()).isEqualTo(200);
        SchemaAssert.assertEnvelope(res.body());
        SchemaAssert.assertModel("login-result", json(res.data()));

        assertThat(res.data().path("token").asText()).isNotBlank();
        assertThat(res.data().path("role").asText()).isEqualTo("SUPPLIER");
        assertThat(res.data().path("providerId").asText(null)).isNotBlank();
        assertThat(res.data().path("status").asText()).isEqualTo("PENDING_CREDENTIAL");

        // 落库校验：密文 != 明文、mask 形如 138****5678、phone_hash = SHA-256(phone)
        String cipher = jdbc.queryForObject("select phone_cipher from aap_provider_account", String.class);
        assertThat(cipher).as("手机号必须以密文落库").isNotNull().doesNotContain(PHONE);
        String masked = jdbc.queryForObject("select phone_masked from aap_provider_account", String.class);
        assertThat(masked).isEqualTo("138****5678");
        String hash = jdbc.queryForObject("select phone_hash from aap_provider_account", String.class);
        assertThat(hash).isEqualTo(sha256(PHONE));

        Long auditRows = jdbc.queryForObject(
                "select count(*) from aap_audit_log where action = 'AUTH_LOGIN'", Long.class);
        assertThat(auditRows).as("登录必须写审计（AC-01）").isEqualTo(1L);
    }

    @Test
    @DisplayName("AC-02 参数非法：手机号/验证码格式不合法 → 400 E-1001 且定位到字段")
    void invalidPayloadIsRejected() throws Exception {
        HttpResult badPhone = post("/auth/sms/send", """
                {"phone":"12345","captcha":"AB12"}
                """);
        assertThat(badPhone.status()).isEqualTo(400);
        assertThat(badPhone.code()).isEqualTo("E-1001");
        SchemaAssert.assertError(badPhone.body());

        HttpResult badCode = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"12"}
                """.formatted(PHONE));
        assertThat(badCode.status()).isEqualTo(400);
        assertThat(badCode.code()).isEqualTo("E-1001");
    }

    @Test
    @DisplayName("AC-03 频控：60s 内重复发码 → 429 E-1903")
    void resendWithinSixtySecondsIsThrottled() {
        sendSmsAndGetCode(PHONE);
        HttpResult again = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(PHONE));

        assertThat(again.status()).isEqualTo(429);
        assertThat(again.code()).isEqualTo("E-1903");
        SchemaAssert.assertError(again.body());
    }

    @Test
    @DisplayName("AC-04 连续 5 次错码 → 锁定 15 分钟（此时正确的码也不接受）")
    void fiveWrongCodesLockThePhone() throws Exception {
        String code = sendSmsAndGetCode(PHONE);
        String wrong = code.equals("000000") ? "111111" : "000000";

        for (int i = 1; i <= 5; i++) {
            HttpResult res = login(PHONE, wrong);
            assertThat(res.status()).as("第 %d 次错码应 400", i).isEqualTo(400);
            assertThat(res.code()).isEqualTo("E-1001");
        }

        HttpResult locked = login(PHONE, code);
        assertThat(locked.status()).as("锁定后即使码正确也应拒绝").isEqualTo(429);
        assertThat(locked.code()).isEqualTo("E-1903");

        var lockedUntil = jdbc.queryForObject(
                "select max(locked_until) from aap_sms_code where phone_hash = ?", java.sql.Timestamp.class, sha256(PHONE));
        assertThat(lockedUntil).as("必须写入锁定截止时间").isNotNull();
    }

    @Test
    @DisplayName("AUTH-05/06 登录态：无 token → 401 E-1902；带 token → /auth/me 返回设置页所需字段")
    void meRequiresTokenAndReturnsSettingsFields() throws Exception {
        HttpResult noToken = get("/auth/me");
        assertThat(noToken.status()).isEqualTo(401);
        assertThat(noToken.code()).isEqualTo("E-1902");
        SchemaAssert.assertError(noToken.body());
        assertThat(noToken.header("X-Trace-Id")).isNotBlank();

        String token = login(PHONE, sendSmsAndGetCode(PHONE)).data().path("token").asText();
        HttpResult me = get("/auth/me", token);

        assertThat(me.status()).isEqualTo(200);
        SchemaAssert.assertModel("me-result", json(me.data()));
        assertThat(me.data().path("phone_masked").asText()).isEqualTo("138****5678");
        assertThat(me.data().path("role").asText()).isEqualTo("SUPPLIER");
        assertThat(me.data().path("wechat_bound").isBoolean()).isTrue();
        assertThat(me.data().path("sms_2fa").isBoolean()).isTrue();
        assertThat(me.data().path("wechat_subscribed").isBoolean()).isTrue();
        assertThat(me.data().path("providerCode").asText(null)).isNotBlank();
    }

    @Test
    @DisplayName("AUTH-04 refresh：换发新 access token，且旧 refresh token 轮换后失效（E-1902）")
    void refreshRotatesTokens() {
        String code = sendSmsAndGetCode(PHONE);
        HttpResult login1 = login(PHONE, code);
        assertThat(login1.status()).isEqualTo(200);
        String refresh1 = login1.data().path("refresh_token").asText();
        assertThat(refresh1).as("登录响应必须带 refresh_token").isNotBlank();

        HttpResult refreshed = post("/auth/refresh", """
                {"refreshToken":"%s"}
                """.formatted(refresh1));
        assertThat(refreshed.status()).as(refreshed.body()).isEqualTo(200);
        SchemaAssert.assertModel("login-result", json(refreshed.data()));
        assertThat(refreshed.data().path("token").asText()).isNotBlank();
        String refresh2 = refreshed.data().path("refresh_token").asText();
        assertThat(refresh2).as("轮换后必须换发新的 refresh token").isNotBlank().isNotEqualTo(refresh1);

        // 新 token 可用；旧 refresh token 已被轮换 → 失效
        assertThat(get("/auth/me", refreshed.data().path("token").asText()).status()).isEqualTo(200);
        HttpResult reuse = post("/auth/refresh", """
                {"refreshToken":"%s"}
                """.formatted(refresh1));
        assertThat(reuse.status()).isEqualTo(401);
        assertThat(reuse.code()).isEqualTo("E-1902");
    }

    @Test
    @DisplayName("AUTH-05 logout：登出后原 access token 立即失效（E-1902）")
    void logoutRevokesToken() throws Exception {
        String token = login(PHONE, sendSmsAndGetCode(PHONE)).data().path("token").asText();
        assertThat(get("/auth/me", token).status()).isEqualTo(200);

        HttpResult logout = post("/auth/logout", null, token);
        assertThat(logout.status()).isEqualTo(200);

        HttpResult after = get("/auth/me", token);
        assertThat(after.status()).isEqualTo(401);
        assertThat(after.code()).isEqualTo("E-1902");

        Long revoked = jdbc.queryForObject(
                "select count(*) from aap_auth_token where revoked_at is not null", Long.class);
        assertThat(revoked).isPositive();
    }

    @Test
    @DisplayName("AC-05 微信登录：同一 code 重复登录命中同一账号（绑定互认）；与手机号账号互不覆盖")
    void wechatLoginBindsToSameAccount() throws Exception {
        HttpResult first = post("/auth/wechat/login", """
                {"code":"wx-code-0001"}
                """);
        assertThat(first.status()).isEqualTo(200);
        SchemaAssert.assertModel("login-result", json(first.data()));
        String providerId = first.data().path("providerId").asText();
        assertThat(providerId).isNotBlank();

        HttpResult second = post("/auth/wechat/login", """
                {"code":"wx-code-0001"}
                """);
        assertThat(second.data().path("providerId").asText()).isEqualTo(providerId);
        assertThat(jdbc.queryForObject("select count(*) from aap_provider_account", Long.class)).isEqualTo(1L);

        // 再走手机号注册 → 新账号（互认只发生在同一 openid 上）
        login(PHONE, sendSmsAndGetCode(PHONE));
        assertThat(jdbc.queryForObject("select count(*) from aap_provider_account", Long.class)).isEqualTo(2L);
    }

    @Test
    @DisplayName("JWT 防篡改：伪造 token 与过期 token 一律 401 E-1902")
    void forgedAndExpiredTokensRejected() throws Exception {
        String token = login(PHONE, sendSmsAndGetCode(PHONE)).data().path("token").asText();

        HttpResult tampered = get("/auth/me", token.substring(0, token.length() - 2) + "xy");
        assertThat(tampered.status()).isEqualTo(401);
        assertThat(tampered.code()).isEqualTo("E-1902");

        String expired = jwt("expired", -60);
        HttpResult expiredRes = get("/auth/me", expired);
        assertThat(expiredRes.status()).isEqualTo(401);
        assertThat(expiredRes.code()).isEqualTo("E-1902");
    }

    /** 测试侧直接签发指定 TTL 的 token（用于过期场景）。 */
    private String jwt(String subject, int ttlSeconds) throws Exception {
        String secret = environment.getProperty("app.jwt.secret");
        var key = new javax.crypto.spec.SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        long now = System.currentTimeMillis() / 1000;
        return io.jsonwebtoken.Jwts.builder()
                .subject(subject)
                .claim("role", "SUPPLIER")
                .claim("subjectType", "PROVIDER")
                .issuedAt(new java.util.Date(now * 1000))
                .expiration(new java.util.Date((now + ttlSeconds) * 1000))
                .signWith(key, io.jsonwebtoken.Jwts.SIG.HS256)
                .compact();
    }

    private static String sha256(String value) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
    }
}
