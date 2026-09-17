package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 请求规则（V15 仅管理端）（表 `aap_price_request_rule`）。 */
@Table(value = "aap_price_request_rule", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class PriceRequestRuleEntity extends BaseEntity {

    private Long itemId;
    private String whenExpr;
    private BigDecimal multiplier;
    private Boolean enabled;

    /** 明细行 */
    public Long getItemId() {
        return itemId;
    }

    public void setItemId(Long v) {
        this.itemId = v;
    }

    /** 条件表达式 */
    public String getWhenExpr() {
        return whenExpr;
    }

    public void setWhenExpr(String v) {
        this.whenExpr = v;
    }

    /** 倍率 */
    public BigDecimal getMultiplier() {
        return multiplier;
    }

    public void setMultiplier(BigDecimal v) {
        this.multiplier = v;
    }

    /** 启用 */
    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean v) {
        this.enabled = v;
    }

}
