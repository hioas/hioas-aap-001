package com.hioas.aap.common;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.common.TraceIdFilter;
import com.hioas.aap.support.ApiTestBase;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T01 · 日志与健康检查（dev SKILL §5「控制台 + 文件双写」、§8「关键健康端点 200」）。
 */
class LoggingAndHealthTest extends ApiTestBase {

    @Test
    @DisplayName("日志文件 logs/aap-server.log 存在，且请求内日志带 traceId 落盘（MDC → 文件 appender 链路生效）")
    void logFileReceivesApplicationLogsWithTraceId() throws Exception {
        String traceId = "t01-trace-" + System.nanoTime();

        var req = java.net.http.HttpRequest.newBuilder()
                .uri(java.net.URI.create(baseUrl() + "/api/v1/__test/echo"))
                .header(TraceIdFilter.HEADER, traceId)
                .GET().build();
        var res = java.net.http.HttpClient.newHttpClient()
                .send(req, java.net.http.HttpResponse.BodyHandlers.ofString(java.nio.charset.StandardCharsets.UTF_8));
        assertThat(res.statusCode()).isEqualTo(200);

        Path logFile = Path.of(environment.getProperty("app.logging.dir", "logs"), "aap-server.log");
        long deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos();
        String content = "";
        while (System.nanoTime() < deadline) {
            if (Files.exists(logFile)) {
                content = Files.readString(logFile, java.nio.charset.StandardCharsets.UTF_8);
                if (content.contains("[" + traceId + "]")) {
                    break;
                }
            }
            Thread.sleep(200);
        }
        assertThat(Files.exists(logFile)).as("日志文件必须存在于 %s", logFile.toAbsolutePath()).isTrue();
        assertThat(content).as("日志须写入文件（控制台 + 文件双写）").contains("T01-ECHO");
        assertThat(content).as("日志行的 MDC traceId 必须等于请求的 traceId").contains("[" + traceId + "]");
    }

    @Test
    @DisplayName("/actuator/health 返回 UP")
    void healthEndpointIsUp() {
        var req = java.net.http.HttpRequest.newBuilder()
                .uri(java.net.URI.create(baseUrl() + "/actuator/health"))
                .GET().build();
        try {
            var res = java.net.http.HttpClient.newHttpClient()
                    .send(req, java.net.http.HttpResponse.BodyHandlers.ofString(java.nio.charset.StandardCharsets.UTF_8));
            assertThat(res.statusCode()).isEqualTo(200);
            assertThat(res.body()).contains("\"status\":\"UP\"");
        } catch (Exception e) {
            throw new AssertionError("健康检查调用失败", e);
        }
    }
}
