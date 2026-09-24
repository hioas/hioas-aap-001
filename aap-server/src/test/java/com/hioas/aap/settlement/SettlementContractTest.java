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
import tools.jackson.databind.JsonNode;

/**
 * 结算单生成与出账闭环（ADM-PAY06…09 + SET-01/02）验收 —— 业务闭环的**资金结算段**。
 *
 * <p>为什么需要这一组端点（运行态实测，非推断）：`aap_settlement_statement` /
 * `aap_settlement_line` 在本仓库此前**只有读路径** —— ADM-PAY03 实测 `total=0`、全仓
 * `insert into aap_settlement_statement` 零命中 ⇒「打款确认（CONFIRMED）之后没有下一环」，
 * 供应商永远看不到自己被结算的明细。而这三件事在 PRD 里**零定义**（D-SETTLE-01）：
 * 出账周期、platform_fee 计费基数、金额计算基数 —— 全目录 grep「结算单/结算周期/出账/
 * platform_fee/费率」均 0 命中。
 *
 * <p>口径由 **D-SETTLE-02 自主拍板**，且全部可配（`app.settlement.*`，改口径不必改代码）：
 * <ul>
 *   <li>周期：自然月 UTC（与用量窗口 {@code month=YYYY-MM} 同口径）</li>
 *   <li>金额基数：{@code aap_usage_hourly.cost_usd} 合计（对账视图即用此字段）</li>
 *   <li>平台费：合同 {@code platform_fee_rate} × 金额基数；低于合同 {@code min_settlement_amount} 不出账</li>
 *   <li>明细维度：渠道 × 模型（= {@code aap_settlement_line} 的表列）</li>
 *   <li>状态机：{@code DRAFT → CONFIRMED}；{@code DRAFT → VOID} 后可重新生成（历史单保留）</li>
 * </ul>
 *
 * <p>本类只覆盖「结算」本身：合同与打款数据用 SQL 直接落到目标态（其生命周期分别由
 * 合同/打款用例覆盖），避免把多处业务规则混进同一组断言。
 */
class SettlementContractTest extends ApiTestBase {

    private static final String SUPPLIER_A = "13800000151";
    private static final String SUPPLIER_B = "13800000152";
    private static final String MONTH = "2026-09";
    private static final long CONTRACT_ID = 990000001L;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    // ------------------------------------------------------------------ 令牌

    private String supplierToken(String phone) {
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

    private String adminToken(long accountId, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, 'x', '结算验收', ?, 'ACTIVE')
                """, accountId, role.toLowerCase() + "-" + accountId, role);
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String bizOperator() {
        return adminToken(980601L, "BIZ_OPERATOR");
    }

    private String techOps() {
        return adminToken(980602L, "TECH_OPS");
    }

    // ------------------------------------------------------------------ 夹具

    /** 走真实接口建供应商档案，返回 provider_id（不直接 SQL 造，避免绕过档案校验）。 */
    private long seedProvider(String token, String uscc) {
        HttpResult r = put("/provider/profile", """
                {"company_name":"结算验收科技有限公司","short_name":"结算验收","uscc":"%s",
                 "industry_category":"ORIGINAL","contact_name":"结算联系人","contact_phone":"13800000151"}
                """.formatted(uscc), token);
        assertThat(r.status()).as(r.body()).isEqualTo(200);
        return Long.parseLong(r.data().path("provider_id").asText());
    }

    /** SIGNED 合同（结算口径载体：费率 / 门槛 / 币种 / 周期）。 */
    private void seedContract(long providerId, String status, String feeRate, String minAmount) {
        jdbc.update("""
                insert into aap_contract (id, contract_no, provider_id, title, status, sign_channel,
                                          settlement_cycle, platform_fee_rate, currency, min_settlement_amount)
                values (?, ?, ?, '结算验收合同', ?, 'OFFLINE', 'MONTHLY', ?::numeric, 'USD', ?::numeric)
                """, CONTRACT_ID, "HT-TEST-SETTLE", providerId, status, feeRate, minAmount);
    }

    /** 用量桶（唯一键 stat_hour + channel_id + model_name + group_name）。 */
    private void seedUsage(long providerId, String statHour, Long channelId, String modelName,
                           int requests, long tokens, String quotaRaw, String costUsd) {
        jdbc.update("""
                insert into aap_usage_hourly (id, stat_hour, channel_id, channel_name, provider_id,
                                              model_name, group_name, request_count, total_tokens,
                                              quota_raw, cost_usd, cache_parse_status, batch_id)
                values (nextval('seq_usage_hourly'), ?::timestamptz, ?, '渠道', ?, ?, 'default', ?, ?, ?::numeric, ?::numeric, 'OK', 1)
                """, statHour, channelId, providerId, modelName, requests, tokens, quotaRaw, costUsd);
    }

    /** 打款记录（打款生命周期由打款用例覆盖，此处只落到被结算所需的状态）。 */
    private void seedPayment(long paymentId, long providerId, String status, String paidAt, String amount) {
        jdbc.update("""
                insert into aap_payment_record (id, provider_id, contract_id, amount, currency, status, paid_at)
                values (?, ?, ?, ?::numeric, 'USD', ?, ?::timestamptz)
                """, paymentId, providerId, CONTRACT_ID, amount, status, paidAt);
    }

    private HttpResult generate(String admin, long providerId) {
        return generate(admin, providerId, MONTH);
    }

    private HttpResult generate(String admin, long providerId, String month) {
        return post("/admin/settlements", """
                {"provider_id":"%d","month":"%s"}
                """.formatted(providerId, month), admin);
    }

    // ------------------------------------------------------------------ ADM-PAY06

    @Test
    @DisplayName("ADM-PAY06 生成结算单：明细按渠道×模型汇总、总额=Σ金额、平台费=费率×基数、净额=总额-平台费")
    void generateAggregatesUsageIntoLines() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE001A");
        seedContract(providerId, "SIGNED", "0.1000", "1.000000");
        // 同渠道同模型两桶 → 必须合并为一行
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");
        seedUsage(providerId, "2026-09-10T04:00:00Z", 1001L, "gpt-4o", 3, 500, "50.000000", "1.000000");
        // 另一渠道另一模型 → 独立一行
        seedUsage(providerId, "2026-09-11T03:00:00Z", 1002L, "claude-3", 5, 2000, "200.000000", "2.500000");

        HttpResult gen = generate(bizOperator(), providerId);
        assertThat(gen.status()).as(gen.body()).isEqualTo(200);
        SchemaAssert.assertModel("settlement-detail", json(gen.data()));

        assertThat(gen.data().path("statement_no").asText()).startsWith("ST");
        assertThat(gen.data().path("status").asText()).isEqualTo("DRAFT");
        assertThat(gen.data().path("provider_id").asText()).isEqualTo(String.valueOf(providerId));
        assertThat(gen.data().path("period_from").asText()).isEqualTo("2026-09-01T00:00:00Z");
        assertThat(gen.data().path("period_to").asText()).isEqualTo("2026-10-01T00:00:00Z");
        assertThat(gen.data().path("currency").asText()).isEqualTo("USD");
        assertThat(gen.data().path("total_amount").decimalValue()).isEqualByComparingTo("5.000000");
        assertThat(gen.data().path("platform_fee").decimalValue()).isEqualByComparingTo("0.500000");
        assertThat(gen.data().path("net_amount").decimalValue()).isEqualByComparingTo("4.500000");

        JsonNode lines = gen.data().path("lines");
        assertThat(lines.size()).as("同渠道同模型的两桶必须合并，跨渠道/模型必须拆行").isEqualTo(2);
        BigDecimal sum = BigDecimal.ZERO;
        for (JsonNode line : lines) {
            sum = sum.add(line.path("amount").decimalValue());
        }
        assertThat(sum).as("明细金额合计必须等于结算总额（防止明细与总额两套口径）")
                .isEqualByComparingTo("5.000000");

        // 落库核对（不是只看响应）
        assertThat(jdbc.queryForObject("""
                select count(*) from aap_settlement_line l
                  join aap_settlement_statement s on s.id = l.statement_id
                 where s.provider_id = ? and s.period_from = '2026-09-01T00:00:00Z'::timestamptz
                """, Long.class, providerId)).isEqualTo(2L);
        assertThat(jdbc.queryForObject("""
                select sum(total_tokens) from aap_settlement_line l
                  join aap_settlement_statement s on s.id = l.statement_id
                 where s.provider_id = ?
                """, Long.class, providerId)).isEqualTo(3500L);
    }

    @Test
    @DisplayName("ADM-PAY06 幂等：同供应商同周期重复生成返回既有单，不新增行")
    void generateIsIdempotentForSamePeriod() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE002A");
        seedContract(providerId, "SIGNED", "0.1000", "1.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");
        String biz = bizOperator();

        HttpResult first = generate(biz, providerId);
        HttpResult second = generate(biz, providerId);
        assertThat(first.status()).as(first.body()).isEqualTo(200);
        assertThat(second.status()).as(second.body()).isEqualTo(200);
        assertThat(second.data().path("statement_no").asText())
                .isEqualTo(first.data().path("statement_no").asText());
        assertThat(jdbc.queryForObject("""
                select count(*) from aap_settlement_statement where provider_id = ?
                """, Long.class, providerId)).isEqualTo(1L);
    }

    @Test
    @DisplayName("ADM-PAY06 前置：该周期无用量 → 409 E-1601（不造空单）")
    void generateRejectsPeriodWithoutUsage() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE003A");
        seedContract(providerId, "SIGNED", "0.1000", "0.000000");

        HttpResult gen = generate(bizOperator(), providerId, "2026-08");
        assertThat(gen.status()).isEqualTo(409);
        assertThat(gen.code()).isEqualTo("E-1601");
        assertThat(gen.message()).contains("用量");
        assertThat(jdbc.queryForObject("select count(*) from aap_settlement_statement", Long.class)).isZero();
    }

    @Test
    @DisplayName("ADM-PAY06 前置：低于合同 min_settlement_amount → 409 E-1601（门槛生效）")
    void generateRejectsBelowMinSettlementAmount() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE004A");
        seedContract(providerId, "SIGNED", "0.1000", "100.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");

        HttpResult gen = generate(bizOperator(), providerId);
        assertThat(gen.status()).isEqualTo(409);
        assertThat(gen.code()).isEqualTo("E-1601");
        assertThat(gen.message()).contains("100");
        assertThat(jdbc.queryForObject("select count(*) from aap_settlement_statement", Long.class)).isZero();
    }

    @Test
    @DisplayName("ADM-PAY06 前置：无 SIGNED 合同 → 409 E-1701（出账必须有生效合同）")
    void generateRequiresSignedContract() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE005A");
        seedContract(providerId, "PENDING_SIGN", "0.1000", "0.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");

        HttpResult gen = generate(bizOperator(), providerId);
        assertThat(gen.status()).isEqualTo(409);
        assertThat(gen.code()).isEqualTo("E-1701");
        assertThat(gen.message()).contains("合同");
    }

    // ------------------------------------------------------------------ ADM-PAY08 / 09

    @Test
    @DisplayName("ADM-PAY08/09 状态机：DRAFT→CONFIRMED 后不可再确认、不可作废；VOID 后可重新生成")
    void statusMachineAndRegeneration() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE006A");
        seedContract(providerId, "SIGNED", "0.1000", "1.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");
        String biz = bizOperator();

        String firstId = generate(biz, providerId).data().path("id").asText();

        HttpResult confirmed = post("/admin/settlements/" + firstId + "/confirm", null, biz);
        assertThat(confirmed.status()).as(confirmed.body()).isEqualTo(200);
        assertThat(confirmed.data().path("status").asText()).isEqualTo("CONFIRMED");

        // 重复确认 / 确认后作废 → 状态非法流转
        HttpResult again = post("/admin/settlements/" + firstId + "/confirm", null, biz);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");
        HttpResult voidConfirmed = post("/admin/settlements/" + firstId + "/void", """
                {"reason":"确认后不允许作废"}
                """, biz);
        assertThat(voidConfirmed.status()).as(voidConfirmed.body()).isEqualTo(409);
        assertThat(voidConfirmed.code()).isEqualTo("E-1601");

        // 空理由 → 400 E-1001（参数级校验先于状态校验）
        HttpResult noReason = post("/admin/settlements/" + firstId + "/void", """
                {"reason":""}
                """, biz);
        assertThat(noReason.status()).isEqualTo(400);
        assertThat(noReason.code()).isEqualTo("E-1001");
    }

    @Test
    @DisplayName("ADM-PAY09 作废后可重新生成：VOID 不占唯一性，历史单保留且状态为 VOID")
    void voidAllowsRegeneration() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE007A");
        seedContract(providerId, "SIGNED", "0.1000", "1.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");
        String biz = bizOperator();

        String firstId = generate(biz, providerId).data().path("id").asText();
        String firstNo = jdbc.queryForObject("select statement_no from aap_settlement_statement where id = ?::bigint",
                String.class, firstId);

        HttpResult voided = post("/admin/settlements/" + firstId + "/void", """
                {"reason":"口径调整，需重算"}
                """, biz);
        assertThat(voided.status()).as(voided.body()).isEqualTo(200);
        assertThat(voided.data().path("status").asText()).isEqualTo("VOID");

        HttpResult regenerated = generate(biz, providerId);
        assertThat(regenerated.status()).as(regenerated.body()).isEqualTo(200);
        assertThat(regenerated.data().path("statement_no").asText()).isNotEqualTo(firstNo);
        assertThat(jdbc.queryForObject("""
                select count(*) from aap_settlement_statement where provider_id = ?
                """, Long.class, providerId)).as("历史单必须保留（可追溯）").isEqualTo(2L);
        assertThat(jdbc.queryForObject("""
                select count(*) from aap_settlement_statement where provider_id = ? and status = 'VOID'
                """, Long.class, providerId)).isEqualTo(1L);
    }

    // ------------------------------------------------------------------ 打款关联

    @Test
    @DisplayName("ADM-PAY06 生成时回填期内打款：period 内的 CONFIRMED 打款挂到结算单，期外的不挂")
    void generateLinksPaymentsInsidePeriodOnly() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE008A");
        seedContract(providerId, "SIGNED", "0.1000", "1.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");
        seedPayment(990000101L, providerId, "CONFIRMED", "2026-09-15T00:00:00Z", "3.000000");
        seedPayment(990000102L, providerId, "CONFIRMED", "2026-10-05T00:00:00Z", "9.000000");

        HttpResult gen = generate(bizOperator(), providerId);
        assertThat(gen.status()).as(gen.body()).isEqualTo(200);
        assertThat(gen.data().path("payments").size()).as("只有期内的打款挂到本期结算单").isEqualTo(1);
        assertThat(jdbc.queryForObject("select statement_id from aap_payment_record where id = ?",
                Long.class, 990000101L)).isNotNull();
        assertThat(jdbc.queryForObject("select statement_id from aap_payment_record where id = ?",
                Long.class, 990000102L)).isNull();
    }

    // ------------------------------------------------------------------ ADM-PAY07 + 越权

    @Test
    @DisplayName("ADM-PAY07 详情：未知 ID → 404 E-1406；详情含明细与供应商名")
    void detailIncludesLinesAndHidesUnknown() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE009A");
        seedContract(providerId, "SIGNED", "0.1000", "1.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");
        String biz = bizOperator();
        String id = generate(biz, providerId).data().path("id").asText();

        HttpResult detail = get("/admin/settlements/" + id, biz);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertModel("settlement-detail", json(detail.data()));
        assertThat(detail.data().path("provider_name").asText()).isNotBlank();
        assertThat(detail.data().path("lines").size()).isEqualTo(1);

        HttpResult missing = get("/admin/settlements/999999999999", biz);
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
    }

    // ------------------------------------------------------------------ SET-01 / SET-02

    @Test
    @DisplayName("SET-01/02 供应商端：只看得到自己的结算单；读他人单 → 404 E-1406（不泄露存在性）")
    void providerSeesOwnStatementsOnly() {
        String tokenA = supplierToken(SUPPLIER_A);
        long providerA = seedProvider(tokenA, "91110108SETTLE0101");
        seedContract(providerA, "SIGNED", "0.1000", "1.000000");
        seedUsage(providerA, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");
        String biz = bizOperator();
        HttpResult genA = generate(biz, providerA);
        assertThat(genA.status()).as(genA.body()).isEqualTo(200);
        String idA = genA.data().path("id").asText();

        HttpResult listA = get("/settlements", tokenA);
        assertThat(listA.status()).as(listA.body()).isEqualTo(200);
        assertThat(listA.data().path("total").asLong()).isEqualTo(1L);
        assertThat(listA.data().path("items").get(0).path("statement_no").asText())
                .isEqualTo(genA.data().path("statement_no").asText());

        HttpResult detailA = get("/settlements/" + idA, tokenA);
        assertThat(detailA.status()).as(detailA.body()).isEqualTo(200);
        SchemaAssert.assertModel("settlement-detail", json(detailA.data()));
        assertThat(detailA.data().path("lines").size()).isEqualTo(1);

        // 另一个供应商登录后不得读到 A 的单
        String tokenB = supplierToken(SUPPLIER_B);
        seedProvider(tokenB, "91110108SETTLE0102");
        HttpResult listB = get("/settlements", tokenB);
        assertThat(listB.status()).as(listB.body()).isEqualTo(200);
        assertThat(listB.data().path("total").asLong()).isZero();
        HttpResult detailB = get("/settlements/" + idA, tokenB);
        assertThat(detailB.status()).isEqualTo(404);
        assertThat(detailB.code()).isEqualTo("E-1406");
    }

    // ------------------------------------------------------------------ 权限

    @Test
    @DisplayName("权限：结算出账仅商务运营/超管（TECH_OPS → 403 E-1901）")
    void techOpsCannotGenerateSettlement() {
        String supplier = supplierToken(SUPPLIER_A);
        long providerId = seedProvider(supplier, "91110108SETTLE0111");
        seedContract(providerId, "SIGNED", "0.1000", "1.000000");
        seedUsage(providerId, "2026-09-10T03:00:00Z", 1001L, "gpt-4o", 7, 1000, "100.000000", "1.500000");

        HttpResult denied = generate(techOps(), providerId);
        assertThat(denied.status()).isEqualTo(403);
        assertThat(denied.code()).isEqualTo("E-1901");
    }
}
