package com.hioas.aap.report;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;

/** 检测报告（表 {@code aap_report}，与检测任务 1:1）。 */
@Table(value = "aap_report", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class ReportEntity extends BaseEntity {

    private String reportNo;
    private Long jobId;
    private Long providerId;
    private Long credentialId;
    private Long templateId;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String templateSnapshot;

    private BigDecimal totalScore;
    private String result;
    private String confidence;
    private Boolean vetoTriggered;
    private String verdict;
    private String providerName;
    private String providerCode;
    private String channelName;
    private String apiKeyMasked;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String modelList;

    private OffsetDateTime detectedAt;
    private Integer durationSeconds;
    private BigDecimal costEstimateUsd;
    private BigDecimal costActualUsd;
    private String renderedHtml;
    private Long pdfFileId;
    private String disclaimer;
    private String status;

    public String getReportNo() {
        return reportNo;
    }

    public void setReportNo(String v) {
        this.reportNo = v;
    }

    public Long getJobId() {
        return jobId;
    }

    public void setJobId(Long v) {
        this.jobId = v;
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

    public Long getTemplateId() {
        return templateId;
    }

    public void setTemplateId(Long v) {
        this.templateId = v;
    }

    public String getTemplateSnapshot() {
        return templateSnapshot;
    }

    public void setTemplateSnapshot(String v) {
        this.templateSnapshot = v;
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

    public Boolean getVetoTriggered() {
        return vetoTriggered;
    }

    public void setVetoTriggered(Boolean v) {
        this.vetoTriggered = v;
    }

    public String getVerdict() {
        return verdict;
    }

    public void setVerdict(String v) {
        this.verdict = v;
    }

    public String getProviderName() {
        return providerName;
    }

    public void setProviderName(String v) {
        this.providerName = v;
    }

    public String getProviderCode() {
        return providerCode;
    }

    public void setProviderCode(String v) {
        this.providerCode = v;
    }

    public String getChannelName() {
        return channelName;
    }

    public void setChannelName(String v) {
        this.channelName = v;
    }

    public String getApiKeyMasked() {
        return apiKeyMasked;
    }

    public void setApiKeyMasked(String v) {
        this.apiKeyMasked = v;
    }

    public String getModelList() {
        return modelList;
    }

    public void setModelList(String v) {
        this.modelList = v;
    }

    public OffsetDateTime getDetectedAt() {
        return detectedAt;
    }

    public void setDetectedAt(OffsetDateTime v) {
        this.detectedAt = v;
    }

    public Integer getDurationSeconds() {
        return durationSeconds;
    }

    public void setDurationSeconds(Integer v) {
        this.durationSeconds = v;
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

    public String getRenderedHtml() {
        return renderedHtml;
    }

    public void setRenderedHtml(String v) {
        this.renderedHtml = v;
    }

    public Long getPdfFileId() {
        return pdfFileId;
    }

    public void setPdfFileId(Long v) {
        this.pdfFileId = v;
    }

    public String getDisclaimer() {
        return disclaimer;
    }

    public void setDisclaimer(String v) {
        this.disclaimer = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }
}
