package com.hioas.aap.common;

import java.util.Optional;

/**
 * 审计上下文：当前操作者（写库时填充 {@code created_by / updated_by}）。
 *
 * <p>为什么用 ThreadLocal：MyBatis-Flex 的 Insert/Update 监听器不是 Spring 管理的 Bean，
 * 拿不到 SecurityContext；链路入口（认证过滤器）与测试在同一线程内写入，插件的监听器读取。
 * 一次性请求内的可见性由「过滤器 finally 清理」保证，避免线程池串味。
 */
public final class AuditContext {

    /** 操作者：provider/admin 账号或 SYSTEM。 */
    public record Actor(Long id, String type, String name, String ip) {

        public static Actor system() {
            return new Actor(null, "SYSTEM", "system", null);
        }
    }

    private static final ThreadLocal<Actor> CURRENT = new ThreadLocal<>();

    private AuditContext() {
    }

    public static void set(Actor actor) {
        CURRENT.set(actor);
    }

    public static Optional<Actor> current() {
        return Optional.ofNullable(CURRENT.get());
    }

    public static Optional<Long> currentActorId() {
        return current().map(Actor::id);
    }

    public static String currentActorType() {
        return current().map(Actor::type).orElse("SYSTEM");
    }

    public static void clear() {
        CURRENT.remove();
    }
}
