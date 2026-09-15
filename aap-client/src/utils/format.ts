/**
 * 数值/日期格式化 — 工作台数据台（page-2-b）文案格式真源
 * 依据：.calicat/raw/pages/page-2-b/design.tree.json
 *   3.86B / 1.24M / 0.86M / 0.08M / ¥128,640 / 45% / 12.5% / 数据台 · 2024-06-14
 */

/** 无数据时的占位符（不显示 NaN / 不编造 0） */
export const PLACEHOLDER = '—'

/** 数量级阈值：≥B 阈值用 B，≥M 阈值用 M（设计稿 0.58B / 0.08M 两种口径并存） */
function scale(value: number, bThreshold: number, mThreshold: number): string {
  const abs = Math.abs(value)
  if (abs >= bThreshold) return `${(value / 1e9).toFixed(2)}B`
  if (abs >= mThreshold) return `${(value / 1e6).toFixed(2)}M`
  return String(value)
}

/** 词元量：3.86B / 1.74B / 0.58B / 0.15B（设计稿全部用 B 表述） */
export function formatTokens(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return PLACEHOLDER
  return scale(value, 1e8, 1e6)
}

/** 调用量：1.24M / 0.86M / 0.08M（设计稿最小到 0.08M） */
export function formatCount(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return PLACEHOLDER
  return scale(value, 1e9, 1e4)
}

/** 金额：¥128,640 */
export function formatAmount(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return PLACEHOLDER
  return `¥${Math.round(value).toLocaleString('en-US')}`
}

/**
 * 比例：小数（0.125）→ 12.5%；已是百分数（42）→ 42%
 * 设计稿 12.5% / 15% / 42% 两种形态都存在，故按值域判别。
 */
export function formatPercent(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return PLACEHOLDER
  const pct = Math.abs(value) <= 1 ? value * 100 : value
  const rounded = Math.round(pct * 10) / 10
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)}%`
}

/** 取整百分比（用于占比条与「1.24M · 42%」） */
export function percentOf(part?: number | null, total?: number | null): number | null {
  if (!part || !total) return null
  return Math.round((part / total) * 100)
}

/** 顶部栏：「数据台 · 2024-06-14」 */
export function formatHeaderDate(date: Date = new Date()): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `数据台 · ${y}-${m}-${d}`
}
