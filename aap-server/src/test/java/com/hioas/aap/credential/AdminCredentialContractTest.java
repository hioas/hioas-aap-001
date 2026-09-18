package com.hioas.aap.credential;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T14 · 管理端凭证（ADM-C01/02）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.4（`ADM-C01` 凭证详情 / `ADM-C02` 明文读取）
 * + `json-schema/models/{credential-detail,reveal-result}.schema.json`
 * + `json-schema/requests/credential-reveal.schema.json`（`smsCode` 6 位数字必填）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>两条都限 `SUPER_ADMIN`（清单）；运营商务/技术运营/供应商 403 `E-1901`，未认证 401 `E-1902`</li>
 *   <li>`ADM-C02` 复用 CRED-07 的二次验证 + `SENSITIVE` 审计（AC-30，同一实现，不复制一套）</li>
 *   <li>明文只在 reveal 响应出现一次；详情接口只回 `api_key_mask`（R-48 / 安全红线）</li>
 *   <li>未命中资源先 404 `E-1406`、**不写审计**（避免伪造「读过明文」的假痕迹）</li>
 * </ul>
 */
class AdminCredentialContractTest extends ApiTestBase {

    private static final String RAW_KEY = "sk-admin-fixture-not-a-secret-0001";
    private static final String SUPPLIER_PHONE = "13800000220";
    private static final String ADMIN_PHONE_A = "13900000021";
    private static final String ADMIN_PHONE_B = "13900000022";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    @Autowired
    private CryptoService cryptoService;

    private String adminToken(long accountId, String role, String phone) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        if (phone == null) {
            jdbc.update("""
                    insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                    values (?, ?, 'x', ?, ?, 'ACTIVE')
                    """, accountId, role.toLowerCase() + "-" + accountId, role, role);
        } else {
            jdbc.update("""
                    insert into aap_admin_user (id, username, password_hash, display_name, role, status,
                                                phone_hash, phone_masked)
                    values (?, ?, 'x', ?, ?, 'ACTIVE', ?, '139****0021')
                    """, accountId, role.toLowerCase() + "-" + accountId, role, role,
                    cryptoService.sha256Hex(phone));
        }
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String supplierToken() {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(SUPPLIER_PHONE));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(SUPPLIER_PHONE, send.data().path("dev_code").asText()));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    /** 夹具：直插一条属于 `providerId` 的凭证（密文走生产同款 CryptoService）。 */
    private void insertCredential(long id, long providerId) {
        jdbc.update("""
                insert into aap_credential (id, provider_id, alias, primary_flag, base_url, api_key_cipher,
                    api_key_mask, api_key_fingerprint, declared_vendor, status, detection_status,
                    created_at, updated_at, deleted, version)
                values (?, ?, '主凭证', true, 'https://api.example.com/v1', ?, ?, ?, 'OpenAI',
                        'PRECHECK_PASSED', 'PASS', now(), now(), false, 0)
                """, id, providerId, cryptoService.encrypt(RAW_KEY), cryptoService.maskApiKey(RAW_KEY),
                cryptoService.sha256Hex(RAW_KEY));
    }

    // ------------------------------------------------------------------ ADM-C01

    @Test
    @DisplayName("ADM-C01 凭证详情：超管可读任意供应商凭证、只回掩码（无明文）、非超管 403、未认证 401")
    void adminCredentialDetail() {
        String superAdmin = adminToken(970301L, "SUPER_ADMIN", null);
        String biz = adminToken(970302L, "BIZ_OPERATOR", null);
        String supplier = supplierToken();
        insertCredential(860001L, 850001L);

        HttpResult res = get("/admin/credentials/860001", superAdmin);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(res.body());
        SchemaAssert.assertModel("credential-detail", json(res.data()));
        assertThat(res.data().path("id").asText()).as("雪花 ID 对外 string").isEqualTo("860001");
        assertThat(res.data().path("provider_id").asText()).isEqualTo("850001");
        assertThat(res.data().path("base_url").asText()).isEqualTo("https://api.example.com/v1");
        assertThat(res.data().path("api_key_mask").asText()).isEqualTo("sk-a***0001");
        assertThat(res.data().path("api_key_masked").asText()).as("客户端容错双读键").isEqualTo("sk-a***0001");
        assertThat(res.body()).as("详情响应体绝不能出现明文 api_key（R-48）").doesNotContain(RAW_KEY);

        HttpResult bizDenied = get("/admin/credentials/860001", biz);
        assertThat(bizDenied.status()).as(bizDenied.body()).isEqualTo(403);
        assertThat(bizDenied.code()).isEqualTo("E-1901");
        HttpResult supplierDenied = get("/admin/credentials/860001", supplier);
        assertThat(supplierDenied.status()).as(supplierDenied.body()).isEqualTo(403);
        assertThat(supplierDenied.code()).isEqualTo("E-1901");
        HttpResult anonymous = get("/admin/credentials/860001");
        assertThat(anonymous.status()).as(anonymous.body()).isEqualTo(401);
        assertThat(anonymous.code()).isEqualTo("E-1902");

        HttpResult missing = get("/admin/credentials/999999", superAdmin);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        HttpResult badId = get("/admin/credentials/abc", superAdmin);
        assertThat(badId.status()).as(badId.body()).isEqualTo(400);
        assertThat(badId.code()).isEqualTo("E-1001");
    }

    // ------------------------------------------------------------------ ADM-C02

    @Test
    @DisplayName("ADM-C02 明文读取：超管 + 短信二次验证回 api_key 并写 SENSITIVE 审计；非超管 403、未认证 401、验证码非法/错误 400")
    void adminReveal() {
        String superAdminB = adminToken(970311L, "SUPER_ADMIN", ADMIN_PHONE_B);
        String superAdminA = adminToken(970312L, "SUPER_ADMIN", ADMIN_PHONE_A);
        String biz = adminToken(970313L, "BIZ_OPERATOR", null);
        String supplier = supplierToken();
        insertCredential(860001L, 850001L);

        // 非超管 / 未认证：安全层先拦，不发短信也不落审计
        HttpResult supplierDenied = post("/admin/credentials/860001/reveal", """
                {"smsCode":"123456"}
                """, supplier);
        assertThat(supplierDenied.status()).as(supplierDenied.body()).isEqualTo(403);
        assertThat(supplierDenied.code()).isEqualTo("E-1901");
        HttpResult bizDenied = post("/admin/credentials/860001/reveal", """
                {"smsCode":"123456"}
                """, biz);
        assertThat(bizDenied.status()).as(bizDenied.body()).isEqualTo(403);
        assertThat(bizDenied.code()).isEqualTo("E-1901");
        HttpResult anonymous = post("/admin/credentials/860001/reveal", """
                {"smsCode":"123456"}
                """, null);
        assertThat(anonymous.status()).as(anonymous.body()).isEqualTo(401);
        assertThat(anonymous.code()).isEqualTo("E-1902");

        // 请求体校验（credential-reveal：smsCode 6 位数字）
        HttpResult badFormat = post("/admin/credentials/860001/reveal", """
                {"smsCode":"12ab"}
                """, superAdminA);
        assertThat(badFormat.status()).as(badFormat.body()).isEqualTo(400);
        assertThat(badFormat.code()).isEqualTo("E-1001");
        assertThat(badFormat.json().path("details").toString()).contains("smsCode");

        // 不存在凭证：即便验证码有效也 404 E-1406，且不得留下「读过明文」的审计
        HttpResult sendB = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(ADMIN_PHONE_B));
        assertThat(sendB.status()).as(sendB.body()).isEqualTo(200);
        HttpResult missing = post("/admin/credentials/999999/reveal", """
                {"smsCode":"%s"}
                """.formatted(sendB.data().path("dev_code").asText()), superAdminB);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        assertThat(jdbc.queryForObject("select count(*) from aap_audit_log where action = 'CREDENTIAL_REVEAL'",
                Long.class)).as("未命中资源不得写审计").isZero();

        // 超管 + 二次验证：回明文一次 + SENSITIVE 审计（AC-30）
        HttpResult sendA = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(ADMIN_PHONE_A));
        assertThat(sendA.status()).as(sendA.body()).isEqualTo(200);
        HttpResult revealed = post("/admin/credentials/860001/reveal", """
                {"smsCode":"%s"}
                """.formatted(sendA.data().path("dev_code").asText()), superAdminA);
        assertThat(revealed.status()).as(revealed.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(revealed.body());
        SchemaAssert.assertModel("reveal-result", json(revealed.data()));
        assertThat(revealed.data().path("api_key").asText()).as("明文仅此一次").isEqualTo(RAW_KEY);
        assertThat(revealed.data().path("expire_at").asText(null)).isNotBlank();

        assertThat(jdbc.queryForObject("select count(*) from aap_audit_log where action = 'CREDENTIAL_REVEAL'",
                Long.class)).isEqualTo(1L);
        assertThat(jdbc.queryForObject("select risk_level from aap_audit_log order by id desc limit 1", String.class))
                .isEqualTo("SENSITIVE");
        assertThat(jdbc.queryForObject("select target_id from aap_audit_log order by id desc limit 1", Long.class))
                .isEqualTo(860001L);
        assertThat(jdbc.queryForObject("select summary from aap_audit_log order by id desc limit 1", String.class))
                .as("审计摘要不得含明文").doesNotContain(RAW_KEY);
        assertThat(jdbc.queryForObject("select count(*) from aap_audit_log where summary like ?", Long.class,
                "%" + RAW_KEY + "%")).as("全表审计摘要都不得含明文").isZero();

        // 验证码错误（格式合法）：400 E-1001（复用 CRED-07 的校验实现，不重造一套）
        String superAdminD = adminToken(970314L, "SUPER_ADMIN", "13900000024");
        insertCredential(860002L, 850002L);
        HttpResult sendD = post("/auth/sms/send", """
                {"phone":"13900000024","captcha":"AB12"}
                """);
        assertThat(sendD.status()).as(sendD.body()).isEqualTo(200);
        String wrong = "000000".equals(sendD.data().path("dev_code").asText()) ? "000001" : "000000";
        HttpResult wrongCode = post("/admin/credentials/860002/reveal", """
                {"smsCode":"%s"}
                """.formatted(wrong), superAdminD);
        assertThat(wrongCode.status()).as(wrongCode.body()).isEqualTo(400);
        assertThat(wrongCode.code()).isEqualTo("E-1001");
        assertThat(wrongCode.json().path("details").toString()).contains("smsCode");
        assertThat(jdbc.queryForObject("select count(*) from aap_audit_log where action = 'CREDENTIAL_REVEAL'",
                Long.class)).as("验证码错不得留审计").isEqualTo(1L);
    }
}
