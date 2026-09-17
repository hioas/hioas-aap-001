package com.hioas.aap.config;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ErrorCode;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import tools.jackson.databind.ObjectMapper;

/**
 * 安全配置：无状态 JWT（无 session、无 CSRF、无表单登录），401/403 也走统一包体。
 *
 * <p>注意：认证过滤器与按角色授权在 T03 落地；本任务先保证
 * 「安全链不干扰统一契约」——未认证访问由 {@code authenticationEntryPoint} 输出 E-1902 包体，
 * 而不是 Spring 默认的 WWW-Authenticate 裸响应。
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private static final String[] PUBLIC_PATHS = {
            "/actuator/health", "/actuator/health/**", "/actuator/info", "/actuator/metrics/**",
    };

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http, ObjectMapper objectMapper) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(PUBLIC_PATHS).permitAll()
                        // 认证与授权在 T03 收紧为 .anyRequest().authenticated() + 角色规则
                        .anyRequest().permitAll())
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((request, response, authException) ->
                                write(response, objectMapper, ErrorCode.E_1902, "未认证或登录已过期"))
                        .accessDeniedHandler((request, response, deniedException) ->
                                write(response, objectMapper, ErrorCode.E_1901, "权限不足")));
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    private static void write(HttpServletResponse response, ObjectMapper mapper, ErrorCode code, String message)
            throws IOException {
        response.setStatus(code.httpStatus());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        String traceId = org.slf4j.MDC.get(ApiEnvelope.TRACE_ID);
        if (traceId != null) {
            response.setHeader("X-Trace-Id", traceId);
        }
        mapper.writeValue(response.getOutputStream(), ApiEnvelope.fail(code, message));
    }
}
