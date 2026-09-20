package com.hioas.aap.catalog;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/**
 * 模型目录（表 {@code aap_model}）。
 *
 * <p>真源：Calicat 设计 page-3-2「新增模型」+ {@code .calicat/prd/13-管理端PRD.md}。
 *
 * <p><b>这张表最重要的消费方不是管理端，而是 H5 端「接入凭证」页</b>：
 * 供应商接入凭证时的模型下拉就来自这里（用户 2026-09-20 指令）。
 * 因此 {@code modelUid} 必须稳定 —— 进凭证 {@code model_list} 的就是它。
 *
 * <p>{@code modelType} 取值：{@code CHAT} 对话 / {@code REASONING} 推理 / {@code EMBEDDING} 向量 /
 * {@code IMAGE} 图像 / {@code AUDIO} 语音。
 *
 * <p>{@code capabilities} 是 JSON 数组（多选能力标签），用于路由与能力筛选。
 */
@Table(value = "aap_model", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class ModelCatalogEntity extends BaseEntity {

    /** 所属厂商（外键 aap_vendor.id，必填） */
    private Long vendorId;

    /** 模型名称（展示用，如 GPT-4o mini） */
    private String modelName;

    /** 模型标识（如 gpt-4o-mini）—— 唯一；进 model_list 的就是它 */
    private String modelUid;

    /** 模型类型：CHAT / REASONING / EMBEDDING / IMAGE / AUDIO */
    private String modelType;

    /** 上下文长度（tokens） */
    private Integer contextWindow;

    /** 最大输出（tokens） */
    private Integer maxOutput;

    /** 输入价格 —— ⚠️ 单位口径见 V9 迁移头部 D-ADM-4（待裁定，未做换算） */
    private BigDecimal inputPrice;

    /** 输出价格 —— ⚠️ 同上 */
    private BigDecimal outputPrice;

    /** 能力标签（JSON 数组：FUNCTION_CALL / VISION / JSON_MODE / STREAM / LONG_TEXT / DEEP_REASONING） */
    @Column(typeHandler = JsonbTypeHandler.class)
    private String capabilities;

    /** 接入地址（Base URL）—— 留空表示继承厂商默认 */
    private String baseUrl;

    /** API Key（密文，覆盖厂商默认；仅管理员可见） */
    private String apiKeyCipher;

    /** 保存后立即启用（启用后该模型将加入可用模型池） */
    private Boolean enabled;

    /** 备注 */
    private String remark;

    public Long getVendorId() {
        return vendorId;
    }

    public void setVendorId(Long v) {
        this.vendorId = v;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String v) {
        this.modelName = v;
    }

    public String getModelUid() {
        return modelUid;
    }

    public void setModelUid(String v) {
        this.modelUid = v;
    }

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String v) {
        this.modelType = v;
    }

    public Integer getContextWindow() {
        return contextWindow;
    }

    public void setContextWindow(Integer v) {
        this.contextWindow = v;
    }

    public Integer getMaxOutput() {
        return maxOutput;
    }

    public void setMaxOutput(Integer v) {
        this.maxOutput = v;
    }

    public BigDecimal getInputPrice() {
        return inputPrice;
    }

    public void setInputPrice(BigDecimal v) {
        this.inputPrice = v;
    }

    public BigDecimal getOutputPrice() {
        return outputPrice;
    }

    public void setOutputPrice(BigDecimal v) {
        this.outputPrice = v;
    }

    public String getCapabilities() {
        return capabilities;
    }

    public void setCapabilities(String v) {
        this.capabilities = v;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String v) {
        this.baseUrl = v;
    }

    public String getApiKeyCipher() {
        return apiKeyCipher;
    }

    public void setApiKeyCipher(String v) {
        this.apiKeyCipher = v;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean v) {
        this.enabled = v;
    }

    public String getRemark() {
        return remark;
    }

    public void setRemark(String v) {
        this.remark = v;
    }
}
