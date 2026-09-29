package com.hioas.aap.supply;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * 写后回读比较（T-M4-09；规格 R-58）—— 纯函数，便于单测。
 *
 * <p><b>为什么必须回读</b>：网关接受请求 ≠ 配置生效（可能被网关自身的校验改写，或被并发写入
 * 覆盖）。只按 HTTP 200 判定成功，会产生「报告说成功、线上没生效」这类最难排查的故障 ——
 * 因此**以回读结果为准**，不一致就是 `MISMATCH`，必须可见（不得静默成功）。
 *
 * <p><b>模型清单按集合比较</b>：网关可能重排或去重 `models`。顺序差异不是配置差异，
 * 按序列比较会把「已一致」误判为不一致 → 触发无意义的重复写入，并让重试机制空转。
 */
public final class ReadbackComparator {

    private ReadbackComparator() {
    }

    /** 期望（我们下发的目标配置）。 */
    public record Expectation(String channelName, List<String> models, String tag, String status) {
    }

    /** 回读（从网关读回的实际配置）。 */
    public record Readback(String channelName, List<String> models, String tag, String status) {
    }

    /** 比较结果：`equal=false` 时 `differences` 必须非空（差异必须可解释）。 */
    public record Result(boolean equal, List<String> differences) {
    }

    public static Result compare(Expectation expected, Readback actual) {
        Expectation exp = expected == null ? new Expectation(null, List.of(), null, null) : expected;
        Readback act = actual == null ? new Readback(null, List.of(), null, null) : actual;
        List<String> differences = new ArrayList<>();
        if (!norm(exp.channelName()).equals(norm(act.channelName()))) {
            differences.add("channelName: " + exp.channelName() + " → " + act.channelName());
        }
        if (!normalizeModels(exp.models()).equals(normalizeModels(act.models()))) {
            differences.add("models: " + normalizeModels(exp.models()) + " → " + normalizeModels(act.models()));
        }
        if (!norm(exp.tag()).equals(norm(act.tag()))) {
            differences.add("tag: " + exp.tag() + " → " + act.tag());
        }
        if (!norm(exp.status()).equalsIgnoreCase(norm(act.status()))) {
            differences.add("status: " + exp.status() + " → " + act.status());
        }
        return new Result(differences.isEmpty(), differences);
    }

    /** 归一化：去空白、去空项、去重并保持出现顺序（用于集合语义比较）。 */
    static Set<String> normalizeModels(List<String> models) {
        Set<String> out = new LinkedHashSet<>();
        if (models != null) {
            for (String model : models) {
                if (model != null && !model.isBlank()) {
                    out.add(model.trim());
                }
            }
        }
        return out;
    }

    private static String norm(String value) {
        return value == null ? "" : value.trim();
    }
}
