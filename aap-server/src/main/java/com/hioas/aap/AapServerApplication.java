package com.hioas.aap;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.security.autoconfigure.UserDetailsServiceAutoConfiguration;

/**
 * AAP 服务端启动类（供应商端 + 管理端 API）。
 *
 * <p>技术栈：Java 25 · Spring Boot 4.1.1 · PostgreSQL · MyBatis-Flex。
 *
 * <p>排除 {@link UserDetailsServiceAutoConfiguration}：本项目用自研 JWT 认证（T03），
 * 不需要 Spring Security 的内存用户与随机密码（否则启动日志会出现
 * "Using generated security password"，干扰验收与日志判读）。
 */
@SpringBootApplication(exclude = UserDetailsServiceAutoConfiguration.class)
public class AapServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(AapServerApplication.class, args);
    }
}
