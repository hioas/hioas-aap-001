package com.hioas.aap.iam;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/** 供应商账号（表 {@code aap_provider_account}）。手机号以密文 + hash + mask 三件套存储（R-48）。 */
@Table(value = "aap_provider_account", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class ProviderAccountEntity extends BaseEntity {

    private String phoneCipher;
    private String phoneHash;
    private String phoneMasked;
    private String nickname;
    private String wxOpenid;
    private String wxUnionid;
    private String role;
    private String status;

    @Column("sms_2fa")
    private Boolean sms2fa;

    private Boolean wechatSubscribed;
    private OffsetDateTime lastLoginAt;

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

    public String getNickname() {
        return nickname;
    }

    public void setNickname(String v) {
        this.nickname = v;
    }

    public String getWxOpenid() {
        return wxOpenid;
    }

    public void setWxOpenid(String v) {
        this.wxOpenid = v;
    }

    public String getWxUnionid() {
        return wxUnionid;
    }

    public void setWxUnionid(String v) {
        this.wxUnionid = v;
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

    public Boolean getSms2fa() {
        return sms2fa;
    }

    public void setSms2fa(Boolean v) {
        this.sms2fa = v;
    }

    public Boolean getWechatSubscribed() {
        return wechatSubscribed;
    }

    public void setWechatSubscribed(Boolean v) {
        this.wechatSubscribed = v;
    }

    public OffsetDateTime getLastLoginAt() {
        return lastLoginAt;
    }

    public void setLastLoginAt(OffsetDateTime v) {
        this.lastLoginAt = v;
    }
}
