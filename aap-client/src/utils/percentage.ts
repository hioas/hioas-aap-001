/**
 * 百分比统一口径（决策 D3，`.agents/state/aap-decisions.md`）
 *
 * 唯一口径，不许每页各写一套：
 *   1) 分母 `denominator = max(total, Σ分类值)`  —— 见 `resolvePercentDenominator`
 *   2) 每段精确百分比 = `value / denominator`，取整用**最大余数法**（Hamilton）
 *   3) 整数百分比之和 == `round(Σ有效值 / 分母 × 100)`，且**恒 ≤ 100**（容差 0）
 *   4) 缺字段（undefined / null / NaN / ≤0）不参与分配、也不占整点 → 由调用方显示占位符（—）
 *
 * 为什么不用 `Math.round(value/total*100)` 逐项取整：设计稿 page-2-b 的图例
 * 45 + 30 + 15 + 4 + 6 + 6 = 106% 就是逐项取整的产物（设计稿只作视觉参考）。
 * 最大余数法保证「环形图分段之和 == 图例整数百分比之和 ≤ 100%」，且与真实占比的
 * 总偏差最小（即「最优」），所以环形图与图例可以共用同一份整数，视觉与数字永不打架。
 */

/** 百分比总量（100，表示「占满一圈」） */
export const PERCENT_TOTAL = 100

function isPositiveNumber(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0
}

/**
 * 百分比分母：`max(total, Σ分类值)`。
 * 六类之和大于总量（含「缓存/未分类」口径不一致）时以六类之和为分母，
 * 保证每段都 ≤ 100 / 6 类分配不溢出；总量更大时以总量为分母，
 * 其余部分作为「未分类余量」由环形图的轨道色表示。
 */
export function resolvePercentDenominator(
  total: number | null | undefined,
  values: Array<number | null | undefined>
): number {
  const partSum = values.reduce<number>((sum, v) => (isPositiveNumber(v) ? sum + v : sum), 0)
  const base = isPositiveNumber(total) ? total : 0
  return Math.max(base, partSum)
}

/** 整数百分比之和（用于断言「分段之和 == 图例之和 ≤ 100」） */
export function percentTotalOf(percents: number[]): number {
  return percents.reduce((sum, p) => (Number.isFinite(p) ? sum + p : sum), 0)
}

/**
 * 最大余数法：把 `values[i] / denominator × total` 取成整数，保证总和 ≤ total。
 * - 缺字段（undefined/null/NaN/≤0）恒得 0，不参与取整、也不抢别人的整点
 * - 平局按索引先后（前一个先拿）
 * - 分母非法（NaN/≤0）→ 全 0，由调用方退占位符，绝不产生 NaN
 */
export function largestRemainderPercentages(
  values: Array<number | null | undefined>,
  denominator: number,
  total: number = PERCENT_TOTAL
): number[] {
  const out = values.map(() => 0)
  if (values.length === 0 || !Number.isFinite(denominator) || denominator <= 0 || total <= 0) return out

  const present: number[] = []
  let presentSum = 0
  values.forEach((v, i) => {
    if (isPositiveNumber(v)) {
      present.push(i)
      presentSum += v
    }
  })
  if (present.length === 0 || presentSum <= 0) return out

  const exact = present.map((i) => ((values[i] as number) / denominator) * total)
  const floors = exact.map((e) => Math.floor(e))
  const target = Math.max(0, Math.min(total, Math.round((presentSum / denominator) * total)))
  floors.forEach((f, k) => {
    out[present[k]] = f
  })

  let points = target - percentTotalOf(floors)
  if (points <= 0) return out

  /* 余数降序、同余数按索引升序（平局稳定） */
  const order = present
    .map((idx, k) => ({ idx, remainder: exact[k] - floors[k] }))
    .sort((a, b) => (b.remainder === a.remainder ? a.idx - b.idx : b.remainder - a.remainder))

  for (const item of order) {
    if (points <= 0) break
    if (item.remainder <= 0) break
    out[item.idx] += 1
    points -= 1
  }
  return out
}
