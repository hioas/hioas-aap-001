package com.hioas.aap.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T05 · 出站地址防护（SSRF，R-07 / AC-29）单元测试。
 *
 * <p>为什么单独做单元测试：测试 profile 为了跑本地上游桩把 {@code allow-loopback} 打开了
 * （HTTP 级用例覆盖不到环回地址被拒）。AC-29 的「环回地址必须被拒」只能在**生产配置**下断言——
 * 这里用 {@code new OutboundUrlGuard(false)} 精确覆盖，两种配置都测。
 */
class OutboundUrlGuardTest {

    private final OutboundUrlGuard production = new OutboundUrlGuard(false);
    private final OutboundUrlGuard localDev = new OutboundUrlGuard(true);

    @Test
    @DisplayName("AC-29 生产配置：环回（127.0.0.1 / ::1 / localhost）全部拒绝 E-1201")
    void loopbackRejectedInProduction() {
        for (String url : new String[]{"http://127.0.0.1/v1", "http://[::1]/v1", "http://localhost:8080/v1"}) {
            assertThatThrownBy(() -> production.verify(url))
                    .as("地址 %s 必须被拒", url)
                    .isInstanceOf(ApiException.class)
                    .extracting(e -> ((ApiException) e).errorCode())
                    .isEqualTo(ErrorCode.E_1201);
        }
    }

    @Test
    @DisplayName("AC-29 生产配置：云元数据 / 私网 / CGNAT / 链路本地 全部拒绝")
    void privateRangesRejectedInProduction() {
        for (String url : new String[]{
                "http://169.254.169.254/latest/meta-data", "http://10.0.0.1/v1", "http://192.168.1.10/v1",
                "http://172.16.5.5/v1", "http://172.31.255.254/v1", "http://100.64.0.1/v1", "http://0.0.0.0/v1",
                "http://[fc00::1]/v1", "http://[fd12:3456::1]/v1"}) {
            assertThatThrownBy(() -> production.verify(url)).as("地址 %s 必须被拒", url).isInstanceOf(ApiException.class);
        }
    }

    @Test
    @DisplayName("生产配置也拒绝：非 http/https 协议、缺主机名、非法 URL")
    void protocolAndShapeChecks() {
        for (String url : new String[]{"ftp://api.example.com/v1", "file:///etc/passwd", "gopher://x/1"}) {
            assertThatThrownBy(() -> production.verify(url)).as("协议 %s 必须被拒", url).isInstanceOf(ApiException.class);
        }
        assertThatThrownBy(() -> production.verify("http:///v1")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> production.verify("  ")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> production.verify("http://[::1")).isInstanceOf(ApiException.class);
    }

    @Test
    @DisplayName("本地联调开关：仅放行环回，私网/元数据仍然拒绝（AC-29 不被开关绕过）")
    void loopbackSwitchDoesNotOpenPrivateRanges() {
        assertThat(localDev.verify("http://127.0.0.1:18080/v1")).isEqualTo("127.0.0.1");
        assertThat(localDev.verify("http://[::1]/v1")).isEqualTo("[::1]");

        assertThatThrownBy(() -> localDev.verify("http://169.254.169.254/")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> localDev.verify("http://10.0.0.1/")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> localDev.verify("http://192.168.0.1/")).isInstanceOf(ApiException.class);
        assertThatThrownBy(() -> localDev.verify("http://100.64.1.1/")).isInstanceOf(ApiException.class);
    }

    @Test
    @DisplayName("公网域名放行；无法解析的域名放行（交给真实连接失败报 E-1101，不误判为攻击）")
    void publicHostsAllowed() {
        assertThat(production.verify("https://api.openai.com/v1")).isEqualTo("api.openai.com");
        assertThat(production.verify("https://not-exist-domain-for-aap-test.invalid/v1"))
                .isEqualTo("not-exist-domain-for-aap-test.invalid");
    }
}
