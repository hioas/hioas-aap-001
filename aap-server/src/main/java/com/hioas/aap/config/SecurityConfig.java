package com.hioas.aap.config;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.iam.JwtAuthenticationFilter;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import tools.jackson.databind.ObjectMapper;

/**
 * 安全配置：无状态 JWT（无 session / CSRF / 表单登录），401 与 403 也走统一包体。
 *
 * <p>授权口径（18-API §通用约定）：
 * <ul>
 *   <li>匿名可访问：健康检查、注册登录四条（sms/send、sms/login、wechat/login、refresh）</li>
 *   <li>其余 {@code /api/v1/**} 一律需认证；角色细粒度用 {@code @PreAuthorize}（方法级）</li>
 * </ul>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private static final String[] PUBLIC_PATHS = {
            "/actuator/health", "/actuator/health/**", "/actuator/info", "/actuator/metrics/**",
            "/api/v1/auth/sms/send", "/api/v1/auth/sms/login", "/api/v1/auth/wechat/login",
            "/api/v1/auth/refresh",
    };

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http, ObjectMapper objectMapper,
                                                   JwtAuthenticationFilter jwtFilter) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(PUBLIC_PATHS).permitAll()
                        .anyRequest().authenticated())
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((request, response, authException) ->
                                write(response, objectMapper, ErrorCode.E_1902, "未认证或登录已过期"))
                        .accessDeniedHandler((request, response, deniedException) ->
                                write(response, objectMapper, ErrorCode.E_1901, "权限不足")))
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter(com.hioas.aap.iam.JwtService jwtService,
                                                           com.hioas.aap.iam.AuthTokenMapper authTokenMapper,
                                                           com.hioas.aap.common.CryptoService cryptoService) {
        return new JwtAuthenticationFilter(jwtService, authTokenMapper, cryptoService);
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
