package com.hioas.aap.sync;

import com.hioas.aap.common.OutboundUrlGuard;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * new-api 同步适配器（**mock 口径**，见偏差表 `D-SYNC-02`）。
 *
 * <p>真源缺口：`.calicat/prd/11-同步与用量统计PRD.md` §3 只给了字段映射与幂等键设计，**没有冻结
 * new-api 的 HTTP 契约**（new-api 侧要「源码改造」才提供服务端接口）。因此本类只落地两端：
 * <ul>
 *   <li>读：{@code GET {base_url}/models} —— 与凭证预检 {@code UpstreamProbe} 同一口径（同一个
 *       上游自然键，避免两套「模型清单」写法）</li>
 *   <li>写：{@code PUT {base_url}/api/channel/} body {@code {"id":<channel_id>,"status":1|2}}
 *       —— 渠道启停（1=启用、2=禁用），随后 {@code GET {base_url}/api/channel/{id}} 回读（AC-34）</li>
 * </ul>
 * 接入真实 new-api 时只需替换本类的路径与方法（调用方只看 {@link Probe}）。
 *
 * <p>安全：出站地址先过 {@link OutboundUrlGuard}（SSRF，AC-29）；api_key 只放 Authorization 头，
 * **不写日志、不进异常消息、不进响应**；响应体读取上限 1 MiB。
 */
@Component
public class NewApiSyncClient {

    private static final Logger log = LoggerFactory.getLogger(NewApiSyncClient.class);
    private static final int MAX_BODY_BYTES = 1024 * 1024;
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);
    private static final Duration REQUEST_TIMEOUT = Duration.ofSeconds(10);

    private final OutboundUrlGuard outboundUrlGuard;

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(CONNECT_TIMEOUT)
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();

    public NewApiSyncClient(OutboundUrlGuard outboundUrlGuard) {
        this.outboundUrlGuard = outboundUrlGuard;
    }

    /**
     * 一次上游调用的结果。
     *
     * @param reachable  是否拿到 HTTP 响应（网络不可达/超时为 false）
     * @param httpStatus 上游状态码（不可达为 0）
     * @param body       响应体（截断至 1 MiB；不可达为 null）
     * @param errorCode  本地判定出的错误码（不可达 → {@code E-1501}）
     * @param error      本地错误说明（不含密钥）
     */
    public record Probe(boolean reachable, int httpStatus, String body, String errorCode, String error) {

        public boolean ok() {
            return reachable && httpStatus >= 200 && httpStatus < 300;
        }

        /** 上游 401/403：鉴权类失败，重试无意义（PRD §5 / A8）。 */
        public boolean denied() {
            return reachable && (httpStatus == 401 || httpStatus == 403);
        }
    }

    public Probe get(String baseUrl, String apiKey, String path) {
        outboundUrlGuard.verify(baseUrl);
        HttpRequest.Builder builder = HttpRequest.newBuilder(resolve(baseUrl, path))
                .timeout(REQUEST_TIMEOUT)
                .header("Accept", "application/json")
                .GET();
        authorize(builder, apiKey);
        return send(builder.build());
    }

    public Probe put(String baseUrl, String apiKey, String path, String jsonBody) {
        outboundUrlGuard.verify(baseUrl);
        HttpRequest.Builder builder = HttpRequest.newBuilder(resolve(baseUrl, path))
                .timeout(REQUEST_TIMEOUT)
                .header("Accept", "application/json")
                .header("Content-Type", "application/json")
                .PUT(HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8));
        authorize(builder, apiKey);
        return send(builder.build());
    }

    private static boolean authorize(HttpRequest.Builder builder, String apiKey) {
        if (apiKey != null && !apiKey.isBlank()) {
            builder.header("Authorization", "Bearer " + apiKey);
            return true;
        }
        return false;
    }

    private static URI resolve(String baseUrl, String path) {
        String base = baseUrl;
        while (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        return URI.create(base + path);
    }

    private Probe send(HttpRequest request) {
        try {
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            byte[] raw = response.body();
            String body = raw == null ? null
                    : new String(raw, 0, Math.min(raw.length, MAX_BODY_BYTES), StandardCharsets.UTF_8);
            return new Probe(true, response.statusCode(), body, null, null);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("new-api 调用被中断: {}", request.method() + " " + request.uri().getPath());
            return new Probe(false, 0, null, "E-1501", "new-api 调用被中断");
        } catch (Exception e) {
            // 只记方法+路径（不含 query/body/密钥）
            log.warn("new-api 不可达 {} {}：{}", request.method(), request.uri().getPath(), e.toString());
            return new Probe(false, 0, null, "E-1501", "无法连接 new-api（网络不可达或超时）");
        }
    }
}
