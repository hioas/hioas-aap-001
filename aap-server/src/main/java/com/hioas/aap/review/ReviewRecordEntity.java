package com.hioas.aap.review;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;

/**
 * 审核记录（表 {@code aap_review_record}）：不可变行动时间线（C8 只插不改）。
 *
 * <p>{@code action} 取值来自 `10-报价与合同结算PRD.md` §3.6：
 * {@code ASSIGN|TECH_REVIEW|APPROVE|REJECT|WITHDRAW}；本任务族产生 ASSIGN（领取）/APPROVE/REJECT。
 */
@Table(value = "aap_review_record", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class ReviewRecordEntity extends BaseEntity {

    private Long quoteId;
    private Long taskId;
    private String action;
    private Long operatorId;
    private String operatorName;
    private String beforeStatus;
    private String afterStatus;
    private String comment;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String snapshot;

    public Long getQuoteId() {
        return quoteId;
    }

    public void setQuoteId(Long v) {
        this.quoteId = v;
    }

    public Long getTaskId() {
        return taskId;
    }

    public void setTaskId(Long v) {
        this.taskId = v;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String v) {
        this.action = v;
    }

    public Long getOperatorId() {
        return operatorId;
    }

    public void setOperatorId(Long v) {
        this.operatorId = v;
    }

    public String getOperatorName() {
        return operatorName;
    }

    public void setOperatorName(String v) {
        this.operatorName = v;
    }

    public String getBeforeStatus() {
        return beforeStatus;
    }

    public void setBeforeStatus(String v) {
        this.beforeStatus = v;
    }

    public String getAfterStatus() {
        return afterStatus;
    }

    public void setAfterStatus(String v) {
        this.afterStatus = v;
    }

    public String getComment() {
        return comment;
    }

    public void setComment(String v) {
        this.comment = v;
    }

    public String getSnapshot() {
        return snapshot;
    }

    public void setSnapshot(String v) {
        this.snapshot = v;
    }
}
