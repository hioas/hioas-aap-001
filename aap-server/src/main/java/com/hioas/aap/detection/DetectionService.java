package com.hioas.aap.detection;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.AuditContext;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.credential.CredentialEntity;
import com.hioas.aap.credential.CredentialMapper;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.provider.ProviderEntity;
import com.hioas.aap.provider.ProviderMapper;
import com.hioas.aap.report.ReportGenerator;
import com.hioas.aap.support.NotificationService;
import com.hioas.aap.support.AuditService;
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
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 检测任务服务（接口 DET-01…06；AC-13…17/19/20/47）。
 *
 * <p>状态机（17-spec §4 + 15-数据模型补充 {@code CANCELLED}）：
 * {@code QUEUED → RUNNING → PARTIAL_DONE → COMPLETED → REPORT_GENERATED}，旁支 {@code FAILED} / {@code CANCELLED}。
 * 非法流转一律 {@code E-1601}；同时仅 1 个活跃任务（C2）。
 *
 * <p>任务的**执行**（D1–D8 真实探测）由引擎工作线程负责，本服务提供
 * {@link #recordProbeResults} 作为引擎回调/离线回放的入口——打分与结论判定全在
 * {@link ProbeScoring} 纯函数里，可独立复算。
 */
@Service
public class DetectionService {

    private static final Logger log = LoggerFactory.getLogger(DetectionService.class);
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 允许取消的状态。 */
    private static final List<String> CANCELLABLE = List.of("QUEUED", "RUNNING", "PARTIAL_DONE");

    private final DetectionJobMapper jobMapper;
    private final DetectionResultMapper resultMapper;
    private final CredentialMapper credentialMapper;
    private final ProviderMapper providerMapper;
    private final DocNoGenerator docNoGenerator;
    private final AuditService auditService;
    /** 报告生成（检测完成 → 报告 1:1，AC-18）。 */
    private final ReportGenerator reportGenerator;
    /** 通过通知（AC-21）。 */
    private final NotificationService notificationService;
    private final int dailyQuota;
    private final int passScore;
    private final int vetoScore;

    public DetectionService(DetectionJobMapper jobMapper, DetectionResultMapper resultMapper,
                            CredentialMapper credentialMapper, ProviderMapper providerMapper,
                            DocNoGenerator docNoGenerator, AuditService auditService,
                            ReportGenerator reportGenerator, NotificationService notificationService,
                            @Value("${app.detection.daily-quota:5}") int dailyQuota,
                            @Value("${app.detection.pass-score:70}") int passScore,
                            @Value("${app.detection.veto-score:40}") int vetoScore) {
        this.jobMapper = jobMapper;
        this.resultMapper = resultMapper;
        this.credentialMapper = credentialMapper;
        this.providerMapper = providerMapper;
        this.docNoGenerator = docNoGenerator;
        this.auditService = auditService;
        this.reportGenerator = reportGenerator;
        this.notificationService = notificationService;
        this.dailyQuota = dailyQuota;
        this.passScore = passScore;
        this.vetoScore = vetoScore;
    }

    // ------------------------------------------------------------------ DET-01

    /** DET-01 新建检测任务（人工重测 / 首次）。 */
    @Transactional
    public DetectionViews.Job createJob(AuthPrincipal principal, Long credentialId, String triggerType) {
        CredentialEntity credential = requireOwnedCredential(principal, credentialId);
        if (!"ACTIVE".equals(credential.getStatus())) {
            throw new ApiException(ErrorCode.E_1303, "凭证当前不可发起检测（需先通过预检）");
        }
        if (hasActiveJob(credentialId)) {
            throw new ApiException(ErrorCode.E_1301, "该凭证已有进行中的检测任务");
        }
        ensureDailyQuota(credential.getProviderId());
        return enqueue(credential, triggerType);
    }

    /** 系统触发的任务（AC-49 定期复测）：不做归属校验，`RECHECK` 不计入日配额。 */
    @Transactional
    public DetectionViews.Job createSystemJob(Long providerId, Long credentialId, String triggerType) {
        CredentialEntity credential = credentialMapper.selectOneById(credentialId);
        if (credential == null) {
            throw new ApiException(ErrorCode.E_1303, "凭证不存在");
        }
        if (!"ACTIVE".equals(credential.getStatus())) {
            throw new ApiException(ErrorCode.E_1303, "凭证当前不可发起检测（需先通过预检）");
        }
        if (hasActiveJob(credentialId)) {
            throw new ApiException(ErrorCode.E_1301, "该凭证已有进行中的检测任务");
        }
        if (providerId != null && !providerId.equals(credential.getProviderId())) {
            throw new ApiException(ErrorCode.E_1303, "凭证不属于该供应商");
        }
        return enqueue(credential, triggerType);
    }

    private DetectionViews.Job enqueue(CredentialEntity credential, String triggerType) {
        DetectionJobEntity job = new DetectionJobEntity();
        job.setJobNo(docNoGenerator.detectionJobNo());
        job.setProviderId(credential.getProviderId());
        job.setCredentialId(credential.getId());
        job.setTriggerType(triggerType == null || triggerType.isBlank() ? "MANUAL" : triggerType.toUpperCase());
        job.setStatus("QUEUED");
        job.setActiveFlag(true);
        job.setAttemptCount(0);
        job.setChallengeVerified(false);
        job.setProgressPercent(BigDecimal.ZERO);
        job.setProgressFinished(0);
        job.setProgressTotal(8);
        job.setConfigSnapshot(JsonCodec.toJson(Map.of("pass_score", passScore, "veto_score", vetoScore,
                "weights", ProbeScoring.DEFAULT_WEIGHTS)));
        jobMapper.insert(job);

        credential.setDetectionStatus("RUNNING");
        credentialMapper.update(credential);
        log.info("检测任务创建 job_no={} trigger={} credential_id={}",
                job.getJobNo(), job.getTriggerType(), credential.getId());
        return toJobView(job);
    }

    // ------------------------------------------------------------------ DET-02/03/04

    /** DET-02 任务详情（含进度）。 */
    public DetectionViews.Job job(AuthPrincipal principal, Long jobId) {
        return toJobView(requireJob(principal, jobId));
    }

    /** DET-03 逐项结果。 */
    public DetectionViews.ResultList results(AuthPrincipal principal, Long jobId) {
        DetectionJobEntity job = requireJob(principal, jobId);
        List<DetectionResultEntity> rows = resultMapper.selectListByQuery(QueryWrapper.create()
                .where("job_id = ?", job.getId())
                .orderBy("probe_code asc"));
        List<DetectionViews.Result> items = rows.stream().map(DetectionService::toResultView).toList();
        return new DetectionViews.ResultList(String.valueOf(job.getId()), items.size(), items);
    }

    /** DET-04 单个探测项结果。 */
    public DetectionViews.Result result(AuthPrincipal principal, Long jobId, String probeCode) {
        DetectionJobEntity job = requireJob(principal, jobId);
        DetectionResultEntity row = resultMapper.selectOneByQuery(QueryWrapper.create()
                .where("job_id = ?", job.getId())
                .and("probe_code = ?", probeCode)
                .limit(1));
        if (row == null) {
            throw new ApiException(ErrorCode.E_1304, "该检测项暂无结果");
        }
        return toResultView(row);
    }

    // ------------------------------------------------------------------ DET-05

    /** DET-05 取消任务（仅未结束的任务可取消）。 */
    @Transactional
    public DetectionViews.Job cancel(AuthPrincipal principal, Long jobId) {
        DetectionJobEntity job = requireJob(principal, jobId);
        if (!CANCELLABLE.contains(job.getStatus())) {
            throw new ApiException(ErrorCode.E_1305, "任务已结束，不可取消");
        }
        job.setStatus("CANCELLED");
        job.setActiveFlag(false);
        job.setFinishedAt(OffsetDateTime.now(ZoneOffset.UTC));
        jobMapper.update(job);

        CredentialEntity credential = credentialMapper.selectOneById(job.getCredentialId());
        if (credential != null) {
            credential.setDetectionStatus("PENDING");
            credentialMapper.update(credential);
        }
        return toJobView(job);
    }

    // ------------------------------------------------------------------ DET-06

    /** DET-06 人工放行（管理端；R-47a 理由必填，审计 DETECTION_RELEASE）。 */
    @Transactional
    public DetectionViews.Job release(Long jobId, String overrideReason, String clientIp) {
        if (overrideReason == null || overrideReason.isBlank()) {
            throw new ApiException(ErrorCode.E_1001, "人工放行必须填写理由",
                    List.of(new com.hioas.aap.common.ApiErrorDetail("override_reason", "人工放行必须填写理由")));
        }
        DetectionJobEntity job = jobMapper.selectOneById(jobId);
        if (job == null) {
            throw new ApiException(ErrorCode.E_1304, "检测任务不存在");
        }
        // 放行是「人工介入跳过自动流程」，除已作废外都可放行；已放行过的任务重复放行无副作用
        if ("CANCELLED".equals(job.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "已取消的任务不可人工放行");
        }

        job.setResult("PASS");
        job.setStatus("COMPLETED");
        job.setActiveFlag(false);
        job.setFinishedAt(OffsetDateTime.now(ZoneOffset.UTC));
        job.setErrorCode(null);
        job.setErrorMsg("人工放行：" + overrideReason);
        jobMapper.update(job);

        CredentialEntity credential = credentialMapper.selectOneById(job.getCredentialId());
        if (credential != null) {
            credential.setDetectionStatus("PASS");
            credentialMapper.update(credential);
        }
        ProviderEntity provider = providerMapper.selectOneById(job.getProviderId());
        if (provider != null && "DETECT_FAILED".equals(provider.getStatus())) {
            provider.setStatus("DETECT_PASSED");
            provider.setManualOverride(true);
            provider.setOverrideReason(overrideReason);
            providerMapper.update(provider);
        }

        // 报告 1:1 生成（AC-18）——与 recordProbeResults 保持同一口径。
        //
        // 缺陷 9（2026-09-19 实测）：人工放行把任务置 COMPLETED 却**不产报告**，而
        // recordProbeResults 里有这句、且注释明确写着「宁可整体回滚也不留『有任务无报告』」。
        // 后果比缺一份报告更严重：任务已 COMPLETED 后 recordProbeResults 会以
        // 「任务已结束，不可回写结果」拒绝 → 这条任务的报告**永远**产不出来。
        // 两条通往 COMPLETED 的路径必须都满足「有任务必有报告」。
        Long reportId = reportGenerator.generate(jobId);
        if ("PASS".equals(job.getResult())) {
            // AC-21 检测通过通知（与 recordProbeResults 的 PASS 分支同口径；内容脱敏）
            notificationService.notifyProvider(job.getProviderId(), "DETECTION_PASSED",
                    "检测通过", "您的接入通道已通过平台检测（人工放行），报告编号见报告中心，有效期 30 天。",
                    "DETECTION", "REPORT", reportId);
        }

        AuditContext.current().or(() -> {
            AuditContext.set(new AuditContext.Actor(null, "ADMIN", "manual-release", clientIp));
            return AuditContext.current();
        });
        auditService.record(AuditService.AuditAction.DETECTION_RELEASE, "detection_job", job.getId(),
                "人工放行检测任务：" + overrideReason, null,
                Map.of("job_no", job.getJobNo(), "reason", overrideReason), "SENSITIVE");
        log.warn("检测任务人工放行 job_no={} reason={}", job.getJobNo(), overrideReason);
        return toJobView(job);
    }

    // ------------------------------------------------------------------ 引擎回调

    /**
     * 引擎回写：把各探测项结果落库，合成总分与结论，并回写凭证/供应商状态。
     *
     * <p>这是「执行器」与「打分/结论」之间的唯一接口：执行器只产出原始指标，
     * 打分与判定一律走 {@link ProbeScoring}（纯函数，可复算）。
     */
    @Transactional
    public DetectionViews.Job recordProbeResults(Long jobId, List<ProbeScoring.ProbeScore> scores,
                                                 Map<String, Map<String, Object>> metricsByProbe,
                                                 Map<String, String> evidenceByProbe) {
        DetectionJobEntity job = jobMapper.selectOneById(jobId);
        if (job == null) {
            throw new ApiException(ErrorCode.E_1304, "检测任务不存在");
        }
        if (!"QUEUED".equals(job.getStatus()) && !"RUNNING".equals(job.getStatus())
                && !"PARTIAL_DONE".equals(job.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "任务已结束，不可回写结果：" + job.getStatus());
        }

        resultMapper.deleteByQuery(QueryWrapper.create().where("job_id = ?", jobId));
        ProbeScoring.Summary summary = ProbeScoring.summarize(scores, passScore, vetoScore);
        // 落库的 weight_used 取「归一化后」的权重（summarize 才算得出来），保证报告与总分口径一致
        Map<String, java.math.BigDecimal> usedWeights = new java.util.HashMap<>();
        for (ProbeScoring.ProbeScore scored : summary.probes()) {
            if (scored.weightUsed() != null) {
                usedWeights.put(scored.probeCode(), BigDecimal.valueOf(scored.weightUsed()));
            }
        }
        for (ProbeScoring.ProbeScore score : scores) {
            DetectionResultEntity row = new DetectionResultEntity();
            row.setJobId(jobId);
            row.setProbeCode(score.probeCode());
            row.setProbeName(ProbeScoring.PROBE_NAMES.getOrDefault(score.probeCode(), score.probeCode()));
            row.setStatus(score.status().name());
            row.setScore(score.score() == null ? null : BigDecimal.valueOf(score.score()));
            row.setWeightOriginal(score.weightOriginal() == null ? null : BigDecimal.valueOf(score.weightOriginal()));
            row.setWeightUsed(usedWeights.get(score.probeCode()));
            row.setMetrics(metricsByProbe == null || metricsByProbe.get(score.probeCode()) == null ? null
                    : JsonCodec.toJson(metricsByProbe.get(score.probeCode())));
            row.setEvidence(evidenceByProbe == null ? null : evidenceByProbe.get(score.probeCode()));
            row.setExplanation(explanation(score));
            row.setAttemptCount(1);
            resultMapper.insert(row);
        }

        job.setStatus("COMPLETED");
        job.setActiveFlag(false);
        job.setTotalScore(summary.totalScore());
        job.setResult(summary.result());
        job.setConfidence(summary.confidence());
        job.setFinishedAt(OffsetDateTime.now(ZoneOffset.UTC));
        job.setProgressPercent(BigDecimal.valueOf(100));
        job.setProgressFinished(scores.size());
        job.setCostActualUsd(job.getCostEstimateUsd());
        if ("FAIL".equals(summary.result()) && summary.vetoTriggered()) {
            job.setErrorCode("E-1301");
            job.setErrorMsg("命中一票否决项（模型指纹 < " + vetoScore + "）");
        }
        jobMapper.update(job);

        CredentialEntity credential = credentialMapper.selectOneById(job.getCredentialId());
        if (credential != null) {
            credential.setDetectionStatus(switch (summary.result()) {
                case "PASS" -> "PASS";
                case "FAIL" -> "FAIL";
                default -> "PENDING";
            });
            credentialMapper.update(credential);
        }
        ProviderEntity provider = providerMapper.selectOneById(job.getProviderId());
        if (provider != null) {
            provider.setStatus(switch (summary.result()) {
                case "PASS" -> "DETECT_PASSED";
                case "FAIL" -> "DETECT_FAILED";
                default -> "DETECTING";
            });
            provider.setLastDetectionJobId(jobId);
            providerMapper.update(provider);
        }
        log.info("检测任务完成 job_no={} 总分={} 结论={} 置信度={}",
                job.getJobNo(), summary.totalScore(), summary.result(), summary.confidence());
        // 报告 1:1 生成（AC-18）；失败不静默：与检测同事务，宁可整体回滚也不留「有任务无报告」
        Long reportId = reportGenerator.generate(jobId);
        if ("PASS".equals(summary.result())) {
            // AC-21 检测通过通知（内容脱敏：不出现手机号与 api_key 明文）
            notificationService.notifyProvider(job.getProviderId(), "DETECTION_PASSED",
                    "检测通过", "您的接入通道已通过平台检测（总分 " + summary.totalScore()
                            + "），报告编号见报告中心，有效期 30 天。", "DETECTION",
                    "REPORT", reportId);
        }
        return toJobView(job);
    }

    /** 四项排名结果（供报告页 consumption）——由后续报告任务扩展。 */
    public List<DetectionResultEntity> rawResults(Long jobId) {
        return resultMapper.selectListByQuery(QueryWrapper.create()
                .where("job_id = ?", jobId)
                .orderBy("probe_code asc"));
    }

    // ------------------------------------------------------------------ 内部

    private void ensureDailyQuota(Long providerId) {
        OffsetDateTime startOfDay = OffsetDateTime.now(ZoneOffset.UTC)
                .withHour(0).withMinute(0).withSecond(0).withNano(0);
        long today = jobMapper.selectCountByQuery(QueryWrapper.create()
                .where("provider_id = ?", providerId)
                .and("(trigger_type = 'FIRST' or trigger_type = 'MANUAL')")
                .and("created_at >= ?", startOfDay));
        if (today >= dailyQuota) {
            throw new ApiException(ErrorCode.E_1302, "今日检测配额已用尽（上限 " + dailyQuota + " 次）");
        }
    }

    private boolean hasActiveJob(Long credentialId) {
        return jobMapper.selectCountByQuery(QueryWrapper.create()
                .where("credential_id = ?", credentialId)
                .and("active_flag = true")) > 0;
    }

    private CredentialEntity requireOwnedCredential(AuthPrincipal principal, Long credentialId) {
        CredentialEntity credential = credentialMapper.selectOneById(credentialId);
        if (credential == null) {
            throw new ApiException(ErrorCode.E_1303, "凭证不存在");
        }
        if (principal == null || principal.providerId() == null
                || !credential.getProviderId().equals(principal.providerId())) {
            throw new ApiException(ErrorCode.E_1304, "检测任务不存在");
        }
        return credential;
    }

    private DetectionJobEntity requireJob(AuthPrincipal principal, Long jobId) {
        DetectionJobEntity job = jobMapper.selectOneById(jobId);
        if (job == null) {
            throw new ApiException(ErrorCode.E_1304, "检测任务不存在");
        }
        if (principal == null || principal.providerId() == null
                || !job.getProviderId().equals(principal.providerId())) {
            throw new ApiException(ErrorCode.E_1304, "检测任务不存在");
        }
        return job;
    }

    private static String explanation(ProbeScoring.ProbeScore score) {
        // 四段式解释（09-PRD §4）：这项测什么 / 怎么测 / 结果说明 / 为什么重要与边界
        return "【测什么】" + ProbeScoring.PROBE_NAMES.getOrDefault(score.probeCode(), score.probeCode())
                + "；【怎么测】按 09-PRD 规格执行探测并记录原始指标；【结果】"
                + (score.note() == null ? "无补充" : score.note())
                + "；【意义与边界】结果仅代表检测时点状态，不构成对上游长期稳定性的担保。";
    }

    private static DetectionViews.Result toResultView(DetectionResultEntity row) {
        Map<String, Object> metrics = row.getMetrics() == null ? Map.of() : JsonCodec.toMap(row.getMetrics());
        return new DetectionViews.Result(row.getProbeCode(), row.getProbeName(), row.getStatus(), row.getScore(),
                row.getWeightOriginal(), row.getWeightUsed(), metrics,
                row.getEvidence() == null ? null : Map.of("summary", row.getEvidence()),
                row.getExplanation(), row.getEvidence(), row.getAttemptCount());
    }

    private DetectionViews.Job toJobView(DetectionJobEntity job) {
        return new DetectionViews.Job(
                String.valueOf(job.getId()), String.valueOf(job.getId()), job.getJobNo(),
                job.getProviderId() == null ? null : String.valueOf(job.getProviderId()),
                job.getCredentialId() == null ? null : String.valueOf(job.getCredentialId()),
                job.getStatus(), job.getTriggerType(),
                format(job.getStartedAt()), format(job.getFinishedAt()),
                job.getTotalScore(), job.getResult(), job.getConfidence(),
                job.getCostEstimateUsd(), job.getCostActualUsd(), job.getChallengeVerified(),
                job.getErrorCode(), job.getErrorMsg(), null, job.getAttemptCount(),
                new DetectionViews.Progress(job.getProgressPercent(), job.getProgressFinished(),
                        job.getProgressTotal(), job.getEtaMinutes()),
                format(job.getCreatedAt()), format(job.getUpdatedAt()));
    }

    private static String format(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    /** 报告任务会用到：把结果行转成报告章节所需的简单结构。 */
    public List<Map<String, Object>> resultDigest(Long jobId) {
        List<Map<String, Object>> digest = new ArrayList<>();
        for (DetectionResultEntity row : rawResults(jobId)) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("code", row.getProbeCode());
            item.put("name", row.getProbeName());
            item.put("score", row.getScore());
            item.put("status", row.getStatus());
            item.put("weight_used", row.getWeightUsed());
            digest.add(item);
        }
        return digest;
    }
}
