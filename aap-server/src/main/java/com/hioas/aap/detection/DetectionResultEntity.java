package com.hioas.aap.detection;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 检测分项结果（表 {@code aap_detection_result}，UQ(job_id, probe_code)）。 */
@Table(value = "aap_detection_result",
        onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class DetectionResultEntity extends BaseEntity {

    private Long jobId;
    private String probeCode;
    private String probeName;
    private String status;
    private BigDecimal score;
    private BigDecimal weightOriginal;
    private BigDecimal weightUsed;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String metrics;

    private String evidence;
    private String evidenceUrl;
    private String explanation;
    private Integer attemptCount;

    public Long getJobId() {
        return jobId;
    }

    public void setJobId(Long v) {
        this.jobId = v;
    }

    public String getProbeCode() {
        return probeCode;
    }

    public void setProbeCode(String v) {
        this.probeCode = v;
    }

    public String getProbeName() {
        return probeName;
    }

    public void setProbeName(String v) {
        this.probeName = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public BigDecimal getScore() {
        return score;
    }

    public void setScore(BigDecimal v) {
        this.score = v;
    }

    public BigDecimal getWeightOriginal() {
        return weightOriginal;
    }

    public void setWeightOriginal(BigDecimal v) {
        this.weightOriginal = v;
    }

    public BigDecimal getWeightUsed() {
        return weightUsed;
    }

    public void setWeightUsed(BigDecimal v) {
        this.weightUsed = v;
    }

    public String getMetrics() {
        return metrics;
    }

    public void setMetrics(String v) {
        this.metrics = v;
    }

    public String getEvidence() {
        return evidence;
    }

    public void setEvidence(String v) {
        this.evidence = v;
    }

    public String getEvidenceUrl() {
        return evidenceUrl;
    }

    public void setEvidenceUrl(String v) {
        this.evidenceUrl = v;
    }

    public String getExplanation() {
        return explanation;
    }

    public void setExplanation(String v) {
        this.explanation = v;
    }

    public Integer getAttemptCount() {
        return attemptCount;
    }

    public void setAttemptCount(Integer v) {
        this.attemptCount = v;
    }
}
