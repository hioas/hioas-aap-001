package com.hioas.aap.iam;

import java.util.List;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

/**
 * 认证主体（放进 SecurityContext 的 principal）。
 *
 * <p>{@code subjectType} 区分供应商端（PROVIDER）与管理端（ADMIN）；
 * 角色映射为 Spring Security 的 {@code ROLE_<role>}，供 {@code @PreAuthorize} 使用。
 */
public record AuthPrincipal(Long accountId, Long providerId, String role, String subjectType, String name) {

    public List<GrantedAuthority> authorities() {
        return List.of(new SimpleGrantedAuthority("ROLE_" + role));
    }

    public boolean isAdmin() {
        return "ADMIN".equals(subjectType);
    }

    public boolean isProvider() {
        return "PROVIDER".equals(subjectType);
    }
}
