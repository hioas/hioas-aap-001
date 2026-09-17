package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 时段规则（V7 tz 白名单 / V10 倍率>0）（表 `aap_price_time_rule`）。 */
@Table(value = "aap_price_time_rule", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class PriceTimeRuleEntity extends BaseEntity {

    private Long itemId;
    private String tz;
    private String weekdayScope;
    private BigDecimal peakMultiplier;
    private BigDecimal offpeakMultiplier;
    private BigDecimal peakPriceOverride;

    /** 明细行 */
    public Long getItemId() {
        return itemId;
    }

    public void setItemId(Long v) {
        this.itemId = v;
    }

    /** 时区（白名单） */
    public String getTz() {
        return tz;
    }

    public void setTz(String v) {
        this.tz = v;
    }

    /** 星期范围 */
    public String getWeekdayScope() {
        return weekdayScope;
    }

    public void setWeekdayScope(String v) {
        this.weekdayScope = v;
    }

    /** 高峰倍率 */
    public BigDecimal getPeakMultiplier() {
        return peakMultiplier;
    }

    public void setPeakMultiplier(BigDecimal v) {
        this.peakMultiplier = v;
    }

    /** 低谷倍率 */
    public BigDecimal getOffpeakMultiplier() {
        return offpeakMultiplier;
    }

    public void setOffpeakMultiplier(BigDecimal v) {
        this.offpeakMultiplier = v;
    }

    /** 高峰覆盖价 */
    public BigDecimal getPeakPriceOverride() {
        return peakPriceOverride;
    }

    public void setPeakPriceOverride(BigDecimal v) {
        this.peakPriceOverride = v;
    }

}
