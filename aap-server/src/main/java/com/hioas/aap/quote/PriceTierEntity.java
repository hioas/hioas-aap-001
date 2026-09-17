package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 阶梯档位（V11 连续无空洞 / V12 首档 min=0 末档 open）（表 `aap_price_tier`）。 */
@Table(value = "aap_price_tier", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class PriceTierEntity extends BaseEntity {

    private Long tierRuleId;
    private Integer seq;
    private BigDecimal minValue;
    private BigDecimal maxValue;
    private String label;
    private BigDecimal inputPrice;
    private BigDecimal outputPrice;
    private BigDecimal cacheReadPrice;
    private BigDecimal multiplier;

    /** 所属阶梯规则 */
    public Long getTierRuleId() {
        return tierRuleId;
    }

    public void setTierRuleId(Long v) {
        this.tierRuleId = v;
    }

    /** 序号 */
    public Integer getSeq() {
        return seq;
    }

    public void setSeq(Integer v) {
        this.seq = v;
    }

    /** 下界 */
    public BigDecimal getMinValue() {
        return minValue;
    }

    public void setMinValue(BigDecimal v) {
        this.minValue = v;
    }

    /** 上界（null=开放） */
    public BigDecimal getMaxValue() {
        return maxValue;
    }

    public void setMaxValue(BigDecimal v) {
        this.maxValue = v;
    }

    /** 档位标签 */
    public String getLabel() {
        return label;
    }

    public void setLabel(String v) {
        this.label = v;
    }

    /** 档内输入价 */
    public BigDecimal getInputPrice() {
        return inputPrice;
    }

    public void setInputPrice(BigDecimal v) {
        this.inputPrice = v;
    }

    /** 档内输出价 */
    public BigDecimal getOutputPrice() {
        return outputPrice;
    }

    public void setOutputPrice(BigDecimal v) {
        this.outputPrice = v;
    }

    /** 档内缓存读取价 */
    public BigDecimal getCacheReadPrice() {
        return cacheReadPrice;
    }

    public void setCacheReadPrice(BigDecimal v) {
        this.cacheReadPrice = v;
    }

    /** 档内倍率 */
    public BigDecimal getMultiplier() {
        return multiplier;
    }

    public void setMultiplier(BigDecimal v) {
        this.multiplier = v;
    }

}
