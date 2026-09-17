package com.hioas.aap.provider;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 供应商资质（表 {@code aap_provider_qualification}）。 */
@Table(value = "aap_provider_qualification",
        onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class QualificationEntity extends BaseEntity {

    private Long providerId;
    private String category;
    private Long fileId;
    private String fileName;
    private Long fileSize;
    private String contentType;
    private String status;
    private OffsetDateTime uploadedAt;

    public Long getProviderId() {
        return providerId;
    }

    public void setProviderId(Long v) {
        this.providerId = v;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String v) {
        this.category = v;
    }

    public Long getFileId() {
        return fileId;
    }

    public void setFileId(Long v) {
        this.fileId = v;
    }

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String v) {
        this.fileName = v;
    }

    public Long getFileSize() {
        return fileSize;
    }

    public void setFileSize(Long v) {
        this.fileSize = v;
    }

    public String getContentType() {
        return contentType;
    }

    public void setContentType(String v) {
        this.contentType = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public OffsetDateTime getUploadedAt() {
        return uploadedAt;
    }

    public void setUploadedAt(OffsetDateTime v) {
        this.uploadedAt = v;
    }
}
