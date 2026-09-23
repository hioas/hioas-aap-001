package com.hioas.aap.detection;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.support.DbTestBase;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * 探针执行器的判定口径（{@link DetectionProbeRunner}）。
 *
 * <p>为什么单独测：这些口径决定了「检测结论从哪来」，且此前有两个会让结论失真的缺陷 ——
 * <ol>
 *   <li>拿**整包 JSON** 比一致性 ⇒ 每次 {@code id}/{@code created} 都不同 ⇒ 一致率恒 0 ⇒
 *       D3 恒 0、指纹 D7 恒 0 ⇒ 触发一票否决，**任何模型都判 FAIL**；</li>
 *   <li>指纹子项键名（{@code determinism}/{@code usage_shape}）不在
 *       {@code ProbeScoring.scoreFingerprint} 认的 5 条线里 ⇒ D7 恒为 {@code NOT_MEASURABLE}。</li>
 * </ol>
 * 两个缺陷叠加会互相掩盖（表面看只是「指纹不可测」），单测把口径钉死。
 *
 * <p>上游用本地 HttpServer 桩（{@code app.credential.allow-loopback: true} 仅测试环境放行）。
 */
class DetectionProbeRunnerTest extends DbTestBase {

    @Autowired
    private DetectionProbeRunner runner;

    @Autowired
    private CryptoService crypto;

    private HttpServer upstream;
    private final AtomicInteger calls = new AtomicInteger();
    private final AtomicReference<String> authHeader = new AtomicReference<>();

    @AfterEach
    void stopUpstream() {
        if (upstream != null) {
            upstream.stop(0);
            upstream = null;
        }
    }

    /**
     * chat 桩：{@code contentForCall} 按第几次调用给正文；{@code usage} 拼进响应体。
     * 每次响应的 {@code id}/{@code created} 都不同（真实上游也如此）。
     */
    private String startUpstream(java.util.function.IntFunction<String> contentForCall, boolean withUsage,
                                 boolean withCachedTokens) throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/v1/chat/completions", exchange -> {
            int n = calls.incrementAndGet();
            authHeader.set(exchange.getRequestHeaders().getFirst("Authorization"));
            String usage = withUsage
                    ? (withCachedTokens
                    ? ",\"usage\":{\"prompt_tokens\":20,\"completion_tokens\":40,"
                    + "\"prompt_tokens_details\":{\"cached_tokens\":7}}"
                    : ",\"usage\":{\"prompt_tokens\":20,\"completion_tokens\":40}")
                    : "";
            String body = "{\"id\":\"chatcmpl-" + n + "\",\"created\":" + (1000 + n)
                    + ",\"choices\":[{\"index\":0,\"message\":{\"role\":\"assistant\",\"content\":\""
                    + contentForCall.apply(n) + "\"}}]" + usage + "}";
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        upstream.start();
        return "http://127.0.0.1:" + upstream.getAddress().getPort() + "/v1";
    }

    private static ProbeScoring.ProbeScore scoreOf(DetectionProbeRunner.ProbeOutcome outcome, String code) {
        return outcome.scores().stream().filter(s -> code.equals(s.probeCode())).findFirst().orElseThrow();
    }

    @Test
    @DisplayName("密文损坏（密钥轮换/落库损坏）：8 项一律 FAILED，不臆造分数")
    void brokenCipherFailsEveryProbe() {
        DetectionProbeRunner.ProbeOutcome outcome =
                runner.run("http://127.0.0.1:1/v1", "not-a-valid-cipher", List.of("gpt-4o"));

        assertThat(outcome.scores()).hasSize(8);
        assertThat(outcome.scores()).allSatisfy(score -> {
            assertThat(score.status()).isEqualTo(ProbeScoring.ProbeStatus.FAILED);
            assertThat(score.score()).as("失败项不得有分数").isNull();
            assertThat(score.note()).contains("解密");
        });
        assertThat(outcome.metricsByProbe()).isEmpty();
        assertThat(outcome.evidenceByProbe()).containsKey("failure");
        assertThat(calls.get()).as("解不出密钥就不该发请求").isZero();
    }

    @Test
    @DisplayName("凭证无模型清单：不发请求、8 项一律 FAILED（不猜模型）")
    void missingModelListFailsEveryProbe() throws Exception {
        String baseUrl = startUpstream(n -> "x", true, false);
        DetectionProbeRunner.ProbeOutcome outcome =
                runner.run(baseUrl, crypto.encrypt("sk-probe-test-key"), List.of());

        assertThat(outcome.scores()).hasSize(8);
        assertThat(outcome.scores()).allSatisfy(score ->
                assertThat(score.status()).isEqualTo(ProbeScoring.ProbeStatus.FAILED));
        assertThat(scoreOf(outcome, "D1").note()).contains("模型清单");
        assertThat(calls.get()).isZero();
    }

    @Test
    @DisplayName("一致性比的是**正文**不是整包：3 轮里 2 轮同文 ⇒ D3=66.67，指纹行为线同值且不否决")
    void consistencyComparesContentNotWholeBody() throws Exception {
        // 第 1 轮正文不同，第 2/3 轮相同；id 与 created 每轮都不同（若拿整包比对，一致率会是 0）
        String baseUrl = startUpstream(n -> n == 1 ? "甲" : "乙", true, false);
        DetectionProbeRunner.ProbeOutcome outcome =
                runner.run(baseUrl, crypto.encrypt("sk-probe-test-key"), List.of("gpt-4o"));

        assertThat(calls.get()).isEqualTo(3);
        assertThat(authHeader.get()).as("api_key 必须解密后按 Bearer 发出").isEqualTo("Bearer sk-probe-test-key");

        assertThat(scoreOf(outcome, "D3").status()).isEqualTo(ProbeScoring.ProbeStatus.SUCCESS);
        assertThat(scoreOf(outcome, "D3").score()).isEqualTo(66.67);
        assertThat(outcome.metricsByProbe().get("D3").get("max_agreeing")).isEqualTo(2);
        assertThat(outcome.metricsByProbe().get("D3").get("samples")).isEqualTo(3);

        // D7 行为线 = 一致率；权重按可测子项重分配；≥40 不触发一票否决
        assertThat(scoreOf(outcome, "D7").score()).isEqualTo(66.67);
        assertThat(scoreOf(outcome, "D7").note()).contains("可测子项 1/5");
        assertThat(outcome.metricsByProbe().get("D7").get("confidence")).isEqualTo("LOW");

        // D2 从 usage.completion_tokens 算输出 TPS（本桩 40 tokens / 极短耗时 ⇒ 满分）
        assertThat(scoreOf(outcome, "D2").status()).isEqualTo(ProbeScoring.ProbeStatus.SUCCESS);
        assertThat(scoreOf(outcome, "D2").score()).isEqualTo(100.0);
        assertThat(outcome.metricsByProbe().get("D2")).containsKey("tps_median");

        // 上游没回缓存字段 ⇒ D6 不可测（不是 0 分）
        assertThat(scoreOf(outcome, "D6").status()).isEqualTo(ProbeScoring.ProbeStatus.NOT_MEASURABLE);
        assertThat(scoreOf(outcome, "D6").score()).isNull();

        // D1 取样 3 次
        assertThat(scoreOf(outcome, "D1").status()).isEqualTo(ProbeScoring.ProbeStatus.SUCCESS);
        assertThat((List<?>) outcome.metricsByProbe().get("D1").get("samples_ms")).hasSize(3);
    }

    @Test
    @DisplayName("上游返回 cached_tokens>0 ⇒ D6 命中满分；usage 缺失 ⇒ D2 标 NOT_MEASURABLE（不填示意分）")
    void cacheAndTpsDependsOnUpstreamFields() throws Exception {
        String withCache = startUpstream(n -> "丙", true, true);
        DetectionProbeRunner.ProbeOutcome cached =
                runner.run(withCache, crypto.encrypt("sk-probe-test-key"), List.of("gpt-4o"));
        assertThat(scoreOf(cached, "D6").status()).isEqualTo(ProbeScoring.ProbeStatus.SUCCESS);
        assertThat(scoreOf(cached, "D6").score()).isEqualTo(100.0);

        upstream.stop(0);
        calls.set(0);
        String noUsage = startUpstream(n -> "丁", false, false);
        DetectionProbeRunner.ProbeOutcome bare =
                runner.run(noUsage, crypto.encrypt("sk-probe-test-key"), List.of("gpt-4o"));
        assertThat(scoreOf(bare, "D2").status()).as("没有 usage 就不能算吞吐，宁可标不可测")
                .isEqualTo(ProbeScoring.ProbeStatus.NOT_MEASURABLE);
        assertThat(scoreOf(bare, "D2").score()).isNull();
        assertThat(scoreOf(bare, "D6").status()).isEqualTo(ProbeScoring.ProbeStatus.NOT_MEASURABLE);
    }
}
