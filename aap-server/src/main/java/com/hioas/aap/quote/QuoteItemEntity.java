package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 报价明细行（八大单价 + 档位/计价方式，UQ(quote_id, model_name)）（表 `aap_quote_item`）。 */
@Table(value = "aap_quote_item", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class QuoteItemEntity extends BaseEntity {

    private Long quoteId;
    private String modelName;
    private String modelAlias;
    private BigDecimal inputPrice;
    private BigDecimal outputPrice;
    private BigDecimal cacheReadPrice;
    private BigDecimal cacheWritePrice;
    /** 列名含数字段，MyBatis-Flex 默认驼峰转换会得到 cache_write1h_price → 必须显式指定列名 */
    @Column("cache_write_1h_price")
    private BigDecimal cacheWrite1hPrice;
    private BigDecimal imageInputPrice;
    private BigDecimal audioInputPrice;
    private BigDecimal imageOutputPrice;
    private BigDecimal audioOutputPrice;
    private String tierLabel;
    private String billingMode;
    private String compileStatus;
    private String note;

    /** 所属报价单 */
    public Long getQuoteId() {
        return quoteId;
    }

    public void setQuoteId(Long v) {
        this.quoteId = v;
    }

    /** 模型名 */
    public String getModelName() {
        return modelName;
    }

    public void setModelName(String v) {
        this.modelName = v;
    }

    /** 模型别名（V16 ≤64） */
    public String getModelAlias() {
        return modelAlias;
    }

    public void setModelAlias(String v) {
        this.modelAlias = v;
    }

    /** 输入价 */
    public BigDecimal getInputPrice() {
        return inputPrice;
    }

    public void setInputPrice(BigDecimal v) {
        this.inputPrice = v;
    }

    /** 输出价 */
    public BigDecimal getOutputPrice() {
        return outputPrice;
    }

    public void setOutputPrice(BigDecimal v) {
        this.outputPrice = v;
    }

    /** 缓存读取价 */
    public BigDecimal getCacheReadPrice() {
        return cacheReadPrice;
    }

    public void setCacheReadPrice(BigDecimal v) {
        this.cacheReadPrice = v;
    }

    /** 缓存写入价 */
    public BigDecimal getCacheWritePrice() {
        return cacheWritePrice;
    }

    public void setCacheWritePrice(BigDecimal v) {
        this.cacheWritePrice = v;
    }

    /** 1 小时缓存写入价 */
    public BigDecimal getCacheWrite1hPrice() {
        return cacheWrite1hPrice;
    }

    public void setCacheWrite1hPrice(BigDecimal v) {
        this.cacheWrite1hPrice = v;
    }

    /** 图像输入价 */
    public BigDecimal getImageInputPrice() {
        return imageInputPrice;
    }

    public void setImageInputPrice(BigDecimal v) {
        this.imageInputPrice = v;
    }

    /** 音频输入价 */
    public BigDecimal getAudioInputPrice() {
        return audioInputPrice;
    }

    public void setAudioInputPrice(BigDecimal v) {
        this.audioInputPrice = v;
    }

    /** 图像输出价 */
    public BigDecimal getImageOutputPrice() {
        return imageOutputPrice;
    }

    public void setImageOutputPrice(BigDecimal v) {
        this.imageOutputPrice = v;
    }

    /** 音频输出价 */
    public BigDecimal getAudioOutputPrice() {
        return audioOutputPrice;
    }

    public void setAudioOutputPrice(BigDecimal v) {
        this.audioOutputPrice = v;
    }

    /** 档位（客户端 body 键 tier） */
    public String getTierLabel() {
        return tierLabel;
    }

    public void setTierLabel(String v) {
        this.tierLabel = v;
    }

    /** 计价方式（客户端 body 键 billing_mode） */
    public String getBillingMode() {
        return billingMode;
    }

    public void setBillingMode(String v) {
        this.billingMode = v;
    }

    /** 编译状态 */
    public String getCompileStatus() {
        return compileStatus;
    }

    public void setCompileStatus(String v) {
        this.compileStatus = v;
    }

    /** 备注 */
    public String getNote() {
        return note;
    }

    public void setNote(String v) {
        this.note = v;
    }

}
