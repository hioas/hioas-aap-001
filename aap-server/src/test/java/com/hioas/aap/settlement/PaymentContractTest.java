package com.hioas.aap.settlement;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T11 · 打款与结算（PAY-01 供应商端 + ADM-PAY01…03 管理端）。
 *
 * <p>契约真源：`docs/backend/endpoints.json` + `docs/backend/json-schema/{models/payment,models/settlement-statement}.schema.json`
 * + `02-API接口模型清单.md` §1.3/§2.5 + `01-ER数据模型.md` §4.7（aap_payment_record / aap_settlement_statement）。
 *
 * <p>硬口径（每条对应断言）：
 * <ul>
 *   <li>**AC-40 未签署禁打款**：确认打款（ADM-PAY02）时合同必须已 SIGNED，否则 409 E-1701，且打款状态不变</li>
 *   <li>**打款仅记录（R-42）**：无资金流转接口；确认只做 PAYMENT_RECORDED→CONFIRMED 状态推进 + 确认人/时间留痕</li>
 *   <li>**幂等与终态**：重复确认 → 409 E-1601</li>
 *   <li>**数据归属**：供应商端 PAY-01 只回本家打款记录</li>
 *   <li>**钱包三项口径**（清单标注「约定，无 PRD 依据」）：三态互斥——pending=UNSETTLED、available=PAYMENT_RECORDED、
 *       settled=CONFIRMED，合计等于全部打款金额，不重复计数</li>
 * </ul>
 */
class PaymentContractTest extends ApiTestBase {

    private static final String PHONE = "13800000092";
    private static final String OTHER_PHONE = "13800000093";

    private static final long BIZ_OPS_ID = 961001L;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    private long seq = 980000L;

    private long nextId() {
        return ++seq;
    }

    // ------------------------------------------------------------------ 前置

    private String token(String phone) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    private long providerId(String token) {
        HttpResult me = get("/auth/me", token);
        assertThat(me.status()).as(me.body()).isEqualTo(200);
        return Long.parseLong(me.data().path("provider_id").asText());
    }

    private String bizOpsToken() {
        jdbc.update("delete from aap_admin_user where id = ?", BIZ_OPS_ID);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, 'bizops-settlement', 'x', 'bizops-settlement', 'BIZ_OPERATOR', 'ACTIVE')
                """, BIZ_OPS_ID);
        var issued = jwtService.issueAccessToken(BIZ_OPS_ID, "BIZ_OPERATOR", "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(BIZ_OPS_ID);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private long contract(long providerId, String status) {
        long id = nextId();
        jdbc.update("""
                insert into aap_contract (id, contract_no, provider_id, title, status, sign_channel, currency,
                    created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, 'OFFLINE', 'USD', now(), now(), false, 0)
                """, id, "HTTEST" + id, providerId, "结算用合同 " + id, status);
        return id;
    }

    /** 打款记录夹具（status 决定钱包口径落点）。 */
    private long payment(long providerId, Long contractId, String status, BigDecimal amount) {
        long id = nextId();
        Long voucher = "UNSETTLED".equals(status) ? null : nextId();
        if (voucher != null) {
            jdbc.update("""
                    insert into aap_file_asset (id, file_key, original_name, content_type, size_bytes, biz_type,
                        encrypted, status, created_at, updated_at)
                    values (?, ?, '打款凭证.png', 'image/png', 1024, 'PAYMENT_VOUCHER', false, 'ACTIVE', now(), now())
                    """, voucher, "vouchers/" + voucher + ".png");
        }
        jdbc.update("""
                insert into aap_payment_record (id, provider_id, contract_id, amount, currency, status,
                    voucher_file_id, paid_at, created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, 'USD', ?, ?, now(), now(), now(), false, 0)
                """, id, providerId, contractId, amount, status, voucher);
        return id;
    }

    private long statement(long providerId, BigDecimal total, BigDecimal fee) {
        long id = nextId();
        jdbc.update("""
                insert into aap_settlement_statement (id, statement_no, provider_id, period_from, period_to,
                    total_amount, platform_fee, status, created_at, updated_at, deleted, version)
                values (?, ?, ?, now() - interval '30 days', now(), ?, ?, 'DRAFT', now(), now(), false, 0)
                """, id, "STTEST" + id, providerId, total, fee);
        return id;
    }

    // ================================================================== PAY-01

    @Test
    @DisplayName("PAY-01 打款列表：只回本供应商，钱包三项三态互斥（未认证 401）")
    void listOwnPaymentsWithWallet() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        long otherProviderId = providerId(token(OTHER_PHONE));
        long signedContract = contract(providerId, "SIGNED");

        payment(providerId, signedContract, "UNSETTLED", new BigDecimal("10.500000"));
        payment(providerId, signedContract, "PAYMENT_RECORDED", new BigDecimal("20.250000"));
        payment(providerId, signedContract, "CONFIRMED", new BigDecimal("30.750000"));
        payment(providerId, signedContract, "VOID", new BigDecimal("99.000000"));
        payment(otherProviderId, contract(otherProviderId, "SIGNED"), "CONFIRMED", new BigDecimal("500.000000"));

        HttpResult list = get("/payments?page=1&pageSize=20", supplier);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("total").asLong()).as(list.body()).isEqualTo(4L);
        assertThat(list.data().path("items").size()).as(list.body()).isEqualTo(4);
        SchemaAssert.assertPageMeta(json(list.data()));
        var first = list.data().path("items").get(0);
        SchemaAssert.assertModel("payment", json(first));
        assertThat(first.path("provider_id").asText()).isEqualTo(String.valueOf(providerId));
        assertThat(first.path("currency").asText()).isEqualTo("USD");

        // 钱包三项：三态互斥，VOID 不计入任何一项
        assertThat(list.data().path("pending_settlement").decimalValue()).isEqualByComparingTo("10.5");
        assertThat(list.data().path("available_balance").decimalValue()).isEqualByComparingTo("20.25");
        assertThat(list.data().path("total_settled").decimalValue()).isEqualByComparingTo("30.75");

        // 分页
        HttpResult paged = get("/payments?page=5&pageSize=2", supplier);
        assertThat(paged.data().path("items").size()).isZero();
        assertThat(paged.data().path("total").asLong()).isEqualTo(4L);

        assertThat(get("/payments").status()).isEqualTo(401);
    }

    // ================================================================== ADM-PAY01

    @Test
    @DisplayName("ADM-PAY01 打款列表：管理端跨供应商检索 + status 过滤（供应商主体 403）")
    void adminListsAllPayments() throws Exception {
        String supplier = token(PHONE);
        long providerA = providerId(supplier);
        long providerB = providerId(token(OTHER_PHONE));
        payment(providerA, contract(providerA, "SIGNED"), "CONFIRMED", new BigDecimal("11.000000"));
        payment(providerB, contract(providerB, "PAYMENT_RECORDED"), "PAYMENT_RECORDED", new BigDecimal("22.000000"));
        String admin = bizOpsToken();

        HttpResult list = get("/admin/payments?page=1&pageSize=20", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("total").asLong()).as(list.body()).isEqualTo(2L);
        SchemaAssert.assertPageMeta(json(list.data()));
        SchemaAssert.assertModel("payment", json(list.data().path("items").get(0)));
        assertThat(get("/admin/payments?status=CONFIRMED", admin).data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/payments?status=VOID", admin).data().path("total").asLong()).isZero();

        assertThat(get("/admin/payments", supplier).status()).isEqualTo(403);
        assertThat(get("/admin/payments").status()).isEqualTo(401);
    }

    // ================================================================== ADM-PAY02

    @Test
    @DisplayName("ADM-PAY02 确认打款：合同未签署 → 409 E-1701 且状态不变；已签署 → CONFIRMED + 留痕；重复确认 → E-1601")
    void confirmRequiresSignedContract() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        String admin = bizOpsToken();

        long pendingContract = contract(providerId, "PENDING_SIGN");
        long blocked = payment(providerId, pendingContract, "PAYMENT_RECORDED", new BigDecimal("100.000000"));
        HttpResult rejected = post("/admin/payments/" + blocked + "/confirm", null, admin);
        assertThat(rejected.status()).as(rejected.body()).isEqualTo(409);
        assertThat(rejected.code()).isEqualTo("E-1701");
        SchemaAssert.assertError(rejected.body());
        // 打款仅记录（R-42）：被拦下时状态与确认人一律不变
        assertThat(jdbc.queryForMap("select status, confirmed_by from aap_payment_record where id = ?", blocked))
                .containsEntry("status", "PAYMENT_RECORDED").containsEntry("confirmed_by", null);

        long signedContract = contract(providerId, "SIGNED");
        long paymentId = payment(providerId, signedContract, "PAYMENT_RECORDED", new BigDecimal("100.000000"));
        HttpResult ok = post("/admin/payments/" + paymentId + "/confirm", null, admin);
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        SchemaAssert.assertModel("payment", json(ok.data()));
        assertThat(ok.data().path("status").asText()).as(ok.body()).isEqualTo("CONFIRMED");
        assertThat(ok.data().path("confirmed_at").asText()).as(ok.body()).isNotBlank();
        var row = jdbc.queryForMap("""
                select status, confirmed_by, confirmed_at from aap_payment_record where id = ?
                """, paymentId);
        assertThat(row.get("status")).isEqualTo("CONFIRMED");
        assertThat(row.get("confirmed_by")).isEqualTo(BIZ_OPS_ID);
        assertThat(row.get("confirmed_at")).isNotNull();
        assertThat(jdbc.queryForList("select action from aap_audit_log where target_type = 'payment'",
                String.class)).contains("PAYMENT_CONFIRM");

        HttpResult twice = post("/admin/payments/" + paymentId + "/confirm", null, admin);
        assertThat(twice.status()).isEqualTo(409);
        assertThat(twice.code()).isEqualTo("E-1601");

        HttpResult missing = post("/admin/payments/999999999/confirm", null, admin);
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");

        assertThat(post("/admin/payments/" + paymentId + "/confirm", null, supplier).status()).isEqualTo(403);
    }

    // ================================================================== ADM-PAY03

    @Test
    @DisplayName("ADM-PAY03 结算单列表：分页契约与模型校验（供应商主体 403）")
    void adminListsSettlements() throws Exception {
        String supplier = token(PHONE);
        long providerA = providerId(supplier);
        long providerB = providerId(token(OTHER_PHONE));
        statement(providerA, new BigDecimal("1000.000000"), new BigDecimal("50.000000"));
        statement(providerB, new BigDecimal("2000.000000"), new BigDecimal("100.000000"));
        String admin = bizOpsToken();

        HttpResult list = get("/admin/settlements?page=1&pageSize=1", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("total").asLong()).as(list.body()).isEqualTo(2L);
        assertThat(list.data().path("items").size()).isEqualTo(1);
        SchemaAssert.assertPageMeta(json(list.data()));
        SchemaAssert.assertModel("settlement-statement", json(list.data().path("items").get(0)));
        assertThat(list.data().path("items").get(0).path("statement_no").asText()).startsWith("ST");

        assertThat(get("/admin/settlements", supplier).status()).isEqualTo(403);
        assertThat(get("/admin/settlements").status()).isEqualTo(401);
    }
}
