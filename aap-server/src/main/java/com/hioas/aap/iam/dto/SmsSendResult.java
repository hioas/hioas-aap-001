package com.hioas.aap.iam.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * 验证码下发结果（契约：docs/backend/json-schema/models/sms-send-result.schema.json）。
 *
 * @param ttl      有效期秒数（客户端用于倒计时）
 * @param expireAt RFC3339 UTC
 * @param devCode  仅 `app.sms.expose-code=true`（测试环境）时返回，生产为 null
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record SmsSendResult(int ttl, @JsonProperty("expire_at") String expireAt, @JsonProperty("dev_code") String devCode) {
}
