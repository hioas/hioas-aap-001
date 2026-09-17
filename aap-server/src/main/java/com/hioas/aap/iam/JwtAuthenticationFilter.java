package com.hioas.aap.iam;

import com.hioas.aap.common.AuditContext;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.mybatisflex.core.query.QueryWrapper;
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * JWT 认证过滤器。
 *
 * <p>职责：解析 Bearer 令牌 → 校验签名/有效期 → 校验 jti 未被撤销（登出即失效）
 * → 写入 SecurityContext（角色）与 {@link AuditContext}（审计操作者）。
 *
 * <p>失败一律**不写响应**，交给 {@code SecurityConfig} 的 authenticationEntryPoint 输出统一包体
 * （E-1902 + traceId），保证 401 也是标准契约。
 *
 * <p>注意：本类**不加 {@code @Component}**——由 {@code SecurityConfig} 以 Bean 形式放进安全链；
 * 若同时被 Spring Boot 当作 Servlet Filter 自动注册，会对每个请求执行两次。
 */
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    public static final String JTI_ATTRIBUTE = "aap.jti";

    private static final Logger log = LoggerFactory.getLogger(JwtAuthenticationFilter.class);

    private final JwtService jwtService;
    private final AuthTokenMapper authTokenMapper;
    private final CryptoService crypto;

    public JwtAuthenticationFilter(JwtService jwtService, AuthTokenMapper authTokenMapper, CryptoService crypto) {
        this.jwtService = jwtService;
        this.authTokenMapper = authTokenMapper;
        this.crypto = crypto;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        try {
            if (header != null && header.startsWith("Bearer ")) {
                String token = header.substring(7).trim();
                Claims claims = jwtService.parse(token);
                String jti = claims.getId();
                if (isRevoked(jti)) {
                    throw new com.hioas.aap.common.ApiException(ErrorCode.E_1902, "登录状态已失效，请重新登录");
                }
                Long accountId = Long.valueOf(claims.getSubject());
                Long providerId = claims.get("providerId") == null ? null
                        : Long.valueOf(String.valueOf(claims.get("providerId")));
                String role = String.valueOf(claims.get("role"));
                String subjectType = String.valueOf(claims.get("subjectType"));

                AuthPrincipal principal = new AuthPrincipal(accountId, providerId, role, subjectType, null);
                var authentication = new UsernamePasswordAuthenticationToken(principal, null, principal.authorities());
                SecurityContextHolder.getContext().setAuthentication(authentication);
                request.setAttribute(JTI_ATTRIBUTE, jti);
                AuditContext.set(new AuditContext.Actor(accountId, subjectType, role, clientIp(request)));
            }
        } catch (com.hioas.aap.common.ApiException e) {
            SecurityContextHolder.clearContext();
            log.debug("令牌校验失败: {}", e.getMessage());
        }
        try {
            chain.doFilter(request, response);
        } finally {
            SecurityContextHolder.clearContext();
            AuditContext.clear();
        }
    }

    private boolean isRevoked(String jti) {
        if (jti == null) {
            return true;
        }
        long active = authTokenMapper.selectCountByQuery(QueryWrapper.create()
                .where("jti = ?", jti)
                .and("revoked_at is null"));
        return active == 0;
    }

    private static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    /** 供其它组件复用：从当前 SecurityContext 取认证主体。 */
    public static AuthPrincipal currentPrincipal() {
        var authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof AuthPrincipal principal) {
            return principal;
        }
        return null;
    }
}
