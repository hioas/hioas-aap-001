package com.hioas.aap.contract;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;

/**
 * 合同（表 {@code aap_contract}）。
 *
 * <p>T10 只负责**生成**：审核通过（ADM-R03 / A9）同事务插入一行 {@code status=CREATED} 并回写
 * {@code aap_quote.contract_id}，确保不存在「已通过但无合同」的中间态。签发/签署确认（ADM-CT02/03）
 * 与打款、结算属 T11，本期不实现对应端点（清单冻结，不抢先定义状态迁移语义）。
 */
@Table(value = "aap_contract", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class ContractEntity extends BaseEntity {

    private String contractNo;
    private Long quoteId;
    private Long providerId;
    private String title;
    private String status;
    private String signChannel;
    private String cooperationMode;
    private OffsetDateTime validFrom;
    private OffsetDateTime validTo;
    private String settlementCycle;
    private BigDecimal platformFeeRate;
    private String currency;
    private BigDecimal minSettlementAmount;
    private OffsetDateTime signDeadline;
    private String signerName;
    private String signerPhoneMask;
    private String signMethod;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String terms;

    private Long fileId;
    private OffsetDateTime signedAt;
    private OffsetDateTime archivedAt;
    private String voidedReason;

    public String getContractNo() {
        return contractNo;
    }

    public void setContractNo(String v) {
        this.contractNo = v;
    }

    public Long getQuoteId() {
        return quoteId;
    }

    public void setQuoteId(Long v) {
        this.quoteId = v;
    }

    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String v) {
        this.title = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public String getSignChannel() {
        return signChannel;
    }

    public void setSignChannel(String v) {
        this.signChannel = v;
    }

    public String getCooperationMode() {
        return cooperationMode;
    }

    public void setCooperationMode(String v) {
        this.cooperationMode = v;
    }

    public OffsetDateTime getValidFrom() {
        return validFrom;
    }

    public void setValidFrom(OffsetDateTime v) {
        this.validFrom = v;
    }

    public OffsetDateTime getValidTo() {
        return validTo;
    }

    public void setValidTo(OffsetDateTime v) {
        this.validTo = v;
    }

    public String getSettlementCycle() {
        return settlementCycle;
    }

    public void setSettlementCycle(String v) {
        this.settlementCycle = v;
    }

    public BigDecimal getPlatformFeeRate() {
        return platformFeeRate;
    }

    public void setPlatformFeeRate(BigDecimal v) {
        this.platformFeeRate = v;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String v) {
        this.currency = v;
    }

    public BigDecimal getMinSettlementAmount() {
        return minSettlementAmount;
    }

    public void setMinSettlementAmount(BigDecimal v) {
        this.minSettlementAmount = v;
    }

    public OffsetDateTime getSignDeadline() {
        return signDeadline;
    }

    public void setSignDeadline(OffsetDateTime v) {
        this.signDeadline = v;
    }

    public String getSignerName() {
        return signerName;
    }

    public void setSignerName(String v) {
        this.signerName = v;
    }

    public String getSignerPhoneMask() {
        return signerPhoneMask;
    }

    public void setSignerPhoneMask(String v) {
        this.signerPhoneMask = v;
    }

    public String getSignMethod() {
        return signMethod;
    }

    public void setSignMethod(String v) {
        this.signMethod = v;
    }

    public String getTerms() {
        return terms;
    }

    public void setTerms(String v) {
        this.terms = v;
    }

    public Long getFileId() {
        return fileId;
    }

    public void setFileId(Long v) {
        this.fileId = v;
    }

    public OffsetDateTime getSignedAt() {
        return signedAt;
    }

    public void setSignedAt(OffsetDateTime v) {
        this.signedAt = v;
    }

    public OffsetDateTime getArchivedAt() {
        return archivedAt;
    }

    public void setArchivedAt(OffsetDateTime v) {
        this.archivedAt = v;
    }

    public String getVoidedReason() {
        return voidedReason;
    }

    public void setVoidedReason(String v) {
        this.voidedReason = v;
    }
}
