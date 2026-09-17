package com.hioas.aap.detection;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 检测项打分与结论判定（纯函数，真源：17-spec §7 与 09-PRD §2/§3）。
 *
 * <p>为什么必须是纯函数：这些公式是本产品的核心资产，要能被逐条断言（AC-14…17、AC-37/38），
 * 且在任何执行器（真实探测、离线回放、回归基线）下结果一致——不掺任何 IO、时间、随机。
 *
 * <p>规则要点：
 * <ul>
 *   <li>D1 TTFT：{@code clamp(100*(3000-p50)/(3000-200))}，样本 &lt;3 判 FAILED</li>
 *   <li>D2 P50/TPS：{@code clamp(100*(tps-5)/(80-5))}</li>
 *   <li>D3 一致性：一致率 × 100</li>
 *   <li>D4/D5 RPM/TPM：{@code clamp(100*实测/申报)}，**未申报 → NOT_MEASURABLE**（不臆造分数）</li>
 *   <li>D6 缓存：命中 100 / 未命中 0 / 上游不返回字段 → NOT_MEASURABLE</li>
 *   <li>D7 指纹：5 条子证据线加权合成（0.15/0.25/0.35/0.15/0.10），不可测子项按比例重分配权重；
 *       score &lt; 40 触发**一票否决**；置信度按可测子项数 4+/3/≤2 → HIGH/MEDIUM/LOW</li>
 *   <li>D8 真实源：仅证据，**权重 0、不计分**</li>
 *   <li>总分：{@code Σ(score_i × weight_i)}，权重在**计分项**内归一化到 1（R-23），结果保留 2 位（R-24）</li>
 *   <li>结论（R-25 四分支）：否决 → FAIL；≥pass_score 且含不可测 → MANUAL_REVIEW；≥pass_score → PASS；
 *       ≥pass_score−10 → MANUAL_REVIEW；否则 FAIL</li>
 * </ul>
 */
public final class ProbeScoring {

    /** 默认阈值与权重（可被检测配置快照覆盖）。 */
    public static final int TTFT_BEST_MS = 200;
    public static final int TTFT_WORST_MS = 3000;
    public static final double TPS_MIN = 5;
    public static final double TPS_CAP = 80;
    public static final int DEFAULT_PASS_SCORE = 70;
    public static final int DEFAULT_VETO_SCORE = 40;

    public static final Map<String, Double> DEFAULT_WEIGHTS = Map.of(
            "D1", 0.10, "D2", 0.15, "D3", 0.10, "D4", 0.10,
            "D5", 0.10, "D6", 0.10, "D7", 0.35, "D8", 0.00);

    public static final Map<String, String> PROBE_NAMES = Map.of(
            "D1", "TTFT", "D2", "P50 延迟", "D3", "一致性", "D4", "RPM",
            "D5", "TPM", "D6", "缓存命中", "D7", "模型指纹", "D8", "真实源");

    private ProbeScoring() {
    }

    /** 单项打分结果。 */
    public record ProbeScore(String probeCode, ProbeStatus status, Double score,
                             Double weightOriginal, Double weightUsed, String note) {

        public boolean scored() {
            return score != null && status == ProbeStatus.SUCCESS;
        }
    }

    /** 探测状态（与 17-spec §4 ProbeStatus 一致）。 */
    public enum ProbeStatus {
        SUCCESS, FAILED, SKIPPED, NOT_MEASURABLE
    }

    // ------------------------------------------------------------------ D1…D8

    /** D1 TTFT：p50 越小越好；样本不足 3 个判 FAILED。 */
    public static ProbeScore scoreTtft(List<Integer> samplesMs) {
        if (samplesMs == null || samplesMs.size() < 3) {
            return failure("D1", "TTFT 有效样本不足（<3）");
        }
        List<Integer> sorted = samplesMs.stream().sorted().toList();
        double p50 = sorted.get(sorted.size() / 2);
        double raw = 100.0 * (TTFT_WORST_MS - p50) / (TTFT_WORST_MS - TTFT_BEST_MS);
        return success("D1", clamp(raw), "p50=" + (int) p50 + "ms");
    }

    /** D2 P50 延迟（用输出 TPS 表征端到端性能）。 */
    public static ProbeScore scoreThroughput(double tps) {
        double raw = 100.0 * (tps - TPS_MIN) / (TPS_CAP - TPS_MIN);
        return success("D2", clamp(raw), "tps=" + round2(tps));
    }

    /** D3 一致性：同 prompt、temp=0 并发 N 次的完全一致率。 */
    public static ProbeScore scoreDeterminism(int samples, int identical) {
        if (samples <= 0) {
            return failure("D3", "一致性无可比样本");
        }
        double rate = Math.min(1.0, (double) identical / samples);
        return success("D3", round2(rate * 100), "一致 " + identical + "/" + samples);
    }

    /** D4/D5 限速：实测 / 申报；未申报 → NOT_MEASURABLE（不编分数）。 */
    public static ProbeScore scoreQuota(String probeCode, Double measured, Integer declared) {
        if (declared == null || declared <= 0) {
            return new ProbeScore(probeCode, ProbeStatus.NOT_MEASURABLE, null, null, null, "供应商未申报，仅报告实测值");
        }
        if (measured == null) {
            return failure(probeCode, "未取得实测值");
        }
        double raw = 100.0 * measured / declared;
        return success(probeCode, clamp(raw), "实测=" + round2(measured) + " 申报=" + declared);
    }

    /** D6 缓存命中：三态（命中 100 / 未命中 0 / 上游无字段 NOT_MEASURABLE）。 */
    public static ProbeScore scoreCache(Boolean hit, boolean fieldPresent) {
        if (!fieldPresent) {
            return new ProbeScore("D6", ProbeStatus.NOT_MEASURABLE, null, null, null,
                    "上游未返回缓存字段，不可测（不臆造数值）");
        }
        if (hit == null) {
            return failure("D6", "缓存命中状态未知");
        }
        return success("D6", hit ? 100.0 : 0.0, hit ? "观测到缓存命中" : "未观测到缓存命中");
    }

    /** D7 指纹：5 条子证据线加权合成 + 权重重分配 + 置信度。 */
    public static ProbeScore scoreFingerprint(Map<String, Double> subScores) {
        Map<String, Double> subWeights = Map.of(
                "self_awareness", 0.15, "tokenizer", 0.25, "behavior", 0.35,
                "probability", 0.15, "context", 0.10);
        double weightSum = 0;
        double weighted = 0;
        int measurable = 0;
        for (var entry : subWeights.entrySet()) {
            Double score = subScores == null ? null : subScores.get(entry.getKey());
            if (score == null) {
                continue;
            }
            measurable++;
            weightSum += entry.getValue();
            weighted += entry.getValue() * score;
        }
        if (weightSum == 0) {
            return new ProbeScore("D7", ProbeStatus.NOT_MEASURABLE, null, null, null, "无可测子证据线");
        }
        double score = round2(weighted / weightSum);
        String note = "可测子项 " + measurable + "/5，权重已按比例重分配";
        return success("D7", score, note);
    }

    /** D7 置信度：可测子项 ≥4 → HIGH；3 → MEDIUM；≤2 → LOW（强制披露）。 */
    public static String fingerprintConfidence(int measurableSubItems) {
        if (measurableSubItems >= 4) {
            return "HIGH";
        }
        return measurableSubItems == 3 ? "MEDIUM" : "LOW";
    }

    /** D8 真实源：仅证据，不计分（权重 0）。 */
    public static ProbeScore scoreUpstreamOrigin(String evidenceSummary) {
        return new ProbeScore("D8", ProbeStatus.SUCCESS, null, 0.0, 0.0,
                "仅输出证据，不纳入总分：" + (evidenceSummary == null ? "" : evidenceSummary));
    }

    // ------------------------------------------------------------------ 总分与结论

    /** 汇总结果：总分（2 位小数）、结论、置信度、各项权重使用值。 */
    public record Summary(BigDecimal totalScore, String result, String confidence,
                          boolean vetoTriggered, List<ProbeScore> probes, int unmeasurableCount) {
    }

    /**
     * 合成总分与结论。
     *
     * @param scores    各项打分（D1–D8；D8 权重 0）
     * @param vetoScore 一票否决线（默认 40）
     * @param passScore 通过线（默认 70）
     */
    public static Summary summarize(List<ProbeScore> scores, int passScore, int vetoScore) {
        List<ProbeScore> counted = scores.stream()
                .filter(s -> !"D8".equals(s.probeCode()))
                .toList();
        double weightSum = counted.stream()
                .filter(ProbeScore::scored)
                .mapToDouble(s -> DEFAULT_WEIGHTS.getOrDefault(s.probeCode(), 0.0))
                .sum();

        double total = 0;
        List<ProbeScore> withWeights = new java.util.ArrayList<>();
        for (ProbeScore score : scores) {
            double original = DEFAULT_WEIGHTS.getOrDefault(score.probeCode(), 0.0);
            Double used = null;
            if (score.scored() && weightSum > 0 && !"D8".equals(score.probeCode())) {
                used = original / weightSum;
                total += score.score() * used;
            } else if ("D8".equals(score.probeCode())) {
                used = 0.0;
            }
            withWeights.add(new ProbeScore(score.probeCode(), score.status(), score.score(),
                    original, used == null ? null : round4(used), score.note()));
        }

        ProbeScore fingerprint = scores.stream()
                .filter(s -> "D7".equals(s.probeCode()))
                .findFirst().orElse(null);
        boolean veto = fingerprint != null && fingerprint.score() != null && fingerprint.score() < vetoScore;

        int unmeasurable = (int) scores.stream()
                .filter(s -> s.status() == ProbeStatus.NOT_MEASURABLE || s.status() == ProbeStatus.FAILED)
                .filter(s -> !"D8".equals(s.probeCode()))
                .count();

        BigDecimal rounded = BigDecimal.valueOf(total).setScale(2, RoundingMode.HALF_UP);
        String result;
        if (veto) {
            result = "FAIL";
        } else if (rounded.doubleValue() >= passScore) {
            result = unmeasurable > 0 ? "MANUAL_REVIEW" : "PASS";
        } else if (rounded.doubleValue() >= passScore - 10) {
            result = "MANUAL_REVIEW";
        } else {
            result = "FAIL";
        }

        int measurableSubItems = fingerprint == null ? 0 : countFingerprintSubItems(fingerprint.note());
        String confidence = measurableSubItems > 0 ? fingerprintConfidence(measurableSubItems)
                : (unmeasurable > 0 ? "LOW" : "MEDIUM");

        return new Summary(rounded, result, confidence, veto, List.copyOf(withWeights), unmeasurable);
    }

    /** 报告口径的结论文案（R-26：禁「正品」措辞）。 */
    public static String verdictText(String result, boolean veto, boolean hasUnmeasurable) {
        return verdictText(result, veto, hasUnmeasurable, null);
    }

    /**
     * 结论措辞（09-PRD「定位声明」字节级约束）：标准措辞为
     * 「未发现与宣称模型不一致的迹象（置信度：高/中/低）」，**禁止**出现「正品 / 已验证为正品」（R-26）。
     */
    public static String verdictText(String result, boolean veto, boolean hasUnmeasurable, String confidence) {
        return switch (result) {
            case "PASS" -> "未发现与宣称模型不一致的迹象（置信度：" + confidenceLabel(confidence) + "）";
            case "MANUAL_REVIEW" -> "存在不可测项或总分处于临界区间，建议人工复核";
            case "FAIL" -> veto ? "命中一票否决项（模型指纹相似度过低），判定未通过" : "检测项未达标，判定未通过";
            default -> "";
        };
    }

    /** 置信度中文标注；未提供时回落到「见报告」，保证措辞仍是标准句式。 */
    public static String confidenceLabel(String confidence) {
        return switch (confidence == null ? "" : confidence) {
            case "HIGH" -> "高";
            case "MEDIUM" -> "中";
            case "LOW" -> "低";
            default -> "见报告";
        };
    }

    private static int countFingerprintSubItems(String note) {
        if (note == null || !note.contains("可测子项")) {
            return 0;
        }
        try {
            String tail = note.substring(note.indexOf("可测子项") + 4).trim();
            return Integer.parseInt(tail.substring(0, tail.indexOf('/')));
        } catch (RuntimeException e) {
            return 0;
        }
    }

    private static ProbeScore success(String code, double score, String note) {
        return new ProbeScore(code, ProbeStatus.SUCCESS, round2(score),
                DEFAULT_WEIGHTS.getOrDefault(code, 0.0), null, note);
    }

    private static ProbeScore failure(String code, String note) {
        return new ProbeScore(code, ProbeStatus.FAILED, null, DEFAULT_WEIGHTS.getOrDefault(code, 0.0), null, note);
    }

    static double clamp(double value) {
        if (Double.isNaN(value)) {
            return 0;
        }
        return Math.max(0, Math.min(100, value));
    }

    static double round2(double value) {
        return BigDecimal.valueOf(value).setScale(2, RoundingMode.HALF_UP).doubleValue();
    }

    static double round4(double value) {
        return BigDecimal.valueOf(value).setScale(4, RoundingMode.HALF_UP).doubleValue();
    }

    /** 便捷：按 code 取权重（未列出的项默认 0）。 */
    public static double weightOf(String probeCode) {
        return Optional.ofNullable(DEFAULT_WEIGHTS.get(probeCode)).orElse(0.0);
    }

    /** 汇总时用于报告展示的 map（code → 名称）。 */
    public static Map<String, String> probeNameMap() {
        return new LinkedHashMap<>(PROBE_NAMES);
    }
}
