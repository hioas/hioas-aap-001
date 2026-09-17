package com.hioas.aap.report;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 报告章节快照（表 {@code aap_report_section}，章节 A–F）。 */
@Table(value = "aap_report_section",
        onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class ReportSectionEntity extends BaseEntity {

    private Long reportId;
    private String sectionCode;
    private String sectionName;
    private BigDecimal avgScore;
    private Boolean scored;
    private String note;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String items;

    private Integer seq;

    public Long getReportId() {
        return reportId;
    }

    public void setReportId(Long v) {
        this.reportId = v;
    }

    public String getSectionCode() {
        return sectionCode;
    }

    public void setSectionCode(String v) {
        this.sectionCode = v;
    }

    public String getSectionName() {
        return sectionName;
    }

    public void setSectionName(String v) {
        this.sectionName = v;
    }

    public BigDecimal getAvgScore() {
        return avgScore;
    }

    public void setAvgScore(BigDecimal v) {
        this.avgScore = v;
    }

    public Boolean getScored() {
        return scored;
    }

    public void setScored(Boolean v) {
        this.scored = v;
    }

    public String getNote() {
        return note;
    }

    public void setNote(String v) {
        this.note = v;
    }

    public String getItems() {
        return items;
    }

    public void setItems(String v) {
        this.items = v;
    }

    public Integer getSeq() {
        return seq;
    }

    public void setSeq(Integer v) {
        this.seq = v;
    }
}
