package com.hioas.aap.compile;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;

/** 单模型计费表达式（R6 多模型独立）（表 `aap_model_expression`）。 */
@Table(value = "aap_model_expression", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class ModelExpressionEntity extends BaseEntity {

    private Long compilationId;
    private String modelName;
    private String exprVersion;
    private String expr;
    @Column(typeHandler = JsonbTypeHandler.class)
    private String tierLabels;
    @Column(typeHandler = JsonbTypeHandler.class)
    private String ruleHits;
    private Boolean verified;
    private String sourceHash;
    private String inlineExpanded;

    /** 编译产物 */
    public Long getCompilationId() {
        return compilationId;
    }

    public void setCompilationId(Long v) {
        this.compilationId = v;
    }

    /** 模型名 */
    public String getModelName() {
        return modelName;
    }

    public void setModelName(String v) {
        this.modelName = v;
    }

    /** 表达式版本 */
    public String getExprVersion() {
        return exprVersion;
    }

    public void setExprVersion(String v) {
        this.exprVersion = v;
    }

    /** 表达式文本 */
    public String getExpr() {
        return expr;
    }

    public void setExpr(String v) {
        this.expr = v;
    }

    /** 档位标签 jsonb */
    public String getTierLabels() {
        return tierLabels;
    }

    public void setTierLabels(String v) {
        this.tierLabels = v;
    }

    /** 命中的规则 jsonb */
    public String getRuleHits() {
        return ruleHits;
    }

    public void setRuleHits(String v) {
        this.ruleHits = v;
    }

    /** 是否通过模拟验证 */
    public Boolean getVerified() {
        return verified;
    }

    public void setVerified(Boolean v) {
        this.verified = v;
    }

    /** 源哈希 */
    public String getSourceHash() {
        return sourceHash;
    }

    public void setSourceHash(String v) {
        this.sourceHash = v;
    }

    /** 展开后的表达式（写入 new-api 用） */
    public String getInlineExpanded() {
        return inlineExpanded;
    }

    public void setInlineExpanded(String v) {
        this.inlineExpanded = v;
    }

}
