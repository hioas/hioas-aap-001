package com.hioas.aap.credential;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 测试凭证（表 {@code aap_credential}，docs/backend/01-ER数据模型.md §4.3）。
 *
 * <p>安全口径：{@code api_key_cipher}（AES-256-GCM，base64(iv‖ct‖tag)）是唯一保存明文信息的列；
 * {@code api_key_mask} 供展示、{@code api_key_fingerprint}（SHA-256）供去重与检索，二者都不可逆。
 */
@Table(value = "aap_credential", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class CredentialEntity extends BaseEntity {

    private Long providerId;
    private String alias;
    private Boolean primaryFlag;
    private String baseUrl;
    private String apiKeyCipher;
    private String apiKeyMask;
    private String apiKeyFingerprint;
    private String declaredVendor;
    private Integer declaredRpm;
    private Integer declaredTpm;
    private Integer declaredContextWindow;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String modelList;

    private String envTag;
    private String status;
    private String detectionStatus;
    private Long latestReportId;
    private Boolean precheckPassed;
    private OffsetDateTime precheckAt;
    private OffsetDateTime lastUsedAt;

    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    public String getAlias() {
        return alias;
    }

    public void setAlias(String v) {
        this.alias = v;
    }

    public Boolean getPrimaryFlag() {
        return primaryFlag;
    }

    public void setPrimaryFlag(Boolean v) {
        this.primaryFlag = v;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String v) {
        this.baseUrl = v;
    }

    public String getApiKeyCipher() {
        return apiKeyCipher;
    }

    public void setApiKeyCipher(String v) {
        this.apiKeyCipher = v;
    }

    public String getApiKeyMask() {
        return apiKeyMask;
    }

    public void setApiKeyMask(String v) {
        this.apiKeyMask = v;
    }

    public String getApiKeyFingerprint() {
        return apiKeyFingerprint;
    }

    public void setApiKeyFingerprint(String v) {
        this.apiKeyFingerprint = v;
    }

    public String getDeclaredVendor() {
        return declaredVendor;
    }

    public void setDeclaredVendor(String v) {
        this.declaredVendor = v;
    }

    public Integer getDeclaredRpm() {
        return declaredRpm;
    }

    public void setDeclaredRpm(Integer v) {
        this.declaredRpm = v;
    }

    public Integer getDeclaredTpm() {
        return declaredTpm;
    }

    public void setDeclaredTpm(Integer v) {
        this.declaredTpm = v;
    }

    public Integer getDeclaredContextWindow() {
        return declaredContextWindow;
    }

    public void setDeclaredContextWindow(Integer v) {
        this.declaredContextWindow = v;
    }

    public String getModelList() {
        return modelList;
    }

    public void setModelList(String v) {
        this.modelList = v;
    }

    public String getEnvTag() {
        return envTag;
    }

    public void setEnvTag(String v) {
        this.envTag = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public String getDetectionStatus() {
        return detectionStatus;
    }

    public void setDetectionStatus(String v) {
        this.detectionStatus = v;
    }

    public Long getLatestReportId() {
        return latestReportId;
    }

    public void setLatestReportId(Long v) {
        this.latestReportId = v;
    }

    public Boolean getPrecheckPassed() {
        return precheckPassed;
    }

    public void setPrecheckPassed(Boolean v) {
        this.precheckPassed = v;
    }

    public OffsetDateTime getPrecheckAt() {
        return precheckAt;
    }

    public void setPrecheckAt(OffsetDateTime v) {
        this.precheckAt = v;
    }

    public OffsetDateTime getLastUsedAt() {
        return lastUsedAt;
    }

    public void setLastUsedAt(OffsetDateTime v) {
        this.lastUsedAt = v;
    }
}
