package com.hioas.aap.credential;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HexFormat;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T05 · 测试凭证验收（接口 CRED-01…07；AC-07…13、AC-29/30/48）。
 *
 * <p>AC 出处：`.calicat/prd/21-验收标准.md`「凭证」与「安全」两组：
 * AC-07 提交加密落库 · AC-08 脱敏无明文 · AC-09 重复 E-1104 · AC-10 base_url 规范化 ·
 * AC-11 连通性失败 E-1101 · AC-12 鉴权 401 不重试 · AC-13 检测互斥 E-1301 ·
 * AC-29 SSRF 全拒 E-1201 · AC-30 明文访问审计 · AC-48 审计含 before/after。
 */
class CredentialContractTest extends ApiTestBase {

    private static final String PHONE = "13800000010";
    private static final String ADMIN_PHONE = "13900000009";
    private static final String RAW_KEY = "sk-test-abcdefghijklmnopqrstuvwxyz1234567890";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    private HttpServer upstream;
    private final AtomicInteger upstreamCalls = new AtomicInteger();

    @AfterEach
    void stopUpstream() {
        if (upstream != null) {
            upstream.stop(0);
            upstream = null;
        }
    }

    /** 启一个本地上游桩（仅测试）：/v1/models 返回 200 或 401。 */
    private String startUpstream(int status) throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/v1/models", exchange -> {
            upstreamCalls.incrementAndGet();
            byte[] body = status == 200
                    ? "{\"data\":[{\"id\":\"gpt-4o\"},{\"id\":\"claude-3-5-sonnet\"}]}".getBytes(StandardCharsets.UTF_8)
                    : "{\"error\":\"unauthorized\"}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(status, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        upstream.start();
        return "http://127.0.0.1:" + upstream.getAddress().getPort() + "/v1";
    }

    private String token() {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(PHONE));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(PHONE, code));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    /** 造一个超管令牌（管理端登录接口属 T14 范围，此处直接签发 + 落 jti 记录）。 */
    private String superAdminToken() throws Exception {
        Long accountId = 900001L;
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status,
                                            phone_hash, phone_masked)
                values (?, 'superadmin', 'x', '超管', 'SUPER_ADMIN', 'ACTIVE', ?, '139****0009')
                on conflict (id) do update set phone_hash = excluded.phone_hash
                """, accountId, sha256(ADMIN_PHONE));
        var issued = jwtService.issueAccessToken(accountId, "SUPER_ADMIN", "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private HttpResult createCredential(String token, String baseUrl, String apiKey, boolean primary) {
        return post("/credentials", """
                {
                  "alias":"主凭证",
                  "base_url":"%s",
                  "api_key":"%s",
                  "primary_flag":%s,
                  "declared_vendor":"OpenAI",
                  "declared_rpm":60,
                  "declared_context_window":128000,
                  "model_list":[{"model_name":"gpt-4o","context_window":128000,"rpm":60}]
                }
                """.formatted(baseUrl, apiKey, primary), token);
    }

    @Test
    @DisplayName("AC-07/08 创建凭证：api_key 密文落库（无明文）、指纹=SHA-256、响应仅回 sk-a***5678 形态")
    void createCredentialEncryptsAndMasks() throws Exception {
        String token = token();

        HttpResult res = createCredential(token, "https://api.example.com/v1/", RAW_KEY, true);

        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertModel("credential-detail", json(res.data()));
        assertThat(res.data().path("api_key_mask").asText()).isEqualTo("sk-t***7890");
        assertThat(res.body()).as("响应体不得出现 api_key 明文").doesNotContain(RAW_KEY);

        String cipher = jdbc.queryForObject("select api_key_cipher from aap_credential", String.class);
        assertThat(cipher).as("必须 AES-256-GCM 密文落库").isNotNull().doesNotContain(RAW_KEY);
        assertThat(jdbc.queryForObject("select api_key_fingerprint from aap_credential", String.class))
                .isEqualTo(sha256(RAW_KEY));
        assertThat(jdbc.queryForObject("select primary_flag from aap_credential", Boolean.class)).isTrue();
    }

    @Test
    @DisplayName("AC-10 base_url 规范化：去尾斜杠但保留 /v1")
    void baseUrlIsNormalized() {
        String token = token();

        assertThat(createCredential(token, "https://api.example.com/v1///", "sk-aaaabbbbccccdddd1111", true)
                .data().path("base_url").asText()).isEqualTo("https://api.example.com/v1");
        assertThat(createCredential(token, "https://api.example.com", "sk-aaaabbbbccccdddd2222", false)
                .data().path("base_url").asText()).isEqualTo("https://api.example.com");
        assertThat(createCredential(token, "HTTPS://API.Example.com/v1/", "sk-aaaabbbbccccdddd3333", false)
                .data().path("base_url").asText()).isEqualTo("https://api.example.com/v1");
    }

    @Test
    @DisplayName("AC-09 指纹重复：同供应商同 api_key 再提交 → 409 E-1104")
    void duplicateKeyConflicts() {
        String token = token();
        assertThat(createCredential(token, "https://api.example.com/v1", RAW_KEY, true).status()).isEqualTo(200);

        HttpResult dup = createCredential(token, "https://api.example.com/v1", RAW_KEY, false);
        assertThat(dup.status()).isEqualTo(409);
        assertThat(dup.code()).isEqualTo("E-1104");
        SchemaAssert.assertError(dup.body());
    }

    @Test
    @DisplayName("AC-29 SSRF：环回/私网/链路本地/元数据地址一律拒绝 → E-1201（不入库）")
    void ssrfAddressesRejected() {
        String token = token();
        String[] blocked = {
                "http://169.254.169.254/v1", "http://10.0.0.1/v1", "http://192.168.1.10/v1",
                "http://172.16.5.5/v1", "http://100.64.0.1/v1", "ftp://api.example.com/v1",
        };
        for (String url : blocked) {
            HttpResult res = createCredential(token, url, "sk-ssrf-" + url.hashCode() + "-key", false);
            assertThat(res.status()).as("地址 %s 必须被拒绝", url).isEqualTo(400);
            assertThat(res.code()).as("地址 %s 的错误码", url).isEqualTo("E-1201");
        }
        assertThat(jdbc.queryForObject("select count(*) from aap_credential", Long.class))
                .as("被拒的凭证不得入库").isZero();
    }

    @Test
    @DisplayName("AC-11 连通性失败 → 预检 E-1101；AC-12 上游 401 → E-1101 且**不重试**（只调用一次）")
    void precheckReportsFailureWithoutRetry() throws Exception {
        String token = token();
        String baseUrl = startUpstream(401);
        String credentialId = createCredential(token, baseUrl, "sk-precheck-aaaa1111bbbb2222", true)
                .data().path("id").asText();

        HttpResult res = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(res.status()).as(res.body()).isEqualTo(400);
        assertThat(res.code()).isEqualTo("E-1101");

        assertThat(upstreamCalls.get()).as("401 属鉴权失败，不重试").isEqualTo(1);
        assertThat(jdbc.queryForObject("select status from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo("PRECHECK_FAILED");
        assertThat(jdbc.queryForObject("select count(*) from aap_credential_precheck", Long.class)).isEqualTo(1L);
    }

    @Test
    @DisplayName("CRED-05/AC-13 预检通过 → 建检测任务入队并回 job_id；同凭证再次提交 → 409 E-1301")
    void precheckCreatesJobAndEnforcesMutualExclusion() throws Exception {
        String token = token();
        String baseUrl = startUpstream(200);
        String credentialId = createCredential(token, baseUrl, "sk-precheck-cccc3333dddd4444", true)
                .data().path("id").asText();

        HttpResult first = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(first.status()).as(first.body()).isEqualTo(200);
        SchemaAssert.assertModel("precheck-result", json(first.data()));
        assertThat(first.data().path("job_id").asText(null)).as("必须回检测任务号（前端据此跳进度页）").isNotBlank();
        assertThat(first.data().path("precheck_status").asText()).isEqualTo("PASSED");
        assertThat(jdbc.queryForObject("select status from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo("ACTIVE");
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_job where active_flag = true", Long.class))
                .isEqualTo(1L);

        // 同凭证再来一次：检测互斥
        HttpResult second = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(second.status()).isEqualTo(409);
        assertThat(second.code()).isEqualTo("E-1301");
    }

    @Test
    @DisplayName("CRED-06 最新预检记录可查（含连通性/鉴权标志与延迟）")
    void latestPrecheckIsQueryable() throws Exception {
        String token = token();
        String baseUrl = startUpstream(200);
        String credentialId = createCredential(token, baseUrl, "sk-precheck-eeee5555ffff6666", true)
                .data().path("id").asText();
        post("/credentials/" + credentialId + "/precheck", null, token);

        HttpResult res = get("/credentials/" + credentialId + "/precheck/latest", token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertModel("credential-precheck", json(res.data()));
        assertThat(res.data().path("status").asText()).isEqualTo("PASSED");
        assertThat(res.data().path("connectivity_ok").asBoolean()).isTrue();
        assertThat(res.data().path("auth_ok").asBoolean()).isTrue();
    }

    @Test
    @DisplayName("CRED-01/03 列表与详情：detection_status、latest_report_id、model_list 齐全且无明文")
    void listAndDetailHideSecret() {
        String token = token();
        String credentialId = createCredential(token, "https://api.example.com/v1", RAW_KEY, true)
                .data().path("id").asText();

        HttpResult list = get("/credentials", token);
        assertThat(list.status()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("list").size()).isEqualTo(1);
        assertThat(list.data().path("list").get(0).path("detection_status").asText()).isEqualTo("PENDING");
        assertThat(list.data().path("list").get(0).path("model_list").size()).isEqualTo(1);
        assertThat(list.body()).doesNotContain(RAW_KEY);

        HttpResult detail = get("/credentials/" + credentialId, token);
        assertThat(detail.status()).isEqualTo(200);
        SchemaAssert.assertModel("credential-detail", json(detail.data()));
        assertThat(detail.data().path("api_key_mask").asText()).isEqualTo("sk-t***7890");
        assertThat(detail.body()).doesNotContain(RAW_KEY);
    }

    @Test
    @DisplayName("CRED-04 轮换 api_key：指纹与掩码更新；旧明文不再可解出（密文被覆盖）")
    void rotateApiKey() throws Exception {
        String token = token();
        String credentialId = createCredential(token, "https://api.example.com/v1", RAW_KEY, true)
                .data().path("id").asText();
        String newKey = "sk-rotated-9999888877776666";

        HttpResult res = put("/credentials/" + credentialId, """
                {"alias":"主凭证（轮换）","base_url":"https://api.example.com/v1","api_key":"%s"}
                """.formatted(newKey), token);

        assertThat(res.status()).as(res.body()).isEqualTo(200);
        assertThat(res.data().path("api_key_mask").asText()).isEqualTo("sk-r***6666");
        assertThat(jdbc.queryForObject("select api_key_fingerprint from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo(sha256(newKey));
        assertThat(jdbc.queryForObject("select alias from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo("主凭证（轮换）");
    }

    @Test
    @DisplayName("C1 主凭证唯一：新凭证设 primary 时旧的主凭证自动降级（同供应商仅 1 条主凭证）")
    void onlyOnePrimaryCredential() {
        String token = token();
        createCredential(token, "https://api.example.com/v1", "sk-primary-aaaa1111bbbb", true);
        createCredential(token, "https://api.example.com/v1", "sk-primary-cccc2222dddd", true);

        Long primary = jdbc.queryForObject(
                "select count(*) from aap_credential where primary_flag = true", Long.class);
        assertThat(primary).isEqualTo(1L);
    }

    @Test
    @DisplayName("AC-30/48 明文访问：仅超管 + 短信二次验证可 reveal，返回明文一次并写 SENSITIVE 审计")
    void revealRequiresSuperAdminAndAudits() throws Exception {
        String providerToken = token();
        String credentialId = createCredential(providerToken, "https://api.example.com/v1", RAW_KEY, true)
                .data().path("id").asText();

        // 供应商自己也不能看明文
        HttpResult forbidden = post("/credentials/" + credentialId + "/reveal", """
                {"smsCode":"123456"}
                """, providerToken);
        assertThat(forbidden.status()).isEqualTo(403);
        assertThat(forbidden.code()).isEqualTo("E-1901");

        // 超管 + 二次验证短信码
        String admin = superAdminToken();
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(ADMIN_PHONE));
        String code = send.data().path("dev_code").asText();
        HttpResult revealed = post("/credentials/" + credentialId + "/reveal", """
                {"smsCode":"%s"}
                """.formatted(code), admin);

        assertThat(revealed.status()).as(revealed.body()).isEqualTo(200);
        SchemaAssert.assertModel("reveal-result", json(revealed.data()));
        assertThat(revealed.data().path("api_key").asText()).isEqualTo(RAW_KEY);

        String action = jdbc.queryForObject("select action from aap_audit_log order by id desc limit 1", String.class);
        String risk = jdbc.queryForObject("select risk_level from aap_audit_log order by id desc limit 1", String.class);
        assertThat(action).isEqualTo("CREDENTIAL_REVEAL");
        assertThat(risk).isEqualTo("SENSITIVE");
        assertThat(jdbc.queryForObject("select summary from aap_audit_log order by id desc limit 1", String.class))
                .as("审计摘要不得含明文").doesNotContain(RAW_KEY);
    }

    @Test
    @DisplayName("越权：他人凭证 id 不可读（404 E-1901 语义），未认证 401")
    void crossProviderAccessDenied() {
        String tokenA = token();
        String credentialId = createCredential(tokenA, "https://api.example.com/v1", RAW_KEY, true)
                .data().path("id").asText();

        // 另一个供应商账号
        HttpResult send = post("/auth/sms/send", """
                {"phone":"13800000011","captcha":"AB12"}
                """);
        String code = send.data().path("dev_code").asText();
        String tokenB = post("/auth/sms/login", """
                {"phone":"13800000011","smsCode":"%s"}
                """.formatted(code)).data().path("token").asText();

        HttpResult res = get("/credentials/" + credentialId, tokenB);
        assertThat(res.status()).isIn(403, 404);
        assertThat(res.code()).isIn("E-1901", "E-1406");

        assertThat(get("/credentials/" + credentialId).status()).isEqualTo(401);
    }

    private static String sha256(String value) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
    }
}
