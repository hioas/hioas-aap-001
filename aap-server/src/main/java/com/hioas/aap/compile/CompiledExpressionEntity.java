package com.hioas.aap.compile;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 编译产物（三道闸门：COMPILED→VERIFIED→CONFIRMED，R-33）（表 `aap_compiled_expression`）。 */
@Table(value = "aap_compiled_expression", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class CompiledExpressionEntity extends BaseEntity {

    private Long quoteId;
    private Integer quoteVersion;
    private Long providerId;
    private String status;
    private String gateStatus;
    private String sourceHash;
    private String compilerVersion;
    @Column(typeHandler = JsonbTypeHandler.class)
    private String previousExpr;
    private Boolean publishBlocked;
    @Column(typeHandler = JsonbTypeHandler.class)
    private String verifyReport;
    private Long confirmedBy;
    private OffsetDateTime confirmedAt;

    /** 报价单 */
    public Long getQuoteId() {
        return quoteId;
    }

    public void setQuoteId(Long v) {
        this.quoteId = v;
    }

    /** 报价版本 */
    public Integer getQuoteVersion() {
        return quoteVersion;
    }

    public void setQuoteVersion(Integer v) {
        this.quoteVersion = v;
    }

    /** 供应商 */
    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    /** 状态 */
    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    /** 闸门状态 COMPILED/VERIFIED/CONFIRMED/FAILED */
    public String getGateStatus() {
        return gateStatus;
    }

    public void setGateStatus(String v) {
        this.gateStatus = v;
    }

    /** 报价内容哈希（R-34 幂等） */
    public String getSourceHash() {
        return sourceHash;
    }

    public void setSourceHash(String v) {
        this.sourceHash = v;
    }

    /** 编译器版本 */
    public String getCompilerVersion() {
        return compilerVersion;
    }

    public void setCompilerVersion(String v) {
        this.compilerVersion = v;
    }

    /** 上一版表达式快照 jsonb（4.3 保留旧快照） */
    public String getPreviousExpr() {
        return previousExpr;
    }

    public void setPreviousExpr(String v) {
        this.previousExpr = v;
    }

    /** 未确认禁止写入 new-api（R-33） */
    public Boolean getPublishBlocked() {
        return publishBlocked;
    }

    public void setPublishBlocked(Boolean v) {
        this.publishBlocked = v;
    }

    /** 模拟验证报告 jsonb */
    public String getVerifyReport() {
        return verifyReport;
    }

    public void setVerifyReport(String v) {
        this.verifyReport = v;
    }

    /** 确认人 */
    public Long getConfirmedBy() {
        return confirmedBy;
    }

    public void setConfirmedBy(Long v) {
        this.confirmedBy = v;
    }

    /** 确认时间 */
    public OffsetDateTime getConfirmedAt() {
        return confirmedAt;
    }

    public void setConfirmedAt(OffsetDateTime v) {
        this.confirmedAt = v;
    }

}
