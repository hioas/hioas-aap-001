/**
 * 数值/日期格式化 — 设计稿页 page-2-b 的文案格式真源
 * 设计与数字依据：.calicat/raw/pages/page-2-b/design.tree.json
 *   3.86B（总词元）· 1.24M（调用请求）· ¥128,640 · ¥54,200 · 45% · 12.5% · 数据台 · 2024-06-14
 */
import { describe, expect, it } from 'vitest'
import {
  formatAmount,
  formatCount,
  formatHeaderDate,
  formatPercent,
  formatTokens
} from '@/utils/format'

describe('formatTokens · 词元量级', () => {
  it('十亿级 → 两位小数 + B', () => {
    expect(formatTokens(3_860_000_000)).toBe('3.86B')
  })

  it('百万级 → 两位小数 + M', () => {
    expect(formatTokens(1_240_000)).toBe('1.24M')
  })

  it('不足百万 → 原样整数（无单位）', () => {
    expect(formatTokens(860)).toBe('860')
  })

  it('空值 → 占位符，不显示 NaN', () => {
    expect(formatTokens(undefined)).toBe('—')
    expect(formatTokens(null)).toBe('—')
  })
})

describe('formatCount · 请求数', () => {
  it('百万级 → 两位小数 + M', () => {
    expect(formatCount(1_240_000)).toBe('1.24M')
  })
})

describe('formatAmount · 金额', () => {
  it('人民币千分位', () => {
    expect(formatAmount(128640)).toBe('¥128,640')
    expect(formatAmount(54200)).toBe('¥54,200')
    expect(formatAmount(8240)).toBe('¥8,240')
  })

  it('空值 → 占位符', () => {
    expect(formatAmount(undefined)).toBe('—')
  })
})

describe('formatPercent', () => {
  it('小数比例 → 百分比整数', () => {
    expect(formatPercent(0.15)).toBe('15%')
    expect(formatPercent(0.125)).toBe('12.5%')
  })

  it('已经是百分数（>1）→ 原样', () => {
    expect(formatPercent(42)).toBe('42%')
  })

  it('空值 → 占位符', () => {
    expect(formatPercent(undefined)).toBe('—')
  })
})

describe('formatHeaderDate · 顶部栏日期', () => {
  it('输出「数据台 · YYYY-MM-DD」（design: 数据台 · 2024-06-14）', () => {
    expect(formatHeaderDate(new Date(2024, 5, 14))).toBe('数据台 · 2024-06-14')
  })

  it('个位数月份/日期补零', () => {
    expect(formatHeaderDate(new Date(2026, 0, 5))).toBe('数据台 · 2026-01-05')
  })
})
