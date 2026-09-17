package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 报价单（状态机 DRAFT/SUBMITTED/REVIEWING/REJECTED/APPROVED/CONVERTED/VOID）（表 `aap_quote`）。 */
@Table(value = "aap_quote", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class QuoteEntity extends BaseEntity {

    private String quoteNo;
    private Long providerId;
    private Long credentialId;
    private String name;
    private String status;
    private Integer currentVersion;
    private String currency;
    private OffsetDateTime validFrom;
    private OffsetDateTime validTo;
    private Integer itemCount;
    private String remark;
    private String rejectReasonCode;
    private String rejectReasonText;
    private OffsetDateTime submittedAt;
    private Long submittedBy;
    private OffsetDateTime withdrawnAt;
    private Long reviewedBy;
    private OffsetDateTime reviewedAt;
    private Integer approvedQuoteVersion;
    private Long contractId;
    private Long lastCompilationId;
    private String sourceHash;

    /** 报价单号 Q{yyyyMMdd}{6位} */
    public String getQuoteNo() {
        return quoteNo;
    }

    public void setQuoteNo(String v) {
        this.quoteNo = v;
    }

    /** 供应商 */
    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    /** 凭证 */
    public Long getCredentialId() {
        return credentialId;
    }

    public void setCredentialId(Long v) {
        this.credentialId = v;
    }

    /** 报价单名称（客户端推断字段 name，missing-prd） */
    public String getName() {
        return name;
    }

    public void setName(String v) {
        this.name = v;
    }

    /** 状态 */
    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    /** 当前版本号 */
    public Integer getCurrentVersion() {
        return currentVersion;
    }

    public void setCurrentVersion(Integer v) {
        this.currentVersion = v;
    }

    /** 币种 */
    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String v) {
        this.currency = v;
    }

    /** 有效期起 */
    public OffsetDateTime getValidFrom() {
        return validFrom;
    }

    public void setValidFrom(OffsetDateTime v) {
        this.validFrom = v;
    }

    /** 有效期止 */
    public OffsetDateTime getValidTo() {
        return validTo;
    }

    public void setValidTo(OffsetDateTime v) {
        this.validTo = v;
    }

    /** 明细行数 */
    public Integer getItemCount() {
        return itemCount;
    }

    public void setItemCount(Integer v) {
        this.itemCount = v;
    }

    /** 备注 */
    public String getRemark() {
        return remark;
    }

    public void setRemark(String v) {
        this.remark = v;
    }

    /** 驳回原因码（10-PRD §5.2） */
    public String getRejectReasonCode() {
        return rejectReasonCode;
    }

    public void setRejectReasonCode(String v) {
        this.rejectReasonCode = v;
    }

    /** 驳回说明 */
    public String getRejectReasonText() {
        return rejectReasonText;
    }

    public void setRejectReasonText(String v) {
        this.rejectReasonText = v;
    }

    /** 提交时间 */
    public OffsetDateTime getSubmittedAt() {
        return submittedAt;
    }

    public void setSubmittedAt(OffsetDateTime v) {
        this.submittedAt = v;
    }

    /** 提交人 */
    public Long getSubmittedBy() {
        return submittedBy;
    }

    public void setSubmittedBy(Long v) {
        this.submittedBy = v;
    }

    /** 撤回时间 */
    public OffsetDateTime getWithdrawnAt() {
        return withdrawnAt;
    }

    public void setWithdrawnAt(OffsetDateTime v) {
        this.withdrawnAt = v;
    }

    /** 审核人 */
    public Long getReviewedBy() {
        return reviewedBy;
    }

    public void setReviewedBy(Long v) {
        this.reviewedBy = v;
    }

    /** 审核时间 */
    public OffsetDateTime getReviewedAt() {
        return reviewedAt;
    }

    public void setReviewedAt(OffsetDateTime v) {
        this.reviewedAt = v;
    }

    /** 通过时的报价版本 */
    public Integer getApprovedQuoteVersion() {
        return approvedQuoteVersion;
    }

    public void setApprovedQuoteVersion(Integer v) {
        this.approvedQuoteVersion = v;
    }

    /** 关联合同 */
    public Long getContractId() {
        return contractId;
    }

    public void setContractId(Long v) {
        this.contractId = v;
    }

    /** 最近编译任务 */
    public Long getLastCompilationId() {
        return lastCompilationId;
    }

    public void setLastCompilationId(Long v) {
        this.lastCompilationId = v;
    }

    /** 编译源哈希（R-34 幂等） */
    public String getSourceHash() {
        return sourceHash;
    }

    public void setSourceHash(String v) {
        this.sourceHash = v;
    }

}
