package com.hioas.aap.detection;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.OutboundUrlGuard;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;

/**
 * 检测探针执行器：对一张凭证**真发请求**，产出 {@link ProbeScoring.ProbeScore} 列表。
 *
 * <p>为什么需要它：{@code DetectionService.recordProbeResults} 此前**全仓零调用方**
 * （缺陷 1）→ 检测任务建了就永远停在 {@code QUEUED}（实测 {@code updated_at == created_at}，
 * 插入后再没被任何代码碰过），凭证卡在 {@code detection_status=RUNNING}，
 * 再预检报 {@code E-1301}，该凭证永久无法重试。
 *
 * <p>覆盖的探针与不可测项处置（真源 09-PRD §2/§5）：
 * <ul>
 *   <li>D1 TTFT —— 真实测首字时延（多轮取样取中位）</li>
 *   <li>D2 P50/TPS —— 输出 TPS = {@code usage.completion_tokens} / 总耗时；上游不回 usage 则
 *       {@code NOT_MEASURABLE}（**不填示意分**）</li>
 *   <li>D3 一致性 —— 同问多次（{@code temperature=0, top_p=1}），比对 {@code choices[0].message.content}</li>
 *   <li>D4/D5 配额 —— 本执行器**不主动打配额**（会真扣费且需管理端声明值），一律
 *       {@code NOT_MEASURABLE}，交 {@code summarize} 按权重再分配</li>
 *   <li>D6 缓存 —— 需上游返回 {@code cached_tokens} 字段；无字段 {@code NOT_MEASURABLE}</li>
 *   <li>D7 模型指纹 —— 由 D3 一致性合成「行为线」，其余 4 条线未实现（见 {@code metrics.D7.unmeasured_lines}），
 *       置信度因此为 LOW；权重 0.35、&lt;40 一票否决</li>
 *   <li>D8 真实源 —— 仅证据摘要（权重 0，不计分）</li>
 * </ul>
 *
 * <p>⚠️ 与 PRD 的**已知差距**（本执行器是方案 A 的最小闭环，不假装做到了规格全量）：
 * <ul>
 *   <li>D1 用非流式整包时延近似首字时延（PRD 要求 {@code stream=true} + SSE 首包；未实现流式解析）</li>
 *   <li>D2 用「固定 prompt + max_tokens=128」而非 PRD 的 500/256 输入输出，且未扣 TTFT → TPS 是**下限**</li>
 *   <li>D4/D5 不施压 → 恒为不可测；D6 未做「长 prompt 二次请求」</li>
 *   <li>D7 仅有 1/5 条子证据线（行为线用一致性代理），未接基线库</li>
 * </ul>
 * 这些差距在 {@code metrics} 里逐条注明，并在报告/结论里以「不可测项」形式体现。
 *
 * <p>安全：出站地址先过 {@link OutboundUrlGuard}（SSRF，PRD §5）；api_key 只在内存里解密，
 * 不写日志、不进 metrics/证据。
 */
@Component
public class DetectionProbeRunner {

    private static final Logger log = LoggerFactory.getLogger(DetectionProbeRunner.class);

    /** 单次探测超时（秒）。探针要测时延，超时须大于最慢可接受响应。 */
    private static final int PROBE_TIMEOUT_SECONDS = 20;
    /** 取样轮数（D1/D2 取中位，D3 统计一致性）。 */
    private static final int ROUNDS = 3;

    /**
     * 探针 prompt：要**确定性且足够长的输出**。
     *
     * <p>为什么不是「回答 pong」：D2（权重 0.15）按 PRD 用输出 TPS 打分，单 token 回复根本测不出吞吐；
     * 这个 prompt 同时服务 D3（一致性比对）与 D2（足够的解码窗口），成本上限由 {@link #PROBE_MAX_TOKENS} 兜住。
     */
    private static final String PROBE_PROMPT = "请只输出数字 1 到 40，用中文逗号分隔，不要输出任何其他文字。";
    /** 输出上限（PRD §5 成本保护）。 */
    private static final int PROBE_MAX_TOKENS = 128;

    private final CryptoService crypto;
    private final OutboundUrlGuard urlGuard;

    public DetectionProbeRunner(CryptoService crypto, OutboundUrlGuard urlGuard) {
        this.crypto = crypto;
        this.urlGuard = urlGuard;
    }

    /** 一次探针运行的全部产物。 */
    public record ProbeOutcome(List<ProbeScoring.ProbeScore> scores,
                               Map<String, Map<String, Object>> metricsByProbe,
                               Map<String, String> evidenceByProbe) {
    }

    /**
     * 对一张凭证跑全部探针。
     *
     * @param baseUrl     凭证的接口地址（已规范化，通常以 /v1 结尾）
     * @param apiKeyCipher 凭证 api_key 的**密文**（本方法内部解密，明文不外传）
     * @param models      本次检测覆盖的模型清单，取首个做探针
     */
    public ProbeOutcome run(String baseUrl, String apiKeyCipher, List<String> models) {
        // 出站地址先过 SSRF 防护（凭证写入时已校验过一次，这里是纵深防御，防的是后续配置被改）
        try {
            urlGuard.verify(baseUrl);
        } catch (ApiException e) {
            return allFailed("上游地址未通过出站校验（SSRF 防护）：" + e.getMessage());
        }

        String apiKey;
        try {
            apiKey = crypto.decrypt(apiKeyCipher);
        } catch (RuntimeException e) {
            // 只记结论，不记异常对象与密文：解密失败 = 连探测都做不了，全部探针标 FAILED
            log.warn("探针启动失败：api_key 解密异常（密钥轮换或密文损坏）");
            return allFailed("凭证密钥无法解密（密钥轮换或密文损坏）");
        }

        String model = (models == null || models.isEmpty()) ? null : models.get(0);
        if (model == null || model.isBlank()) {
            return allFailed("凭证无模型清单，无法探测");
        }

        List<ProbeScoring.ProbeScore> scores = new ArrayList<>();
        Map<String, Map<String, Object>> metrics = new LinkedHashMap<>();
        Map<String, String> evidence = new LinkedHashMap<>();

        List<Integer> elapsedSamples = new ArrayList<>();
        List<Double> tpsSamples = new ArrayList<>();
        List<String> contents = new ArrayList<>();
        boolean cacheFieldSeen = false;
        boolean cacheHitSeen = false;

        for (int round = 0; round < ROUNDS; round++) {
            ChatCall call = chat(baseUrl, apiKey, model);
            if (!call.ok()) {
                if (round == 0) {
                    // 首轮就失败 ⇒ 连通/鉴权问题，无需继续取样
                    return allFailed("上游调用失败：" + call.error());
                }
                // 后续轮失败：用已有样本继续（样本不足时 D1 自会判 FAILED，不补假样本）
                log.warn("探针第 {} 轮失败（已取得 {} 轮样本，按现有样本继续）：{}",
                        round + 1, contents.size(), call.error());
                break;
            }
            elapsedSamples.add(call.elapsedMs());
            contents.add(call.content());
            if (call.completionTokens() != null && call.elapsedMs() > 0) {
                tpsSamples.add(call.completionTokens() * 1000.0 / call.elapsedMs());
            }
            if (call.cachedTokens() != null) {
                cacheFieldSeen = true;
                cacheHitSeen = cacheHitSeen || call.cachedTokens() > 0;
            }
        }

        if (contents.isEmpty()) {
            return allFailed("上游未返回任何可用响应");
        }

        // ── D1 TTFT ──
        scores.add(ProbeScoring.scoreTtft(elapsedSamples));
        metrics.put("D1", Map.of(
                "samples_ms", elapsedSamples,
                "method", "非流式请求，以整包到达耗时近似首字时延（未实现 stream=true 的 SSE 首包解析）"));
        evidence.put("D1", ROUNDS + " 轮整包耗时（近似 TTFT）：" + elapsedSamples + " ms");

        // ── D2 P50 / 输出 TPS ──
        if (tpsSamples.isEmpty()) {
            scores.add(notMeasurable("D2", "上游未返回 usage.completion_tokens，无法计算输出 TPS（不臆造吞吐分）"));
            metrics.put("D2", Map.of("method", "需要 usage.completion_tokens；本次未取得"));
            evidence.put("D2", "上游未返回 usage.completion_tokens，未取得实测吞吐（不可测，不填示意分）");
        } else {
            double tps = median(tpsSamples);
            scores.add(ProbeScoring.scoreThroughput(tps));
            metrics.put("D2", Map.of(
                    "tps_samples", tpsSamples,
                    "tps_median", ProbeScoring.round2(tps),
                    "method", "输出 TPS = completion_tokens / 总耗时；非流式且未扣 TTFT，故为下限"));
            evidence.put("D2", "输出 TPS 中位 " + ProbeScoring.round2(tps) + "（completion_tokens/总耗时，下限口径）");
        }

        // ── D3 一致性 ── 同 prompt、temperature=0、top_p=1，比对响应正文（不是整包：整包含 id/created 等易变字段）
        int maxAgreeing = maxFrequency(contents);
        double consistencyRate = (double) maxAgreeing / contents.size();
        scores.add(ProbeScoring.scoreDeterminism(contents.size(), maxAgreeing));
        metrics.put("D3", Map.of(
                "samples", contents.size(),
                "max_agreeing", maxAgreeing,
                "method", "同一 prompt 重复 " + ROUNDS + " 次（temperature=0, top_p=1），比对 choices[0].message.content"));
        evidence.put("D3", "同问 " + contents.size() + " 次，最大一致 " + maxAgreeing + "/" + contents.size());

        // ── D4/D5 配额 ── 不主动打配额（会真扣费），标不可测交 summarize 再分配权重。
        // 仍然落库「原始指标」（这里是不可测的原因与口径）——PRD A2 要求每项都有指标+证据+解释，不可测项也不例外。
        String d4Note = "未主动施压配额（避免真实扣费）；上游未申报 RPM 时不臆造分数";
        String d5Note = "未主动施压配额（避免真实扣费）；上游未申报 TPM 时不臆造分数";
        scores.add(notMeasurable("D4", d4Note));
        scores.add(notMeasurable("D5", d5Note));
        metrics.put("D4", Map.of("method", "本执行器不施压配额", "reason", d4Note));
        metrics.put("D5", Map.of("method", "本执行器不施压配额", "reason", d5Note));
        evidence.put("D4", "RPM 未实测：方案 A 不主动压测（PRD D4 压测会产生真实费用）");
        evidence.put("D5", "TPM 未实测：方案 A 不主动压测（PRD D5 压测会产生真实费用）");

        // ── D6 缓存 ──
        scores.add(ProbeScoring.scoreCache(cacheFieldSeen ? cacheHitSeen : null, cacheFieldSeen));
        metrics.put("D6", Map.of(
                "cached_tokens_field_present", cacheFieldSeen,
                "cache_hit_observed", cacheHitSeen,
                "method", "读 usage.prompt_tokens_details.cached_tokens（或 cache_read_input_tokens）；未做长 prompt 二次请求"));
        evidence.put("D6", cacheFieldSeen
                ? "上游返回缓存字段，观测到命中：" + cacheHitSeen
                : "上游未返回 cached_tokens 字段（不可测）");

        // ── D7 模型指纹（★权重 0.35，<40 一票否决）──
        // 只放**真实测到的**子项：行为线以「同问多次响应一致率」代理。
        // 其余 4 条线（自我认知/tokenizer/概率/上下文）本执行器未实现 —— 不填分，由 ProbeScoring 按比例重分配权重。
        Map<String, Double> subScores = new LinkedHashMap<>();
        subScores.put("behavior", ProbeScoring.round2(consistencyRate * 100));
        scores.add(ProbeScoring.scoreFingerprint(subScores));
        metrics.put("D7", Map.of(
                "sub_scores", subScores,
                "unmeasured_lines", List.of("self_awareness", "tokenizer", "probability", "context"),
                "confidence", ProbeScoring.fingerprintConfidence(subScores.size()),
                "method", "行为线以一致性代理（PRD 要求 40 题难度分层题库 + 基线库比对，本执行器未实现）"));
        evidence.put("D7", "行为线（一致性代理）=" + ProbeScoring.round2(consistencyRate * 100)
                + "；未测线：自我认知 / tokenizer / 概率 / 上下文，权重已按比例重分配");

        // ── D8 真实源 ── 仅证据，不计分
        String upstreamEvidence = "上游真实返回 " + contents.size() + " 次；usage.completion_tokens "
                + (tpsSamples.isEmpty() ? "缺失" : "存在") + "；缓存字段 " + (cacheFieldSeen ? "存在" : "缺失");
        scores.add(ProbeScoring.scoreUpstreamOrigin(upstreamEvidence));
        evidence.put("D8", upstreamEvidence);
        metrics.put("D8", Map.of("method", "仅输出证据，不纳入总分（权重 0）", "returned_rounds", contents.size()));

        scores.sort(Comparator.comparing(ProbeScoring.ProbeScore::probeCode));
        return new ProbeOutcome(scores, metrics, evidence);
    }

    /** 全部探针失败（连探测都做不了）：不臆造分数，交 {@code summarize} 给出诚实结论。 */
    public static ProbeOutcome allFailed(String reason) {
        List<ProbeScoring.ProbeScore> scores = new ArrayList<>();
        for (Map.Entry<String, Double> entry : ProbeScoring.DEFAULT_WEIGHTS.entrySet()) {
            scores.add(new ProbeScoring.ProbeScore(entry.getKey(), ProbeScoring.ProbeStatus.FAILED,
                    null, entry.getValue(), null, reason));
        }
        scores.sort(Comparator.comparing(ProbeScoring.ProbeScore::probeCode));
        return new ProbeOutcome(scores, Map.of(), Map.of("failure", reason));
    }

    private static ProbeScoring.ProbeScore notMeasurable(String code, String note) {
        double weight = ProbeScoring.DEFAULT_WEIGHTS.getOrDefault(code, 0.0);
        return new ProbeScoring.ProbeScore(code, ProbeScoring.ProbeStatus.NOT_MEASURABLE,
                null, weight, null, note);
    }

    /** 出现次数最多的取值（一致性率的分母口径：N 次里最大一致条约数 / N）。 */
    private static int maxFrequency(List<String> values) {
        Map<String, Integer> counts = new HashMap<>();
        int max = 0;
        for (String value : values) {
            int count = counts.merge(value, 1, Integer::sum);
            max = Math.max(max, count);
        }
        return max;
    }

    private static double median(List<Double> values) {
        List<Double> sorted = values.stream().sorted().toList();
        return sorted.get(sorted.size() / 2);
    }

    /** 单次 chat 调用的观测结果（{@code completionTokens}/{@code cachedTokens} 为 null = 上游未回该字段）。 */
    private record ChatCall(boolean ok, int elapsedMs, String content,
                            Integer completionTokens, Integer cachedTokens, String error) {
    }

    /**
     * 发一次 chat/completions 并观测耗时与用量字段。
     *
     * <p>用**非流式**请求：D1 的首字时延只能用整包到达近似（口径已写进 metrics，不假装是精确 TTFT）。
     * 不跟随重定向（HttpClient 默认 NEVER，比 PRD 的「重定向 ≤3」更严）。
     */
    private ChatCall chat(String baseUrl, String apiKey, String model) {
        String url = baseUrl.replaceAll("/+$", "") + "/chat/completions";
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("model", model);
        payload.put("messages", List.of(Map.of("role", "user", "content", PROBE_PROMPT)));
        payload.put("max_tokens", PROBE_MAX_TOKENS);
        // D3 规格：temperature=0, top_p=1（09-PRD §2-D3）
        payload.put("temperature", 0);
        payload.put("top_p", 1);
        payload.put("stream", false);

        long start = System.nanoTime();
        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(PROBE_TIMEOUT_SECONDS))
                    .build();
            HttpRequest req = HttpRequest.newBuilder(URI.create(url))
                    .timeout(Duration.ofSeconds(PROBE_TIMEOUT_SECONDS))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + apiKey)
                    .POST(HttpRequest.BodyPublishers.ofString(JsonCodec.toJson(payload), StandardCharsets.UTF_8))
                    .build();
            HttpResponse<String> res = client.send(req, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            // 取整毫秒下限 1ms：本机/环回桩常在 1ms 内返回，直接取整会得到 0 → 时延与 TPS 都会退化为「未取得」
            int elapsedMs = Math.max(1, (int) ((System.nanoTime() - start) / 1_000_000));
            if (res.statusCode() < 200 || res.statusCode() >= 300) {
                return new ChatCall(false, elapsedMs, "", null, null, "HTTP " + res.statusCode());
            }
            String body = res.body() == null ? "" : res.body();
            return new ChatCall(true, elapsedMs, extractContent(body),
                    intAt(body, "usage", "completion_tokens"),
                    cachedTokens(body), null);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return new ChatCall(false, 0, "", null, null, "中断");
        } catch (Exception e) {
            // 消息只含地址/网络原因，不含 api_key（api_key 只在请求头，不进异常文本）
            return new ChatCall(false, 0, "", null, null,
                    Objects.toString(e.getMessage(), e.getClass().getSimpleName()));
        }
    }

    /**
     * 取响应正文文本（{@code choices[0].message.content}）。
     *
     * <p>为什么要取正文而不是整包：整包里 {@code id}/{@code created} 每次都变，
     * 直接比整包会让一致性**恒为 0** → D3 恒 0、D7 恒 0 → 一票否决，任何模型都判 FAIL。
     * 结构异常时退化为整包文本（仍比不比更诚实）。
     */
    private static String extractContent(String body) {
        try {
            JsonNode root = JsonCodec.readTree(body);
            JsonNode content = root == null ? null
                    : root.path("choices").path(0).path("message").path("content");
            if (content != null && !content.isMissingNode() && !content.isNull()) {
                String text = content.asText(null);
                if (text != null) {
                    return text;
                }
            }
        } catch (RuntimeException e) {
            log.warn("上游响应不是预期结构，一致性比对退化为整包文本");
        }
        return body;
    }

    /** 缓存命中字段：OpenAI {@code usage.prompt_tokens_details.cached_tokens} 或 Claude {@code cache_read_input_tokens}。 */
    private static Integer cachedTokens(String body) {
        Integer openai = intAt(body, "usage", "prompt_tokens_details", "cached_tokens");
        return openai != null ? openai : intAt(body, "usage", "cache_read_input_tokens");
    }

    /** 按 JSON 路径取整数；字段缺失/非数字 → null（不把「缺失」当成 0）。 */
    private static Integer intAt(String body, String... path) {
        try {
            JsonNode node = JsonCodec.readTree(body);
            if (node == null) {
                return null;
            }
            for (String key : path) {
                node = node.path(key);
            }
            return node != null && node.isNumber() ? node.asInt() : null;
        } catch (RuntimeException e) {
            return null;
        }
    }
}
