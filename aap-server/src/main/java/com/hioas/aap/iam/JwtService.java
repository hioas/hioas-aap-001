package com.hioas.aap.iam;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.config.AppProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Date;
import java.util.UUID;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Component;

/**
 * JWT 签发与校验（HS256）。
 *
 * <p>claims：{@code sub}(账号 id) {@code role} {@code subjectType}(PROVIDER/ADMIN) {@code providerId} {@code exp} {@code jti}。
 * jti 用于「登出即失效」——令牌本身无状态，但每次请求会校验 {@code aap_auth_token} 中该 jti 未被撤销。
 */
@Component
public class JwtService {

    private final SecretKey key;
    private final Duration accessTtl;

    public JwtService(AppProperties properties) {
        String secret = properties.jwt().secret();
        if (secret == null || secret.length() < 32) {
            throw new IllegalStateException(
                    "app.jwt.secret 缺失或过短：请在 E:\\env\\aap-server.env 配置 AAP_JWT_SECRET（≥32 字符）");
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.accessTtl = Duration.ofMinutes(properties.jwt().accessTtlMinutes());
    }

    /** 签发访问令牌。 */
    public IssuedAccessToken issueAccessToken(Long accountId, String role, String subjectType, Long providerId) {
        String jti = UUID.randomUUID().toString().replace("-", "");
        OffsetDateTime expireAt = OffsetDateTime.now(ZoneOffset.UTC).plus(accessTtl);
        String token = Jwts.builder()
                .subject(String.valueOf(accountId))
                .claim("role", role)
                .claim("subjectType", subjectType)
                .claim("providerId", providerId)
                .id(jti)
                .issuedAt(Date.from(OffsetDateTime.now(ZoneOffset.UTC).toInstant()))
                .expiration(Date.from(expireAt.toInstant()))
                .signWith(key, Jwts.SIG.HS256)
                .compact();
        return new IssuedAccessToken(token, jti, expireAt);
    }

    /** 解析并校验签名与有效期；失败一律 {@code E-1902}（不区分原因，避免给攻击者信息）。 */
    public Claims parse(String token) {
        try {
            return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
        } catch (JwtException | IllegalArgumentException e) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
    }

    public Duration accessTtl() {
        return accessTtl;
    }

    /** 访问令牌签发结果。 */
    public record IssuedAccessToken(String token, String jti, OffsetDateTime expireAt) {
    }
}
