package com.hioas.aap.detection;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.credential.CredentialEntity;
import com.hioas.aap.credential.CredentialMapper;
import com.hioas.aap.provider.ProviderEntity;
import com.hioas.aap.provider.ProviderMapper;
import com.hioas.aap.report.ReportMapper;
import com.mybatisflex.core.query.QueryWrapper;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * 定期复测（AC-49）。
 *
 * <p>规则：报告有效期 30 天（R-26 披露口径一致）→ 已通过检测、且**最近一次通过报告**早于
 * `now - intervalDays` 的供应商，应自动进入复测队列。复测任务 `trigger_type=RECHECK`，
 * 不计入供应商日配额（R-09 只约束 FIRST/MANUAL），但仍受「单凭证互斥」（R-08）约束。
 *
 * <p>调度：{@link RecheckScheduler} 按 `app.detection.recheck-cron` 触发；
 * 本期以「可测试的 {@link #runOnce()}」为核心，调度器仅做薄封装（测试环境关闭，避免与用例抢库）。
 */
@Service
public class RecheckService {

    private static final Logger log = LoggerFactory.getLogger(RecheckService.class);

    private final ProviderMapper providerMapper;
    private final CredentialMapper credentialMapper;
    private final DetectionService detectionService;
    private final ReportMapper reportMapper;
    private final int intervalDays;

    public RecheckService(ProviderMapper providerMapper, CredentialMapper credentialMapper,
                          DetectionService detectionService, ReportMapper reportMapper,
                          @Value("${app.detection.recheck-interval-days:30}") int intervalDays) {
        this.providerMapper = providerMapper;
        this.credentialMapper = credentialMapper;
        this.detectionService = detectionService;
        this.reportMapper = reportMapper;
        this.intervalDays = intervalDays;
    }

    /** 到期供应商：状态为 DETECT_PASSED，且最近一次通过报告的检测时间早于 now − intervalDays。 */
    public List<Long> dueProviderIds() {
        OffsetDateTime deadline = OffsetDateTime.now(ZoneOffset.UTC).minusDays(intervalDays);
        List<ProviderEntity> providers = providerMapper.selectListByQuery(QueryWrapper.create()
                .where("status = ?", "DETECT_PASSED")
                .and("deleted = false"));
        List<Long> due = new ArrayList<>();
        for (ProviderEntity provider : providers) {
            OffsetDateTime lastPassed = latestPassedAt(provider.getId());
            if (lastPassed == null || lastPassed.isBefore(deadline)) {
                due.add(provider.getId());
            }
        }
        return due;
    }

    /** 最近一次通过报告的检测时间（无报告 → null）。 */
    public OffsetDateTime latestPassedAt(Long providerId) {
        return reportMapper.selectLatestPassedAt(providerId);
    }

    /**
     * 执行一轮复测扫描：为到期供应商的**主凭证**入队复测任务。
     *
     * @return 成功入队的任务数
     */
    public int runOnce() {
        int enqueued = 0;
        for (Long providerId : dueProviderIds()) {
            CredentialEntity credential = primaryActiveCredential(providerId);
            if (credential == null) {
                log.info("复测跳过：无可用主凭证 provider_id={}", providerId);
                continue;
            }
            try {
                detectionService.createSystemJob(providerId, credential.getId(), "RECHECK");
                enqueued++;
            } catch (ApiException e) {
                // 已有进行中的任务 → 跳过，不视为失败
                log.info("复测跳过 provider_id={} reason={}", providerId, e.getMessage());
            }
        }
        if (enqueued > 0) {
            log.info("复测扫描完成，入队 {} 个任务", enqueued);
        }
        return enqueued;
    }

    private CredentialEntity primaryActiveCredential(Long providerId) {
        CredentialEntity primary = credentialMapper.selectOneByQuery(QueryWrapper.create()
                .where("provider_id = ?", providerId)
                .and("primary_flag = true")
                .and("status = ?", "ACTIVE")
                .and("deleted = false")
                .orderBy("id asc")
                .limit(1));
        if (primary != null) {
            return primary;
        }
        return credentialMapper.selectOneByQuery(QueryWrapper.create()
                .where("provider_id = ?", providerId)
                .and("status = ?", "ACTIVE")
                .and("deleted = false")
                .orderBy("id asc")
                .limit(1));
    }

    public int intervalDays() {
        return intervalDays;
    }
}
