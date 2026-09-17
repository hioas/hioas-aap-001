package com.hioas.aap.provider;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T04 · 供应商档案与资质验收（接口 PROV-01…05；AC-06）。
 *
 * <p>AC-06 出处：`.calicat/prd/21-验收标准.md`「供应商档案」。规则出处：R-47a（人工放行必填理由）、
 * 15-数据模型（uscc 唯一 → E-1104）、18-API（PUT /provider/profile 支持 Idempotency-Key 与 If-Match）。
 */
class ProviderContractTest extends ApiTestBase {

    private static final String PHONE = "13800000001";

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

    @Test
    @DisplayName("PROV-01 档案查询：返回主体信息与完整度；未填写字段为 null（不用 0 冒充）")
    void profileReturnsRegisteredProvider() throws Exception {
        String token = token();

        HttpResult res = get("/provider/profile", token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertModel("provider-profile", json(res.data()));
        assertThat(res.data().path("provider_code").asText()).startsWith("AAP-P-");
        assertThat(res.data().path("status").asText()).isEqualTo("PENDING_CREDENTIAL");
        assertThat(res.data().path("company_name").isNull()).isTrue();
        assertThat(res.data().path("completeness").asInt()).isZero();
    }

    @Test
    @DisplayName("PROV-02 保存档案：写入成功 + 完整度按必填项计算 + 响应含联系人与 updated_at")
    void updateProfileComputesCompleteness() throws Exception {
        String token = token();

        HttpResult res = put("/provider/profile", """
                {
                  "short_name":"示例科技",
                  "company_name":"示例科技（上海）有限公司",
                  "uscc":"91310115MA1K3XYZ12",
                  "industry_category":"ORIGINAL",
                  "province":"上海市","city":"上海市","address":"浦东新区示例路 1 号",
                  "contact_name":"张三","contact_title":"技术负责人",
                  "contact_phone":"13900000002","contact_email":"zhang@example.com",
                  "company_intro":"专注大模型推理服务",
                  "recheck_interval_days":30
                }
                """, token);

        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertModel("provider-profile", json(res.data()));
        assertThat(res.data().path("company_name").asText()).isEqualTo("示例科技（上海）有限公司");
        assertThat(res.data().path("uscc").asText()).isEqualTo("91310115MA1K3XYZ12");
        assertThat(res.data().path("contact").path("phone_masked").asText()).isEqualTo("139****0002");
        assertThat(res.data().path("completeness").asInt()).isGreaterThan(50);
        assertThat(res.data().path("updated_at").asText(null)).isNotBlank();

        // 落库校验：手机号密文 + mask + hash 三件套（R-48）
        String cipher = jdbc.queryForObject("select contact_phone_cipher from aap_provider", String.class);
        assertThat(cipher).isNotNull().doesNotContain("13900000002");
        assertThat(jdbc.queryForObject("select contact_phone_mask from aap_provider", String.class))
                .isEqualTo("139****0002");
    }

    @Test
    @DisplayName("PROV-02 校验：uscc 非 18 位 → 400 E-1001；手机号非法 → 400 E-1001（并定位字段）")
    void updateProfileValidatesFields() {
        String token = token();

        HttpResult badUscc = put("/provider/profile", """
                {"company_name":"示例公司","uscc":"123"}
                """, token);
        assertThat(badUscc.status()).isEqualTo(400);
        assertThat(badUscc.code()).isEqualTo("E-1001");
        assertThat(badUscc.json().path("details").toString()).contains("uscc");

        HttpResult badPhone = put("/provider/profile", """
                {"company_name":"示例公司","contact_phone":"123456"}
                """, token);
        assertThat(badPhone.status()).isEqualTo(400);
        assertThat(badPhone.json().path("details").toString()).contains("contact_phone");
    }

    @Test
    @DisplayName("PROV-02 唯一性冲突：uscc 与其他供应商重复 → 409 E-1104")
    void duplicateUsccConflicts() throws Exception {
        String tokenA = token();
        assertThat(put("/provider/profile", """
                {"company_name":"甲公司","uscc":"91310115MA1K3XYZ12"}
                """, tokenA).status()).isEqualTo(200);

        // 第二个供应商（另一手机号）
        HttpResult send = post("/auth/sms/send", """
                {"phone":"13800000002","captcha":"AB12"}
                """);
        String code = send.data().path("dev_code").asText();
        String tokenB = post("/auth/sms/login", """
                {"phone":"13800000002","smsCode":"%s"}
                """.formatted(code)).data().path("token").asText();

        HttpResult conflict = put("/provider/profile", """
                {"company_name":"乙公司","uscc":"91310115MA1K3XYZ12"}
                """, tokenB);
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(conflict.code()).isEqualTo("E-1104");
    }

    @Test
    @DisplayName("PROV-02 幂等：同一 Idempotency-Key 重复提交只落一次库，第二次返回首次响应")
    void updateProfileIsIdempotent() throws Exception {
        String token = token();
        String body = """
                {"company_name":"幂等公司","uscc":"91310115MA1K3XYZ34"}
                """;

        HttpResult first = sendWithIdempotency("PUT", "/provider/profile", body, token, "prov-idem-key-0001");
        assertThat(first.status()).as(first.body()).isEqualTo(200);
        Long updatedAt1 = jdbc.queryForObject("select version from aap_provider", Long.class);

        HttpResult second = sendWithIdempotency("PUT", "/provider/profile", body, token, "prov-idem-key-0001");
        assertThat(second.status()).isEqualTo(200);
        assertThat(second.json()).as("重放必须返回首次响应（语义相等）").isEqualTo(first.json());
        assertThat(second.traceId()).as("重放沿用首次 traceId（同一次结果）").isEqualTo(first.traceId());
        assertThat(jdbc.queryForObject("select version from aap_provider", Long.class))
                .as("重放不得再写一次库").isEqualTo(updatedAt1);
    }

    @Test
    @DisplayName("PROV-02 乐观锁：If-Match 过期 → 409 E-1601（不覆盖他人改动）")
    void staleIfMatchRejected() throws Exception {
        String token = token();
        String body = """
                {"company_name":"并发公司","uscc":"91310115MA1K3XYZ56"}
                """;
        HttpResult first = put("/provider/profile", body, token);
        assertThat(first.status()).isEqualTo(200);
        String etag = first.data().path("etag").asText(null);
        assertThat(etag).as("响应必须带 etag（=version）供 If-Match 使用").isNotNull();

        // 别人又改了一次 → 版本前进
        assertThat(put("/provider/profile", """
                {"company_name":"并发公司 v2"}
                """, token).status()).isEqualTo(200);

        HttpResult stale = sendWithIfMatch("PUT", "/provider/profile", """
                {"company_name":"过期写入"}
                """, token, etag);
        assertThat(stale.status()).isEqualTo(409);
        assertThat(stale.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select company_name from aap_provider", String.class))
                .isEqualTo("并发公司 v2");
    }

    @Test
    @DisplayName("PROV-03/04/05 资质：登记 → 列表可见 → 逻辑删除后不可见")
    void qualificationLifecycle() {
        String token = token();

        HttpResult created = post("/provider/qualifications", """
                {"category":"BUSINESS_LICENSE","file_name":"营业执照.pdf","file_size":204800,"content_type":"application/pdf"}
                """, token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        SchemaAssert.assertModel("qualification-created", json(created.data()));
        String id = created.data().path("id").asText();
        assertThat(id).isNotBlank();

        HttpResult list = get("/provider/qualifications", token);
        assertThat(list.status()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("items").size()).isEqualTo(1);
        assertThat(list.data().path("items").get(0).path("file_name").asText()).isEqualTo("营业执照.pdf");

        HttpResult deleted = delete("/provider/qualifications/" + id, token);
        assertThat(deleted.status()).isEqualTo(200);
        assertThat(get("/provider/qualifications", token).data().path("items").size()).isZero();
        assertThat(jdbc.queryForObject("select count(*) from aap_provider_qualification", Long.class))
                .as("逻辑删除：行仍保留").isEqualTo(1L);
    }

    @Test
    @DisplayName("资质超限校验：超过 10MB 或非法扩展名 → 400 E-1001")
    void qualificationValidatesFile() {
        String token = token();

        HttpResult tooBig = post("/provider/qualifications", """
                {"category":"BUSINESS_LICENSE","file_name":"营业执照.pdf","file_size":11534336}
                """, token);
        assertThat(tooBig.status()).isEqualTo(400);
        assertThat(tooBig.code()).isEqualTo("E-1001");

        HttpResult badType = post("/provider/qualifications", """
                {"category":"BUSINESS_LICENSE","file_name":"营业执照.exe","file_size":1024}
                """, token);
        assertThat(badType.status()).isEqualTo(400);
        assertThat(badType.code()).isEqualTo("E-1001");
    }

    /** 带 Idempotency-Key 的原始请求（ApiTestBase 未覆盖该头）。 */
    private HttpResult sendWithIdempotency(String method, String path, String body, String token, String key) {
        return sendWithHeader(method, path, body, token, "Idempotency-Key", key);
    }

    private HttpResult sendWithIfMatch(String method, String path, String body, String token, String etag) {
        return sendWithHeader(method, path, body, token, "If-Match", etag);
    }

    private HttpResult sendWithHeader(String method, String path, String body, String token,
                                      String headerName, String headerValue) {
        var builder = java.net.http.HttpRequest.newBuilder()
                .uri(java.net.URI.create(baseUrl() + "/api/v1" + path))
                .header("Content-Type", "application/json")
                .header(headerName, headerValue)
                .header("Authorization", "Bearer " + token);
        builder.method(method, body == null ? java.net.http.HttpRequest.BodyPublishers.noBody()
                : java.net.http.HttpRequest.BodyPublishers.ofString(body, java.nio.charset.StandardCharsets.UTF_8));
        try {
            var res = java.net.http.HttpClient.newHttpClient().send(builder.build(),
                    java.net.http.HttpResponse.BodyHandlers.ofString(java.nio.charset.StandardCharsets.UTF_8));
            return new HttpResult(res.statusCode(), res.headers(), res.body());
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @Test
    @DisplayName("权限：未认证访问 /provider/profile → 401 E-1902")
    void profileRequiresAuth() {
        HttpResult res = get("/provider/profile");
        assertThat(res.status()).isEqualTo(401);
        assertThat(res.code()).isEqualTo("E-1902");
    }
}
