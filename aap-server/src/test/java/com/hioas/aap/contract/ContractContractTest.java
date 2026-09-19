package com.hioas.aap.contract;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T11 · 合同（CON-01…04 供应商端 + ADM-CT01…03 管理端）。
 *
 * <p>契约真源：`docs/backend/endpoints.json` + `docs/backend/json-schema/{models/contract,models/report-export,requests/contract-issue,requests/contract-sign}.schema.json`
 * + `02-API接口模型清单.md` §1.3/§2.5（路径、错误码）+ `01-ER数据模型.md` §4.7（表结构）+ `03-任务与TDD计划.md` T11。
 *
 * <p>硬口径（每条对应断言）：
 * <ul>
 *   <li>**状态机**：CREATED（T10 审核通过自动生成）→[ADM-CT02 签发] PENDING_SIGN →[CON-04 供应商签署] SUPPLIER_SIGNED
 *       →[ADM-CT03 平台确认] SIGNED；非法流转一律 409（E-1601/E-1701），不静默覆盖</li>
 *   <li>**数据归属**：供应商端只能看到/操作自己的合同，越权按「不存在」（E-1406/404）处理，不泄露存在性</li>
 *   <li>**未签发无文件**：contract.file_id 为空说明尚未签发，CON-03 文件下载 → 409 E-1701</li>
 *   <li>**脱敏**：签署人手机号落 `signer_phone_mask`（R-48），不接受明文</li>
 *   <li>**权限**：管理端动作仅 BIZ_OPERATOR/SUPER_ADMIN；供应商主体访问管理端 403</li>
 * </ul>
 *
 * <p>夹具口径：合同行由 SQL 直接插入（T10 已覆盖「审核通过自动生成合同」，本任务族验证的是**签发之后的流转**），
 * 因此形态可控（状态/文件/条款可精确构造）。
 */
class ContractContractTest extends ApiTestBase {

    private static final String PHONE = "13800000090";
    private static final String OTHER_PHONE = "13800000091";

    private static final long BIZ_OPS_ID = 960001L;
    private static final long SUPER_ADMIN_ID = 960002L;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    /** 存储后端（夹具需要真的写入对象，否则下载必然 E-1406）。 */
    @Autowired
    private com.hioas.aap.file.StorageBackend storage;

    /** 夹具 PDF 字节（内容不重要，关键是能逐字节取回）。 */
    private static final byte[] PDF_BYTES = "%PDF-1.4 AAP contract fixture\n".getBytes(java.nio.charset.StandardCharsets.UTF_8);

    /** 夹具自增主键（每个用例前 truncate，不跨用例冲突）。 */
    private long seq = 970000L;

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

    private String adminToken(long accountId, String username, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, 'x', ?, ?, 'ACTIVE')
                """, accountId, username, role, role);
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String bizOpsToken() {
        return adminToken(BIZ_OPS_ID, "bizops-contract", "BIZ_OPERATOR");
    }

    private String superAdminToken() {
        return adminToken(SUPER_ADMIN_ID, "superadmin-contract", "SUPER_ADMIN");
    }

    /**
     * 文件资产夹具（合同 PDF）。
     *
     * <p><b>已随缺陷2 修复而更新</b>：原实现只插 {@code aap_file_asset} 元数据、**不写存储对象**，
     * 注释也写着「对象存储未接线」。文件服务接线后，只插元数据会让下载必然失败
     * （元数据在、对象不在 → E-1406），所以这里同步把字节写进存储后端，
     * 让夹具与真实上传后的状态一致。
     */
    private long asset(String originalName) {
        long id = nextId();
        String key = "CONTRACT/test/" + id + ".pdf";
        storage.put(key, PDF_BYTES);
        jdbc.update("""
                insert into aap_file_asset (id, file_key, bucket, original_name, content_type, size_bytes,
                    biz_type, encrypted, status, created_at, updated_at)
                values (?, ?, 'local', ?, 'application/pdf', ?, 'CONTRACT', false, 'ACTIVE', now(), now())
                """, id, key, originalName, PDF_BYTES.length);
        return id;
    }

    private long contract(long providerId, String status, Long fileId) {
        long id = nextId();
        jdbc.update("""
                insert into aap_contract (id, contract_no, provider_id, title, status, sign_channel, currency,
                    file_id, terms, created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, 'OFFLINE', 'USD', ?, cast(? as jsonb), now(), now(), false, 0)
                """, id, "HTTEST" + id, providerId, "渠道合作合同 " + id, status, fileId,
                "[\"合作期限 1 年\",\"月结 30 天\"]");
        return id;
    }

    private void signRecord(long contractId, String signerType, String signMethod, String tone) {
        long id = nextId();
        jdbc.update("""
                insert into aap_contract_sign (id, contract_id, signer_type, signer_name, sign_method, tone,
                    signed_at, created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, ?, now(), now(), now(), false, 0)
                """, id, contractId, signerType, signerType.equals("SUPPLIER") ? "张三" : "平台运营", signMethod, tone);
    }

    // ================================================================== CON-01

    @Test
    @DisplayName("CON-01 合同列表：只回本供应商，status 过滤与分页契约一致（未认证 401）")
    void listOwnContracts() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        long otherProviderId = providerId(token(OTHER_PHONE));
        contract(providerId, "PENDING_SIGN", null);
        contract(providerId, "CREATED", null);
        contract(otherProviderId, "PENDING_SIGN", null);

        HttpResult list = get("/contracts?page=1&pageSize=20", supplier);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("total").asLong()).as(list.body()).isEqualTo(2L);
        assertThat(list.data().path("items").size()).as(list.body()).isEqualTo(2);
        SchemaAssert.assertPageMeta(json(list.data()));

        var first = list.data().path("items").get(0);
        SchemaAssert.assertModel("contract", json(first));
        assertThat(first.path("contract_no").asText()).startsWith("HT");
        assertThat(first.path("provider_id").asText()).isEqualTo(String.valueOf(providerId));
        assertThat(first.path("sign_channel").asText()).isEqualTo("OFFLINE");

        // status 过滤不得被忽略（否则列表页筛选形同虚设）
        assertThat(get("/contracts?status=CREATED", supplier).data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/contracts?status=SIGNED", supplier).data().path("total").asLong()).isZero();

        // 分页：pageSize=1 时第 2 页回第 2 条（total 仍是全量），越界页回空
        HttpResult paged = get("/contracts?page=2&pageSize=1", supplier);
        assertThat(paged.data().path("items").size()).isEqualTo(1);
        assertThat(paged.data().path("total").asLong()).isEqualTo(2L);
        HttpResult beyond = get("/contracts?page=3&pageSize=1", supplier);
        assertThat(beyond.data().path("items").size()).isZero();
        assertThat(beyond.data().path("total").asLong()).isEqualTo(2L);

        assertThat(get("/contracts").status()).isEqualTo(401);
    }

    // ================================================================== CON-02

    @Test
    @DisplayName("CON-02 合同详情：terms[] 与签署 records[] 齐备；越权/不存在一律 404 E-1406")
    void detailCarriesTermsAndRecords() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        long contractId = contract(providerId, "SUPPLIER_SIGNED", null);
        signRecord(contractId, "SUPPLIER", "SMS", "pending");

        HttpResult detail = get("/contracts/" + contractId, supplier);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertModel("contract", json(detail.data()));
        assertThat(detail.data().path("id").asText()).isEqualTo(String.valueOf(contractId));
        assertThat(detail.data().path("contract_id").asText()).isEqualTo(String.valueOf(contractId));
        assertThat(detail.data().path("terms").size()).as(detail.body()).isEqualTo(2);
        assertThat(detail.data().path("terms").get(0).asText()).isEqualTo("合作期限 1 年");
        assertThat(detail.data().path("records").size()).as(detail.body()).isEqualTo(1);
        var record = detail.data().path("records").get(0);
        assertThat(record.path("signer_type").asText()).isEqualTo("SUPPLIER");
        assertThat(record.path("tone").asText()).isEqualTo("pending");
        assertThat(record.path("at").asText()).isNotBlank();

        // 越权与不存在对调用方**同形**（不泄露别家合同是否存在）
        HttpResult foreign = get("/contracts/" + contractId, token(OTHER_PHONE));
        assertThat(foreign.status()).isEqualTo(404);
        assertThat(foreign.code()).isEqualTo("E-1406");
        SchemaAssert.assertError(foreign.body());

        HttpResult missing = get("/contracts/999999999", supplier);
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
    }

    // ================================================================== CON-03

    @Test
    @DisplayName("CON-03 合同文件：已签发回 {url,file_name}；尚未签发（CREATED）→ 409 E-1701")
    void fileRequiresIssuedContract() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        long fileId = asset("合作合同.pdf");

        long created = contract(providerId, "CREATED", fileId);
        HttpResult notIssued = get("/contracts/" + created + "/file", supplier);
        assertThat(notIssued.status()).as(notIssued.body()).isEqualTo(409);
        assertThat(notIssued.code()).isEqualTo("E-1701");

        long issued = contract(providerId, "PENDING_SIGN", fileId);
        HttpResult file = get("/contracts/" + issued + "/file", supplier);
        assertThat(file.status()).as(file.body()).isEqualTo(200);
        SchemaAssert.assertModel("report-export", json(file.data()));
        // ⚠️ 期望已更新：此前 url 回的是**存储键**（`contracts/{id}.pdf`，因为对象存储未接线），
        //    这条用例把那个占位值固化成了期望。文件服务接线后，url 必须是**真实可下载地址**，
        //    否则前端拿到 file_key 根本下不了文件。
        assertThat(file.data().path("url").asText()).as(file.body())
                .isEqualTo("/api/v1/files/" + fileId);
        assertThat(file.data().path("file_name").asText()).isEqualTo("合作合同.pdf");
        assertThat(file.data().path("expire_at").asText()).isNotBlank();

        // url 必须真的能下载到东西（不只是格式对）
        BinaryResult downloaded = getBinary("/files/" + fileId, supplier);
        assertThat(downloaded.status()).as("合同文件 url 应可下载").isEqualTo(200);
        assertThat(downloaded.body().length).as("下载内容不应为空").isGreaterThan(0);

        // 越权：别人的合同文件同样按不存在处理
        HttpResult foreign = get("/contracts/" + issued + "/file", token(OTHER_PHONE));
        assertThat(foreign.status()).isEqualTo(404);
        assertThat(foreign.code()).isEqualTo("E-1406");

        // 未签发且无文件资产：也不能 500
        long noFile = contract(providerId, "PENDING_SIGN", null);
        HttpResult missing = get("/contracts/" + noFile + "/file", supplier);
        assertThat(missing.status()).as("无文件资产时应为 409 E-1701，实际：" + missing.body()).isEqualTo(409);
        assertThat(missing.code()).isEqualTo("E-1701");
    }

    // ================================================================== CON-04 + ADM-CT02/03

    @Test
    @DisplayName("CON-04 全链路状态机：CREATED→[签发]PENDING_SIGN→[供应商签署]SUPPLIER_SIGNED→[平台确认]SIGNED")
    void signStateMachineEndToEnd() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        jdbc.update("update aap_provider set contact_name = '张三', contact_phone_mask = '138****0090' where id = ?",
                providerId);
        long fileId = asset("合作合同-全链路.pdf");
        long contractId = contract(providerId, "CREATED", null);
        String admin = bizOpsToken();

        // ① 签发（ADM-CT02）
        HttpResult issued = post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"%d","valid_from":"2026-10-01T00:00:00Z","valid_to":"2027-09-30T00:00:00Z",
                 "cooperation_mode":"API_RESALE","settlement_cycle":"MONTHLY","platform_fee_rate":0.05,
                 "currency":"USD","min_settlement_amount":100,"sign_deadline":"2026-10-15T00:00:00Z",
                 "terms":["合作期限 1 年","月结 30 天"]}
                """.formatted(fileId), admin);
        assertThat(issued.status()).as(issued.body()).isEqualTo(200);
        SchemaAssert.assertModel("contract", json(issued.data()));
        assertThat(issued.data().path("status").asText()).as(issued.body()).isEqualTo("PENDING_SIGN");
        assertThat(issued.data().path("file_id").asText()).isEqualTo(String.valueOf(fileId));
        assertThat(issued.data().path("terms").size()).isEqualTo(2);
        assertThat(issued.data().path("sign_deadline").asText()).isEqualTo("2026-10-15T00:00:00Z");
        Map<String, Object> afterIssue = jdbc.queryForMap("""
                select status, file_id, platform_fee_rate, min_settlement_amount, settlement_cycle,
                       cooperation_mode, valid_from, valid_to from aap_contract where id = ?
                """, contractId);
        assertThat(afterIssue.get("status")).isEqualTo("PENDING_SIGN");
        assertThat(afterIssue.get("file_id")).isEqualTo(fileId);
        assertThat(String.valueOf(afterIssue.get("platform_fee_rate"))).isEqualTo("0.0500");

        // ② 供应商签署（CON-04）：SMS + 6 位验证码
        HttpResult signed = post("/contracts/" + contractId + "/sign", """
                {"sign_method":"SMS","smsCode":"123456"}
                """, supplier);
        assertThat(signed.status()).as(signed.body()).isEqualTo(200);
        assertThat(signed.data().path("status").asText()).as(signed.body()).isEqualTo("SUPPLIER_SIGNED");
        assertThat(signed.data().path("sign_method").asText()).as(signed.body()).isEqualTo("SMS");
        assertThat(signed.data().path("signer_name").asText()).as(signed.body()).isEqualTo("张三");
        // R-48：只落脱敏手机号，明文不得进库
        assertThat(signed.data().path("signer_phone_masked").asText()).as(signed.body()).isEqualTo("138****0090");
        Map<String, Object> signRow = jdbc.queryForMap("""
                select signer_type, sign_method, tone from aap_contract_sign where contract_id = ?
                """, contractId);
        assertThat(signRow.get("signer_type")).isEqualTo("SUPPLIER");
        assertThat(signRow.get("tone")).isEqualTo("pending");

        HttpResult detailAfterSign = get("/contracts/" + contractId, supplier);
        assertThat(detailAfterSign.data().path("records").size()).as(detailAfterSign.body()).isEqualTo(1);

        // ③ 平台确认（ADM-CT03）
        HttpResult confirmed = post("/admin/contracts/" + contractId + "/confirm-sign", null, admin);
        assertThat(confirmed.status()).as(confirmed.body()).isEqualTo(200);
        assertThat(confirmed.data().path("status").asText()).as(confirmed.body()).isEqualTo("SIGNED");
        assertThat(confirmed.data().path("signed_at").asText()).as(confirmed.body()).isNotBlank();
        assertThat(jdbc.queryForObject("select signed_at from aap_contract where id = ?",
                OffsetDateTime.class, contractId)).isNotNull();
        HttpResult detailFinal = get("/contracts/" + contractId, supplier);
        assertThat(detailFinal.data().path("records").size()).as(detailFinal.body()).isEqualTo(2);
        assertThat(detailFinal.data().path("records").get(1).path("tone").asText()).isEqualTo("success");

        // ④ 终态不可再签署
        HttpResult again = post("/contracts/" + contractId + "/sign", """
                {"sign_method":"SEAL"}
                """, supplier);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");

        assertThat(jdbc.queryForList("select action from aap_audit_log where target_type = 'contract'",
                String.class)).contains("CONTRACT_SIGN");
    }

    @Test
    @DisplayName("CON-04 幂等：同 Idempotency-Key 重复签署只落一条签署记录，响应逐字一致")
    void signIsIdempotent() throws Exception {
        String supplier = token(PHONE);
        long contractId = contract(providerId(supplier), "PENDING_SIGN", asset("幂等合同.pdf"));
        Map<String, String> headers = Map.of("Idempotency-Key", "con04-" + contractId);

        HttpResult first = send("POST", "/contracts/" + contractId + "/sign", """
                {"sign_method":"SEAL"}
                """, supplier, headers);
        HttpResult second = send("POST", "/contracts/" + contractId + "/sign", """
                {"sign_method":"SEAL"}
                """, supplier, headers);
        assertThat(first.status()).as(first.body()).isEqualTo(200);
        assertThat(second.status()).as(second.body()).isEqualTo(200);
        // 幂等重放：响应体存在 jsonb 列（PostgreSQL 会重排键序与空白），故按 JSON 树比较而非逐字比较
        assertThat(second.json()).as("幂等重放必须回放首次响应").isEqualTo(first.json());
        assertThat(jdbc.queryForObject("select count(*) from aap_contract_sign where contract_id = ?",
                Long.class, contractId)).isEqualTo(1L);
    }

    @Test
    @DisplayName("CON-04 前置与入参：未签发（CREATED）→ 409 E-1701；sign_method/smsCode 非法 → 400 E-1001")
    void signValidatesStateAndInput() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        long notIssued = contract(providerId, "CREATED", null);

        HttpResult early = post("/contracts/" + notIssued + "/sign", """
                {"sign_method":"SEAL"}
                """, supplier);
        assertThat(early.status()).as(early.body()).isEqualTo(409);
        assertThat(early.code()).isEqualTo("E-1701");
        assertThat(jdbc.queryForObject("select status from aap_contract where id = ?",
                String.class, notIssued)).isEqualTo("CREATED");

        long pending = contract(providerId, "PENDING_SIGN", null);
        HttpResult badMethod = post("/contracts/" + pending + "/sign", """
                {"sign_method":"PEN"}
                """, supplier);
        assertThat(badMethod.status()).isEqualTo(400);
        assertThat(badMethod.code()).isEqualTo("E-1001");

        HttpResult missingCode = post("/contracts/" + pending + "/sign", """
                {"sign_method":"SMS"}
                """, supplier);
        assertThat(missingCode.status()).as(missingCode.body()).isEqualTo(400);
        assertThat(missingCode.code()).isEqualTo("E-1001");

        HttpResult badCode = post("/contracts/" + pending + "/sign", """
                {"sign_method":"SMS","smsCode":"12ab"}
                """, supplier);
        assertThat(badCode.status()).isEqualTo(400);
        assertThat(badCode.code()).isEqualTo("E-1001");

        // 三次失败都不得改状态/留痕
        assertThat(jdbc.queryForObject("select status from aap_contract where id = ?",
                String.class, pending)).isEqualTo("PENDING_SIGN");
        assertThat(jdbc.queryForObject("select count(*) from aap_contract_sign", Long.class)).isZero();
    }

    // ================================================================== ADM-CT01

    @Test
    @DisplayName("ADM-CT01 合同列表：管理端可跨供应商检索（供应商主体 403）")
    void adminListsAllContracts() throws Exception {
        String supplier = token(PHONE);
        long providerA = providerId(supplier);
        long providerB = providerId(token(OTHER_PHONE));
        contract(providerA, "CREATED", null);
        contract(providerB, "PENDING_SIGN", null);
        String admin = bizOpsToken();

        HttpResult list = get("/admin/contracts?page=1&pageSize=20", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("total").asLong()).as(list.body()).isEqualTo(2L);
        SchemaAssert.assertPageMeta(json(list.data()));
        SchemaAssert.assertModel("contract", json(list.data().path("items").get(0)));
        assertThat(get("/admin/contracts?status=PENDING_SIGN", admin).data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/contracts?status=SIGNED", admin).data().path("total").asLong()).isZero();

        assertThat(get("/admin/contracts", supplier).status()).isEqualTo(403);
        assertThat(get("/admin/contracts").status()).isEqualTo(401);
    }

    // ================================================================== ADM-CT02

    @Test
    @DisplayName("ADM-CT02 签发入参：file_id 必填且须存在、费率 ∈[0,1]、有效期先后 → 400 E-1001；重复签发 → 409 E-1601")
    void issueValidatesBody() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        long contractId = contract(providerId, "CREATED", null);
        long fileId = asset("签发校验.pdf");
        String admin = bizOpsToken();

        HttpResult noFile = post("/admin/contracts/" + contractId + "/issue", """
                {"terms":["缺文件"]}
                """, admin);
        assertThat(noFile.status()).as(noFile.body()).isEqualTo(400);
        assertThat(noFile.code()).isEqualTo("E-1001");

        HttpResult ghostFile = post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"888888888"}
                """, admin);
        assertThat(ghostFile.status()).as(ghostFile.body()).isEqualTo(400);
        assertThat(ghostFile.code()).isEqualTo("E-1001");

        HttpResult badRate = post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"%d","platform_fee_rate":1.5}
                """.formatted(fileId), admin);
        assertThat(badRate.status()).as(badRate.body()).isEqualTo(400);
        assertThat(badRate.code()).isEqualTo("E-1001");

        HttpResult badRange = post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"%d","valid_from":"2027-01-01T00:00:00Z","valid_to":"2026-01-01T00:00:00Z"}
                """.formatted(fileId), admin);
        assertThat(badRange.status()).as(badRange.body()).isEqualTo(400);
        assertThat(badRange.code()).isEqualTo("E-1001");

        // 权限：供应商主体不得签发
        assertThat(post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"%d"}
                """.formatted(fileId), supplier).status()).isEqualTo(403);
        assertThat(jdbc.queryForObject("select status from aap_contract where id = ?",
                String.class, contractId)).isEqualTo("CREATED");

        HttpResult ok = post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"%d","valid_from":"2026-10-01T00:00:00Z","valid_to":"2027-09-30T00:00:00Z"}
                """.formatted(fileId), superAdminToken());
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        assertThat(ok.data().path("status").asText()).as(ok.body()).isEqualTo("PENDING_SIGN");
        // 未提供的字段保持原值（签发是补全不是清空）：currency 省略仍为默认 USD，不得被写成 null
        assertThat(ok.data().path("currency").asText()).as(ok.body()).isEqualTo("USD");
        assertThat(jdbc.queryForObject("select currency from aap_contract where id = ?",
                String.class, contractId)).isEqualTo("USD");

        HttpResult twice = post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"%d"}
                """.formatted(fileId), admin);
        assertThat(twice.status()).isEqualTo(409);
        assertThat(twice.code()).isEqualTo("E-1601");
    }

    // ================================================================== ADM-CT03

    @Test
    @DisplayName("ADM-CT03 平台确认：仅 SUPPLIER_SIGNED 可确认；PENDING_SIGN 直接确认 → 409 E-1601")
    void confirmSignRequiresSupplierSignature() throws Exception {
        String supplier = token(PHONE);
        long providerId = providerId(supplier);
        String admin = bizOpsToken();

        long pending = contract(providerId, "PENDING_SIGN", null);
        HttpResult tooEarly = post("/admin/contracts/" + pending + "/confirm-sign", null, admin);
        assertThat(tooEarly.status()).as(tooEarly.body()).isEqualTo(409);
        assertThat(tooEarly.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select signed_at from aap_contract where id = ?",
                OffsetDateTime.class, pending)).isNull();

        long supplierSigned = contract(providerId, "SUPPLIER_SIGNED", null);
        HttpResult ok = post("/admin/contracts/" + supplierSigned + "/confirm-sign", null, admin);
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        assertThat(ok.data().path("status").asText()).as(ok.body()).isEqualTo("SIGNED");
        assertThat(jdbc.queryForObject("""
                select signer_type from aap_contract_sign where contract_id = ?
                """, String.class, supplierSigned)).isEqualTo("PLATFORM");

        assertThat(post("/admin/contracts/" + supplierSigned + "/confirm-sign", null, supplier).status())
                .isEqualTo(403);
    }
}
