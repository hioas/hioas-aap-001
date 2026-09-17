package com.hioas.aap.support;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;

/**
 * 审计日志（表 {@code aap_audit_log}，append-only，C8）。
 *
 * <p>四类必录操作（R-47 / AC-48）：凭证明文访问、报价审核、同步写价、检测人工放行；
 * 本表只插入不更新（迁移里 DB 层只授予 INSERT/SELECT）。
 */
@Table(value = "aap_audit_log", onInsert = AuditListeners.Insert.class)
public class AuditLogEntity extends BaseEntity {

    private String traceId;
    private String actorType;
    private Long actorId;
    private String actorName;
    private String actorIp;
    private String userAgent;
    private String action;
    private String targetType;
    private Long targetId;
    private String summary;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String beforeValue;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String afterValue;

    private String result;
    private String riskLevel;

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String v) {
        this.traceId = v;
    }

    public String getActorType() {
        return actorType;
    }

    public void setActorType(String v) {
        this.actorType = v;
    }

    public Long getActorId() {
        return actorId;
    }

    public void setActorId(Long v) {
        this.actorId = v;
    }

    public String getActorName() {
        return actorName;
    }

    public void setActorName(String v) {
        this.actorName = v;
    }

    public String getActorIp() {
        return actorIp;
    }

    public void setActorIp(String v) {
        this.actorIp = v;
    }

    public String getUserAgent() {
        return userAgent;
    }

    public void setUserAgent(String v) {
        this.userAgent = v;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String v) {
        this.action = v;
    }

    public String getTargetType() {
        return targetType;
    }

    public void setTargetType(String v) {
        this.targetType = v;
    }

    public Long getTargetId() {
        return targetId;
    }

    public void setTargetId(Long v) {
        this.targetId = v;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String v) {
        this.summary = v;
    }

    public String getBeforeValue() {
        return beforeValue;
    }

    public void setBeforeValue(String v) {
        this.beforeValue = v;
    }

    public String getAfterValue() {
        return afterValue;
    }

    public void setAfterValue(String v) {
        this.afterValue = v;
    }

    public String getResult() {
        return result;
    }

    public void setResult(String v) {
        this.result = v;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public void setRiskLevel(String v) {
        this.riskLevel = v;
    }
}
