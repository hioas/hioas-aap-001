package com.hioas.aap.support;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;

/**
 * 集成测试基类：**真实 HTTP** 打本进程内的服务端。
 *
 * <p>为什么不用 MockMvc：{@code @AutoConfigureMockMvc} 在 Spring Boot 4.1.1 的
 * {@code spring-boot-starter-test} 里已不在（迁到 {@code spring-boot-webmvc-test}）。
 * 真实 HTTP 反而更严格——序列化、过滤器、状态码、响应头全部走生产路径，
 * 契约测试（JSON Schema 校验真实响应体）才有意义。
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
public abstract class ApiTestBase {

    protected static final ObjectMapper MAPPER = new ObjectMapper();
    private static final HttpClient CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    @LocalServerPort
    protected int port;

    @Autowired
    protected org.springframework.core.env.Environment environment;

    protected String baseUrl() {
        return "http://localhost:" + port;
    }

    /** 一次 HTTP 调用的结果（状态码 + 响应头 + 原始 body 文本）。 */
    public record HttpResult(int status, java.net.http.HttpHeaders headers, String body) {

        public String header(String name) {
            return headers.firstValue(name).orElse(null);
        }

        public JsonNode json() {
            try {
                return MAPPER.readTree(body);
            } catch (RuntimeException e) {
                throw new AssertionError("响应不是合法 JSON: " + body, e);
            }
        }

        public String code() {
            return json().path("code").asText(null);
        }

        public String message() {
            return json().path("message").asText(null);
        }

        /** data 节点（可能为 NullNode）。 */
        public JsonNode data() {
            return json().path("data");
        }

        public String traceId() {
            return json().path("traceId").asText(null);
        }
    }

    protected HttpResult get(String path) {
        return get(path, null);
    }

    protected HttpResult get(String path, String token) {
        return send("GET", path, null, token);
    }

    protected HttpResult post(String path, String bodyJson) {
        return post(path, bodyJson, null);
    }

    protected HttpResult post(String path, String bodyJson, String token) {
        return send("POST", path, bodyJson, token);
    }

    protected HttpResult put(String path, String bodyJson, String token) {
        return send("PUT", path, bodyJson, token);
    }

    protected HttpResult delete(String path, String token) {
        return send("DELETE", path, null, token);
    }

    protected HttpResult send(String method, String path, String bodyJson, String token) {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl() + "/api/v1" + path))
                .timeout(Duration.ofSeconds(30))
                .header("Content-Type", "application/json");
        if (token != null) {
            builder.header("Authorization", "Bearer " + token);
        }
        if (bodyJson == null) {
            builder.method(method, HttpRequest.BodyPublishers.noBody());
        } else {
            builder.method(method, HttpRequest.BodyPublishers.ofString(bodyJson, StandardCharsets.UTF_8));
        }
        try {
            HttpResponse<String> res = CLIENT.send(builder.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            return new HttpResult(res.statusCode(), res.headers(), res.body());
        } catch (IOException | InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("HTTP 调用失败: " + method + " " + path, e);
        }
    }

    protected String json(Object value) {
        return MAPPER.writeValueAsString(value);
    }
}
