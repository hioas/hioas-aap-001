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

    /**
     * {@code exposeCode} 仅测试环境开启：把验证码放进响应体，便于端到端验收（生产必须 false）。
     *
     * <p>{@code fixedCode} 非空时所有手机号下发同一个固定验证码（本地联调用，生产必须留空）；
     * {@code lockMinutes <= 0} 表示不启用「连续错码锁定」（本地联调用，生产必须 > 0）。
     */
    public record Sms(int ttlSeconds, int resendIntervalSeconds, int maxAttempts, int lockMinutes,
                      boolean exposeCode, String fixedCode) {
    }

    public record Detection(int dailyQuota, int passScore, int vetoScore) {
    }

    public record Logging(String dir) {
    }
}
