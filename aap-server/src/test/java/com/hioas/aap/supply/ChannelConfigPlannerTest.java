package com.hioas.aap.supply;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * T-M4-07 · 渠道配置规划器单测（红基线 → 实现 → 绿）。
 *
 * <p>契约真源：`specs/001-intake-automation/spec.md` §6 R-54/R-56/R-59、§7 AC-03/AC-04/AC-10。
 *
 * <p>为什么差异计算要独立测：它是「重复执行不产生副作用」（AC-03 幂等）与
 * 「单模型失败不波及其他模型」（AC-04 隔离）两件事的共同落点 ——
 * 一旦 SKIP 判定漏了某个字段，重跑就会把已一致的渠道反复改写；
 * 一旦展开时把多模型塞进 PER_MODEL，模型级调度的前提就失效（R-56）。
 */
class ChannelConfigPlannerTest {

    private static ChannelConfigPlanner.Input input(String unitId, String shortCode, String modelName) {
        return new ChannelConfigPlanner.Input(unitId, 1L, shortCode, modelName, List.of(modelName),
                "PER_MODEL", 10, 20);
    }

    @Test
    @DisplayName("R-54/R-56 展开：渠道名由命名器生成，models 为单元素")
    void planProducesDeterministicNameAndSingleModel() {
        var t = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        assertThat(t.channelName()).isEqualTo("AAP-ace-gpt-4o");
        assertThat(t.models()).containsExactly("gpt-4o");
        assertThat(t.tag()).isEqualTo("aap-provider-1");
        assertThat(t.supplyUnitId()).isEqualTo("u1");
    }

    @Test
    @DisplayName("R-56 PER_MODEL 展开失败要显式拒绝，不得把多模型塞进单模型渠道")
    void planRejectsMultipleModelsInModelLevel() {
        var bad = new ChannelConfigPlanner.Input("u1", 1L, "ace", "gpt-4o",
                List.of("gpt-4o", "gpt-4o-mini"), "PER_MODEL", 10, 20);
        assertThat(ChannelConfigPlanner.plan(bad)).isNull();
    }

    @Test
    @DisplayName("AC-03 幂等：现存与目标完全一致 → SKIP（重复执行不产生副作用）")
    void identicalExistingIsSkipped() {
        var target = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var existing = new ChannelConfigPlanner.Existing("u1", "AAP-ace-gpt-4o", List.of("gpt-4o"),
                "aap-provider-1", 10, 20, "ENABLED");
        var diffs = ChannelConfigPlanner.diff(List.of(target), List.of(existing), Set.of());
        assertThat(diffs).hasSize(1);
        assertThat(diffs.get(0).action()).isEqualTo(ChannelConfigPlanner.SKIP);
    }

    @Test
    @DisplayName("无现存绑定 → CREATE")
    void missingExistingIsCreate() {
        var target = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var diffs = ChannelConfigPlanner.diff(List.of(target), List.of(), Set.of());
        assertThat(diffs.get(0).action()).isEqualTo(ChannelConfigPlanner.CREATE);
    }

    @Test
    @DisplayName("权重/优先级变化 → UPDATE（调度策略调整要下发）")
    void routingChangeIsUpdate() {
        var target = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var existing = new ChannelConfigPlanner.Existing("u1", "AAP-ace-gpt-4o", List.of("gpt-4o"),
                "aap-provider-1", 10, 99, "ENABLED");
        var diffs = ChannelConfigPlanner.diff(List.of(target), List.of(existing), Set.of());
        assertThat(diffs.get(0).action()).isEqualTo(ChannelConfigPlanner.UPDATE);
    }

    @Test
    @DisplayName("模型清单变化 → UPDATE")
    void modelChangeIsUpdate() {
        var target = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var existing = new ChannelConfigPlanner.Existing("u1", "AAP-ace-gpt-4o", List.of("gpt-4o-mini"),
                "aap-provider-1", 10, 20, "ENABLED");
        var diffs = ChannelConfigPlanner.diff(List.of(target), List.of(existing), Set.of());
        assertThat(diffs.get(0).action()).isEqualTo(ChannelConfigPlanner.UPDATE);
    }

    @Test
    @DisplayName("下线：有现存绑定 → DISABLE；无现存 → SKIP（并说明无需动作）")
    void offlineHandling() {
        var target = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var existing = new ChannelConfigPlanner.Existing("u1", "AAP-ace-gpt-4o", List.of("gpt-4o"),
                "aap-provider-1", 10, 20, "ENABLED");
        var withBinding = ChannelConfigPlanner.diff(List.of(target), List.of(existing), Set.of("u1"));
        assertThat(withBinding.get(0).action()).isEqualTo(ChannelConfigPlanner.DISABLE);

        var withoutBinding = ChannelConfigPlanner.diff(List.of(target), List.of(), Set.of("u1"));
        assertThat(withoutBinding.get(0).action()).isEqualTo(ChannelConfigPlanner.SKIP);
        assertThat(withoutBinding.get(0).reason()).contains("无需");
    }

    @Test
    @DisplayName("R-59 单模型隔离：多个供给单元各自成项，一个的变化不影响另一个")
    void unitsAreIsolated() {
        var t1 = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var t2 = ChannelConfigPlanner.plan(input("u2", "ace", "gpt-4o-mini"));
        var existing = List.of(new ChannelConfigPlanner.Existing("u1", "AAP-ace-gpt-4o", List.of("gpt-4o"),
                "aap-provider-1", 10, 20, "ENABLED"));
        var diffs = ChannelConfigPlanner.diff(List.of(t1, t2), existing, Set.of());
        assertThat(diffs).hasSize(2);
        assertThat(diffs.get(0).action()).isEqualTo(ChannelConfigPlanner.SKIP);
        assertThat(diffs.get(1).action()).isEqualTo(ChannelConfigPlanner.CREATE);
        assertThat(diffs.get(0).supplyUnitId()).isEqualTo("u1");
        assertThat(diffs.get(1).supplyUnitId()).isEqualTo("u2");
    }

    @Test
    @DisplayName("确定性：输入顺序稳定 → 输出顺序稳定（dry-run 清单可比对）")
    void orderIsDeterministic() {
        var t1 = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var t2 = ChannelConfigPlanner.plan(input("u2", "ace", "gpt-4o-mini"));
        var a = ChannelConfigPlanner.diff(List.of(t1, t2), List.of(), Set.of());
        var b = ChannelConfigPlanner.diff(List.of(t1, t2), List.of(), Set.of());
        assertThat(a).isEqualTo(b);
    }

    @Test
    @DisplayName("AC-10 isWrite：CREATE/UPDATE/DISABLE 需写上游，SKIP 不写")
    void isWriteClassification() {
        assertThat(ChannelConfigPlanner.isWrite(ChannelConfigPlanner.CREATE)).isTrue();
        assertThat(ChannelConfigPlanner.isWrite(ChannelConfigPlanner.UPDATE)).isTrue();
        assertThat(ChannelConfigPlanner.isWrite(ChannelConfigPlanner.DISABLE)).isTrue();
        assertThat(ChannelConfigPlanner.isWrite(ChannelConfigPlanner.SKIP)).isFalse();
    }

    @Test
    @DisplayName("汇总统计：按动作计数（dry-run 影响面展示）")
    void summarizeCounts() {
        var t1 = ChannelConfigPlanner.plan(input("u1", "ace", "gpt-4o"));
        var t2 = ChannelConfigPlanner.plan(input("u2", "ace", "gpt-4o-mini"));
        var t3 = ChannelConfigPlanner.plan(input("u3", "ace", "o3-mini"));
        var existing = List.of(new ChannelConfigPlanner.Existing("u1", "AAP-ace-gpt-4o", List.of("gpt-4o"),
                "aap-provider-1", 10, 20, "ENABLED"));
        var diff = ChannelConfigPlanner.diff(List.of(t1, t2, t3), existing, Set.of());
        var summary = ChannelConfigPlanner.summarize(diff);
        assertThat(summary).containsEntry(ChannelConfigPlanner.SKIP, 1L)
                .containsEntry(ChannelConfigPlanner.CREATE, 2L);
    }
}
