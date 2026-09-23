package com.hioas.aap.iam;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

/**
 * 管理端登录（**新增**：此前管理端没有登录入口）。
 *
 * <p>背景（2026-09-23 运行态实测）：{@code aap-admin} 登录页调的是 {@code /auth/sms/login}，
 * 而该端点固定签发 {@code subjectType=PROVIDER} → 管理端拿到供应商身份 → 调
 * {@code /api/v1/admin/**} 一律 403 {@code E-1901} → **人工放行 DET-06 等管理端能力在真实环境里
 * 无法调用**（而报价前置的 PASS 只能来自人工放行 → 供应商全流程断在「检测 → 报价」）。
 *
 * <p>本类锁定新端点的契约：
 * <ul>
 *   <li>{@code POST /api/v1/admin/auth/sms/login}：仅 {@code aap_admin_user} 里 ACTIVE 的手机号可登录，
 *       签发 {@code subjectType=ADMIN} + 账号 role 的令牌；</li>
 *   <li>登录后管理端接口**真的可用**（用返回的令牌调 {@code /admin/**} 得 200）；</li>
 *   <li>{@code GET /auth/me} 对管理端主体返回管理端档案（否则控制台登录完就「登录过期」）；</li>
 *   <li>非管理端手机号一律拒绝且**不注册任何账号**；验证码错误不发令牌；停用账号拒绝。</li>
 * </ul>
 *
 * <p>⚠️ 每个用例用**独立手机号**：短信验证码是一次性的（同码二次使用必失败），
 * 且同一手机号 60 秒内不可重发 —— 这是本项目已知的测试陷阱。
 */
class AdminAuthContractTest extends ApiTestBase {

    private static final long ADMIN_ID = 984001L;

    @Autowired
    private CryptoService crypto;

    /** 造一个管理端账号（手机号三件套与角色按真源列填）。 */
    private void seedAdmin(long id, String phone, String role, String status) {
        jdbc.update("delete from aap_admin_user where id = ?", id);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status,
                                            phone_hash, phone_masked)
                values (?, ?, 'x', '运营小李', ?, ?, ?, ?)
                """, id, "ops-e2e-" + id, role, status, crypto.sha256Hex(phone), crypto.maskPhone(phone));
    }

    private String codeFor(String phone) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        return send.data().path("dev_code").asText();
    }

    private HttpResult adminLogin(String phone, String smsCode) {
        return post("/admin/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, smsCode));
    }

    /** 解出 JWT 载荷（断言用，不校验签名）。 */
    private static JsonNode claims(String token) {
        String payload = token.split("\\.")[1];
        return MAPPER.readTree(new String(Base64.getUrlDecoder().decode(payload), StandardCharsets.UTF_8));
    }

    @Test
    @DisplayName("管理端登录：ACTIVE 账号可登录，令牌为 ADMIN 身份 + 账号角色，且管理端接口真的可用")
    void adminSmsLoginIssuesAdminToken() {
        String phone = "13800000070";
        seedAdmin(ADMIN_ID, phone, "TECH_OPS", "ACTIVE");
        String code = codeFor(phone);

        HttpResult login = adminLogin(phone, code);

        assertThat(login.status()).as(login.body()).isEqualTo(200);
        SchemaAssert.assertModel("login-result", json(login.data()));
        String token = login.data().path("token").asText();
        assertThat(token).isNotBlank();
        assertThat(claims(token).path("subjectType").asText()).as("必须是管理端身份").isEqualTo("ADMIN");
        assertThat(claims(token).path("role").asText()).isEqualTo("TECH_OPS");
        assertThat(login.data().path("role").asText()).isEqualTo("TECH_OPS");

        // 关键：不止「登录成功」，而是管理端能力真的调得动（修复前这里必是 403 E-1901）
        HttpResult adminApi = get("/admin/detection-configs?page=1&pageSize=5", token);
        assertThat(adminApi.status()).as("管理端接口必须可用：" + adminApi.body()).isEqualTo(200);

        // 控制台登录后必调 /auth/me：必须返回管理端档案，而不是 E-1902
        HttpResult me = get("/auth/me", token);
        assertThat(me.status()).as(me.body()).isEqualTo(200);
        assertThat(me.data().path("role").asText()).isEqualTo("TECH_OPS");
        assertThat(me.data().path("nickname").asText()).isEqualTo("运营小李");
        assertThat(me.data().path("phone_masked").asText()).isEqualTo("138****0070");

        // 审计留痕（管理端登录可追责）
        assertThat(jdbc.queryForObject("select count(*) from aap_audit_log "
                + "where action = 'AUTH_LOGIN' and target_type = 'admin_user' and target_id = ?",
                Integer.class, ADMIN_ID)).isEqualTo(1);
        // 令牌落 jti（登出/撤销依据），且 subject 类型是 ADMIN
        assertThat(jdbc.queryForObject("select subject_type from aap_auth_token where account_id = ?",
                String.class, ADMIN_ID)).isEqualTo("ADMIN");
    }

    @Test
    @DisplayName("管理端登录：非管理端手机号一律拒绝，且不注册任何账号（供应商侧才自动注册）")
    void nonAdminPhoneIsRejectedWithoutRegistration() {
        String phone = "13800000071";
        String code = codeFor(phone);

        HttpResult login = adminLogin(phone, code);

        assertThat(login.status()).as(login.body()).isEqualTo(401);
        assertThat(login.code()).isEqualTo("E-1902");
        assertThat(jdbc.queryForObject("select count(*) from aap_admin_user", Integer.class)).isZero();
        assertThat(jdbc.queryForObject("select count(*) from aap_provider_account", Integer.class))
                .as("管理端登录绝不自动注册供应商账号").isZero();
    }

    @Test
    @DisplayName("管理端登录：验证码错误 → 拒发令牌（E-1001），不留任何令牌记录")
    void wrongSmsCodeIsRejected() {
        String phone = "13800000072";
        seedAdmin(ADMIN_ID, phone, "BIZ_OPERATOR", "ACTIVE");
        String code = codeFor(phone);
        String wrong = "000000".equals(code) ? "111111" : "000000";

        HttpResult res = adminLogin(phone, wrong);

        assertThat(res.status()).as(res.body()).isEqualTo(400);
        assertThat(res.code()).isEqualTo("E-1001");
        assertThat(jdbc.queryForObject("select count(*) from aap_auth_token where account_id = ?",
                Integer.class, ADMIN_ID)).as("错误验证码不得签发令牌").isZero();
    }

    @Test
    @DisplayName("管理端登录：停用账号 → 403 E-1901（手机号正确、验证码正确也不放行）")
    void suspendedAdminIsRejected() {
        String phone = "13800000073";
        seedAdmin(ADMIN_ID, phone, "TECH_OPS", "SUSPENDED");
        String code = codeFor(phone);

        HttpResult res = adminLogin(phone, code);

        assertThat(res.status()).as(res.body()).isEqualTo(403);
        assertThat(res.code()).isEqualTo("E-1901");
        assertThat(jdbc.queryForObject("select count(*) from aap_auth_token where account_id = ?",
                Integer.class, ADMIN_ID)).isZero();
    }
}
