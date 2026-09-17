package com.hioas.aap.common;

import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.Locale;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 出站地址防护（SSRF，R-07 / AC-29）。
 *
 * <p>规则：
 * <ul>
 *   <li>仅允许 {@code http} / {@code https}（其余协议一律 {@code E-1201}）</li>
 *   <li>拒绝环回、RFC1918 私网、RFC6598（100.64/10）、链路本地 169.254/16（含云元数据 169.254.169.254）、
 *       组播、未指定地址、IPv6 唯一本地 fc00::/7 与 IPv4-mapped 私网</li>
 *   <li>域名无法解析时**放行**（此刻判不出私网，真正的连接会失败并报 {@code E-1101}）——
 *       避免把「DNS 抖动」误判成攻击而拒绝正常提交</li>
 * </ul>
 *
 * <p>{@code app.credential.allow-loopback}（默认 false）仅用于本地端到端联调与测试：
 * 放行 127.0.0.1/::1，**不放行**私网、链路本地与元数据地址（AC-29 仍可验证）。
 */
@Component
public class OutboundUrlGuard {

    private static final Set<String> ALLOWED_SCHEMES = Set.of("http", "https");

    private final boolean allowLoopback;

    public OutboundUrlGuard(@Value("${app.credential.allow-loopback:false}") boolean allowLoopback) {
        this.allowLoopback = allowLoopback;
    }

    /** 校验地址；不合法直接抛 {@code E-1201}。返回规范化后的 host（便于日志脱敏展示）。 */
    public String verify(String url) {
        if (url == null || url.isBlank()) {
            throw new ApiException(ErrorCode.E_1201, "缺少 base_url");
        }
        URI uri;
        try {
            uri = URI.create(url);
        } catch (IllegalArgumentException e) {
            throw new ApiException(ErrorCode.E_1201, "base_url 不是合法地址");
        }
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        if (!ALLOWED_SCHEMES.contains(scheme)) {
            throw new ApiException(ErrorCode.E_1201, "仅允许 http/https 协议");
        }
        String host = uri.getHost();
        if (host == null || host.isBlank()) {
            throw new ApiException(ErrorCode.E_1201, "base_url 缺少主机名");
        }
        // IPv6 字面量在 URI.getHost() 里带方括号（[::1]），解析前必须去掉，否则 DNS 解析失败被误放行
        String resolvable = host.startsWith("[") && host.endsWith("]")
                ? host.substring(1, host.length() - 1) : host;

        InetAddress[] addresses;
        try {
            addresses = InetAddress.getAllByName(resolvable);
        } catch (UnknownHostException e) {
            // 无法解析：交给真实连接去失败（E-1101），不在这里误判
            return host;
        }
        for (InetAddress address : addresses) {
            if (isBlocked(address)) {
                throw new ApiException(ErrorCode.E_1201,
                        "目标地址属于内网/保留网段，已拒绝（SSRF 防护）");
            }
        }
        return host;
    }

    private boolean isBlocked(InetAddress address) {
        if (address.isLoopbackAddress()) {
            return !allowLoopback;
        }
        return address.isAnyLocalAddress()
                || address.isLinkLocalAddress()
                || address.isSiteLocalAddress()
                || address.isMulticastAddress()
                || isCarrierGradeNat(address)
                || isIpv6UniqueLocal(address);
    }

    /** RFC6598 100.64.0.0/10（运营商级 NAT，云内网常用）。 */
    private static boolean isCarrierGradeNat(InetAddress address) {
        byte[] bytes = address.getAddress();
        return bytes.length == 4 && (bytes[0] & 0xFF) == 100 && (bytes[1] & 0xC0) == 64;
    }

    /** IPv6 唯一本地地址 fc00::/7；IPv4-mapped 私网（::ffff:10.0.0.1）交由上面按 4 字节判断。 */
    private static boolean isIpv6UniqueLocal(InetAddress address) {
        byte[] bytes = address.getAddress();
        if (bytes.length != 16) {
            return false;
        }
        boolean mapped = true;
        for (int i = 0; i < 10; i++) {
            if (bytes[i] != 0) {
                mapped = false;
                break;
            }
        }
        if (mapped && bytes[10] == (byte) 0xFF && bytes[11] == (byte) 0xFF) {
            // IPv4-mapped：按 IPv4 规则判定第二段
            byte[] v4 = {bytes[12], bytes[13], bytes[14], bytes[15]};
            return isPrivateV4(v4);
        }
        return (bytes[0] & 0xFE) == 0xFC;
    }

    private static boolean isPrivateV4(byte[] b) {
        int a = b[0] & 0xFF;
        int c = b[1] & 0xFF;
        return a == 10
                || (a == 172 && c >= 16 && c <= 31)
                || (a == 192 && c == 168)
                || (a == 169 && c == 254)
                || (a == 100 && (c & 0xC0) == 64)
                || a == 127;
    }
}
