package com.hioas.aap.detection;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;

/**
 * 检测任务（表 {@code aap_detection_job}）。
 *
 * <p>{@code active_flag} 是 C2「同凭证同时仅 1 个活跃任务」的载体：部分唯一索引
 * {@code uq_job_active(credential_id) where active_flag = true and deleted = false}。
 * 应用层先查（给出 {@code E-1301} 的友好提示），数据库索引兜并发。
 */
@Table(value = "aap_detection_job", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class DetectionJobEntity extends BaseEntity {

    private String jobNo;
    private Long providerId;
    private Long credentialId;
    private String triggerType;
    private String status;
    private Boolean activeFlag;
    private Long configId;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String configSnapshot;

    /**
     * 本次检测覆盖的**具体模型清单**快照（渠道拉取结果，jsonb）。
     *
     * <p>用户口径 2026-09-23：「每次提交…之前的检测记录一个版本记录，重新提交的也是一条新纪录，
     * 都执行检测的具体模型」。每条检测记录都留痕，供版本比对；
     * 也是「重复检测去重」的匹配键（同一凭证 + 同一模型集合）。
     */
    @Column(typeHandler = JsonbTypeHandler.class)
    private String modelList;

    private OffsetDateTime startedAt;
    private OffsetDateTime finishedAt;
    private BigDecimal totalScore;
    private String result;
    private String confidence;
    private BigDecimal costEstimateUsd;
    private BigDecimal costActualUsd;
    private Boolean challengeVerified;
    private String errorCode;
    private String errorMsg;
    private Integer attemptCount;
    private BigDecimal progressPercent;
    private Integer progressFinished;
    private Integer progressTotal;
    private BigDecimal etaMinutes;

    public String getJobNo() {
        return jobNo;
    }

    public void setJobNo(String v) {
        this.jobNo = v;
    }

    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    public Long getCredentialId() {
        return credentialId;
    }

    public void setCredentialId(Long v) {
        this.credentialId = v;
    }

    public String getTriggerType() {
        return triggerType;
    }

    public void setTriggerType(String v) {
        this.triggerType = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public Boolean getActiveFlag() {
        return activeFlag;
    }

    public void setActiveFlag(Boolean v) {
        this.activeFlag = v;
    }

    public Long getConfigId() {
        return configId;
    }

    public void setConfigId(Long v) {
        this.configId = v;
    }

    public String getModelList() {
        return modelList;
    }

    public void setModelList(String v) {
        this.modelList = v;
    }

    public String getConfigSnapshot() {
        return configSnapshot;
    }

    public void setConfigSnapshot(String v) {
        this.configSnapshot = v;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(OffsetDateTime v) {
        this.startedAt = v;
    }

    public OffsetDateTime getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(OffsetDateTime v) {
        this.finishedAt = v;
    }

    public BigDecimal getTotalScore() {
        return totalScore;
    }

    public void setTotalScore(BigDecimal v) {
        this.totalScore = v;
    }

    public String getResult() {
        return result;
    }

    public void setResult(String v) {
        this.result = v;
    }

    public String getConfidence() {
        return confidence;
    }

    public void setConfidence(String v) {
        this.confidence = v;
    }

    public BigDecimal getCostEstimateUsd() {
        return costEstimateUsd;
    }

    public void setCostEstimateUsd(BigDecimal v) {
        this.costEstimateUsd = v;
    }

    public BigDecimal getCostActualUsd() {
        return costActualUsd;
    }

    public void setCostActualUsd(BigDecimal v) {
        this.costActualUsd = v;
    }

    public Boolean getChallengeVerified() {
        return challengeVerified;
    }

    public void setChallengeVerified(Boolean v) {
        this.challengeVerified = v;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public void setErrorCode(String v) {
        this.errorCode = v;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public void setErrorMsg(String v) {
        this.errorMsg = v;
    }

    public Integer getAttemptCount() {
        return attemptCount;
    }

    public void setAttemptCount(Integer v) {
        this.attemptCount = v;
    }

    public BigDecimal getProgressPercent() {
        return progressPercent;
    }

    public void setProgressPercent(BigDecimal v) {
        this.progressPercent = v;
    }

    public Integer getProgressFinished() {
        return progressFinished;
    }

    public void setProgressFinished(Integer v) {
        this.progressFinished = v;
    }

    public Integer getProgressTotal() {
        return progressTotal;
    }

    public void setProgressTotal(Integer v) {
        this.progressTotal = v;
    }

    public BigDecimal getEtaMinutes() {
        return etaMinutes;
    }

    public void setEtaMinutes(BigDecimal v) {
        this.etaMinutes = v;
    }
}
