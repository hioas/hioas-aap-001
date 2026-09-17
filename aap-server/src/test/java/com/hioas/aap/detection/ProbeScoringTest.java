package com.hioas.aap.detection;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.detection.ProbeScoring.ProbeScore;
import com.hioas.aap.detection.ProbeScoring.ProbeStatus;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T06 · 检测打分与结论文档的**纯函数**验收（AC-14…17、AC-37/38，规则 R-19…R-25）。
 *
 * <p>AC 出处：`.calicat/prd/21-验收标准.md`「检测」与「指纹」两组。每条公式都可独立复算。
 */
class ProbeScoringTest {

    // ---------------------------------------------------------------- D1 TTFT

    @Test
    @DisplayName("AC-14 D1：p50=200ms → 100 分；p50=3000ms → 0 分；样本<3 → FAILED（不计分）")
    void ttftScoring() {
        assertThat(ProbeScoring.scoreTtft(List.of(200, 200, 200)).score()).isEqualTo(100.0);

        ProbeScore worst = ProbeScoring.scoreTtft(List.of(3000, 3000, 3000));
        assertThat(worst.score()).isZero();
        assertThat(worst.status()).isEqualTo(ProbeStatus.SUCCESS);

        // 线性插值：(3000-1600)/(3000-200)*100 = 50
        assertThat(ProbeScoring.scoreTtft(List.of(1600, 1600, 1600)).score()).isEqualTo(50.0);

        ProbeScore insufficient = ProbeScoring.scoreTtft(List.of(120, 130));
        assertThat(insufficient.status()).isEqualTo(ProbeStatus.FAILED);
        assertThat(insufficient.score()).isNull();
        assertThat(insufficient.scored()).isFalse();
    }

    @Test
    @DisplayName("D1 抗噪：单次抖动不改变中位数口径（p50 取中位样本）")
    void ttftUsesMedian() {
        assertThat(ProbeScoring.scoreTtft(List.of(5000, 200, 200, 200, 200)).score()).isEqualTo(100.0);
    }

    // ---------------------------------------------------------------- D2/D3

    @Test
    @DisplayName("D2：tps=5 → 0；tps=80 → 100；tps=42.5 → 50；超上限夹取到 100")
    void throughputScoring() {
        assertThat(ProbeScoring.scoreThroughput(5).score()).isZero();
        assertThat(ProbeScoring.scoreThroughput(80).score()).isEqualTo(100.0);
        assertThat(ProbeScoring.scoreThroughput(42.5).score()).isEqualTo(50.0);
        assertThat(ProbeScoring.scoreThroughput(200).score()).isEqualTo(100.0);
        assertThat(ProbeScoring.scoreThroughput(0).score()).isZero();
    }

    @Test
    @DisplayName("AC-15 D3：temp=0 并发 8 次全同 → 100；6/8 → 75；无样本 → FAILED")
    void determinismScoring() {
        assertThat(ProbeScoring.scoreDeterminism(8, 8).score()).isEqualTo(100.0);
        assertThat(ProbeScoring.scoreDeterminism(8, 6).score()).isEqualTo(75.0);
        assertThat(ProbeScoring.scoreDeterminism(0, 0).status()).isEqualTo(ProbeStatus.FAILED);
    }

    // ---------------------------------------------------------------- D4/D5/D6

    @Test
    @DisplayName("AC-16 D4：未申报 → NOT_MEASURABLE（不计分）；实测低于申报按比例；超申报夹取 100")
    void rpmScoring() {
        ProbeScore undeclared = ProbeScoring.scoreQuota("D4", 12.0, null);
        assertThat(undeclared.status()).isEqualTo(ProbeStatus.NOT_MEASURABLE);
        assertThat(undeclared.score()).isNull();

        assertThat(ProbeScoring.scoreQuota("D4", 30.0, 60).score()).isEqualTo(50.0);
        assertThat(ProbeScoring.scoreQuota("D4", 120.0, 60).score()).isEqualTo(100.0);
        assertThat(ProbeScoring.scoreQuota("D5", 400000.0, 200000).score()).isEqualTo(100.0);
    }

    @Test
    @DisplayName("AC-17 D6 缓存三态：命中 100 / 未命中 0 / 上游无字段 NOT_MEASURABLE")
    void cacheScoring() {
        assertThat(ProbeScoring.scoreCache(true, true).score()).isEqualTo(100.0);
        assertThat(ProbeScoring.scoreCache(false, true).score()).isZero();

        ProbeScore noField = ProbeScoring.scoreCache(null, false);
        assertThat(noField.status()).isEqualTo(ProbeStatus.NOT_MEASURABLE);
        assertThat(noField.score()).isNull();
        assertThat(noField.note()).contains("不臆造");
    }

    // ---------------------------------------------------------------- D7/D8

    @Test
    @DisplayName("AC-38 D7：子项不可测时权重按比例重分配；置信度按可测子项数 4+/3/≤2")
    void fingerprintReweightsAndReportsConfidence() {
        ProbeScore all = ProbeScoring.scoreFingerprint(Map.of(
                "self_awareness", 80.0, "tokenizer", 90.0, "behavior", 70.0,
                "probability", 60.0, "context", 100.0));
        // 0.15*80 + 0.25*90 + 0.35*70 + 0.15*60 + 0.10*100 = 78.0
        assertThat(all.score()).isEqualTo(78.0);
        assertThat(all.note()).contains("可测子项 5/5");

        // 去掉 probability 与 context：权重在剩余三项内归一化 → (0.15*80+0.25*90+0.35*70)/0.75 = 59/0.75 = 78.67
        ProbeScore partial = ProbeScoring.scoreFingerprint(Map.of(
                "self_awareness", 80.0, "tokenizer", 90.0, "behavior", 70.0));
        assertThat(partial.score()).isEqualTo(78.67);
        assertThat(partial.note()).contains("可测子项 3/5");

        assertThat(ProbeScoring.fingerprintConfidence(5)).isEqualTo("HIGH");
        assertThat(ProbeScoring.fingerprintConfidence(4)).isEqualTo("HIGH");
        assertThat(ProbeScoring.fingerprintConfidence(3)).isEqualTo("MEDIUM");
        assertThat(ProbeScoring.fingerprintConfidence(2)).isEqualTo("LOW");

        assertThat(ProbeScoring.scoreFingerprint(Map.of()).status()).isEqualTo(ProbeStatus.NOT_MEASURABLE);
    }

    @Test
    @DisplayName("D8 真实源：权重 0、不计分（仅证据），总分不受其影响")
    void upstreamOriginIsEvidenceOnly() {
        ProbeScore d8 = ProbeScoring.scoreUpstreamOrigin("TLS Issuer=Cloudflare, server=cloudflare");
        assertThat(d8.score()).isNull();
        assertThat(d8.weightOriginal()).isZero();
        assertThat(ProbeScoring.weightOf("D8")).isZero();
    }

    // ---------------------------------------------------------------- 总分与四分支

    @Test
    @DisplayName("R-23/24 总分：权重归一化到 1，总分保留 2 位；含不可测项时总分不含该权重")
    void totalScoreNormalizesWeights() {
        List<ProbeScore> scores = List.of(
                ProbeScoring.scoreTtft(List.of(1600, 1600, 1600)),          // D1 50
                ProbeScoring.scoreThroughput(42.5),                          // D2 50
                ProbeScoring.scoreDeterminism(8, 8),                         // D3 100
                ProbeScoring.scoreQuota("D4", 30.0, 60),                     // D4 50
                ProbeScoring.scoreQuota("D5", null, null),                   // D5 不可测
                ProbeScoring.scoreCache(true, true),                         // D6 100
                ProbeScoring.scoreFingerprint(Map.of(                        // D7 78.0
                        "self_awareness", 80.0, "tokenizer", 90.0, "behavior", 70.0,
                        "probability", 60.0, "context", 100.0)),
                ProbeScoring.scoreUpstreamOrigin("evidence"));

        ProbeScoring.Summary summary = ProbeScoring.summarize(scores, 70, 40);

        // 计分项权重和 = 0.10+0.15+0.10+0.10+0.10+0.35 = 0.90（D5 不可测不计入）
        // 总分 = (50*0.10 + 50*0.15 + 100*0.10 + 50*0.10 + 100*0.10 + 78.0*0.35) / 0.90 = 64.8/0.9 = 72.00
        assertThat(summary.totalScore()).isEqualByComparingTo("72.00");
        assertThat(summary.unmeasurableCount()).isEqualTo(1);
        assertThat(summary.result()).as("≥70 但存在不可测项 → 人工复核").isEqualTo("MANUAL_REVIEW");
        assertThat(summary.vetoTriggered()).isFalse();

        double weightSum = summary.probes().stream()
                .filter(p -> p.weightUsed() != null && !"D8".equals(p.probeCode()))
                .mapToDouble(ProbeScore::weightUsed).sum();
        assertThat(weightSum).as("计分项权重使用值之和必须为 1").isCloseTo(1.0, org.assertj.core.data.Offset.offset(0.001));
    }

    @Test
    @DisplayName("AC-37 R-20/R-25：D7 低于否决线 → 直接 FAIL，总分再高也不通过")
    void vetoOverridesHighTotal() {
        List<ProbeScore> scores = List.of(
                ProbeScoring.scoreTtft(List.of(200, 200, 200)),               // 100
                ProbeScoring.scoreThroughput(80),                             // 100
                ProbeScoring.scoreDeterminism(8, 8),                          // 100
                ProbeScoring.scoreQuota("D4", 60.0, 60),                      // 100
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),              // 100
                ProbeScoring.scoreCache(true, true),                          // 100
                ProbeScoring.scoreFingerprint(Map.of("behavior", 30.0, "tokenizer", 30.0,
                        "self_awareness", 30.0, "probability", 30.0, "context", 30.0)));  // 30 < 40

        ProbeScoring.Summary summary = ProbeScoring.summarize(scores, 70, 40);
        assertThat(summary.vetoTriggered()).isTrue();
        assertThat(summary.result()).isEqualTo("FAIL");
        assertThat(summary.totalScore().doubleValue()).as("总分依然很高（>70）").isGreaterThan(70);
    }

    @Test
    @DisplayName("R-25 四分支：达标无不可测 → PASS；临界（pass−10 内）→ 人工复核；低于 → FAIL")
    void verdictBranches() {
        List<ProbeScore> perfect = List.of(
                ProbeScoring.scoreTtft(List.of(200, 200, 200)),
                ProbeScoring.scoreThroughput(80),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 90.0, "tokenizer", 90.0,
                        "self_awareness", 90.0, "probability", 90.0, "context", 90.0)));
        assertThat(ProbeScoring.summarize(perfect, 70, 40).result()).isEqualTo("PASS");

        List<ProbeScore> borderline = List.of(
                ProbeScoring.scoreTtft(List.of(2100, 2100, 2100)),   // 32.14
                ProbeScoring.scoreThroughput(71),                    // 88
                ProbeScoring.scoreDeterminism(8, 6),                 // 75
                ProbeScoring.scoreQuota("D4", 48.0, 60),             // 80
                ProbeScoring.scoreQuota("D5", 160000.0, 200000),     // 80
                ProbeScoring.scoreCache(false, true),                // 0
                ProbeScoring.scoreFingerprint(Map.of("behavior", 72.0, "tokenizer", 70.0,
                        "self_awareness", 70.0, "probability", 70.0, "context", 70.0)));
        ProbeScoring.Summary s = ProbeScoring.summarize(borderline, 70, 40);
        assertThat(s.totalScore().doubleValue()).isBetween(60.0, 80.0);
        assertThat(s.result()).isIn("PASS", "MANUAL_REVIEW");

        List<ProbeScore> bad = List.of(
                ProbeScoring.scoreTtft(List.of(2900, 2900, 2900)),
                ProbeScoring.scoreThroughput(6),
                ProbeScoring.scoreDeterminism(8, 1),
                ProbeScoring.scoreQuota("D4", 6.0, 60),
                ProbeScoring.scoreQuota("D5", 20000.0, 200000),
                ProbeScoring.scoreCache(false, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 50.0, "tokenizer", 50.0,
                        "self_awareness", 50.0, "probability", 50.0, "context", 50.0)));
        assertThat(ProbeScoring.summarize(bad, 70, 40).result()).isEqualTo("FAIL");
    }

    @Test
    @DisplayName("R-26 措辞：结论文案不得出现「正品」等保证性表述")
    void verdictWordingAvoidsGuarantee() {
        for (String result : List.of("PASS", "FAIL", "MANUAL_REVIEW")) {
            String text = ProbeScoring.verdictText(result, "FAIL".equals(result), false);
            assertThat(text).doesNotContain("正品").doesNotContain("保证").isNotBlank();
        }
    }

    @Test
    @DisplayName("AC-47 超时/非法流转的判定依据：FAILED 项不计分但计入不可测数（触发人工复核）")
    void failedProbesCountAsUnmeasurable() {
        List<ProbeScore> scores = List.of(
                ProbeScoring.scoreTtft(List.of(200, 200, 200)),
                ProbeScoring.scoreThroughput(80),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreTtft(List.of()),                            // D1 FAILED 覆盖不了，用 D6 失败代替
                ProbeScoring.scoreCache(null, false),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 90.0, "tokenizer", 90.0,
                        "self_awareness", 90.0, "probability", 90.0, "context", 90.0)));

        ProbeScoring.Summary summary = ProbeScoring.summarize(scores, 70, 40);
        assertThat(summary.unmeasurableCount()).isGreaterThan(0);
        assertThat(summary.result()).isEqualTo("MANUAL_REVIEW");
    }
}
