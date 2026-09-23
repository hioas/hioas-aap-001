package com.hioas.aap.detection;

import static org.assertj.core.api.Assertions.assertThat;

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
 * T14 · 管理端检测任务列表（**新增端点 ADM-DET01**）。
 *
 * <p>背景（2026-09-23 运行态实测）：「检测中心」页拿不到任何任务数据 —— 管理端相关的检测端点只有
 * {@code POST /detection-jobs/{jobId}/release}（按 id 放行），{@code DET-01…05} 全部限供应商本人 →
 * KPI 只能显「未知」、任务表为空、**人工放行需手输任务 ID**（运营无从得知）→ 放行实际不可用，
 * 而它是凭证拿到 PASS（进而报价）的唯一路径。
 *
 * <p>锁定口径：
 * <ul>
 *   <li>列表跨供应商、按创建时间倒序、分页元数据符合公共 schema；</li>
 *   <li>管理端附加字段 {@code provider_name}/{@code credential_alias} 必须带上（否则运营无法辨认单据）；</li>
 *   <li>过滤 status/credentialId/providerId 生效；</li>
 *   <li>权限：TECH_OPS + SUPER_ADMIN；BIZ_OPERATOR 与供应商一律 403；未认证 401。</li>
 * </ul>
 */
class AdminDetectionListTest extends ApiTestBase {

    private static final long TECH_ID = 963001L;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    private long seq = 996000L;

    private long nextId() {
        return ++seq;
    }

    private String adminToken(long id, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", id);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, '!', ?, ?, 'ACTIVE')
                """, id, "ops-" + id, "ops-" + id, role);
        var issued = jwtService.issueAccessToken(id, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(id);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

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

    /** 造一条检测任务（含供应商 + 凭证，供别名/名称断言）。 */
    private long seedJob(String providerCompany, String credentialAlias, String status) {
        long providerId = nextId();
        long credentialId = nextId();
        long jobId = nextId();
        jdbc.update("""
                insert into aap_provider (id, provider_code, company_name, status, created_at, updated_at,
                    deleted, version)
                values (?, ?, ?, 'ACTIVE', now(), now(), false, 0)
                """, providerId, "AAP-P-T" + providerId, providerCompany);
        jdbc.update("""
                insert into aap_credential (id, provider_id, alias, base_url, api_key_cipher, api_key_mask,
                    api_key_fingerprint, model_list, status, detection_status, created_at, updated_at,
                    deleted, version)
                values (?, ?, ?, 'http://127.0.0.1:9911/v1', 'x', 'sk-***test', ?, '[]'::jsonb, 'ACTIVE',
                    'RUNNING', now(), now(), false, 0)
                """, credentialId, providerId, credentialAlias, "f".repeat(64));
        jdbc.update("""
                insert into aap_detection_job (id, job_no, provider_id, credential_id, status, trigger_type,
                    attempt_count, challenge_verified, progress_percent, progress_finished, progress_total,
                    created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, 'MANUAL', 0, false, 0, 0, 8, now(), now(), false, 0)
                """, jobId, "DJ-TEST-" + jobId, providerId, credentialId, status);
        return jobId;
    }

    @Test
    @DisplayName("ADM-DET01 任务列表：跨供应商可读、带供应商名/凭证别名、分页合规、filter 生效")
    void adminListsDetectionJobs() {
        long runningJob = seedJob("检测列表测试公司", "列表用凭证-A", "RUNNING");
        long queuedJob = seedJob("检测列表测试公司", "列表用凭证-B", "QUEUED");
        String tech = adminToken(TECH_ID, "TECH_OPS");

        HttpResult list = get("/admin/detection-jobs?page=1&pageSize=20", tech);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).isGreaterThanOrEqualTo(2L);
        SchemaAssert.assertModel("detection-job", json(list.data().path("items").get(0)));

        var row = list.data().path("items").get(0);
        assertThat(row.path("provider_name").asText()).isEqualTo("检测列表测试公司");
        assertThat(row.path("credential_alias").asText()).startsWith("列表用凭证-");

        // 过滤生效（这两条是刚造的，用 credential 过滤最精确）
        long target = runningJob;
        var created = list.data().path("items");
        String credentialId = null;
        for (int i = 0; i < created.size(); i++) {
            if (String.valueOf(target).equals(created.get(i).path("id").asText())) {
                credentialId = created.get(i).path("credential_id").asText();
            }
        }
        assertThat(credentialId).as("刚造的任务必须在列表里").isNotNull();
        HttpResult filtered = get("/admin/detection-jobs?credentialId=" + credentialId, tech);
        assertThat(filtered.data().path("total").asLong()).isEqualTo(1L);

        HttpResult byStatus = get("/admin/detection-jobs?status=QUEUED&page=1&pageSize=50", tech);
        for (var item : byStatus.data().path("items")) {
            assertThat(item.path("status").asText()).isEqualTo("QUEUED");
        }

        // 响应里不得出现 api_key 明文/密文
        assertThat(list.body()).doesNotContain("api_key_cipher");
    }

    @Test
    @DisplayName("ADM-DET01 权限：TECH_OPS/SUPER_ADMIN 可用；BIZ_OPERATOR 与供应商 403、未认证 401")
    void permissions() {
        seedJob("权限测试公司", "权限用凭证", "COMPLETED");
        String biz = adminToken(nextId(), "BIZ_OPERATOR");
        String tech = adminToken(nextId(), "TECH_OPS");
        String superAdmin = adminToken(nextId(), "SUPER_ADMIN");

        assertThat(get("/admin/detection-jobs", biz).status()).as("运营商务不参与检测").isEqualTo(403);
        assertThat(get("/admin/detection-jobs", tech).status()).isEqualTo(200);
        assertThat(get("/admin/detection-jobs", superAdmin).status()).isEqualTo(200);
        assertThat(get("/admin/detection-jobs", supplierToken("13800000240")).status()).isEqualTo(403);
        assertThat(get("/admin/detection-jobs").status()).as("未认证").isEqualTo(401);
    }
}
