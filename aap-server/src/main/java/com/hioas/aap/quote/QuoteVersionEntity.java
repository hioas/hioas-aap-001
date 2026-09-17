package com.hioas.aap.quote;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;

/** 报价版本快照（不可变 C9）（表 `aap_quote_version`）。 */
@Table(value = "aap_quote_version", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class QuoteVersionEntity extends BaseEntity {

    private Long quoteId;
    private Integer versionNo;
    @Column(typeHandler = JsonbTypeHandler.class)
    private String snapshot;
    private String sourceHash;

    /** 报价单 */
    public Long getQuoteId() {
        return quoteId;
    }

    public void setQuoteId(Long v) {
        this.quoteId = v;
    }

    /** 版本号 */
    public Integer getVersionNo() {
        return versionNo;
    }

    public void setVersionNo(Integer v) {
        this.versionNo = v;
    }

    /** 快照 jsonb（不可变） */
    public String getSnapshot() {
        return snapshot;
    }

    public void setSnapshot(String v) {
        this.snapshot = v;
    }

    /** 源哈希 */
    public String getSourceHash() {
        return sourceHash;
    }

    public void setSourceHash(String v) {
        this.sourceHash = v;
    }

}
