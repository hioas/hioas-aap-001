package com.hioas.aap.credential;

import com.hioas.aap.common.JsonCodec;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;

/**
 * 凭证预检的上游探测（连通性 + 鉴权 + 模型清单）。
 *
 * <p>规则（R-10/R-11/§10 安全）：
 * <ul>
 *   <li>GET {@code {base_url}/models}，携带 {@code Authorization: Bearer <api_key>}</li>
 *   <li>**401/403 不重试**（鉴权失败重试无意义且可能触发上游封禁）；网络错误/5xx 最多重试 2 次</li>
 *   <li>响应体读取上限 10 MiB（超限即截断，避免被大响应拖垮）</li>
 *   <li>出站地址必须先过 {@code OutboundUrlGuard}（SSRF）</li>
 * </ul>
 *
 * <p>注意：本类**不记录 api_key**（日志只出现掩码），异常信息不含密钥。
 */
@Component
public class UpstreamProbe {

    private static final Logger log = LoggerFactory.getLogger(UpstreamProbe.class);
    private static final int MAX_BODY_BYTES = 10 * 1024 * 1024;
    private static final int MAX_RETRY = 2;

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();

    /** 探测结果。 */
    public record ProbeResult(boolean connectivityOk, boolean authOk, boolean modelsOk,
                              int httpStatus, int latencyMs, String errorCode, String errorMsg,
                              List<String> models, int attempts) {
    }

    public ProbeResult probe(String baseUrl, String apiKey, int timeoutSeconds) {
        URI uri = URI.create(stripTrailingSlash(baseUrl) + "/models");
        int attempts = 0;
        long start = System.nanoTime();
        while (true) {
            attempts++;
            try {
                HttpRequest request = HttpRequest.newBuilder(uri)
                        .timeout(Duration.ofSeconds(timeoutSeconds))
                        .header("Authorization", "Bearer " + apiKey)
                        .header("Accept", "application/json")
                        .GET()
                        .build();
                HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
                int status = response.statusCode();
                int latency = (int) ((System.nanoTime() - start) / 1_000_000);

                if (status == 401 || status == 403) {
                    return new ProbeResult(true, false, false, status, latency, "E-1101",
                            "上游拒绝鉴权（HTTP " + status + "），请检查 APIKey 与模型开放范围", List.of(), attempts);
                }
                if (status >= 200 && status < 300) {
                    List<String> models = parseModels(response.body());
                    return new ProbeResult(true, true, !models.isEmpty(), status, latency, null, null, models, attempts);
                }
                if (attempts <= MAX_RETRY && status >= 500) {
                    log.warn("上游预检返回 {}，第 {} 次重试", status, attempts);
                    continue;
                }
                return new ProbeResult(true, false, false, status, latency, "E-1101",
                        "上游返回 HTTP " + status + "，无法确认接口可用性", List.of(), attempts);
            } catch (Exception e) {
                int latency = (int) ((System.nanoTime() - start) / 1_000_000);
                if (attempts <= MAX_RETRY) {
                    log.warn("上游预检网络异常，第 {} 次重试: {}", attempts, e.toString());
                    continue;
                }
                log.warn("上游预检失败（已重试 {} 次）: {}", attempts, e.toString());
                return new ProbeResult(false, false, false, 0, latency, "E-1101",
                        "无法连接上游地址（网络不可达或超时）", List.of(), attempts);
            }
        }
    }

    private static List<String> parseModels(byte[] body) {
        if (body == null || body.length == 0) {
            return List.of();
        }
        int limit = Math.min(body.length, MAX_BODY_BYTES);
        String text = new String(body, 0, limit, StandardCharsets.UTF_8);
        List<String> models = new ArrayList<>();
        try {
            JsonNode root = JsonCodec.readTree(text);
            JsonNode data = root == null ? null : root.path("data");
            if (data != null && data.isArray()) {
                for (JsonNode item : data) {
                    String id = item.path("id").asText(null);
                    if (id != null && !id.isBlank()) {
                        models.add(id);
                    }
                }
            }
        } catch (RuntimeException e) {
            log.warn("上游模型清单解析失败（按不可判定处理）: {}", e.toString());
        }
        return models;
    }

    private static String stripTrailingSlash(String url) {
        String result = url;
        while (result.endsWith("/")) {
            result = result.substring(0, result.length() - 1);
        }
        return result;
    }
}
