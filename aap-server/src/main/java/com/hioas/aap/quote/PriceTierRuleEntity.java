package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;

/** 阶梯规则（V13 tier_field=len / V14 OVERRIDE 每档有价）（表 `aap_price_tier_rule`）。 */
@Table(value = "aap_price_tier_rule", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class PriceTierRuleEntity extends BaseEntity {

    private Long itemId;
    private String tierField;
    private String priceStrategy;

    /** 明细行 */
    public Long getItemId() {
        return itemId;
    }

    public void setItemId(Long v) {
        this.itemId = v;
    }

    /** 分档字段（仅 len） */
    public String getTierField() {
        return tierField;
    }

    public void setTierField(String v) {
        this.tierField = v;
    }

    /** 价格策略 OVERRIDE */
    public String getPriceStrategy() {
        return priceStrategy;
    }

    public void setPriceStrategy(String v) {
        this.priceStrategy = v;
    }

}
