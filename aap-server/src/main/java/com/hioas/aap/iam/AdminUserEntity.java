package com.hioas.aap.iam;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 管理端账号（表 {@code aap_admin_user}）。手机号三件套支撑「明文读取二次验证」（R-05/AC-30）。 */
@Table(value = "aap_admin_user", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class AdminUserEntity extends BaseEntity {

    private String username;
    private String passwordHash;
    private String displayName;
    private String role;
    private String status;
    private String phoneCipher;
    private String phoneHash;
    private String phoneMasked;
    private OffsetDateTime lastLoginAt;

    public String getUsername() {
        return username;
    }

    public void setUsername(String v) {
        this.username = v;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public void setPasswordHash(String v) {
        this.passwordHash = v;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String v) {
        this.displayName = v;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String v) {
        this.role = v;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String v) {
        this.status = v;
    }

    public String getPhoneCipher() {
        return phoneCipher;
    }

    public void setPhoneCipher(String v) {
        this.phoneCipher = v;
    }

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

    public OffsetDateTime getLastLoginAt() {
        return lastLoginAt;
    }

    public void setLastLoginAt(OffsetDateTime v) {
        this.lastLoginAt = v;
    }
}
