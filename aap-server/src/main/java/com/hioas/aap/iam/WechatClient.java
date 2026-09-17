package com.hioas.aap.iam;

import com.hioas.aap.common.CryptoService;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/**
 * 微信登录适配器。
 *
 * <p>生产实现需调用微信 {@code jscode2session} 换取 openid（需要 AppID/AppSecret，属外部凭据，
 * 目前不接入）。默认实现为**确定性桩**：同一 code 恒得同一 openid，
 * 便于端到端验收（AC-05 绑定互认），且不引入伪造的外部调用。
 */
public interface WechatClient {

    /** 用登录 code 换 openid（同一 code 幂等）。 */
    String exchangeOpenid(String code);

    @Component
    @Profile("!prod")
    class StubWechatClient implements WechatClient {

        private final CryptoService crypto;

        StubWechatClient(CryptoService crypto) {
            this.crypto = crypto;
        }

        @Override
        public String exchangeOpenid(String code) {
            // 确定性映射：code → wx_{sha256 前 16 位}，同一 code 恒等
            return "wx_" + crypto.sha256Hex(code).substring(0, 16);
        }
    }
}
