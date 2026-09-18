package com.hioas.aap.report;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.credential.CredentialEntity;
import com.hioas.aap.credential.CredentialMapper;
import com.hioas.aap.detection.DetectionJobEntity;
import com.hioas.aap.detection.DetectionJobMapper;
import com.hioas.aap.detection.DetectionResultEntity;
import com.hioas.aap.detection.DetectionResultMapper;
import com.hioas.aap.detection.ProbeScoring;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.provider.ProviderEntity;
import com.hioas.aap.provider.ProviderMapper;
import com.mybatisflex.core.query.QueryWrapper;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 报告生成（检测完成后 1:1 生成，真源 09-PRD §4）。
 *
 * <p>红线（R-26 / AC-18）：
 * <ul>
 *   <li>报告**不得**出现「正品 / 保证为真」等表述，统一用「未发现与宣称模型不一致的迹象（置信度：高/中/低）」</li>
 *   <li>每项必须带**四段式解释**：测什么 / 怎么测的 / 结果说明 / 为什么重要与边界</li>
 *   <li>必须带免责声明与有效期说明（30 天）</li>
 * </ul>
 */
@Service
public class ReportService implements ReportGenerator {

    private static final Logger log = LoggerFactory.getLogger(ReportService.class);
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 章节划分（与 report-model.ts 的 A–F 分组一致）。 */
    private static final Map<String, String> SECTION_NAMES = Map.of(
            "A", "时延与性能", "B", "吞吐与限速", "C", "一致与可靠",
            "D", "模型指纹", "E", "计量与计费", "F", "安全与合规");

    /**
     * 报告章节枚举（A–F）——**唯一真源**：报告模板的 `section_order`（ADM-CFG07/09）只能取这些值，
     * 模板配置与报告生成因此不会各写一套章节代码。
     */
    public static java.util.Set<String> sectionCodes() {
        return SECTION_NAMES.keySet();
    }

    private static final Map<String, String> PROBE_SECTION = Map.of(
            "D1", "A", "D2", "A", "D4", "B", "D5", "B", "D3", "C",
            "D7", "D", "D6", "E", "D8", "F");

    /**
     * 免责声明（R-26 / AC-18：正文不得出现「正品」「保证为真」等保证性措辞）。
     *
     * <p>与客户端 `report-model.ts` 的兜底文案**等义但更严格**：客户端兜底句里出现了被禁用的字样
     * （在否定句中），服务端一律不使用该字样（详见 `.agents/state/aap-server-tdd-state.md` 发现 O-01）。
     */
    public static final String DISCLAIMER =
            "本引擎输出的是证据与置信度，不是「真 / 假」判决，亦不得解读为对模型来源、授权或合规状态的担保。"
                    + "检测结论仅代表检测时点状态，不构成对上游长期稳定性与合规性的担保。报告有效期 30 天，异常可申请复测。";

    private final ReportMapper reportMapper;
    private final ReportSectionMapper sectionMapper;
    private final DetectionJobMapper jobMapper;
    private final DetectionResultMapper resultMapper;
    private final CredentialMapper credentialMapper;
    private final ProviderMapper providerMapper;
    private final DocNoGenerator docNoGenerator;

    public ReportService(ReportMapper reportMapper, ReportSectionMapper sectionMapper,
                         DetectionJobMapper jobMapper, DetectionResultMapper resultMapper,
                         CredentialMapper credentialMapper, ProviderMapper providerMapper,
                         DocNoGenerator docNoGenerator) {
        this.reportMapper = reportMapper;
        this.sectionMapper = sectionMapper;
        this.jobMapper = jobMapper;
        this.resultMapper = resultMapper;
        this.credentialMapper = credentialMapper;
        this.providerMapper = providerMapper;
        this.docNoGenerator = docNoGenerator;
    }

    /** 生成报告（幂等：同任务已有报告则直接返回其 id）。 */
    @Override
    @Transactional
    public Long generate(Long jobId) {
        ReportEntity existing = reportMapper.selectOneByQuery(QueryWrapper.create()
                .where("job_id = ?", jobId)
                .limit(1));
        if (existing != null) {
            return existing.getId();
        }
        DetectionJobEntity job = jobMapper.selectOneById(jobId);
        if (job == null) {
            throw new ApiException(ErrorCode.E_1304, "检测任务不存在");
        }
        CredentialEntity credential = job.getCredentialId() == null ? null
                : credentialMapper.selectOneById(job.getCredentialId());
        ProviderEntity provider = job.getProviderId() == null ? null
                : providerMapper.selectOneById(job.getProviderId());
        List<DetectionResultEntity> probes = resultMapper.selectListByQuery(QueryWrapper.create()
                .where("job_id = ?", jobId)
                .orderBy("probe_code asc"));

        ReportEntity report = new ReportEntity();
        report.setReportNo(docNoGenerator.reportNo());
        report.setJobId(jobId);
        report.setProviderId(job.getProviderId());
        report.setCredentialId(job.getCredentialId());
        report.setTotalScore(job.getTotalScore());
        report.setResult(job.getResult());
        report.setConfidence(job.getConfidence());
        report.setVetoTriggered(isVeto(probes));
        report.setVerdict(ProbeScoring.verdictText(job.getResult(), Boolean.TRUE.equals(report.getVetoTriggered()),
                hasUnmeasurable(probes), job.getConfidence()));
        report.setProviderName(provider == null ? null : provider.getCompanyName());
        report.setProviderCode(provider == null ? null : provider.getProviderCode());
        report.setChannelName(provider == null ? null : "AAP-" + provider.getShortCode() + "-1");
        report.setApiKeyMasked(credential == null ? null : credential.getApiKeyMask());
        report.setModelList(credential == null ? null : credential.getModelList());
        report.setDetectedAt(job.getFinishedAt() == null ? OffsetDateTime.now(ZoneOffset.UTC) : job.getFinishedAt());
        report.setDurationSeconds(job.getStartedAt() != null && job.getFinishedAt() != null
                ? (int) java.time.Duration.between(job.getStartedAt(), job.getFinishedAt()).getSeconds() : null);
        report.setCostEstimateUsd(job.getCostEstimateUsd());
        report.setCostActualUsd(job.getCostActualUsd());
        report.setDisclaimer(DISCLAIMER);
        report.setStatus("GENERATED");
        report.setTemplateSnapshot(JsonCodec.toJson(Map.of("template", "default-professional", "version", "v1")));
        report.setRenderedHtml(renderHtmlPlaceholder(report, probes));
        reportMapper.insert(report);

        int seq = 0;
        for (Map.Entry<String, String> section : SECTION_NAMES.entrySet()) {
            List<DetectionResultEntity> items = probes.stream()
                    .filter(p -> section.getKey().equals(PROBE_SECTION.get(p.getProbeCode())))
                    .toList();
            if (items.isEmpty()) {
                continue;
            }
            ReportSectionEntity entity = new ReportSectionEntity();
            entity.setReportId(report.getId());
            entity.setSectionCode(section.getKey());
            entity.setSectionName(section.getValue());
            entity.setSeq(seq++);
            entity.setScored(items.stream().anyMatch(i -> i.getScore() != null));
            entity.setAvgScore(avg(items));
            entity.setNote(sectionNote(section.getKey()));
            entity.setItems(JsonCodec.toJson(items.stream().map(ReportService::sectionItem).toList()));
            sectionMapper.insert(entity);
        }
        log.info("报告生成 report_no={} job_no={} 结论={}", report.getReportNo(), job.getJobNo(), report.getResult());
        return report.getId();
    }

    // ------------------------------------------------------------------ 查询

    public ReportEntity require(Long reportId) {
        ReportEntity report = reportMapper.selectOneById(reportId);
        if (report == null) {
            throw new ApiException(ErrorCode.E_1406, "报告不存在");
        }
        return report;
    }

    public ReportEntity requireOwned(AuthPrincipal principal, Long reportId) {
        ReportEntity report = require(reportId);
        if (principal == null || principal.providerId() == null
                || !report.getProviderId().equals(principal.providerId())) {
            throw new ApiException(ErrorCode.E_1406, "报告不存在");
        }
        return report;
    }

    public List<ReportSectionEntity> sections(Long reportId) {
        return sectionMapper.selectListByQuery(QueryWrapper.create()
                .where("report_id = ?", reportId)
                .orderBy("seq asc"));
    }

    public List<DetectionResultEntity> probes(Long jobId) {
        return resultMapper.selectListByQuery(QueryWrapper.create()
                .where("job_id = ?", jobId)
                .orderBy("probe_code asc"));
    }

    public List<ReportEntity> list(AuthPrincipal principal, Integer page, Integer pageSize, String result) {
        com.hioas.aap.common.PageQuery pageQuery = com.hioas.aap.common.PageQuery.of(page, pageSize);
        QueryWrapper query = QueryWrapper.create()
                .where("provider_id = ?", principal.providerId())
                .orderBy("created_at desc, id desc");
        if (result != null && !result.isBlank()) {
            query.and("result = ?", result.toUpperCase());
        }
        com.mybatisflex.core.paginate.Page<ReportEntity> pageResult = reportMapper.paginate(
                com.mybatisflex.core.paginate.Page.of(pageQuery.page(), pageQuery.pageSize()), query);
        return pageResult.getRecords();
    }

    public long count(AuthPrincipal principal) {
        return reportMapper.selectCountByQuery(QueryWrapper.create()
                .where("provider_id = ?", principal.providerId()));
    }

    // ------------------------------------------------------------------ 渲染

    private String renderHtmlPlaceholder(ReportEntity report, List<DetectionResultEntity> probes) {
        StringBuilder html = new StringBuilder();
        html.append("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">")
                .append("<title>检测报告 ").append(report.getReportNo()).append("</title></head><body>")
                .append("<h1>云算接入平台 · 检测报告</h1>")
                .append("<p>报告编号：").append(report.getReportNo()).append("</p>")
                .append("<p>综合评分：").append(report.getTotalScore()).append(" / 100</p>")
                .append("<p>结论：").append(report.getVerdict()).append("</p>")
                .append("<h2>分项结果</h2><table><tr><th>检测项</th><th>状态</th><th>得分</th></tr>");
        for (DetectionResultEntity probe : probes) {
            html.append("<tr><td>").append(probe.getProbeCode()).append(' ').append(probe.getProbeName())
                    .append("</td><td>").append(probe.getStatus()).append("</td><td>")
                    .append(probe.getScore() == null ? "—" : probe.getScore()).append("</td></tr>");
        }
        html.append("</table><h2>免责声明</h2><p>").append(DISCLAIMER).append("</p></body></html>");
        return html.toString();
    }

    private static boolean isVeto(List<DetectionResultEntity> probes) {
        return probes.stream()
                .filter(p -> "D7".equals(p.getProbeCode()))
                .anyMatch(p -> p.getScore() != null && p.getScore().doubleValue() < 40);
    }

    private static boolean hasUnmeasurable(List<DetectionResultEntity> probes) {
        return probes.stream().anyMatch(p -> "NOT_MEASURABLE".equals(p.getStatus()) || "FAILED".equals(p.getStatus()));
    }

    private static BigDecimal avg(List<DetectionResultEntity> items) {
        List<BigDecimal> scores = items.stream().map(DetectionResultEntity::getScore)
                .filter(java.util.Objects::nonNull).toList();
        if (scores.isEmpty()) {
            return null;
        }
        BigDecimal sum = scores.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        return sum.divide(BigDecimal.valueOf(scores.size()), 2, java.math.RoundingMode.HALF_UP);
    }

    private static Map<String, Object> sectionItem(DetectionResultEntity probe) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("code", probe.getProbeCode());
        item.put("name", probe.getProbeName());
        item.put("metric", probe.getEvidence());
        item.put("score", probe.getScore());
        item.put("status", probe.getStatus());
        item.put("value", probe.getScore() == null ? null : probe.getScore().toPlainString());
        item.put("explanation", probe.getExplanation());
        return item;
    }

    private static String sectionNote(String sectionCode) {
        return switch (sectionCode) {
            case "A" -> "时延与性能反映用户体感；受网络路径影响，不区分首 token 慢的原因。";
            case "B" -> "吞吐与限速用于核对申报能力；压测会产生真实费用，已启用成本保护。";
            case "C" -> "一致性高是「正常」但不是「证明」，上游结果缓存也会导致全同。";
            case "D" -> "模型指纹是最需克制的一项：输出的是相似度与置信度，不是真伪判决。";
            case "E" -> "计量与计费用于核对缓存与计费特性是否与买到的一致。";
            case "F" -> "真实源仅输出证据（DNS/TLS/响应头/错误格式/模型列表/时间特征），不纳入总分。";
            default -> "";
        };
    }
}
