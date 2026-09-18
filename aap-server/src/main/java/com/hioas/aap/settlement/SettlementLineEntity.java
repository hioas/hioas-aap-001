package com.hioas.aap.settlement;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 结算明细行（表 {@code aap_settlement_line}）：按渠道/模型汇总用量与金额。 */
@Table(value = "aap_settlement_line", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class SettlementLineEntity extends BaseEntity {

    private Long statementId;
    private Long channelId;
    private String modelName;
    private Long totalTokens;
    private BigDecimal quotaRaw;
    private BigDecimal amount;

    public Long getStatementId() {
        return statementId;
    }

    public void setStatementId(Long v) {
        this.statementId = v;
    }

    public Long getChannelId() {
        return channelId;
    }

    public void setChannelId(Long v) {
        this.channelId = v;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String v) {
        this.modelName = v;
    }

    public Long getTotalTokens() {
        return totalTokens;
    }

    public void setTotalTokens(Long v) {
        this.totalTokens = v;
    }

    public BigDecimal getQuotaRaw() {
        return quotaRaw;
    }

    public void setQuotaRaw(BigDecimal v) {
        this.quotaRaw = v;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal v) {
        this.amount = v;
    }
}
