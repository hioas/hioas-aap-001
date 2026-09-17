package com.hioas.aap.config;

import com.hioas.aap.config.AppProperties;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * 启动自检：密钥缺失时**立刻失败**，不进入"能启动但行为不可信"的状态。
 *
 * <p>依据 SOUL：变量缺失时停止依赖该变量的操作，并明确指出需要补齐的文件路径与变量名。
 */
@Component
public class SecretStartupCheck {

    private final AppProperties properties;

    public SecretStartupCheck(AppProperties properties) {
        this.properties = properties;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void verify() {
        check("AAP_JWT_SECRET", properties.jwt() == null ? null : properties.jwt().secret(), 32);
        check("AAP_CREDENTIAL_AES_KEY", properties.credential() == null ? null : properties.credential().aesKey(), 8);
    }

    private void check(String variable, String value, int minLength) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(
                    "缺少环境变量 " + variable + "：请在 E:\\env\\aap-server.env 中配置后用 "
                            + "`tools/with-env.sh aap-server <命令>` 启动（模板见 aap-server/.env.example）");
        }
        if (value.length() < minLength) {
            throw new IllegalStateException(
                    "环境变量 " + variable + " 长度不足（至少 " + minLength + " 字符），请在 E:\\env\\aap-server.env 重新生成");
        }
    }
}
