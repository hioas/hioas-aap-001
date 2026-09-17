package com.hioas.aap.compile;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 模拟验证用例（样例 token 向量）（表 `aap_verify_case`）。 */
@Table(value = "aap_verify_case", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class VerifyCaseEntity extends BaseEntity {

    private Long runId;
    private String caseCode;
    private String caseName;
    @Column(typeHandler = JsonbTypeHandler.class)
    private String input;
    private BigDecimal expected;
    private BigDecimal actual;
    private Boolean passed;
    private String diffNote;

    /** 验证批次 */
    public Long getRunId() {
        return runId;
    }

    public void setRunId(Long v) {
        this.runId = v;
    }

    /** 用例码 V1–V6 */
    public String getCaseCode() {
        return caseCode;
    }

    public void setCaseCode(String v) {
        this.caseCode = v;
    }

    /** 用例名 */
    public String getCaseName() {
        return caseName;
    }

    public void setCaseName(String v) {
        this.caseName = v;
    }

    /** 令牌向量 jsonb */
    public String getInput() {
        return input;
    }

    public void setInput(String v) {
        this.input = v;
    }

    /** 预期 */
    public BigDecimal getExpected() {
        return expected;
    }

    public void setExpected(BigDecimal v) {
        this.expected = v;
    }

    /** 实际 */
    public BigDecimal getActual() {
        return actual;
    }

    public void setActual(BigDecimal v) {
        this.actual = v;
    }

    /** 是否通过 */
    public Boolean getPassed() {
        return passed;
    }

    public void setPassed(Boolean v) {
        this.passed = v;
    }

    /** 差异说明 */
    public String getDiffNote() {
        return diffNote;
    }

    public void setDiffNote(String v) {
        this.diffNote = v;
    }

}
