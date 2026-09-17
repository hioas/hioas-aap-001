package com.hioas.aap.iam.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * 登录/换发令牌响应（契约：docs/backend/json-schema/models/login-result.schema.json）。
 *
 * <p>同时输出 camelCase 与 snake_case 两套 ID 字段：`aap-client` 读 `providerId`（`src/api/auth.ts`），
 * 而项目决策 D-JSON-01 要求字段与数据字典同名（snake_case）——两者都保留，避免任一端踩空。
 */
public class LoginResult {

    private final String token;
    private final String refreshToken;
    private final String role;
    private final String providerId;
    private final String providerCode;
    private final String status;
    private final long expiresIn;

    public LoginResult(String token, String refreshToken, String role, String providerId,
                       String providerCode, String status, long expiresIn) {
        this.token = token;
        this.refreshToken = refreshToken;
        this.role = role;
        this.providerId = providerId;
        this.providerCode = providerCode;
        this.status = status;
        this.expiresIn = expiresIn;
    }

    public String getToken() {
        return token;
    }

    /** 客户端读 refreshToken（`src/api/auth.ts` refresh 入参）。 */
    @JsonProperty("refreshToken")
    public String getRefreshTokenCamel() {
        return refreshToken;
    }

    /** 契约字段名（snake_case，D-JSON-01）。 */
    @JsonProperty("refresh_token")
    public String getRefreshToken() {
        return refreshToken;
    }

    public String getRole() {
        return role;
    }

    /** 客户端读 providerId（camelCase）。 */
    public String getProviderId() {
        return providerId;
    }

    /** 数据字典同名（snake_case）。 */
    @JsonProperty("provider_id")
    public String getProviderIdSnake() {
        return providerId;
    }

    /** 客户端读 providerCode（camelCase）。 */
    public String getProviderCode() {
        return providerCode;
    }

    @JsonProperty("provider_code")
    public String getProviderCodeSnake() {
        return providerCode;
    }

    public String getStatus() {
        return status;
    }

    @JsonProperty("expires_in")
    public long getExpiresIn() {
        return expiresIn;
    }
}
