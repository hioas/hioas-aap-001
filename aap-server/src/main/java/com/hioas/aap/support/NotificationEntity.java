package com.hioas.aap.support;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 站内信/短信通知（表 {@code aap_notification}；列表与已读接口见 T13）。 */
@Table(value = "aap_notification", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class NotificationEntity extends BaseEntity {

    private String recipientType;
    private Long recipientId;
    private String channel;
    private String eventCode;
    private String title;
    private String content;
    private String bizType;
    private Long bizId;
    private String category;
    private OffsetDateTime readAt;
    private String status;

    public String getRecipientType() {
        return recipientType;
    }

    public void setRecipientType(String v) {
        this.recipientType = v;
    }

    public Long getRecipientId() {
        return recipientId;
    }

    public void setRecipientId(Long v) {
        this.recipientId = v;
    }

    public String getChannel() {
        return channel;
    }

    public void setChannel(String v) {
        this.channel = v;
    }

    public String getEventCode() {
        return eventCode;
    }

    public void setEventCode(String v) {
        this.eventCode = v;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String v) {
        this.title = v;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String v) {
        this.content = v;
    }

    public String getBizType() {
        return bizType;
    }

    public void setBizType(String v) {
        this.bizType = v;
    }

    public Long getBizId() {
        return bizId;
    }

    public void setBizId(Long v) {
        this.bizId = v;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String v) {
        this.category = v;
    }

    public OffsetDateTime getReadAt() {
        return readAt;
    }

    public void setReadAt(OffsetDateTime v) {
        this.readAt = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }
}
