package com.hioas.aap.compile;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 模拟验证批次（★ 强制闸门）（表 `aap_verify_run`）。 */
@Table(value = "aap_verify_run", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class VerifyRunEntity extends BaseEntity {

    private Long compilationId;
    private String status;
    private Integer caseTotal;
    private Integer casePassed;
    private String failedField;
    private OffsetDateTime startedAt;
    private OffsetDateTime finishedAt;

    /** 编译产物 */
    public Long getCompilationId() {
        return compilationId;
    }

    public void setCompilationId(Long v) {
        this.compilationId = v;
    }

    /** PASSED/FAILED */
    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    /** 用例总数 */
    public Integer getCaseTotal() {
        return caseTotal;
    }

    public void setCaseTotal(Integer v) {
        this.caseTotal = v;
    }

    /** 通过数 */
    public Integer getCasePassed() {
        return casePassed;
    }

    public void setCasePassed(Integer v) {
        this.casePassed = v;
    }

    /** 失败定位字段（4.2 必须定位到报价单字段） */
    public String getFailedField() {
        return failedField;
    }

    public void setFailedField(String v) {
        this.failedField = v;
    }

    /** 开始 */
    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(OffsetDateTime v) {
        this.startedAt = v;
    }

    /** 结束 */
    public OffsetDateTime getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(OffsetDateTime v) {
        this.finishedAt = v;
    }

}
