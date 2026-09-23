package com.hioas.aap.file;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * S-1 越权修复：{@code GET /files/{id}} 必须有归属校验。
 *
 * <p><b>修复前的缺陷（代码层已确证）</b>：{@code aap_file_asset} 无归属列，下载端点只做「按 id 取文件」，
 * 而 {@code /files/**} 只要求「已登录」。于是供应商 A 只要拿到供应商 B 的 {@code file_id}
 * （合同/资质在多个流程里以 file_id 流转），就能下载 B 的合同、资质原件 —— 典型 IDOR。
 *
 * <p>修复后的规则（真源 {@code FileService#loadForDownload}）：
 * 管理端可下载全部；供应商只能下载自己上传的；无归属文件（管理端上传的平台文件）对所有登录方可见。
 */
class FileOwnershipTest extends ApiTestBase {

    private static final long ADMIN_ID = 982001L;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    private static final byte[] CONTRACT = "甲方/乙方合同正文（供应商私密件）\nS-1-FIXTURE\n"
            .getBytes(StandardCharsets.UTF_8);

    private record ProviderFixture(long providerId, String token) {
    }

    /** 真实登录路径造供应商主体（手机号首次登录即注册）。 */
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

    /** 超管 token（角色在 JWT claim，jti 必须落库否则被登出校验拒掉）。 */
    private String adminToken() {
        jdbc.update("delete from aap_admin_user where id = ?", ADMIN_ID);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, 'superadmin-file-owner', 'x', 'SUPER_ADMIN', 'SUPER_ADMIN', 'ACTIVE')
                """, ADMIN_ID);
        var issued = jwtService.issueAccessToken(ADMIN_ID, "SUPER_ADMIN", "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(ADMIN_ID);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String uploadAs(String token) {
        HttpResult up = postMultipart("/files", token, "file", "合同扫描件.pdf",
                "application/pdf", CONTRACT, Map.of("biz_type", "CONTRACT"));
        assertThat(up.status()).as(up.body()).isEqualTo(200);
        return up.data().path("file_id").asText();
    }

    private static String textOf(ApiTestBase.BinaryResult result) {
        return new String(result.body(), StandardCharsets.UTF_8);
    }

    @Test
    @DisplayName("S-1 供应商不能下载他人文件（403 E-1901）；自己可下；管理端可审阅全部")
    void crossProviderDownloadIsDenied() {
        ProviderFixture a = loginProvider("13800000050");
        ProviderFixture b = loginProvider("13800000051");
        String fileId = uploadAs(a.token());

        // 归属必须真的落库（而不是靠推断）
        assertThat(jdbc.queryForObject("select owner_provider_id from aap_file_asset where id = ?::bigint",
                Long.class, fileId)).isEqualTo(a.providerId());

        // 自己下载：逐字节一致（不能因为加了校验把正常流程挡掉）
        ApiTestBase.BinaryResult own = getBinary("/files/" + fileId, a.token());
        assertThat(own.status()).as("本人下载必须成功").isEqualTo(200);
        assertThat(own.body()).isEqualTo(CONTRACT);

        // 另一个供应商：修复前这里是 200（拿到全部字节），现在是 403
        ApiTestBase.BinaryResult other = getBinary("/files/" + fileId, b.token());
        assertThat(other.status()).as("他人文件必须 403，而不是 200").isEqualTo(403);
        assertThat(textOf(other)).contains("E-1901");
        assertThat(other.body()).as("越权响应不得夹带文件内容").isNotEqualTo(CONTRACT);

        // 管理端：要审供应商材料，必须能下
        ApiTestBase.BinaryResult admin = getBinary("/files/" + fileId, adminToken());
        assertThat(admin.status()).as("管理端必须能下载供应商文件").isEqualTo(200);
        assertThat(admin.body()).isEqualTo(CONTRACT);

        // 未认证：401（不是 200）
        assertThat(getBinary("/files/" + fileId, null).status()).isEqualTo(401);
    }

    @Test
    @DisplayName("S-1 管理端上传的平台文件（无归属）对所有登录方可见，否则「平台签发→供应商下载」会断")
    void adminUploadedFileStaysAccessible() {
        ProviderFixture a = loginProvider("13800000052");
        String fileId = uploadAs(adminToken());

        assertThat(jdbc.queryForObject("select owner_provider_id from aap_file_asset where id = ?::bigint",
                Long.class, fileId)).as("管理端上传 = 无归属").isNull();

        ApiTestBase.BinaryResult dl = getBinary("/files/" + fileId, a.token());
        assertThat(dl.status()).isEqualTo(200);
        assertThat(dl.body()).isEqualTo(CONTRACT);
    }
}
