package com.hioas.aap.supply;

import java.util.ArrayList;
import java.util.List;

/**
 * 批量配置的**限速计划**（T-M4-08；规格 R-57）—— 纯函数，便于单测。
 *
 * <p>为什么限速是硬约束而不是可调参数：一次编排要按「供应商 × 模型」逐条调用网关建渠道，
 * 数量级随供给规模放大；不限速会把网关打挂，而网关是全平台的路由中枢（共用面）。上限因此
 * 不可被调用方突破 —— {@link #normalizeRate} 对超限值**收敛到上限**而不是抛错，
 * 避免「因为传了 100 就整批失败」，但绝不按 100 执行。
 */
public final class ConfigApplyRateLimiter {

    /** R-57：每秒请求数上限（不可突破）。 */
    public static final int MAX_RATE_PER_SEC = 5;
    /** R-57：默认限速。 */
    public static final int DEFAULT_RATE_PER_SEC = 5;
    /** R-57：每批处理上限（断点续传的粒度）。 */
    public static final int BATCH_SIZE = 20;
    /** R-57：退避序列（秒）——30s / 2min / 10min。 */
    public static final List<Integer> BACKOFF_SECONDS = List.of(30, 120, 600);

    private ConfigApplyRateLimiter() {
    }

    /** 归一化限速：null 或非正 → 默认；超上限 → 收敛到上限（**不突破**）。 */
    public static int normalizeRate(Integer requested) {
        if (requested == null || requested <= 0) {
            return DEFAULT_RATE_PER_SEC;
        }
        return Math.min(requested, MAX_RATE_PER_SEC);
    }

    /** 两条请求之间的最小间隔（毫秒）。 */
    public static long intervalMillis(int ratePerSec) {
        return 1000L / normalizeRate(ratePerSec);
    }

    /** 分批：`total` 条按 `batchSize` 切成 `[from, to)` 区间（确定、无重叠、全覆盖）。 */
    public static List<int[]> batches(int total, int batchSize) {
        List<int[]> out = new ArrayList<>();
        if (total <= 0) {
            return out;
        }
        int size = batchSize <= 0 ? BATCH_SIZE : batchSize;
        for (int from = 0; from < total; from += size) {
            out.add(new int[] {from, Math.min(from + size, total)});
        }
        return out;
    }

    /** 第 `attempt` 次重试前的等待秒数（1→30、2→120、3→600、超出→600）。 */
    public static int backoffSeconds(int attempt) {
        if (attempt <= 0) {
            return BACKOFF_SECONDS.get(0);
        }
        int index = Math.min(attempt, BACKOFF_SECONDS.size()) - 1;
        return BACKOFF_SECONDS.get(index);
    }

    /** 是否还允许重试（R-57：最多 3 次退避，之后转人工）。 */
    public static boolean retryable(int attempt) {
        return attempt >= 1 && attempt < BACKOFF_SECONDS.size();
    }
}
