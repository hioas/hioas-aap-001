package com.hioas.aap.report;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.detection.DetectionJobEntity;
import com.hioas.aap.detection.DetectionJobMapper;
import com.hioas.aap.detection.DetectionResultEntity;
import com.hioas.aap.detection.ProbeScoring;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 检测报告接口（RPT-01…04；AC-18/21/49）。
 *
 * <p>红线：报告正文与 HTML **不得**出现「正品 / 保证为真」表述（R-26），统一措辞见 {@link ProbeScoring#verdictText}。
 * 导出接口本期返回 HTML 版本地址（对象存储 PDF 需 MinIO 凭据，未接入 → 见 T14/T15 台账）。
 */
@RestController
@RequestMapping("/api/v1/reports")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class ReportController {

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private final ReportService reportService;
    private final DetectionJobMapper jobMapper;

    public ReportController(ReportService reportService, DetectionJobMapper jobMapper) {
        this.reportService = reportService;
        this.jobMapper = jobMapper;
    }

    /** RPT-01 报告列表。 */
    @GetMapping
    public ApiEnvelope<com.hioas.aap.common.PageResult<ReportViews.Summary>> list(
            @AuthenticationPrincipal AuthPrincipal principal,
            @RequestParam(required = false) Integer page,
            @RequestParam(required = false) Integer pageSize,
            @RequestParam(required = false) String result) {
        List<ReportViews.Summary> items = reportService.list(principal, page, pageSize, result).stream()
                .map(ReportController::toSummary)
                .toList();
        com.hioas.aap.common.PageQuery pageQuery = com.hioas.aap.common.PageQuery.of(page, pageSize);
        return ApiEnvelope.ok(com.hioas.aap.common.PageResult.of(items, pageQuery.page(), pageQuery.pageSize(),
                reportService.count(principal)));
    }

    /** RPT-02 报告详情（多维度专业版与未通过页共用的超集）。 */
    @GetMapping("/{reportId}")
    public ApiEnvelope<ReportViews.Full> detail(@AuthenticationPrincipal AuthPrincipal principal,
                                                @PathVariable Long reportId) {
        return ApiEnvelope.ok(buildFull(reportService.requireOwned(principal, reportId)));
    }

    /** RPT-03 在线 HTML 版。 */
    @GetMapping(value = "/{reportId}/html", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> html(@AuthenticationPrincipal AuthPrincipal principal,
                                       @PathVariable Long reportId) {
        ReportEntity report = reportService.requireOwned(principal, reportId);
        String html = report.getRenderedHtml() == null
                ? "<html><body><p>报告尚未渲染</p></body></html>" : report.getRenderedHtml();
        return ResponseEntity.ok().contentType(MediaType.TEXT_HTML).body(html);
    }

    /** RPT-04 导出（本期返回 HTML 版地址；PDF 对象存储未接线）。 */
    @GetMapping("/{reportId}/export")
    public ApiEnvelope<ReportViews.Export> export(@AuthenticationPrincipal AuthPrincipal principal,
                                                  @PathVariable Long reportId) {
        ReportEntity report = reportService.requireOwned(principal, reportId);
        String url = "/api/v1/reports/" + report.getId() + "/html";
        return ApiEnvelope.ok(new ReportViews.Export(url, url,
                "检测报告-" + report.getReportNo() + ".html",
                RFC3339.format(OffsetDateTime.now(ZoneOffset.UTC).plusHours(1))));
    }

    // ------------------------------------------------------------------ 组装

    private ReportViews.Full buildFull(ReportEntity report) {
        List<ReportSectionEntity> sections = reportService.sections(report.getId());
        List<DetectionResultEntity> probes = report.getJobId() == null ? List.of()
                : reportService.probes(report.getJobId());
        DetectionJobEntity job = report.getJobId() == null ? null : jobMapper.selectOneById(report.getJobId());

        List<ReportViews.Section> sectionViews = new ArrayList<>();
        List<ReportViews.Dim> dims = new ArrayList<>();
        for (ReportSectionEntity section : sections) {
            List<ReportViews.SectionItem> items = JsonCodec.toList(section.getItems(), ReportViews.SectionItem.class);
            sectionViews.add(new ReportViews.Section(section.getSectionCode(), section.getSectionName(),
                    section.getAvgScore(), section.getScored(), section.getNote(), items));
            if (Boolean.TRUE.equals(section.getScored())) {
                dims.add(new ReportViews.Dim(section.getSectionCode(), section.getSectionName(), section.getAvgScore()));
            }
        }

        List<ReportViews.KeyMetric> keyMetrics = keyMetrics(probes);
        List<ReportViews.Finding> findings = findings(probes);
        List<ReportViews.Evidence> evidence = probes.stream()
                .filter(p -> p.getEvidence() != null)
                .map(p -> new ReportViews.Evidence(p.getProbeCode() + " " + p.getProbeName(), p.getEvidence()))
                .toList();

        DetectionResultEntity failing = probes.stream()
                .filter(p -> p.getScore() == null || p.getScore().doubleValue() < 70)
                .findFirst().orElse(null);
        ReportViews.Detail detail = failing == null ? null : new ReportViews.Detail(
                failing.getProbeCode(), failing.getProbeName() + " · 详情", failing.getScore(),
                List.of(failing.getExplanation() == null ? "" : failing.getExplanation(),
                        failing.getEvidence() == null ? "无原始证据" : failing.getEvidence()));

        int passCount = (int) probes.stream().filter(p -> p.getScore() != null && p.getScore().doubleValue() >= 70).count();
        int unmeasurable = (int) probes.stream()
                .filter(p -> "NOT_MEASURABLE".equals(p.getStatus()) || "FAILED".equals(p.getStatus())).count();

        return new ReportViews.Full(
                String.valueOf(report.getId()), String.valueOf(report.getId()), report.getReportNo(),
                report.getJobId() == null ? null : String.valueOf(report.getJobId()),
                report.getCredentialId() == null ? null : String.valueOf(report.getCredentialId()),
                report.getChannelName(), report.getTotalScore(), report.getResult(), report.getConfidence(),
                ProbeScoring.confidenceLabel(report.getConfidence()), passCount, probes.size(), unmeasurable,
                report.getVetoTriggered(), report.getVerdict(), report.getProviderName(), report.getProviderCode(),
                report.getApiKeyMasked(), modelList(report), format(report.getDetectedAt()),
                job == null ? null : job.getTriggerType(), durationText(report),
                report.getCostEstimateUsd(), report.getCostActualUsd(), keyMetrics, sectionViews, dims, detail,
                findings, evidence, report.getDisclaimer(), vetoNote(report), WEIGHT_NOTE,
                metricsOf(probes));
    }

    private static final String WEIGHT_NOTE =
            "总分 = Σ(检测项得分 × 权重)；默认权重：指纹 0.35、P50 0.15、TTFT/一致性/RPM/TPM/缓存各 0.10；"
                    + "真实源仅证据不计分。权重在计分项内归一化到 1；不可测项不占权重。"
                    + "置信度：可测子项 ≥4 且一致 → 高。";

    private static String vetoNote(ReportEntity report) {
        if (!Boolean.TRUE.equals(report.getVetoTriggered())) {
            return null;
        }
        return "一票否决项：模型指纹得分低于 40 将直接判定不通过。本项得分按 5 条子证据线加权"
                + "（行为 0.35 / Tokenizer 0.25 / 自我认知 0.15 / 概率 0.15 / 上下文 0.10）。";
    }

    private static String durationText(ReportEntity report) {
        if (report.getDurationSeconds() == null) {
            return null;
        }
        int seconds = report.getDurationSeconds();
        return seconds < 60 ? seconds + " 秒" : (seconds / 60) + " 分 " + (seconds % 60) + " 秒";
    }

    private static List<String> modelList(ReportEntity report) {
        if (report.getModelList() == null) {
            return List.of();
        }
        try {
            List<Map<String, Object>> raw = JsonCodec.fromJson(report.getModelList(),
                    new tools.jackson.core.type.TypeReference<>() {
                    });
            List<String> names = new ArrayList<>();
            if (raw != null) {
                for (Map<String, Object> entry : raw) {
                    Object name = entry.get("model_name");
                    if (name != null) {
                        names.add(String.valueOf(name));
                    }
                }
            }
            return names;
        } catch (RuntimeException e) {
            return List.of();
        }
    }

    private static List<ReportViews.KeyMetric> keyMetrics(List<DetectionResultEntity> probes) {
        List<ReportViews.KeyMetric> metrics = new ArrayList<>();
        for (DetectionResultEntity probe : probes) {
            if ("D8".equals(probe.getProbeCode())) {
                continue;
            }
            Map<String, Object> m = probe.getMetrics() == null ? Map.of() : JsonCodec.toMap(probe.getMetrics());
            Object value = m.values().stream().findFirst().orElse(null);
            metrics.add(new ReportViews.KeyMetric(probe.getProbeCode(),
                    ProbeScoring.PROBE_NAMES.getOrDefault(probe.getProbeCode(), probe.getProbeCode()),
                    value == null ? (probe.getScore() == null ? "—" : probe.getScore().toPlainString())
                            : String.valueOf(value),
                    "", probe.getStatus(), tone(probe)));
            if (metrics.size() >= 6) {
                break;
            }
        }
        return metrics;
    }

    private static String tone(DetectionResultEntity probe) {
        if ("NOT_MEASURABLE".equals(probe.getStatus()) || "FAILED".equals(probe.getStatus())) {
            return "warning";
        }
        if (probe.getScore() == null) {
            return "info";
        }
        return probe.getScore().doubleValue() >= 70 ? "success" : "danger";
    }

    private static List<ReportViews.Finding> findings(List<DetectionResultEntity> probes) {
        List<ReportViews.Finding> findings = new ArrayList<>();
        for (DetectionResultEntity probe : probes) {
            if (probe.getScore() != null && probe.getScore().doubleValue() < 70) {
                findings.add(new ReportViews.Finding(
                        ProbeScoring.PROBE_NAMES.getOrDefault(probe.getProbeCode(), probe.getProbeCode()) + " 未达标",
                        probe.getExplanation() == null ? "该项得分偏低，建议核对上游能力。" : probe.getExplanation(),
                        "danger"));
            } else if ("NOT_MEASURABLE".equals(probe.getStatus())) {
                findings.add(new ReportViews.Finding(
                        ProbeScoring.PROBE_NAMES.getOrDefault(probe.getProbeCode(), probe.getProbeCode()) + " 不可测",
                        "上游未提供必要字段或供应商未申报，本项不计分（权重已重分配）。", "warning"));
            }
        }
        return findings;
    }

    private static Map<String, Object> metricsOf(List<DetectionResultEntity> probes) {
        Map<String, Object> all = new LinkedHashMap<>();
        for (DetectionResultEntity probe : probes) {
            all.put(probe.getProbeCode(), probe.getMetrics() == null ? Map.of() : JsonCodec.toMap(probe.getMetrics()));
        }
        return all;
    }

    private static ReportViews.Summary toSummary(ReportEntity report) {
        return new ReportViews.Summary(String.valueOf(report.getId()), String.valueOf(report.getId()),
                report.getReportNo(), report.getResult(), report.getTotalScore(), report.getConfidence(),
                format(report.getDetectedAt()), format(report.getCreatedAt()), report.getProviderCode(),
                report.getCredentialId() == null ? null : String.valueOf(report.getCredentialId()),
                report.getChannelName());
    }

    private static String format(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    /** 供其它组件复用的常量（导出/校验用）。 */
    public static String disclaimer() {
        return ReportService.DISCLAIMER;
    }

    /**
     * 报告正文禁用的**保证性断言**（R-26 校验用）。
     *
     * <p>判定口径：禁止对模型真伪作断言，不禁止在免责声明中出现「不是真伪判决」这类**否定**表达。
     * 但服务端自身输出连「正品」字样都不用（更严格），见 {@link ReportService#DISCLAIMER}。
     */
    public static List<String> forbiddenPhrases() {
        return List.of("保证为真", "保证正品", "官方正版", "100% 真实", "绝对真实", "已验证该模型为正品");
    }

    /** 全量正文（含免责声明）是否通过 R-26 措辞校验。 */
    public static boolean wordingCompliant(String text) {
        if (text == null || text.isBlank()) {
            return true;
        }
        return forbiddenPhrases().stream().noneMatch(text::contains);
    }

    /** 组装 BigDecimal 的空安全展示。 */
    static String plain(BigDecimal value) {
        return value == null ? "—" : value.toPlainString();
    }

    static ApiException notFound() {
        return new ApiException(ErrorCode.E_1406, "报告不存在");
    }
}
