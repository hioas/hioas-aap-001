package com.hioas.aap.credential;

import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.detection.DetectionJobEntity;
import com.hioas.aap.detection.DetectionJobMapper;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * 预检结果的落库（**独立事务** REQUIRES_NEW）。
 *
 * <p>为什么独立：预检失败要「先落库（预检记录 + 凭证状态 PRECHECK_FAILED）再抛 {@code E-1101}」；
 * 若与业务异常同事务，异常回滚会把失败记录一并抹掉——这正是 T03 在验证码锁定上踩过的同一个坑
 * （见 `.agents/state/aap-server-tdd-state.md` R03）。
 *
 * <p>成功路径同理：凭证状态更新与检测任务入队必须在**同一个事务**里成功或一起失败，
 * 不能出现「凭证 ACTIVE 但没有检测任务」的中间态。
 */
@Component
public class CredentialPrecheckRecorder {

    private final CredentialMapper credentialMapper;
    private final CredentialPrecheckMapper precheckMapper;
    private final DetectionJobMapper detectionJobMapper;
    private final DocNoGenerator docNoGenerator;

    public CredentialPrecheckRecorder(CredentialMapper credentialMapper, CredentialPrecheckMapper precheckMapper,
                                      DetectionJobMapper detectionJobMapper, DocNoGenerator docNoGenerator) {
        this.credentialMapper = credentialMapper;
        this.precheckMapper = precheckMapper;
        this.detectionJobMapper = detectionJobMapper;
        this.docNoGenerator = docNoGenerator;
    }

    /** 记录失败：写预检记录 + 凭证置 PRECHECK_FAILED（提交后调用方再抛异常）。 */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public Long recordFailure(Long credentialId, CredentialPrecheckEntity record) {
        precheckMapper.insert(record);
        CredentialEntity entity = credentialMapper.selectOneById(credentialId);
        if (entity != null) {
            entity.setStatus("PRECHECK_FAILED");
            entity.setPrecheckPassed(false);
            entity.setPrecheckAt(record.getCheckedAt());
            credentialMapper.update(entity);
        }
        return record.getId();
    }

    /** 记录成功：写预检记录 + 凭证置 ACTIVE + 建检测任务（同事务，要么全成要么全败）。 */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public DetectionJobEntity recordSuccess(Long credentialId, Long providerId, CredentialPrecheckEntity record) {
        precheckMapper.insert(record);
        CredentialEntity entity = credentialMapper.selectOneById(credentialId);
        entity.setStatus("ACTIVE");
        entity.setPrecheckPassed(true);
        entity.setPrecheckAt(record.getCheckedAt());
        entity.setDetectionStatus("RUNNING");
        credentialMapper.update(entity);

        DetectionJobEntity job = new DetectionJobEntity();
        job.setJobNo(docNoGenerator.detectionJobNo());
        job.setProviderId(providerId);
        job.setCredentialId(credentialId);
        job.setTriggerType("FIRST");
        job.setStatus("QUEUED");
        job.setActiveFlag(true);
        job.setConfigSnapshot(JsonCodec.toJson(Map.of(
                "pass_score", 70, "veto_score", 40,
                "weights", Map.of("D1", 0.10, "D2", 0.15, "D3", 0.10, "D4", 0.10,
                        "D5", 0.10, "D6", 0.10, "D7", 0.35, "D8", 0.0))));
        job.setAttemptCount(0);
        job.setChallengeVerified(false);
        job.setProgressPercent(BigDecimal.ZERO);
        job.setProgressFinished(0);
        job.setProgressTotal(8);
        detectionJobMapper.insert(job);
        return job;
    }
}
