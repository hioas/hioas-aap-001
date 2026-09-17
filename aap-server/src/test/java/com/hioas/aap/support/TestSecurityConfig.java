package com.hioas.aap.support;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

/**
 * 测试专用安全链：放行 {@code /api/v1/__test/**}（契约探针控制器），其余仍走生产链。
 *
 * <p>放在 test 源码里且**不加** {@code @TestConfiguration}：{@code @SpringBootTest} 扫的是
 * {@code com.hioas.aap} 包（含 target/test-classes），这样所有测试共享同一条测试链，
 * 不必每个测试类都 import。
 */
@Configuration
public class TestSecurityConfig {

    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE)
    public SecurityFilterChain testProbeChain(HttpSecurity http) throws Exception {
        http.securityMatcher("/api/v1/__test/**")
                .csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }
}
