package com.hioas.aap.common;

import static org.assertj.core.api.Assertions.assertThat;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.stream.StreamSupport;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

/**
 * T01 · 统一契约单元测试。
 *
 * <p>覆盖：包体形状（code/message/data/traceId）、成功码 "0"、traceId 从 MDC 取、
 * 错误码表与 docs/backend/json-schema/common/error.schema.json 的枚举**逐条一致**。
 */
class ApiEnvelopeTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Test
    @DisplayName("成功包体：code=0、message=ok、data 原样、traceId 取自 MDC")
    void okEnvelopeCarriesTraceIdFromMdc() throws Exception {
        MDC.put("traceId", "trace-abc-123");
        try {
            ApiEnvelope<java.util.Map<String, Object>> env = ApiEnvelope.ok(java.util.Map.of("k", "v"));
            assertThat(env.code()).isEqualTo("0");
            assertThat(env.message()).isEqualTo("ok");
            assertThat(env.traceId()).isEqualTo("trace-abc-123");

            JsonNode node = MAPPER.readTree(MAPPER.writeValueAsString(env));
            assertThat(node.path("code").asText()).isEqualTo("0");
            assertThat(node.path("data").path("k").asText()).isEqualTo("v");
            assertThat(node.path("traceId").asText()).isEqualTo("trace-abc-123");
            assertThat(node.path("message").asText()).isEqualTo("ok");
        } finally {
            MDC.remove("traceId");
        }
    }

    @Test
    @DisplayName("失败包体：code=E-xxxx、message 保留、data 为 null（禁止用 0 冒充没有数据）")
    void failEnvelopeHasNullData() throws Exception {
        ApiEnvelope<Void> env = ApiEnvelope.fail(ErrorCode.E_1001, "手机号格式不正确");
        assertThat(env.code()).isEqualTo("E-1001");
        assertThat(env.message()).isEqualTo("手机号格式不正确");
        assertThat(env.data()).isNull();

        JsonNode node = MAPPER.readTree(MAPPER.writeValueAsString(env));
        assertThat(node.get("data").isNull()).isTrue();
    }

    @Test
    @DisplayName("成功码恒为字符串 \"0\"（客户端 http.ts 以 typeof body.code==='string' 做形状校验）")
    void successCodeIsString() throws Exception {
        JsonNode node = MAPPER.readTree(MAPPER.writeValueAsString(ApiEnvelope.ok(null)));
        assertThat(node.get("code").isString()).isTrue();
        assertThat(node.get("code").asText()).isEqualTo("0");
    }

    @Test
    @DisplayName("错误码表与 docs/backend/json-schema/common/error.schema.json 枚举一致（含全部 E-xxxx）")
    void errorCodeEnumMatchesContract() throws Exception {
        Path schema = Path.of("..", "docs", "backend", "json-schema", "common", "error.schema.json");
        assertThat(Files.exists(schema)).as("契约文件必须存在: %s", schema.toAbsolutePath()).isTrue();
        JsonNode root = MAPPER.readTree(Files.readString(schema));
        List<String> inSchema = StreamSupport.stream(root.path("properties").path("code").path("enum").spliterator(), false)
                .map(JsonNode::asText).sorted().toList();
        List<String> inJava = Arrays.stream(ErrorCode.values())
                .map(ErrorCode::code)
                .filter(c -> !"0".equals(c))
                .sorted().toList();
        assertThat(inJava).as("Java 错误码与契约 must 一致").isEqualTo(inSchema);
    }

    @Test
    @DisplayName("错误码的 HTTP 状态映射符合 PRD §9（401/403/404/409/429/500/503）")
    void errorCodeHttpStatusMapping() {
        assertThat(ErrorCode.E_1902.httpStatus()).isEqualTo(401);
        assertThat(ErrorCode.E_1901.httpStatus()).isEqualTo(403);
        assertThat(ErrorCode.E_1903.httpStatus()).isEqualTo(429);
        assertThat(ErrorCode.E_1301.httpStatus()).isEqualTo(409);
        assertThat(ErrorCode.E_1601.httpStatus()).isEqualTo(409);
        assertThat(ErrorCode.E_1701.httpStatus()).isEqualTo(409);
        assertThat(ErrorCode.E_1104.httpStatus()).isEqualTo(409);
        assertThat(ErrorCode.E_1406.httpStatus()).isEqualTo(404);
        assertThat(ErrorCode.E_1304.httpStatus()).isEqualTo(404);
        assertThat(ErrorCode.E_2001.httpStatus()).isEqualTo(500);
        assertThat(ErrorCode.E_1801.httpStatus()).isEqualTo(503);
        assertThat(ErrorCode.E_1001.httpStatus()).isEqualTo(400);
        assertThat(ErrorCode.of("E-2001")).isEqualTo(ErrorCode.E_2001);
    }
}
