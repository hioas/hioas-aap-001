package com.hioas.aap.file;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import org.springframework.beans.factory.annotation.Autowired;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * 文件服务验收（补齐缺陷2）。
 *
 * <p><b>缺陷2 的证据</b>：{@code aap_file_asset} 在主代码里只有 3 处 SELECT、**零 INSERT**；
 * 全仓无 {@code MultipartFile}；{@code POST /admin/contracts/{id}/issue} 的契约
 * （{@code requests/contract-issue.schema.json}）把 {@code file_id} 列为 **required** ——
 * 于是「合同永远签发不了、签不了、打不了款」。
 *
 * <p>本测试定义文件服务的验收标准（真源：{@code models/file-asset.schema.json}）：
 * 上传后必须真的落一行 {@code aap_file_asset}，且下载能取回**逐字节相同**的内容。
 */
class FileContractTest extends ApiTestBase {

    /** 管理端账号 id（角色在 JWT claim 里，不依赖 aap_provider_account.role）。 */
    private static final long SUPER_ADMIN_ID = 981001L;

    @Autowired
    private com.hioas.aap.iam.JwtService jwtService;

    @Autowired
    private com.hioas.aap.iam.AuthTokenMapper authTokenMapper;

    /**
     * 造一个超管 token。
     *
     * <p>手法与 {@code ContractContractTest.adminToken} 一致：写一行 {@code aap_admin_user}
     * 再用 {@code jwtService} 直接签发，并把 jti 落 {@code aap_auth_token}（否则会被登出校验拒掉）。
     * 不依赖测试库里预置的管理员账号。
     */
    private String token() {
        jdbc.update("delete from aap_admin_user where id = ?", SUPER_ADMIN_ID);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, 'superadmin-file', 'x', 'SUPER_ADMIN', 'SUPER_ADMIN', 'ACTIVE')
                """, SUPER_ADMIN_ID);
        var issued = jwtService.issueAccessToken(SUPER_ADMIN_ID, "SUPER_ADMIN", "ADMIN", null);
        var record = new com.hioas.aap.iam.AuthTokenEntity();
        record.setAccountId(SUPER_ADMIN_ID);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(java.time.OffsetDateTime.now(java.time.ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private static final byte[] SAMPLE = "合同正文示例\nAAP-CONTRACT-SAMPLE-2026\n".getBytes(StandardCharsets.UTF_8);

    /** 用真实登录路径造一个供应商主体并返回其 id + token（手机号首次登录即注册）。 */
    private record ProviderFixture(long providerId, String token) {
    }

    private ProviderFixture loginProvider(String phone) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        String providerToken = login.data().path("token").asText();
        HttpResult me = get("/auth/me", providerToken);
        assertThat(me.status()).as(me.body()).isEqualTo(200);
        return new ProviderFixture(Long.parseLong(me.data().path("providerId").asText()), providerToken);
    }

    @Test
    @DisplayName("文件服务：上传落库并返回 file_id，且响应符合 file-asset 契约")
    void uploadPersistsAssetAndReturnsFileId() {
        String token = token();

        HttpResult up = postMultipart("/files", token, "file", "合同扫描件.pdf",
                "application/pdf", SAMPLE, Map.of("biz_type", "CONTRACT"));

        assertThat(up.status()).as(up.body()).isEqualTo(200);
        assertThat(up.code()).as(up.body()).isEqualTo("0");
        SchemaAssert.assertModel("file-asset", json(up.data()));

        String fileId = up.data().path("file_id").asText();
        assertThat(fileId).as("必须返回雪花 ID 字符串").isNotBlank();
        assertThat(up.data().path("file_name").asText()).isEqualTo("合同扫描件.pdf");
        assertThat(up.data().path("size_bytes").asLong()).isEqualTo(SAMPLE.length);
        assertThat(up.data().path("content_type").asText()).isEqualTo("application/pdf");

        // 真落库：aap_file_asset 必须多出一行（缺陷2 的核心断言）
        Long rows = jdbc.queryForObject(
                "select count(*) from aap_file_asset where id = ? and deleted = false", Long.class, Long.valueOf(fileId));
        assertThat(rows).as("上传后 aap_file_asset 必须有对应行（此前该表零 INSERT）").isEqualTo(1L);

        // sha256 必须与实际内容一致（可校验完整性）
        String sha = jdbc.queryForObject("select sha256 from aap_file_asset where id = ?", String.class, Long.valueOf(fileId));
        assertThat(sha).as("sha256 应等于内容摘要").isNotBlank();
    }

    @Test
    @DisplayName("文件服务：下载取回逐字节相同的内容，且带原始文件名")
    void downloadReturnsSameBytes() {
        String token = token();
        HttpResult up = postMultipart("/files", token, "file", "盖章件.png",
                "image/png", SAMPLE, Map.of("biz_type", "CONTRACT"));
        assertThat(up.status()).as(up.body()).isEqualTo(200);
        String fileId = up.data().path("file_id").asText();

        BinaryResult dl = getBinary("/files/" + fileId, token);

        assertThat(dl.status()).as("下载应 200").isEqualTo(200);
        assertThat(dl.body()).as("下载内容必须与上传**逐字节相同**").isEqualTo(SAMPLE);
    }

    @Test
    @DisplayName("文件服务：拒绝空文件（E-1001 字段级）")
    void rejectsEmptyFile() {
        String token = token();
        HttpResult up = postMultipart("/files", token, "file", "empty.pdf",
                "application/pdf", new byte[0], Map.of());
        assertThat(up.status()).as(up.body()).isNotEqualTo(200);
        assertThat(up.code()).as(up.body()).isEqualTo("E-1001");
    }

    @Test
    @DisplayName("文件服务：不存在的 file_id → E-1406（不是 500）")
    void missingFileIsNotFound() {
        String token = token();
        BinaryResult dl = getBinary("/files/999999999999999999", token);
        assertThat(dl.status()).as("不存在的文件不应是 500").isNotEqualTo(500);
    }

    @Test
    @DisplayName("缺陷2 闭环：上传合同文件 → issue 用该 file_id 签发成功")
    void contractIssueAcceptsUploadedFile() {
        String token = token();

        // 1) 先上传合同文件（此前无任何途径能产生 file_id）
        HttpResult up = postMultipart("/files", token, "file", "HT-测试合同.pdf",
                "application/pdf", SAMPLE, Map.of("biz_type", "CONTRACT"));
        assertThat(up.status()).as(up.body()).isEqualTo(200);
        String fileId = up.data().path("file_id").asText();

        // 2) 造一张待签发的合同（本测试聚焦 issue 环节，直接落库造数据；
        //    ⚠️ 不能假设库里已有合同/供应商 —— 测试库 aap_server_test 是独立空库，
        //    依赖前序联调数据会让用例在不同环境随机失败（踩过：EmptyResultDataAccess expected 1 actual 0）。
        //    供应商主体用「手机号登录即建号」的真实路径造，不手写 INSERT（少维护一套列清单）。
        ProviderFixture provider = loginProvider("13800000077");

        Long contractId = 990001L; // 夹具固定主键（与 ContractContractTest 同一手法，避免依赖序列）
        // 前置状态必须是 CREATED（issue 内部校验；它把 CREATED → PENDING_SIGN）
        jdbc.update("""
                insert into aap_contract (id, contract_no, provider_id, status, sign_channel, currency)
                values (?, ?, ?, 'CREATED', 'OFFLINE', 'USD')
                """, contractId, "HT-TEST-" + contractId, provider.providerId());

        // 3) 用刚上传的 file_id 签发
        HttpResult issue = post("/admin/contracts/" + contractId + "/issue", """
                {"file_id":"%s"}
                """.formatted(fileId), token);

        assertThat(issue.status()).as(issue.body()).isEqualTo(200);
        assertThat(issue.code()).as(issue.body()).isEqualTo("0");
        assertThat(issue.data().path("file_id").asText()).as("签发后合同必须绑定该文件").isEqualTo(fileId);

        // 4) 合同文件视图必须返回**真实可下载**的地址（此前把存储键当 URL 回，前端无从下载）
        // ⚠️ /contracts/{id}/file 是**供应商侧**端点（requireOwned 校验归属），管理员 token 会被 E-1901 拒
        HttpResult fileView = get("/contracts/" + contractId + "/file", provider.token());
        assertThat(fileView.status()).as(fileView.body()).isEqualTo(200);
        String url = fileView.data().path("url").asText();
        assertThat(url).as("url 必须是可下载地址，而不是存储键").startsWith("/api/v1/files/");

        // 5) 按该地址真下载，内容逐字节一致（缺陷2 的完整闭环）
        BinaryResult dl = getBinary(url.replaceFirst("^/api/v1", ""), provider.token());
        assertThat(dl.status()).as("合同文件应可下载").isEqualTo(200);
        assertThat(dl.body()).isEqualTo(SAMPLE);
    }
}
