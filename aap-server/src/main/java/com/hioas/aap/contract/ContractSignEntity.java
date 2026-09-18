package com.hioas.aap.contract;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 合同签署记录（表 {@code aap_contract_sign}）：不可变时间轴（C8 只插不改）。
 *
 * <p>{@code signer_type} = {@code SUPPLIER|PLATFORM}；{@code tone} 供客户端时间轴着色
 * （{@code success|pending|void}）：供应商签署 = {@code pending}（等平台确认），平台确认 = {@code success}。
 */
@Table(value = "aap_contract_sign", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class ContractSignEntity extends BaseEntity {

    private Long contractId;
    private String signerType;
    private String signerName;
    private String signMethod;
    private Long smsCodeId;
    private String tone;
    private OffsetDateTime signedAt;

    public Long getContractId() {
        return contractId;
    }

    public void setContractId(Long v) {
        this.contractId = v;
    }

    public String getSignerType() {
        return signerType;
    }

    public void setSignerType(String v) {
        this.signerType = v;
    }

    public String getSignerName() {
        return signerName;
    }

    public void setSignerName(String v) {
        this.signerName = v;
    }

    public String getSignMethod() {
        return signMethod;
    }

    public void setSignMethod(String v) {
        this.signMethod = v;
    }

    public Long getSmsCodeId() {
        return smsCodeId;
    }

    public void setSmsCodeId(Long v) {
        this.smsCodeId = v;
    }

    public String getTone() {
        return tone;
    }

    public void setTone(String v) {
        this.tone = v;
    }

    public OffsetDateTime getSignedAt() {
        return signedAt;
    }

    public void setSignedAt(OffsetDateTime v) {
        this.signedAt = v;
    }
}
