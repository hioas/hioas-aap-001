package com.hioas.aap.file;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 文件资产（表 {@code aap_file_asset}）。
 *
 * <p><b>补缺陷2</b>：本表此前在主代码里只有 3 处 SELECT、**零 INSERT**，
 * 导致合同签发（{@code contract-issue} 的 {@code file_id} 必填）永远无法完成。
 */
@Table(value = "aap_file_asset",
        onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class FileAssetEntity extends BaseEntity {

    /** 存储键（相对 storage root 的路径，不含 root 前缀；唯一索引 uq_file_key）。 */
    private String fileKey;
    private String bucket;
    private String originalName;
    private String contentType;
    private Long sizeBytes;
    private String sha256;
    /** 业务类型：CONTRACT / QUALIFICATION / VOUCHER 等（调用方声明，用于归属判断）。 */
    private String bizType;
    private Boolean encrypted;
    private String status;
    private OffsetDateTime expireAt;

    public String getFileKey() {
        return fileKey;
    }

    public void setFileKey(String v) {
        this.fileKey = v;
    }

    public String getBucket() {
        return bucket;
    }

    public void setBucket(String v) {
        this.bucket = v;
    }

    public String getOriginalName() {
        return originalName;
    }

    public void setOriginalName(String v) {
        this.originalName = v;
    }

    public String getContentType() {
        return contentType;
    }

    public void setContentType(String v) {
        this.contentType = v;
    }

    public Long getSizeBytes() {
        return sizeBytes;
    }

    public void setSizeBytes(Long v) {
        this.sizeBytes = v;
    }

    public String getSha256() {
        return sha256;
    }

    public void setSha256(String v) {
        this.sha256 = v;
    }

    public String getBizType() {
        return bizType;
    }

    public void setBizType(String v) {
        this.bizType = v;
    }

    public Boolean getEncrypted() {
        return encrypted;
    }

    public void setEncrypted(Boolean v) {
        this.encrypted = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public OffsetDateTime getExpireAt() {
        return expireAt;
    }

    public void setExpireAt(OffsetDateTime v) {
        this.expireAt = v;
    }
}
