package com.hioas.aap.compile;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 计费表达式 AST（真源 `06-报价模型与计费编译规则.md §3`）。
 *
 * <p>**同一棵树同时负责 render（产出 new-api 表达式文本）与 eval（模拟验证求值）**——
 * 这样「写出去的表达式」与「验证过的表达式」在结构上必然一致，避免出现
 * 「验证用 A 逻辑、写盘用 B 文本」的经典漂移。
 *
 * <p>变量（PRD 06 §3 R1–R3）：{@code p} 输入 token、{@code c} 输出 token、{@code cr} 缓存读取 token、
 * {@code cw} 缓存写入 token、{@code len} 上下文总长度；{@code hour(tz)}、{@code weekday(tz)} 为环境函数。
 */
public sealed interface BillingExpr {

    /** 表达式文本（写成 new-api 认的形态）。 */
    String render();

    /** 求值（模拟验证使用真实语义，不走字符串解析）。 */
    BigDecimal eval(Ctx ctx);

    /** 求值上下文。 */
    record Ctx(long p, long c, long cr, long cw, long len, int hour, int weekday) {

        public static Ctx of(long p, long c, long cr, long cw, long len, int hour, int weekday) {
            return new Ctx(p, c, cr, cw, len, hour, weekday);
        }

        public long len() {
            return len;
        }
    }

    // ------------------------------------------------------------------ 节点

    /** 基础价：`p * input + c * output [+ cr * cacheRead] [+ cw * cacheWrite]`（单位 $/1M token，故除 1e6）。 */
    record Price(BigDecimal input, BigDecimal output, BigDecimal cacheRead, BigDecimal cacheWrite,
                 BigDecimal cacheWrite1h) implements BillingExpr {

        @Override
        public String render() {
            StringBuilder sb = new StringBuilder("p * ").append(num(input)).append(" + c * ").append(num(output));
            if (cacheRead != null) {
                sb.append(" + cr * ").append(num(cacheRead));
            }
            if (cacheWrite != null) {
                sb.append(" + cw * ").append(num(cacheWrite));
            }
            return sb.toString();
        }

        @Override
        public BigDecimal eval(Ctx ctx) {
            BigDecimal cost = input.multiply(BigDecimal.valueOf(ctx.p()))
                    .add(output.multiply(BigDecimal.valueOf(ctx.c())));
            if (cacheRead != null) {
                cost = cost.add(cacheRead.multiply(BigDecimal.valueOf(ctx.cr())));
            }
            if (cacheWrite != null) {
                cost = cost.add(cacheWrite.multiply(BigDecimal.valueOf(ctx.cw())));
            }
            return scale(cost);
        }
    }

    /** 档位包装：`tier("name", inner)`——档位名进账单明细，便于对账。 */
    record Tier(String name, BillingExpr inner) implements BillingExpr {

        @Override
        public String render() {
            return "tier(\"" + name + "\", " + inner.render() + ")";
        }

        @Override
        public BigDecimal eval(Ctx ctx) {
            return inner.eval(ctx);
        }
    }

    /** 倍率：`inner * factor`（峰谷价、请求级加价）。 */
    record Multiply(BillingExpr inner, BigDecimal factor) implements BillingExpr {

        @Override
        public String render() {
            return "(" + inner.render() + ") * " + num(factor);
        }

        @Override
        public BigDecimal eval(Ctx ctx) {
            return scale(inner.eval(ctx).multiply(factor));
        }
    }

    /** 条件：`cond ? then : else`。 */
    record Cond(Condition condition, BillingExpr then, BillingExpr otherwise) implements BillingExpr {

        @Override
        public String render() {
            return condition.render() + " ? " + then.render() + " : (" + otherwise.render() + ")";
        }

        @Override
        public BigDecimal eval(Ctx ctx) {
            return condition.test(ctx) ? then.eval(ctx) : otherwise.eval(ctx);
        }
    }

    /** 条件节点。 */
    sealed interface Condition {

        String render();

        boolean test(Ctx ctx);

        /** `len <= threshold`（★ 阶梯必须用 len 而非 p）。 */
        record LenLte(long threshold) implements Condition {
            @Override
            public String render() {
                return "len <= " + threshold;
            }

            @Override
            public boolean test(Ctx ctx) {
                return ctx.len() <= threshold;
            }
        }

        /** `hour(tz) >= start && hour(tz) < end`（半开区间）。 */
        record HourRange(String tz, int start, int end) implements Condition {
            @Override
            public String render() {
                return "hour(\"" + tz + "\") >= " + start + " && hour(\"" + tz + "\") < " + end;
            }

            @Override
            public boolean test(Ctx ctx) {
                return ctx.hour() >= start && ctx.hour() < end;
            }
        }

        /** `weekday(tz) in [...]`。 */
        record WeekdayIn(String tz, List<Integer> days) implements Condition {
            @Override
            public String render() {
                return "weekday(\"" + tz + "\") in [" + days.stream().map(String::valueOf)
                        .reduce((a, b) -> a + ", " + b).orElse("") + "]";
            }

            @Override
            public boolean test(Ctx ctx) {
                return days.contains(ctx.weekday());
            }
        }

        /** 与：`a && b`。 */
        record And(List<Condition> items) implements Condition {
            @Override
            public String render() {
                List<String> parts = new ArrayList<>();
                for (Condition item : items) {
                    parts.add(item.render());
                }
                return String.join(" && ", parts);
            }

            @Override
            public boolean test(Ctx ctx) {
                return items.stream().allMatch(item -> item.test(ctx));
            }
        }

        /** 或：`a || b`。 */
        record Or(List<Condition> items) implements Condition {
            @Override
            public String render() {
                List<String> parts = new ArrayList<>();
                for (Condition item : items) {
                    parts.add(item.render());
                }
                return parts.size() == 1 ? parts.get(0) : String.join(" || ", parts);
            }

            @Override
            public boolean test(Ctx ctx) {
                return items.stream().anyMatch(item -> item.test(ctx));
            }
        }
    }

    // ------------------------------------------------------------------ 工具

    static BigDecimal scale(BigDecimal value) {
        return value.setScale(8, RoundingMode.HALF_UP);
    }

    /** 数字渲染：去掉无意义尾零，保证 render 稳定（source_hash 依赖它）。 */
    static String num(BigDecimal value) {
        return value.stripTrailingZeros().toPlainString();
    }

    /** 按模型名归集的表达式集合（写入 `billing_setting.billing_expr[model_name]`）。 */
    static String renderAll(Map<String, BillingExpr> byModel) {
        StringBuilder sb = new StringBuilder();
        byModel.forEach((model, expr) -> sb.append(model).append(": ").append(expr.render()).append('\n'));
        return sb.toString();
    }
}
