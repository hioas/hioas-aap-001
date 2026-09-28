package com.hioas.aap.supply;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T-M4-04 · 供给单元状态机单测（红基线 → 实现 → 绿）。
 *
 * <p>契约真源：`specs/001-intake-automation/spec.md` §3.2/§4；宪法 C-05（非法流转拒绝 `E-1601`）。
 *
 * <p>为什么状态机要单独测：供给单元的状态决定「渠道能不能写、价格能不能算、供应商看到什么」。
 * 若允许任意跳变（例如 OFFLINE 直接跳到 ONLINE 而不重新配置渠道），
 * 就会出现「库里说在线、网关里没渠道」的静默不一致。
 */
class SupplyUnitStatusTest {

    @Test
    @DisplayName("正常路径：PENDING → CONFIGURING → ONLINE")
    void happyPath() {
        assertThat(SupplyUnitStatus.PENDING.canTransitionTo(SupplyUnitStatus.CONFIGURING)).isTrue();
        assertThat(SupplyUnitStatus.CONFIGURING.canTransitionTo(SupplyUnitStatus.ONLINE)).isTrue();
    }

    @Test
    @DisplayName("配置失败可回退：CONFIGURING → PENDING")
    void configuringCanFallBack() {
        assertThat(SupplyUnitStatus.CONFIGURING.canTransitionTo(SupplyUnitStatus.PENDING)).isTrue();
    }

    @Test
    @DisplayName("在架可降级并可恢复：ONLINE ⇄ DEGRADED")
    void degradeAndRecover() {
        assertThat(SupplyUnitStatus.ONLINE.canTransitionTo(SupplyUnitStatus.DEGRADED)).isTrue();
        assertThat(SupplyUnitStatus.DEGRADED.canTransitionTo(SupplyUnitStatus.ONLINE)).isTrue();
    }

    @Test
    @DisplayName("重配置：ONLINE/DEGRADED/SUSPENDED 均可回到 CONFIGURING")
    void canReconfigureFromLiveStates() {
        assertThat(SupplyUnitStatus.ONLINE.canTransitionTo(SupplyUnitStatus.CONFIGURING)).isTrue();
        assertThat(SupplyUnitStatus.DEGRADED.canTransitionTo(SupplyUnitStatus.CONFIGURING)).isTrue();
        assertThat(SupplyUnitStatus.SUSPENDED.canTransitionTo(SupplyUnitStatus.CONFIGURING)).isTrue();
    }

    @Test
    @DisplayName("下线只能经 CONFIGURING 重新上线（不允许 OFFLINE 直接跳 ONLINE）")
    void offlineMustReconfigure() {
        assertThat(SupplyUnitStatus.OFFLINE.canTransitionTo(SupplyUnitStatus.CONFIGURING)).isTrue();
        assertThat(SupplyUnitStatus.OFFLINE.canTransitionTo(SupplyUnitStatus.ONLINE)).isFalse();
    }

    @Test
    @DisplayName("非法流转：PENDING 不得直接跳到 ONLINE / DEGRADED")
    void illegalShortcutsAreRejected() {
        assertThat(SupplyUnitStatus.PENDING.canTransitionTo(SupplyUnitStatus.ONLINE)).isFalse();
        assertThat(SupplyUnitStatus.PENDING.canTransitionTo(SupplyUnitStatus.DEGRADED)).isFalse();
        assertThat(SupplyUnitStatus.PENDING.canTransitionTo(SupplyUnitStatus.SUSPENDED)).isFalse();
    }

    @Test
    @DisplayName("自流转非法（幂等由调用方按值判断，不靠状态机）")
    void selfTransitionIsRejected() {
        for (SupplyUnitStatus s : SupplyUnitStatus.values()) {
            assertThat(s.canTransitionTo(s)).as(s + " → " + s).isFalse();
        }
    }

    @Test
    @DisplayName("终态检查：只有 ONLINE / DEGRADED 算在架")
    void liveStates() {
        assertThat(SupplyUnitStatus.ONLINE.isLive()).isTrue();
        assertThat(SupplyUnitStatus.DEGRADED.isLive()).isTrue();
        assertThat(SupplyUnitStatus.PENDING.isLive()).isFalse();
        assertThat(SupplyUnitStatus.CONFIGURING.isLive()).isFalse();
        assertThat(SupplyUnitStatus.SUSPENDED.isLive()).isFalse();
        assertThat(SupplyUnitStatus.OFFLINE.isLive()).isFalse();
    }

    @Test
    @DisplayName("解析：大小写容错；未知值抛异常（不回落默认值）")
    void parse() {
        assertThat(SupplyUnitStatus.of("online")).isEqualTo(SupplyUnitStatus.ONLINE);
        assertThat(SupplyUnitStatus.of(" Offline ")).isEqualTo(SupplyUnitStatus.OFFLINE);
        assertThatThrownBy(() -> SupplyUnitStatus.of("PER_MODEL"))
                .as("粒度值不是状态值，必须拒绝而不是静默回落")
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SupplyUnitStatus.of("BOGUS"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SupplyUnitStatus.of(null))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
