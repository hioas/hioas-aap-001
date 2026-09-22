package com.hioas.aap.credential;

import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.detection.DetectionJobEntity;
import com.hioas.aap.detection.DetectionJobMapper;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
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

    private static final Logger log = LoggerFactory.getLogger(CredentialPrecheckRecorder.class);

    private final CredentialMapper credentialMapper;
    private final CredentialPrecheckMapper precheckMapper;
    private final DetectionJobMapper detectionJobMapper;
    private final DocNoGenerator docNoGenerator;
    private final JdbcTemplate jdbcTemplate;

    public CredentialPrecheckRecorder(CredentialMapper credentialMapper, CredentialPrecheckMapper precheckMapper,
                                      DetectionJobMapper detectionJobMapper, DocNoGenerator docNoGenerator,
                                      JdbcTemplate jdbcTemplate) {
        this.credentialMapper = credentialMapper;
        this.precheckMapper = precheckMapper;
        this.detectionJobMapper = detectionJobMapper;
        this.docNoGenerator = docNoGenerator;
        this.jdbcTemplate = jdbcTemplate;
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

        // ── 检测记录版本化（用户口径 2026-09-23）──
        // 「每次提交…之前的检测记录一个版本记录，重新提交的也是一条新纪录，都执行检测的具体模型」
        // 故每条检测任务都**快照本次覆盖的具体模型**（= 渠道拉取结果，凭证的 model_list）。
        String modelsJson = entity.getModelList();

        // 重复检测策略（用户口径：开启 ⇒ 同一凭证+同一模型 指回同一条；没开 ⇒ 每次新建一条）
        DetectionJobEntity reusable = findReusableJob(credentialId, modelsJson);
        if (reusable != null) {
            reusable.setActiveFlag(true);
            reusable.setStatus("QUEUED");
            reusable.setAttemptCount(0);
            detectionJobMapper.update(reusable);
            return reusable;
        }

        DetectionJobEntity job = new DetectionJobEntity();
        job.setJobNo(docNoGenerator.detectionJobNo());
        job.setProviderId(providerId);
        job.setCredentialId(credentialId);
        job.setTriggerType("FIRST");
        job.setStatus("QUEUED");
        job.setActiveFlag(true);
        job.setModelList(modelsJson);
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

    /**
     * 查找可复用的既有检测任务。
     *
     * <p>用户口径 2026-09-23：
     * <ul>
     *   <li>「是否可重复检测」**开启** ⇒ 同一凭证下的同一模型多次提交 **指向同一条检测**；</li>
     *   <li>**没开** ⇒ 重复提交生成**重复的检测**（每次新建一条，= 默认行为）。</li>
     * </ul>
     * ⚠️ 该开关按**行为**命名 `reuse_existing_detection`（复用已有检测结果）——
     * 用户口中叫「可重复检测」，但其描述的极性与字面直觉相反，见 V10 迁移注释。
     *
     * @return 命中的既有任务；未开启策略 / 无模型 / 无命中 → {@code null}（调用方新建一条）
     */
    private DetectionJobEntity findReusableJob(Long credentialId, String modelsJson) {
        if (modelsJson == null || modelsJson.isBlank() || !reuseExistingDetectionEnabled()) {
            return null;
        }
        try {
            List<Long> ids = jdbcTemplate.queryForList(
                    "SELECT id FROM aap_detection_job "
                            + "WHERE credential_id = ? AND deleted = false AND model_list = cast(? as jsonb) "
                            + "ORDER BY id DESC LIMIT 1",
                    Long.class, credentialId, modelsJson);
            if (ids.isEmpty()) {
                return null;
            }
            return detectionJobMapper.selectOneById(ids.get(0));
        } catch (RuntimeException e) {
            // 去重是优化、不是正确性前提：读失败就退回「每次新建」的默认行为，不阻断预检
            log.warn("重复检测去重查询失败，按默认「每次新建」处理 credential_id={}", credentialId, e);
            return null;
        }
    }

    /**
     * 读取「复用已有检测结果」策略。
     *
     * <p>取已发布（PUBLISHED）的最新一条检测配置；**无已发布配置时默认 false**
     * —— 即「没开」分支：每次都生成新的一条检测记录。
     */
    private boolean reuseExistingDetectionEnabled() {
        try {
            List<Boolean> flags = jdbcTemplate.queryForList(
                    "SELECT reuse_existing_detection FROM aap_detection_config "
                            + "WHERE status = 'PUBLISHED' AND deleted = false "
                            + "ORDER BY published_at DESC NULLS LAST, id DESC LIMIT 1",
                    Boolean.class);
            return !flags.isEmpty() && Boolean.TRUE.equals(flags.get(0));
        } catch (RuntimeException e) {
            log.warn("读取重复检测策略失败，按默认 false（每次新建）处理", e);
            return false;
        }
    }
}
