/**
 * 百分比统一口径（决策 D3，`.agents/state/aap-decisions.md`）
 *
 * 口径（唯一，不许每页各写一套）：
 *   1) 分母 = max(total, Σ分类值)
 *   2) 每段精确百分比 = value / 分母，取整用**最大余数法**（Hamilton）
 *   3) 整数百分比之和 == round(Σ有效值 / 分母 × 100)，且**恒 ≤ 100**（容差 0）
 *   4) 缺字段（undefined/null/NaN）不参与分配、不占用整点 → 调用方显示占位符（—）
 *
 * 设计稿 page-2-b「构成图例」的 45/30/15/4/6/6（=106%）只作视觉参考：
 * 真源是 `GET /usage/summary` 的数值，本文件把它算成自洽的整数百分比。
 */
import { describe, expect, it } from 'vitest'
import {
  largestRemainderPercentages,
  resolvePercentDenominator,
  percentTotalOf
} from '@/utils/percentage'

describe('D3 · 分母 = max(total, Σ分类值)', () => {
  it('六类和大于总量时取六类和（设计稿场景：总量 3.86B 而六类合计 4.09B）', () => {
    expect(resolvePercentDenominator(3_860_000_000, [1_740_000_000, 1_160_000_000, 580_000_000, 150_000_000, 230_000_000, 230_000_000]))
      .toBe(4_090_000_000)
  })

  it('总量大于六类和时取总量（缓存/未分类部分计入分母，不虚高比例）', () => {
    expect(resolvePercentDenominator(1000, [100, 50, 100, 50])).toBe(1000)
  })

  it('总量缺失时退回六类和；都缺失/为 0 时返回 0（调用方显示占位符）', () => {
    expect(resolvePercentDenominator(undefined, [60, 40])).toBe(100)
    expect(resolvePercentDenominator(undefined, [undefined, null, NaN])).toBe(0)
    expect(resolvePercentDenominator(0, [])).toBe(0)
  })
})

describe('D3 · 最大余数法取整（整数百分比自洽）', () => {
  it('设计稿图例场景：1.74/1.16/0.58/0.15/0.23/0.23B，分母 4.09B → 42/28/14/4/6/6（合计 100）', () => {
    const parts = [1_740_000_000, 1_160_000_000, 580_000_000, 150_000_000, 230_000_000, 230_000_000]
    const pct = largestRemainderPercentages(parts, resolvePercentDenominator(3_860_000_000, parts))
    expect(pct).toEqual([42, 28, 14, 4, 6, 6])
    expect(percentTotalOf(pct)).toBe(100)
  })

  it('音频/视频 相等余数同分（不允许一个 6% 一个 7%）', () => {
    const pct = largestRemainderPercentages([1740, 1160, 580, 150, 230, 230], 4090)
    expect(pct[4]).toBe(pct[5])
  })

  it('分母远大于分类和时只分配真实份额，其余留作余量（合计 < 100）', () => {
    const pct = largestRemainderPercentages([100, 50, 100, 50], 1000)
    expect(pct).toEqual([10, 5, 10, 5])
    expect(percentTotalOf(pct)).toBe(30)
  })

  it('三等分：33/33/33 → 34/33/33（多出的 1 点给最大余数，平局按索引先后）', () => {
    const pct = largestRemainderPercentages([1, 1, 1], 3)
    expect(pct).toEqual([34, 33, 33])
    expect(percentTotalOf(pct)).toBe(100)
  })

  it('恒 ≤ 100（容差 0）：多组输入逐条断言', () => {
    const cases: Array<[number[], number]> = [
      [[1, 1, 1, 1, 1, 1], 100],
      [[1, 1, 1], 3],
      [[1, 2, 3, 4, 5, 6], 21],
      [[999, 1, 0, 0, 0, 0], 1000],
      [[1, 1, 1, 1, 1, 1], 6],
      [[7, 0, 0, 0, 0, 0], 7],
      [[1_740_000_000, 1_160_000_000, 580_000_000, 150_000_000, 230_000_000, 230_000_000], 4_090_000_000]
    ]
    for (const [values, denominator] of cases) {
      const pct = largestRemainderPercentages(values, denominator)
      expect(percentTotalOf(pct), `${JSON.stringify(values)} / ${denominator}`).toBeLessThanOrEqual(100)
      expect(pct).toHaveLength(values.length)
      expect(pct.every((p) => Number.isInteger(p) && p >= 0)).toBe(true)
    }
  })

  it('缺字段不参与分配也不占整点（留下的份额不进别人口袋）', () => {
    const pct = largestRemainderPercentages([1_740_000_000, undefined, 580_000_000, null, NaN, 230_000_000], 4_090_000_000)
    expect(pct[1]).toBe(0)
    expect(pct[3]).toBe(0)
    expect(pct[4]).toBe(0)
    expect(percentTotalOf(pct)).toBe(percentTotalOf([pct[0], pct[2], pct[5]]))
  })

  it('分母为 0 / 非法 → 全 0（不产生 NaN）', () => {
    expect(largestRemainderPercentages([1, 2], 0)).toEqual([0, 0])
    expect(largestRemainderPercentages([1, 2], Number.NaN)).toEqual([0, 0])
    expect(largestRemainderPercentages([], 100)).toEqual([])
  })

  it('同输入同输出（两轮稳定，取整不抖动）', () => {
    const values = [1_740_000_000, 1_160_000_000, 580_000_000, 150_000_000, 230_000_000, 230_000_000]
    expect(largestRemainderPercentages(values, 4_090_000_000)).toEqual(largestRemainderPercentages(values, 4_090_000_000))
  })
})
