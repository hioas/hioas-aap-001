package com.hioas.aap.settlement;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;

/**
 * 打款记录（表 {@code aap_payment_record}）。
 *
 * <p>R-42：平台**只记录打款**，不做资金流转——本表是留痕，不是账户余额。
 * {@code status} = {@code UNSETTLED/PAYMENT_RECORDED/CONFIRMED/VOID}；{@code voucher_file_id} 为打款凭证（C5 必填）。
 */
@Table(value = "aap_payment_record", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class PaymentRecordEntity extends BaseEntity {

    private Long providerId;
    private Long contractId;
    private Long statementId;
    private BigDecimal amount;
    private String currency;
    private String status;
    private Long voucherFileId;
    private OffsetDateTime paidAt;
    private Long confirmedBy;
    private OffsetDateTime confirmedAt;
    private String remark;

    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    public Long getContractId() {
        return contractId;
    }

    public void setContractId(Long v) {
        this.contractId = v;
    }

    public Long getStatementId() {
        return statementId;
    }

    public void setStatementId(Long v) {
        this.statementId = v;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal v) {
        this.amount = v;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String v) {
        this.currency = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public Long getVoucherFileId() {
        return voucherFileId;
    }

    public void setVoucherFileId(Long v) {
        this.voucherFileId = v;
    }

    public OffsetDateTime getPaidAt() {
        return paidAt;
    }

    public void setPaidAt(OffsetDateTime v) {
        this.paidAt = v;
    }

    public Long getConfirmedBy() {
        return confirmedBy;
    }

    public void setConfirmedBy(Long v) {
        this.confirmedBy = v;
    }

    public OffsetDateTime getConfirmedAt() {
        return confirmedAt;
    }

    public void setConfirmedAt(OffsetDateTime v) {
        this.confirmedAt = v;
    }

    public String getRemark() {
        return remark;
    }

    public void setRemark(String v) {
        this.remark = v;
    }
}
