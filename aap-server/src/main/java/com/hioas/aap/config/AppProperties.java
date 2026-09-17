package com.hioas.aap.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.NestedConfigurationProperty;

/**
 * 应用配置（前缀 {@code app.*}，见 application.yml）。
 *
 * <p>密钥类（jwt.secret / credential.aes-key）一律来自 `E:\env\aap-server.env`；
 * 缺失时应用启动即失败（{@link SecretStartupCheck}），不静默用默认值。
 */
@ConfigurationProperties(prefix = "app")
public record AppProperties(
        @NestedConfigurationProperty Jwt jwt,
        @NestedConfigurationProperty Credential credential,
        @NestedConfigurationProperty Sms sms,
        @NestedConfigurationProperty Detection detection,
        @NestedConfigurationProperty Logging logging) {

    public record Jwt(String secret, int accessTtlMinutes, int refreshTtlDays) {
    }

    public record Credential(String aesKey) {
    }

    /** {@code exposeCode} 仅测试环境开启：把验证码放进响应体，便于端到端验收（生产必须 false）。 */
    public record Sms(int ttlSeconds, int resendIntervalSeconds, int maxAttempts, int lockMinutes, boolean exposeCode) {
    }

    public record Detection(int dailyQuota, int passScore, int vetoScore) {
    }

    public record Logging(String dir) {
    }
}
