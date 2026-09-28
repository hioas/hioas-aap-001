package com.hioas.aap.supply;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/**
 * 供给单元（表 {@code aap_supply_unit}）—— 可调度单元 = **模型 × 供应商**。
 *
 * <p>真源：`specs/001-intake-automation/spec.md` §3.2（渠道粒度范式）+ `data-model.md` §3。
 *
 * <p>为什么它是聚合根：new-api 的调度能力（`priority` / `weight` / `auto_ban` / 启停 /
 * 参数覆盖）全部挂在**渠道**上。把渠道粒度定为「模型 × 供应商」后，这些能力才从供应商级
 * 提升为**模型级** —— 某模型上游故障只影响该模型，同供应商其他模型不受牵连。
 *
 * <p>{@code modelSlug} 由 {@code ChannelNameGenerator} 生成（R-55：超长含 4 位哈希后缀），
 * 与 {@code channel_name} 一一对应，是「同名即同一供给单元」幂等判定的自然键。
 */
@Table(value = "aap_supply_unit", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class SupplyUnitEntity extends BaseEntity {

    /** 供应商（外键 aap_provider.id，必填） */
    private Long providerId;

    /** 凭证（外键 aap_credential.id） */
    private Long credentialId;

    /** 平台模型名（权威来源；渠道名中的 slug 由它归一而来） */
    private String modelName;

    /** 渠道名用 slug（R-55） */
    private String modelSlug;

    /** 关联模型目录标识 aap_model.model_uid（可空） */
    private String modelUid;

    /** 状态机：PENDING/CONFIGURING/ONLINE/DEGRADED/SUSPENDED/OFFLINE */
    private String status;

    /** 最近一次检测总分（快照） */
    private BigDecimal detectTotalScore;

    /** 最近一次检测置信度：HIGH/MEDIUM/LOW */
    private String detectConfidence;

    /** 运行质量分（仅由质量反馈聚合任务写入，R-64 可解释性） */
    private BigDecimal qualityScore;

    /** 期望调度优先级（写入网关的期望值；实际值以渠道回读为准） */
    private Integer routingPriority;

    /** 期望调度权重（由检测分与质量分计算，INNOV-4） */
    private Integer routingWeight;

    /** 是否开启网关自动禁用（连续失败自动摘除，模型级熔断） */
    private Boolean autoBanEnabled;

    /** 对应渠道绑定（PER_MODEL 时 1:1） */
    private Long bindingId;

    /** 粒度：PER_MODEL 一模型一渠道 / PER_PROVIDER 合并渠道（DR-03） */
    private String granularity;

    // ---- getters / setters ----

    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long providerId) {
        this.providerId = providerId;
    }

    public Long getCredentialId() {
        return credentialId;
    }

    public void setCredentialId(Long credentialId) {
        this.credentialId = credentialId;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getModelSlug() {
        return modelSlug;
    }

    public void setModelSlug(String modelSlug) {
        this.modelSlug = modelSlug;
    }

    public String getModelUid() {
        return modelUid;
    }

    public void setModelUid(String modelUid) {
        this.modelUid = modelUid;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public BigDecimal getDetectTotalScore() {
        return detectTotalScore;
    }

    public void setDetectTotalScore(BigDecimal detectTotalScore) {
        this.detectTotalScore = detectTotalScore;
    }

    public String getDetectConfidence() {
        return detectConfidence;
    }

    public void setDetectConfidence(String detectConfidence) {
        this.detectConfidence = detectConfidence;
    }

    public BigDecimal getQualityScore() {
        return qualityScore;
    }

    public void setQualityScore(BigDecimal qualityScore) {
        this.qualityScore = qualityScore;
    }

    public Integer getRoutingPriority() {
        return routingPriority;
    }

    public void setRoutingPriority(Integer routingPriority) {
        this.routingPriority = routingPriority;
    }

    public Integer getRoutingWeight() {
        return routingWeight;
    }

    public void setRoutingWeight(Integer routingWeight) {
        this.routingWeight = routingWeight;
    }

    public Boolean getAutoBanEnabled() {
        return autoBanEnabled;
    }

    public void setAutoBanEnabled(Boolean autoBanEnabled) {
        this.autoBanEnabled = autoBanEnabled;
    }

    public Long getBindingId() {
        return bindingId;
    }

    public void setBindingId(Long bindingId) {
        this.bindingId = bindingId;
    }

    public String getGranularity() {
        return granularity;
    }

    public void setGranularity(String granularity) {
        this.granularity = granularity;
    }
}
