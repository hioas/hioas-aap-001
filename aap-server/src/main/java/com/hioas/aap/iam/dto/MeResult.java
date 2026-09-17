package com.hioas.aap.iam.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * 当前登录者（契约：docs/backend/json-schema/models/me-result.schema.json）。
 *
 * <p>除认证所需字段外，还承载「我的设置」页（序号 23，`src/utils/settings-model.ts`）消费的
 * `wechat_bound / sms_2fa / wechat_subscribed`——18-API 未定义这些字段，属约定字段（D-PRD-01）。
 */
public class MeResult {

    private final String phoneMasked;
    private final String role;
    private final String providerId;
    private final String providerCode;
    private final String status;
    private final String nickname;
    private final boolean wechatBound;
    private final boolean sms2fa;
    private final boolean wechatSubscribed;

    public MeResult(String phoneMasked, String role, String providerId, String providerCode, String status,
                    String nickname, boolean wechatBound, boolean sms2fa, boolean wechatSubscribed) {
        this.phoneMasked = phoneMasked;
        this.role = role;
        this.providerId = providerId;
        this.providerCode = providerCode;
        this.status = status;
        this.nickname = nickname;
        this.wechatBound = wechatBound;
        this.sms2fa = sms2fa;
        this.wechatSubscribed = wechatSubscribed;
    }

    /** 契约字段（脱敏手机号；后端**永不回明文**）。 */
    @JsonProperty("phone_masked")
    public String getPhoneMasked() {
        return phoneMasked;
    }

    /** 客户端 settings-model 读取的多个候选键之一。 */
    @JsonProperty("phone")
    public String getPhone() {
        return phoneMasked;
    }

    @JsonProperty("mobile")
    public String getMobile() {
        return phoneMasked;
    }

    public String getRole() {
        return role;
    }

    public String getProviderId() {
        return providerId;
    }

    @JsonProperty("provider_id")
    public String getProviderIdSnake() {
        return providerId;
    }

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

    public String getNickname() {
        return nickname;
    }

    @JsonProperty("wechat_bound")
    public boolean isWechatBound() {
        return wechatBound;
    }

    @JsonProperty("sms_2fa")
    public boolean isSms2fa() {
        return sms2fa;
    }

    @JsonProperty("login_security")
    public String getLoginSecurity() {
        return sms2fa ? "已开启短信二次校验" : "未开启短信二次校验";
    }

    @JsonProperty("wechat_subscribed")
    public boolean isWechatSubscribed() {
        return wechatSubscribed;
    }

    @JsonProperty("subscribed")
    public boolean isSubscribed() {
        return wechatSubscribed;
    }
}
