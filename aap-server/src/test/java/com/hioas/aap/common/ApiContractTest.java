package com.hioas.aap.common;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T01 · 统一契约的**端到端**验证（真实 HTTP + JSON Schema 校验真实响应体）。
 */
class ApiContractTest extends ApiTestBase {

    @Test
    @DisplayName("成功响应：HTTP 200 + code=0 + 包体符合 envelope 契约 + X-Trace-Id 与包体 traceId 一致")
    void successEnvelopeMatchesContract() {
        HttpResult res = get("/__test/echo");

        assertThat(res.status()).isEqualTo(200);
        assertThat(res.code()).isEqualTo("0");
        SchemaAssert.assertEnvelope(res.body());
        assertThat(res.traceId()).isNotBlank();
        assertThat(res.header("X-Trace-Id")).isEqualTo(res.traceId());
        assertThat(res.data().path("hello").asText()).isEqualTo("world");
    }

    @Test
    @DisplayName("data 为空时仍返回 null 字段而不是省略（前端做形状校验）")
    void emptyDataStillPresent() {
        HttpResult res = get("/__test/empty");
        assertThat(res.status()).isEqualTo(200);
        assertThat(res.json().has("data")).isTrue();
        assertThat(res.json().get("data").isNull()).isTrue();
    }

    @Test
    @DisplayName("业务失败：HTTP 与 code 对应（E-1001→400，E-1301→409，E-1902→401），body 符合 error 契约")
    void businessErrorsMatchContract() {
        HttpResult bad = get("/__test/business-error?code=E-1001");
        assertThat(bad.status()).isEqualTo(400);
        assertThat(bad.code()).isEqualTo("E-1001");
        SchemaAssert.assertError(bad.body());

        HttpResult conflict = get("/__test/business-error?code=E-1301");
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(conflict.code()).isEqualTo("E-1301");

        HttpResult unauth = get("/__test/business-error?code=E-1902");
        assertThat(unauth.status()).isEqualTo(401);
        assertThat(unauth.code()).isEqualTo("E-1902");
    }

    @Test
    @DisplayName("参数校验失败：400 + E-1001 + details 定位字段（不返回 500）")
    void validationFailureMapsToE1001WithFieldDetails() {
        HttpResult res = post("/__test/validate", """
                {"phone":"","smsCode":"12"}
                """, null);

        assertThat(res.status()).isEqualTo(400);
        assertThat(res.code()).isEqualTo("E-1001");
        SchemaAssert.assertError(res.body());
        assertThat(res.json().path("details").isArray()).isTrue();
        java.util.List<String> fields = new java.util.ArrayList<>();
        for (var node : res.json().path("details")) {
            fields.add(node.path("field").asText());
        }
        assertThat(fields).contains("phone", "smsCode");
    }

    @Test
    @DisplayName("未捕获异常：500 + E-2001，且**不泄漏堆栈与敏感内容**（日志里才有根因）")
    void unhandledExceptionBecomesE2001WithoutLeaking() {
        HttpResult res = get("/__test/boom");

        assertThat(res.status()).isEqualTo(500);
        assertThat(res.code()).isEqualTo("E-2001");
        assertThat(res.message()).doesNotContain("sk-secret-should-not-leak");
        assertThat(res.body()).doesNotContain("IllegalStateException");
        assertThat(res.body()).doesNotContain("at com.hioas");
        SchemaAssert.assertError(res.body());
    }

    @Test
    @DisplayName("非法 JSON 体：400 + E-1001（而不是 500）")
    void malformedJsonIsBadRequest() {
        HttpResult res = post("/__test/validate", "{not-json", null);
        assertThat(res.status()).isEqualTo(400);
        assertThat(res.code()).isEqualTo("E-1001");
    }

    @Test
    @DisplayName("不存在的路由：404 + E-1406，包体仍是统一包体（不是 whitelabel 页面）")
    void unknownRouteReturnsUnifiedEnvelope() {
        HttpResult res = get("/__test/not-exists");
        assertThat(res.status()).isEqualTo(404);
        assertThat(res.code()).isEqualTo("E-1406");
        SchemaAssert.assertEnvelope(res.body());
    }

    @Test
    @DisplayName("traceId 透传：客户端带 X-Trace-Id 时沿用（跨服务链路不截断）")
    void clientTraceIdIsPropagated() {
        HttpResult res = send("GET", "/__test/echo", null, null);
        assertThat(res.header("X-Trace-Id")).isNotBlank();

        var withHeader = java.net.http.HttpRequest.newBuilder()
                .uri(java.net.URI.create(baseUrl() + "/api/v1/__test/echo"))
                .header("X-Trace-Id", "client-supplied-trace-0001")
                .GET().build();
        try {
            var response = java.net.http.HttpClient.newHttpClient()
                    .send(withHeader, java.net.http.HttpResponse.BodyHandlers.ofString(java.nio.charset.StandardCharsets.UTF_8));
            assertThat(response.headers().firstValue("X-Trace-Id")).contains("client-supplied-trace-0001");
            assertThat(response.body()).contains("client-supplied-trace-0001");
        } catch (Exception e) {
            throw new AssertionError(e);
        }
    }
}
