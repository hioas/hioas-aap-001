package com.hioas.aap.review;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 审核任务（表 {@code aap_review_task}，与报价单 1:1 —— 唯一索引 {@code uq_review_quote}）。
 *
 * <p>状态机（`10-报价与合同结算PRD.md` §4.1 状态-动作矩阵）：
 * {@code PENDING}（提交入池）→ {@code CLAIMED}（运营商务领取）→ {@code APPROVED} | {@code REJECTED}；
 * 驳回后供应商重提 → 复用同一行**回到 PENDING**（不新插行，避免唯一索引冲突）。
 *
 * <p>{@code tech_metrics_snapshot}：领取时冻结的检测结论快照（审核台左栏证据区）。
 * {@code tech_reviewed_by/at} 本任务族不写：清单内没有「技术指标复核」端点（TECH_OPS 只读），
 * 不臆造写入路径（偏差表 D-STATE-03）。
 */
@Table(value = "aap_review_task", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class ReviewTaskEntity extends BaseEntity {

    private Long quoteId;
    private Long providerId;
    private String status;
    private Long claimedBy;
    private OffsetDateTime claimedAt;
    private Long techReviewedBy;
    private OffsetDateTime techReviewedAt;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String techMetricsSnapshot;

    private String reviewComment;
    private String rejectReasonCode;
    private String rejectReasonText;

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

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public Long getClaimedBy() {
        return claimedBy;
    }

    public void setClaimedBy(Long v) {
        this.claimedBy = v;
    }

    public OffsetDateTime getClaimedAt() {
        return claimedAt;
    }

    public void setClaimedAt(OffsetDateTime v) {
        this.claimedAt = v;
    }

    public Long getTechReviewedBy() {
        return techReviewedBy;
    }

    public void setTechReviewedBy(Long v) {
        this.techReviewedBy = v;
    }

    public OffsetDateTime getTechReviewedAt() {
        return techReviewedAt;
    }

    public void setTechReviewedAt(OffsetDateTime v) {
        this.techReviewedAt = v;
    }

    public String getTechMetricsSnapshot() {
        return techMetricsSnapshot;
    }

    public void setTechMetricsSnapshot(String v) {
        this.techMetricsSnapshot = v;
    }

    public String getReviewComment() {
        return reviewComment;
    }

    public void setReviewComment(String v) {
        this.reviewComment = v;
    }

    public String getRejectReasonCode() {
        return rejectReasonCode;
    }

    public void setRejectReasonCode(String v) {
        this.rejectReasonCode = v;
    }

    public String getRejectReasonText() {
        return rejectReasonText;
    }

    public void setRejectReasonText(String v) {
        this.rejectReasonText = v;
    }
}
