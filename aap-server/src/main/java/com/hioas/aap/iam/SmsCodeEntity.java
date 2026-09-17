package com.hioas.aap.iam;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 短信验证码（表 {@code aap_sms_code}）。
 *
 * <p>安全口径：**只存 SHA-256(code_hash)，不存明文**；错误次数与锁定写在记录上（R-02）。
 */
@Table(value = "aap_sms_code", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class SmsCodeEntity extends BaseEntity {

    private String phoneHash;
    private String phoneMasked;
    private String scene;
    private String codeHash;
    private OffsetDateTime sentAt;
    private OffsetDateTime expireAt;
    private Integer attemptCount;
    private OffsetDateTime lockedUntil;
    private OffsetDateTime usedAt;
    private String clientIp;

    public String getPhoneHash() {
        return phoneHash;
    }

    public void setPhoneHash(String v) {
        this.phoneHash = v;
    }

    public String getPhoneMasked() {
        return phoneMasked;
    }

    public void setPhoneMasked(String v) {
        this.phoneMasked = v;
    }

    public String getScene() {
        return scene;
    }

    public void setScene(String v) {
        this.scene = v;
    }

    public String getCodeHash() {
        return codeHash;
    }

    public void setCodeHash(String v) {
        this.codeHash = v;
    }

    public OffsetDateTime getSentAt() {
        return sentAt;
    }

    public void setSentAt(OffsetDateTime v) {
        this.sentAt = v;
    }

    public OffsetDateTime getExpireAt() {
        return expireAt;
    }

    public void setExpireAt(OffsetDateTime v) {
        this.expireAt = v;
    }

    public Integer getAttemptCount() {
        return attemptCount;
    }

    public void setAttemptCount(Integer v) {
        this.attemptCount = v;
    }

    public OffsetDateTime getLockedUntil() {
        return lockedUntil;
    }

    public void setLockedUntil(OffsetDateTime v) {
        this.lockedUntil = v;
    }

    public OffsetDateTime getUsedAt() {
        return usedAt;
    }

    public void setUsedAt(OffsetDateTime v) {
        this.usedAt = v;
    }

    public String getClientIp() {
        return clientIp;
    }

    public void setClientIp(String v) {
        this.clientIp = v;
    }
}
