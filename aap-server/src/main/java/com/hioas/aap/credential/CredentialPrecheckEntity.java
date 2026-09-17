package com.hioas.aap.credential;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 凭证预检记录（表 {@code aap_credential_precheck}）。 */
@Table(value = "aap_credential_precheck",
        onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class CredentialPrecheckEntity extends BaseEntity {

    private Long credentialId;
    private String status;
    private Boolean connectivityOk;
    private Boolean authOk;
    private Boolean modelsOk;
    private String errorCode;
    private String errorMsg;
    private Integer latencyMs;
    private OffsetDateTime checkedAt;

    public Long getCredentialId() {
        return credentialId;
    }

    public void setCredentialId(Long v) {
        this.credentialId = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public Boolean getConnectivityOk() {
        return connectivityOk;
    }

    public void setConnectivityOk(Boolean v) {
        this.connectivityOk = v;
    }

    public Boolean getAuthOk() {
        return authOk;
    }

    public void setAuthOk(Boolean v) {
        this.authOk = v;
    }

    public Boolean getModelsOk() {
        return modelsOk;
    }

    public void setModelsOk(Boolean v) {
        this.modelsOk = v;
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

    public Integer getLatencyMs() {
        return latencyMs;
    }

    public void setLatencyMs(Integer v) {
        this.latencyMs = v;
    }

    public OffsetDateTime getCheckedAt() {
        return checkedAt;
    }

    public void setCheckedAt(OffsetDateTime v) {
        this.checkedAt = v;
    }
}
