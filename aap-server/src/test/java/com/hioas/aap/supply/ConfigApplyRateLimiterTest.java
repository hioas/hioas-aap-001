package com.hioas.aap.supply;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** T-M4-08 · 限速计划单测（红基线 → 实现 → 绿）。契约：spec.md R-57。 */
class ConfigApplyRateLimiterTest {

    @Test
    @DisplayName("R-57 上限不可突破：传 100 只能按上限 5 执行，而不是整批失败")
    void rateIsCappedNotRejected() {
        assertThat(ConfigApplyRateLimiter.normalizeRate(100))
                .isEqualTo(ConfigApplyRateLimiter.MAX_RATE_PER_SEC);
        assertThat(ConfigApplyRateLimiter.normalizeRate(null))
                .isEqualTo(ConfigApplyRateLimiter.DEFAULT_RATE_PER_SEC);
        assertThat(ConfigApplyRateLimiter.normalizeRate(0))
                .isEqualTo(ConfigApplyRateLimiter.DEFAULT_RATE_PER_SEC);
        assertThat(ConfigApplyRateLimiter.normalizeRate(-3))
                .isEqualTo(ConfigApplyRateLimiter.DEFAULT_RATE_PER_SEC);
        assertThat(ConfigApplyRateLimiter.normalizeRate(2)).isEqualTo(2);
    }

    @Test
    @DisplayName("间隔：5 req/s → 200ms")
    void interval() {
        assertThat(ConfigApplyRateLimiter.intervalMillis(5)).isEqualTo(200L);
        assertThat(ConfigApplyRateLimiter.intervalMillis(1)).isEqualTo(1000L);
    }

    @Test
    @DisplayName("分批：45 条 / 每批 20 → 3 批，无重叠且全覆盖")
    void batching() {
        List<int[]> batches = ConfigApplyRateLimiter.batches(45, 20);
        assertThat(batches).hasSize(3);
        assertThat(batches.get(0)).containsExactly(0, 20);
        assertThat(batches.get(1)).containsExactly(20, 40);
        assertThat(batches.get(2)).containsExactly(40, 45);
        int covered = batches.stream().mapToInt(b -> b[1] - b[0]).sum();
        assertThat(covered).isEqualTo(45);
    }

    @Test
    @DisplayName("空输入与非法批长：0 条 → 无批次；批长非正 → 回退默认批长")
    void edgeCases() {
        assertThat(ConfigApplyRateLimiter.batches(0, 20)).isEmpty();
        assertThat(ConfigApplyRateLimiter.batches(25, 0)).hasSize(2);
    }

    @Test
    @DisplayName("退避序列 30s / 2min / 10min，超出后维持最长值")
    void backoff() {
        assertThat(ConfigApplyRateLimiter.backoffSeconds(1)).isEqualTo(30);
        assertThat(ConfigApplyRateLimiter.backoffSeconds(2)).isEqualTo(120);
        assertThat(ConfigApplyRateLimiter.backoffSeconds(3)).isEqualTo(600);
        assertThat(ConfigApplyRateLimiter.backoffSeconds(9)).isEqualTo(600);
    }

    @Test
    @DisplayName("最多 3 次退避，之后转人工（不得无限重试）")
    void retryBound() {
        assertThat(ConfigApplyRateLimiter.retryable(1)).isTrue();
        assertThat(ConfigApplyRateLimiter.retryable(2)).isTrue();
        assertThat(ConfigApplyRateLimiter.retryable(3)).isFalse();
    }
}
