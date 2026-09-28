package com.hioas.aap.supply;

import com.hioas.aap.sync.ChannelNameGenerator;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * 渠道配置规划器（T-M4-07 的纯逻辑核心）—— 展开与差异计算。
 *
 * <p>规格：`specs/001-intake-automation/spec.md` §6 `R-54`/`R-56`/`R-59`、§7 `AC-03`（幂等）/
 * `AC-04`（单模型隔离）/ `AC-10`（dry-run 零写入）；`plan.md` §3.2 编排器五步的第 1–2 步。
 *
 * <p>设计为**纯函数**（不碰 DB、不碰网络）：展开与差异计算是这条链路里最容易出错、
 * 也最值得单测的部分；执行与回读（第 3–4 步）由编排器复用既有 `SyncPublishService` 的三段式完成。
 *
 * <p>与既有「一供应商一渠道」实现的差异只有一处、但很关键：本规划器产出的 `models`
 * 在 `PER_MODEL` 下**恒为单元素**，使网关的 `priority`/`weight`/`auto_ban` 按模型生效。
 */
public final class ChannelConfigPlanner {

    public static final String CREATE = "CREATE";
    public static final String UPDATE = "UPDATE";
    public static final String SKIP = "SKIP";
    public static final String DISABLE = "DISABLE";

    private static final String PER_MODEL = "PER_MODEL";

    private ChannelConfigPlanner() {
    }

    /**
     * 展开：把一个供给单元折算为目标渠道配置。
     *
     * <p>`PER_MODEL` 下 `models` 必须恰为该模型（R-56）；不满足返回 {@code null}
     * 而不是抛异常 —— 让编排器能把「不可规划的项」记入批次明细并单独重试，
     * 其它供给单元继续（R-59 单模型隔离）。
     */
    public static Target plan(Input input) {
        if (input == null || input.supplyUnitId() == null) {
            return null;
        }
        String modelName = input.modelName() == null ? "" : input.modelName().trim();
        List<String> models = input.models() == null ? List.of() : input.models().stream()
                .filter(m -> m != null && !m.isBlank())
                .map(String::trim)
                .toList();
        boolean perModel = PER_MODEL.equalsIgnoreCase(input.granularity() == null ? "" : input.granularity().trim());
        if (perModel) {
            if (modelName.isEmpty() || models.size() != 1 || !models.get(0).equals(modelName)) {
                return null;
            }
        } else if (models.isEmpty()) {
            return null;
        }
        String channelName = ChannelNameGenerator.forModel(input.shortCode(), modelName);
        return new Target(input.supplyUnitId(), channelName, models,
                "aap-provider-" + input.providerId(), input.priority(), input.weight(), input.granularity());
    }

    /**
     * 差异计算：目标 vs 现存 → 动作清单（顺序与输入一致，保证确定性——dry-run 清单可比对）。
     *
     * @param offlineUnits 需下线的供给单元 id（有现存绑定 → DISABLE；无 → SKIP 且说明无需动作）
     */
    public static List<Diff> diff(List<Target> targets, List<Existing> existing, Set<String> offlineUnits) {
        Map<String, Existing> byUnit = new LinkedHashMap<>();
        if (existing != null) {
            for (Existing e : existing) {
                if (e != null && e.supplyUnitId() != null) {
                    byUnit.put(e.supplyUnitId(), e);
                }
            }
        }
        Set<String> offline = offlineUnits == null ? Set.of() : offlineUnits;
        List<Diff> diffs = new ArrayList<>();
        if (targets == null) {
            return diffs;
        }
        for (Target target : targets) {
            if (target == null) {
                continue;
            }
            Existing current = byUnit.get(target.supplyUnitId());
            if (offline.contains(target.supplyUnitId())) {
                diffs.add(current == null
                        ? new Diff(target.supplyUnitId(), SKIP, "目标已下线且库内无绑定，无需动作", target)
                        : new Diff(target.supplyUnitId(), DISABLE, "目标已下线，需禁用现存渠道", target));
                continue;
            }
            if (current == null) {
                diffs.add(new Diff(target.supplyUnitId(), CREATE, "库内无绑定，需创建渠道", target));
                continue;
            }
            if (isSame(target, current)) {
                diffs.add(new Diff(target.supplyUnitId(), SKIP, "与目标一致，无需变更（幂等跳过，不打上游）", target));
                continue;
            }
            diffs.add(new Diff(target.supplyUnitId(), UPDATE, describeChange(target, current), target));
        }
        return diffs;
    }

    private static boolean isSame(Target target, Existing current) {
        return Objects.equals(target.channelName(), current.channelName())
                && Objects.equals(target.models(), current.models())
                && Objects.equals(target.tag(), current.tag())
                && target.priority() == current.priority()
                && target.weight() == current.weight();
    }

    private static String describeChange(Target target, Existing current) {
        List<String> changes = new ArrayList<>();
        if (!Objects.equals(target.channelName(), current.channelName())) {
            changes.add("name " + current.channelName() + " → " + target.channelName());
        }
        if (!Objects.equals(target.models(), current.models())) {
            changes.add("models " + current.models() + " → " + target.models());
        }
        if (!Objects.equals(target.tag(), current.tag())) {
            changes.add("tag " + current.tag() + " → " + target.tag());
        }
        if (target.priority() != current.priority()) {
            changes.add("priority " + current.priority() + " → " + target.priority());
        }
        if (target.weight() != current.weight()) {
            changes.add("weight " + current.weight() + " → " + target.weight());
        }
        return "需更新：" + String.join("；", changes);
    }

    /** 该动作是否需要写上游（AC-10：dry-run 据此断言零写入）。 */
    public static boolean isWrite(String action) {
        return CREATE.equals(action) || UPDATE.equals(action) || DISABLE.equals(action);
    }

    /** 按动作计数（dry-run 影响面展示）。 */
    public static Map<String, Long> summarize(List<Diff> diffs) {
        Map<String, Long> summary = new LinkedHashMap<>();
        if (diffs == null) {
            return summary;
        }
        for (Diff diff : diffs) {
            summary.merge(diff.action(), 1L, Long::sum);
        }
        return summary;
    }

    /** 规划输入：供给单元 + 供应商画像。 */
    public record Input(String supplyUnitId,
                        long providerId,
                        String shortCode,
                        String modelName,
                        List<String> models,
                        String granularity,
                        int priority,
                        int weight) {
    }

    /** 目标渠道配置。 */
    public record Target(String supplyUnitId,
                         String channelName,
                         List<String> models,
                         String tag,
                         int priority,
                         int weight,
                         String granularity) {
    }

    /** 库内现存绑定（实况）。 */
    public record Existing(String supplyUnitId,
                           String channelName,
                           List<String> models,
                           String tag,
                           int priority,
                           int weight,
                           String status) {
    }

    /** 差异项。 */
    public record Diff(String supplyUnitId, String action, String reason, Target target) {
    }

    /** 便于测试与调试的空清单。 */
    public static final List<Diff> NO_DIFF = List.of();
}
