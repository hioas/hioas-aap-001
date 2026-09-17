package com.hioas.aap.iam;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 令牌记录（表 {@code aap_auth_token}）：承载 access token 的 jti（用于登出即失效）
 * 与 refresh token 的哈希（用于轮换，只存 SHA-256）。
 */
@Table(value = "aap_auth_token", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class AuthTokenEntity extends BaseEntity {

    private Long accountId;
    private String subjectType;
    private String jti;
    private String refreshTokenHash;
    private OffsetDateTime expireAt;
    private OffsetDateTime revokedAt;
    private String userAgent;
    private String clientIp;

    public Long getAccountId() {
        return accountId;
    }

    public void setAccountId(Long v) {
        this.accountId = v;
    }

    public String getSubjectType() {
        return subjectType;
    }

    public void setSubjectType(String v) {
        this.subjectType = v;
    }

    public String getJti() {
        return jti;
    }

    public void setJti(String v) {
        this.jti = v;
    }

    public String getRefreshTokenHash() {
        return refreshTokenHash;
    }

    public void setRefreshTokenHash(String v) {
        this.refreshTokenHash = v;
    }

    public OffsetDateTime getExpireAt() {
        return expireAt;
    }

    public void setExpireAt(OffsetDateTime v) {
        this.expireAt = v;
    }

    public OffsetDateTime getRevokedAt() {
        return revokedAt;
    }

    public void setRevokedAt(OffsetDateTime v) {
        this.revokedAt = v;
    }

    public String getUserAgent() {
        return userAgent;
    }

    public void setUserAgent(String v) {
        this.userAgent = v;
    }

    public String getClientIp() {
        return clientIp;
    }

    public void setClientIp(String v) {
        this.clientIp = v;
    }
}
