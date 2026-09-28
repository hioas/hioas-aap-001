package com.hioas.aap.supply;

import java.util.Locale;

/**
 * 供给单元状态机（T-M4-04）。
 *
 * <p>规格：`specs/001-intake-automation/spec.md` §3.2/§4 与 `data-model.md` §3；
 * 非法流转统一拒绝 `E-1601`（宪法 C-05：状态流转必须经领域方法）。
 *
 * <p>流转表（唯一权威定义）：
 * <pre>
 *   PENDING     → CONFIGURING | OFFLINE
 *   CONFIGURING → ONLINE | PENDING（配置失败回退）| OFFLINE
 *   ONLINE      → DEGRADED | SUSPENDED | CONFIGURING（重配置）| OFFLINE
 *   DEGRADED    → ONLINE（恢复）| SUSPENDED | CONFIGURING | OFFLINE
 *   SUSPENDED   → ONLINE | CONFIGURING | OFFLINE
 *   OFFLINE     → CONFIGURING（重新上线，不允许直跳 ONLINE）
 * </pre>
 *
 * <p>为什么 OFFLINE 不能直跳 ONLINE：渠道已被禁用/删除，直接标记在线会造成
 * 「库里在线、网关无渠道」的静默不一致 —— 必须经 CONFIGURING 重新建渠道与回读。
 */
public enum SupplyUnitStatus {

    /** 已登记，尚未开始配置渠道 */
    PENDING,
    /** 正在配置（建渠道 / 写价 / 回读中） */
    CONFIGURING,
    /** 已上线（渠道存在、回读一致、已启用） */
    ONLINE,
    /** 已降级（质量或价格漂移触发降权，仍在架） */
    DEGRADED,
    /** 被暂停（人工或治理动作） */
    SUSPENDED,
    /** 已下线（渠道禁用/删除；可重新上线） */
    OFFLINE;

    /**
     * 判断本状态能否流转到目标状态。
     *
     * <p>自流转一律为 false —— 幂等由调用方按值判断（`同值即跳过，不打上游`），
     * 不依赖状态机表达。
     *
     * @return 允许返回 true；否则 false（调用方据此抛 `E-1601`）
     */
    public boolean canTransitionTo(SupplyUnitStatus target) {
        if (target == null || target == this) {
            return false;
        }
        return switch (this) {
            case PENDING -> target == CONFIGURING || target == OFFLINE;
            case CONFIGURING -> target == ONLINE || target == PENDING || target == OFFLINE;
            case ONLINE -> target == DEGRADED || target == SUSPENDED || target == CONFIGURING || target == OFFLINE;
            case DEGRADED -> target == ONLINE || target == SUSPENDED || target == CONFIGURING || target == OFFLINE;
            case SUSPENDED -> target == ONLINE || target == CONFIGURING || target == OFFLINE;
            case OFFLINE -> target == CONFIGURING;
        };
    }

    /**
     * 解析状态字符串（大小写与首尾空白容错）。
     *
     * @throws IllegalArgumentException 未知或空值（不猜测、不回落默认值 —— 静默回落会把
     *         脏数据变成「合法状态」，是最难排查的一类线上问题）
     */
    public static SupplyUnitStatus of(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new IllegalArgumentException("供给单元状态为空");
        }
        try {
            return SupplyUnitStatus.valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("未知供给单元状态：" + raw);
        }
    }

    /** 是否为在架状态（ONLINE / DEGRADED）—— 决定是否参与调度与结算。 */
    public boolean isLive() {
        return this == ONLINE || this == DEGRADED;
    }
}
