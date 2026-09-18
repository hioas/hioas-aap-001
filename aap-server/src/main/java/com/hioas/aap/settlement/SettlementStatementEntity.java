package com.hioas.aap.settlement;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;

/** 结算单（表 {@code aap_settlement_statement}）：周期 + 平台服务费；明细见 {@code aap_settlement_line}。 */
@Table(value = "aap_settlement_statement", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class SettlementStatementEntity extends BaseEntity {

    private String statementNo;
    private Long providerId;
    private OffsetDateTime periodFrom;
    private OffsetDateTime periodTo;
    private BigDecimal totalAmount;
    private BigDecimal platformFee;
    private String status;

    public String getStatementNo() {
        return statementNo;
    }

    public void setStatementNo(String v) {
        this.statementNo = v;
    }

    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    public OffsetDateTime getPeriodFrom() {
        return periodFrom;
    }

    public void setPeriodFrom(OffsetDateTime v) {
        this.periodFrom = v;
    }

    public OffsetDateTime getPeriodTo() {
        return periodTo;
    }

    public void setPeriodTo(OffsetDateTime v) {
        this.periodTo = v;
    }

    public BigDecimal getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(BigDecimal v) {
        this.totalAmount = v;
    }

    public BigDecimal getPlatformFee() {
        return platformFee;
    }

    public void setPlatformFee(BigDecimal v) {
        this.platformFee = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }
}
