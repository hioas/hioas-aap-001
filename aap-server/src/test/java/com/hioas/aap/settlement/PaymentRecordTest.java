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
 * T11 · 记录打款与作废打款（**新增端点 ADM-PAY04 / ADM-PAY05**）。
 *
 * <p>背景（2026-09-23 运行态实测）：{@code aap_payment_record} 在本仓库**没有任何 insert 代码路径**
 * → {@code ADM-PAY02 确认打款}永远没有可确认对象（实测 {@code /admin/payments} total=0），
 * 合同签完后链路断开。真源 PRD 10 §4.3/§5.3：运营商务线下打款后「记录打款」（凭证截图）→ 确认；
 * {@code VOID 作废后重录}。
 *
 * <p>锁定口径：
 * <ul>
 *   <li>合同必须 SIGNED（未签署 → 409 E-1601，且不留半成品记录）；</li>
 *   <li>C4：金额 &gt; 0；币种与合同一致（不传币种回退合同币种）；</li>
 *   <li>C5：凭证必填且文件必须存在；</li>
 *   <li>同合同不允许两笔生效中打款；作废后可重录（PRD 4.3）；</li>
 *   <li>不产生资金流水（R-42）：只落记录 + 状态 + 审计。</li>
 * </ul>
 */
class PaymentRecordTest extends ApiTestBase {

    private static final String PHONE = "13800000094";
    private static final long BIZ_OPS_ID = 961002L;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    private long seq = 990000L;

    private long nextId() {
        return ++seq;
    }

    private String token(String phone) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, send.data().path("dev_code").asText()));
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
                values (?, 'bizops-payment', 'x', 'bizops-payment', 'BIZ_OPERATOR', 'ACTIVE')
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

    private long contract(long providerId, String status, String currency) {
        long id = nextId();
        jdbc.update("""
                insert into aap_contract (id, contract_no, provider_id, title, status, sign_channel, currency,
                    created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, 'OFFLINE', ?, now(), now(), false, 0)
                """, id, "HTREC" + id, providerId, "记录打款用合同 " + id, status, currency);
        return id;
    }

    private long voucherFile() {
        long id = nextId();
        jdbc.update("""
                insert into aap_file_asset (id, file_key, original_name, content_type, size_bytes, biz_type,
                    encrypted, status, created_at, updated_at)
                values (?, ?, '打款凭证.png', 'image/png', 1024, 'PAYMENT_VOUCHER', false, 'ACTIVE', now(), now())
                """, id, "vouchers/" + id + ".png");
        return id;
    }

    private String recordBody(long contractId, String amount, String currency, Long voucherId, String remark) {
        return """
                {"contract_id":"%d","amount":%s%s,"voucher_file_id":%s%s}
                """.formatted(contractId, amount,
                currency == null ? "" : ",\"currency\":\"" + currency + "\"",
                voucherId == null ? "null" : "\"" + voucherId + "\"",
                remark == null ? "" : ",\"remark\":\"" + remark + "\"");
    }

    // ================================================================== ADM-PAY04

    @Test
    @DisplayName("ADM-PAY04 记录打款：SIGNED 合同 → PAYMENT_RECORDED，落归属/凭证/审计，并进入钱包与列表")
    void recordPaymentSucceeds() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        String admin = bizOpsToken();
        long contractId = contract(providerId, "SIGNED", "CNY");
        long voucher = voucherFile();

        HttpResult res = post("/admin/payments", recordBody(contractId, "1234.560000", "CNY", voucher, "首笔打款"), admin);

        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertModel("payment", json(res.data()));
        assertThat(res.data().path("status").asText()).isEqualTo("PAYMENT_RECORDED");
        assertThat(res.data().path("provider_id").asText()).isEqualTo(String.valueOf(providerId));
        assertThat(res.data().path("contract_id").asText()).isEqualTo(String.valueOf(contractId));
        assertThat(res.data().path("currency").asText()).isEqualTo("CNY");
        assertThat(res.data().path("voucher_file_id").asText()).isEqualTo(String.valueOf(voucher));
        assertThat(res.data().path("paid_at").asText()).isNotBlank();
        long paymentId = Long.parseLong(res.data().path("id").asText());

        var row = jdbc.queryForMap("""
                select provider_id, contract_id, status, amount, currency, voucher_file_id, created_by
                  from aap_payment_record where id = ?
                """, paymentId);
        assertThat(row).containsEntry("status", "PAYMENT_RECORDED")
                .containsEntry("provider_id", providerId).containsEntry("contract_id", contractId)
                .containsEntry("currency", "CNY").containsEntry("voucher_file_id", voucher);
        assertThat(((BigDecimal) row.get("amount"))).isEqualByComparingTo("1234.56");
        assertThat(row.get("created_by")).isEqualTo(BIZ_OPS_ID);

        assertThat(jdbc.queryForList("select action from aap_audit_log where target_type = 'payment'", String.class))
                .contains("PAYMENT_RECORD");

        // 进入管理端列表与该供应商钱包（available_balance = PAYMENT_RECORDED 合计，R-42 仅记录）
        assertThat(get("/admin/payments?status=PAYMENT_RECORDED", admin).data().path("total").asLong()).isEqualTo(1L);
        HttpResult wallet = get("/payments?page=1&pageSize=5", supplier);
        assertThat(wallet.data().path("total").asLong()).isEqualTo(1L);
        assertThat(wallet.data().path("available_balance").decimalValue()).isEqualByComparingTo("1234.56");

        // 与 ADM-PAY02 串起来：确认打款（状态机闭合）
        HttpResult confirmed = post("/admin/payments/" + paymentId + "/confirm", null, admin);
        assertThat(confirmed.status()).as(confirmed.body()).isEqualTo(200);
        assertThat(confirmed.data().path("status").asText()).isEqualTo("CONFIRMED");
    }

    @Test
    @DisplayName("ADM-PAY04 守卫：未签署 409、金额≤0 400、币种不一致 400、凭证缺失/不存在 400、重复记录 409")
    void recordPaymentGuards() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        String admin = bizOpsToken();
        long voucher = voucherFile();

        // 未签署 → 409，且不留半成品
        long pending = contract(providerId, "PENDING_SIGN", "CNY");
        HttpResult unsigned = post("/admin/payments", recordBody(pending, "100", "CNY", voucher, null), admin);
        assertThat(unsigned.status()).as(unsigned.body()).isEqualTo(409);
        assertThat(unsigned.code()).isEqualTo("E-1601");
        SchemaAssert.assertError(unsigned.body());
        assertThat(jdbc.queryForObject("select count(*) from aap_payment_record where contract_id = ?",
                Long.class, pending)).isZero();

        long signed = contract(providerId, "SIGNED", "CNY");
        HttpResult zero = post("/admin/payments", recordBody(signed, "0", "CNY", voucher, null), admin);
        assertThat(zero.status()).as(zero.body()).isEqualTo(400);
        assertThat(zero.code()).isEqualTo("E-1001");
        assertThat(zero.body()).contains("amount");

        HttpResult mismatch = post("/admin/payments", recordBody(signed, "100", "USD", voucher, null), admin);
        assertThat(mismatch.status()).as(mismatch.body()).isEqualTo(400);
        assertThat(mismatch.body()).contains("currency");

        HttpResult noVoucher = post("/admin/payments", recordBody(signed, "100", "CNY", null, null), admin);
        assertThat(noVoucher.status()).as(noVoucher.body()).isEqualTo(400);
        assertThat(noVoucher.body()).contains("voucher_file_id");

        HttpResult ghostVoucher = post("/admin/payments",
                recordBody(signed, "100", "CNY", 999999999999L, null), admin);
        assertThat(ghostVoucher.status()).as(ghostVoucher.body()).isEqualTo(400);
        assertThat(ghostVoucher.body()).contains("voucher_file_id");

        // 合法一笔
        HttpResult ok = post("/admin/payments", recordBody(signed, "100", null, voucher, "不传币种→取合同币种"), admin);
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        assertThat(ok.data().path("currency").asText()).as("不传币种应回退合同币种").isEqualTo("CNY");

        // 同合同第二笔生效中 → 409
        HttpResult dup = post("/admin/payments", recordBody(signed, "200", "CNY", voucher, null), admin);
        assertThat(dup.status()).as(dup.body()).isEqualTo(409);
        assertThat(dup.code()).isEqualTo("E-1601");

        // 合同不存在 → 404；供应商主体 → 403；未认证 → 401
        assertThat(post("/admin/payments", recordBody(999999999999L, "100", "CNY", voucher, null), admin).code())
                .isEqualTo("E-1406");
        assertThat(post("/admin/payments", recordBody(signed, "100", "CNY", voucher, null), supplier).status())
                .isEqualTo(403);
        assertThat(post("/admin/payments", recordBody(signed, "100", "CNY", voucher, null), null).status())
                .isEqualTo(401);
    }

    // ================================================================== ADM-PAY05

    @Test
    @DisplayName("ADM-PAY05 作废打款：必填理由，→ VOID 并留痕，作废后可重录（PRD 4.3）")
    void voidPaymentAllowsReRecord() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        String admin = bizOpsToken();
        long contractId = contract(providerId, "SIGNED", "CNY");
        long voucher = voucherFile();

        long paymentId = Long.parseLong(post("/admin/payments",
                recordBody(contractId, "500", "CNY", voucher, "原记录"), admin).data().path("id").asText());

        HttpResult noReason = post("/admin/payments/" + paymentId + "/void", "{}", admin);
        assertThat(noReason.status()).as(noReason.body()).isEqualTo(400);
        assertThat(noReason.body()).contains("reason");

        HttpResult voided = post("/admin/payments/" + paymentId + "/void", "{\"reason\":\"金额填错\"}", admin);
        assertThat(voided.status()).as(voided.body()).isEqualTo(200);
        assertThat(voided.data().path("status").asText()).isEqualTo("VOID");
        assertThat(voided.data().path("remark").asText()).contains("金额填错").contains("原记录");
        assertThat(jdbc.queryForList("select action from aap_audit_log where target_type = 'payment'", String.class))
                .contains("PAYMENT_VOID");

        // 作废后不计入钱包
        assertThat(get("/payments?page=1&pageSize=5", supplier).data().path("available_balance").decimalValue())
                .isEqualByComparingTo("0");

        // 作废后可重录（本用例证明「VOID 作废后重录」口径）
        HttpResult reRecord = post("/admin/payments", recordBody(contractId, "600", "CNY", voucher, "重录"), admin);
        assertThat(reRecord.status()).as(reRecord.body()).isEqualTo(200);
        assertThat(reRecord.data().path("status").asText()).isEqualTo("PAYMENT_RECORDED");

        // 重复作废 → 409；不存在的记录 → 404；供应商主体 → 403
        HttpResult twice = post("/admin/payments/" + paymentId + "/void", "{\"reason\":\"再来一次\"}", admin);
        assertThat(twice.status()).as(twice.body()).isEqualTo(409);
        assertThat(twice.code()).isEqualTo("E-1601");
        assertThat(post("/admin/payments/999999999/void", "{\"reason\":\"x\"}", admin).code()).isEqualTo("E-1406");
        assertThat(post("/admin/payments/" + paymentId + "/void", "{\"reason\":\"x\"}", supplier).status())
                .isEqualTo(403);
    }
}
