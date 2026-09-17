package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;

/** 时段片段（V8 start<end / V9 不重叠）（表 `aap_price_time_segment`）。 */
@Table(value = "aap_price_time_segment", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class PriceTimeSegmentEntity extends BaseEntity {

    private Long timeRuleId;
    private java.time.LocalTime startTime;
    private java.time.LocalTime endTime;
    private Integer seq;

    /** 所属时段规则 */
    public Long getTimeRuleId() {
        return timeRuleId;
    }

    public void setTimeRuleId(Long v) {
        this.timeRuleId = v;
    }

    /** 开始 */
    public java.time.LocalTime getStartTime() {
        return startTime;
    }

    public void setStartTime(java.time.LocalTime v) {
        this.startTime = v;
    }

    /** 结束 */
    public java.time.LocalTime getEndTime() {
        return endTime;
    }

    public void setEndTime(java.time.LocalTime v) {
        this.endTime = v;
    }

    /** 序号 */
    public Integer getSeq() {
        return seq;
    }

    public void setSeq(Integer v) {
        this.seq = v;
    }

}
