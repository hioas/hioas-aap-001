/**
 * 序号 22【工作台与我的】我的与用量概览（page-22-2 / /pages/usage/index）视图模型
 *
 * 设计真源：.calicat/raw/pages/page-22-2/design.tree.json（430 宽 · 设计总高 1138 · 无 TabBar）
 *   顶部导航 0..96（白底 padding 48/16/12/16：「用量概览」17px Bold + 月份选择 pill h30 r10 #F1F5F9）
 *   本月汇总卡 108..336（padding 20/16 r18：标题 20 + 16 + 四宫格 72×2 行（gap 9）+ 行距 8）
 *   近 7 日用量趋势卡 348..570（padding 20 r18 描边 #EEF2F7：标题行 20 + 12 + 趋势图 150）
 *   模型用量分布卡 582..766（4 行 h18 行距 12：名称 131 + 轨道 h10 r5 #F1F5F9 + 百分比）
 *   成本构成卡 778..985（成本项 3 行 h18 行距 12 + 合计行 padding 10 r10 #F8FAFC）
 *   明细入口卡 997..1057（padding 16/20：图标 18px + 13px 文案 + chevron 20px）
 *   底部说明 1057..1138（padding 24/0/24/0 · 11px 两行居中）
 *
 * 接口真源：18-API设计OpenAPI.md「Usage」Tag（GET /usage/summary，前缀 /api/v1）。
 * ⚠️ 响应体字段级 schema 未在 18-API 定义 → 本文件所有字段名均为**推断**（已记台账 missing-prd）：
 *   请求数 request_count · Token total_tokens/tokens · 费用 amount_total/amount/cost_usd ·
 *   较上月节省 mom_saved_amount/mom_saving/saved_amount（PRD 11 §4「对账视图指标」只有「环比」，无「节省」口径）·
 *   逐日 daily[]{stat_date|date|day, total_tokens|tokens} · 模型占比 models[]{model_name|name, share|percent|ratio} ·
 *   成本构成 cost{input|input_cost|prompt_cost, output|output_cost|completion_cost, platform_fee|service_fee, platform_fee_rate|fee_rate, total|total_cost}
 *   （亦可扁平 input_cost/output_cost/platform_fee/total_cost）· 更新时间 updated_at/refreshed_at。
 *   缺字段一律渲染占位符「—」，不编造 0。
 */
import { PLACEHOLDER, formatAmount, formatCount, formatPercent, formatTokens } from './format'
import { base64Ascii } from './base64'

/* ------------------------------- 设计稿原文 ------------------------------- */

export const NAV_TITLE = '用量概览'
export const SUMMARY_TITLE = '本月汇总'
export const TREND_TITLE = '近 7 日用量趋势'
export const TREND_LEGEND = 'Token（亿）'
export const MODEL_TITLE = '模型用量分布'
export const COST_TITLE = '成本构成'
export const DETAIL_ENTRY_TEXT = '查看逐日 / 逐模型明细'
export const FOOTER_NOTE = '数据每小时更新一次，最终以结算账单为准'
export const UPDATED_PREFIX = '更新时间：'

/** 设计帧成本构成第三行文案「平台服务费（8%）」→ 费率优先取服务端，缺省用设计常量 8 */
export const PLATFORM_FEE_RATE_DEFAULT = 8
export function platformFeeLabel(rate?: number | null): string {
  const value = rate === undefined || rate === null || Number.isNaN(rate) ? PLATFORM_FEE_RATE_DEFAULT : rate
  return `平台服务费（${value}%）`
}

/** 取数失败提示（设计帧无该文案 → 占位，与序号 21 同口径） */
export const LOAD_FAIL_TEXT = '数据加载失败，请稍后重试'

/** 合计行文案（设计帧 cost 合计行） */
export const COST_TOTAL_LABEL = '合计'

/** 四宫格（设计帧 汇总1~4：底色 / 值色 / 标签，顺序与设计逐格一致） */
export const TILE_COLORS: Array<{ color: string; bg: string }> = [
  { color: '#1D4ED8', bg: '#EFF6FF' },
  { color: '#15803D', bg: '#ECFDF5' },
  { color: '#B45309', bg: '#FFF7ED' },
  { color: '#7C3AED', bg: '#FAF5FF' }
]

/** 模型占比条取色（设计帧 模型1~4 条填：#2563EB / #22C55E / #F59E0B / #94A3B8） */
export const MODEL_BAR_COLORS = ['#2563EB', '#22C55E', '#F59E0B', '#94A3B8']
/** 占比条轨道底色（设计帧 模型N条底 #F1F5F9） */
export const MODEL_BAR_TRACK = '#F1F5F9'

/* ------------------------------- 接口原始类型 ------------------------------- */

export interface UsageDailyRaw {
  stat_date?: string
  date?: string
  day?: string
  total_tokens?: number
  tokens?: number
}

export interface UsageModelShareRaw {
  model_name?: string
  name?: string
  share?: number
  percent?: number
  ratio?: number
  total_tokens?: number
  amount?: number
}

export interface UsageCostRaw {
  input?: number
  input_cost?: number
  prompt_cost?: number
  output?: number
  output_cost?: number
  completion_cost?: number
  platform_fee?: number
  service_fee?: number
  platform_fee_rate?: number
  fee_rate?: number
  total?: number
  total_cost?: number
}

export interface UsageOverviewRaw {
  month?: string
  request_count?: number
  total_tokens?: number
  tokens?: number
  amount_total?: number
  amount?: number
  cost_usd?: number
  mom_saved_amount?: number
  mom_saving?: number
  saved_amount?: number
  updated_at?: string
  refreshed_at?: string
  daily?: UsageDailyRaw[]
  models?: UsageModelShareRaw[]
  cost?: UsageCostRaw
  /* 扁平成本字段（无嵌套 cost 时的容错） */
  input_cost?: number
  output_cost?: number
  platform_fee?: number
  platform_fee_rate?: number
  total_cost?: number
}

/* --------------------------------- 工具 --------------------------------- */

function numOf(...values: unknown[]): number | undefined {
  for (const value of values) {
    if (typeof value === 'number' && !Number.isNaN(value)) return value
    if (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value))) return Number(value)
  }
  return undefined
}

function strOf(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === 'string' && value.trim() !== '') return value
  }
  return ''
}

function pad2(value: number): string {
  return String(value).padStart(2, '0')
}

/** 当前月（'YYYY-MM'）—— 月份口径由服务端给，缺失时才回退本机当前月 */
export function currentMonth(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}`
}

/** 月份标签：'2024-06' / '2024-6' → '2024-06'；非法值回退当前月（设计帧 pill 文案格式 YYYY-MM） */
export function formatMonthLabel(value?: string | null): string {
  const matched = typeof value === 'string' ? value.trim().match(/^(\d{4})-(\d{1,2})$/) : null
  if (!matched) return currentMonth()
  const month = Number(matched[2])
  if (month < 1 || month > 12) return currentMonth()
  return `${matched[1]}-${pad2(month)}`
}

/** 横轴标签：设计帧为 M-DD（6-08 … 6-14）；无法解析返回空串（不编造日期） */
export function dayLabel(value?: string | null): string {
  const matched = typeof value === 'string' ? value.trim().match(/^\d{4}-(\d{1,2})-(\d{1,2})/) : null
  if (!matched) return ''
  return `${Number(matched[1])}-${pad2(Number(matched[2]))}`
}

/**
 * 纵轴上限：取 {1, 2, 2.5, 5, 10} × 10^k 中 ≥ max 的最小值。
 * 设计帧 7 日峰值 1.92 亿 → 上限 2（按上限线性映射得到的折线 y 与设计帧 117.78..29.28 差 ≤0.2）。
 */
export function niceCeil(max: number): number {
  if (!(max > 0)) return 1
  const exponent = Math.floor(Math.log10(max))
  const base = Math.pow(10, exponent)
  for (const step of [1, 2, 2.5, 5, 10]) {
    if (max <= step * base) return step * base
  }
  return 10 * base
}

/* -------------------------------- 趋势图几何 -------------------------------- */

export interface TrendGeometry {
  width: number
  height: number
  left: number
  right: number
  top: number
  bottom: number
}

/** 设计帧趋势图几何（帧内坐标：绘图区 x 30..338 · 纵轴 y 25.28..129.69 · 图高 150） */
export const TREND_GEOMETRY: TrendGeometry = {
  width: 358,
  height: 150,
  left: 30,
  right: 338,
  top: 25.28,
  bottom: 129.69
}

export interface TrendPoint {
  x: number
  y: number
  value: number
}

/**
 * 序列 → 绘图坐标。x 在 [left, right] 上等距；y 按「值 / niceCeil(峰值)」线性映射到 [top, bottom]。
 * 值为 0 的点贴底线（保留，保证与横轴标签一一对应）；null/undefined/NaN 视为缺口跳过；
 * 无有效点或峰值 ≤ 0 → 返回空数组（不画线、不编造数字）。
 */
export function trendPoints(values: Array<number | null | undefined>, geometry: TrendGeometry = TREND_GEOMETRY): TrendPoint[] {
  const clean = values.filter((v): v is number => typeof v === 'number' && !Number.isNaN(v) && v >= 0)
  if (clean.length === 0) return []
  const peak = Math.max(...clean)
  if (!(peak > 0)) return []
  const axisMax = niceCeil(peak)
  const span = clean.length > 1 ? (geometry.right - geometry.left) / (clean.length - 1) : 0
  return clean.map((value, index) => ({
    x: geometry.left + span * index,
    y: geometry.bottom - (value / axisMax) * (geometry.bottom - geometry.top),
    value
  }))
}

function round2(value: number): number {
  return Math.round(value * 100) / 100
}

/**
 * 趋势图 SVG（design d952b5d4）：
 *   4 条横向网格线（前 3 条 #F1F5F9、末条 #E2E8F0）· 折线下方面积 rgba(191,219,254,0.35) ·
 *   折线 #2563EB 3px 圆角 · 数据点 r4 #2563EB（末点 r5 #1D4ED8）
 * ⚠️ mp-weixin 不支持内联 svg 标签 → 由 trendDataUri 编码成 data-URI 交给 <image>（同序号 6 雷达图）。
 */
export function usageTrendSvg(points: TrendPoint[], geometry: TrendGeometry = TREND_GEOMETRY): string {
  const grid = [0, 1, 2, 3]
    .map((index) => {
      const y = round2(geometry.top + ((geometry.bottom - geometry.top) / 3) * index)
      const color = index === 3 ? '#E2E8F0' : '#F1F5F9'
      return `<line x1="${geometry.left}" y1="${y}" x2="${geometry.right}" y2="${y}" stroke="${color}" stroke-width="1"/>`
    })
    .join('')
  if (points.length === 0) {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${geometry.width}" height="${geometry.height}" viewBox="0 0 ${geometry.width} ${geometry.height}">${grid}</svg>`
  }
  const coords = points.map((p) => `${round2(p.x)},${round2(p.y)}`)
  const area = `<polygon points="${coords.join(' ')} ${geometry.right},${geometry.bottom} ${points[0].x},${geometry.bottom}" fill="rgba(191,219,254,0.35)"/>`
  const line = `<polyline points="${coords.join(' ')}" fill="none" stroke="#2563EB" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`
  const dots = points
    .map((p, index) => {
      const last = index === points.length - 1
      return `<circle cx="${round2(p.x)}" cy="${round2(p.y)}" r="${last ? 5 : 4}" fill="${last ? '#1D4ED8' : '#2563EB'}"/>`
    })
    .join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${geometry.width}" height="${geometry.height}" viewBox="0 0 ${geometry.width} ${geometry.height}">${grid}${area}${line}${dots}</svg>`
}

/** 趋势图 data-URI（小程序屏上无法渲染内联 svg，只能走 <image src>） */
export function trendDataUri(points: TrendPoint[], geometry: TrendGeometry = TREND_GEOMETRY): string {
  return `data:image/svg+xml;base64,${base64Ascii(usageTrendSvg(points, geometry))}`
}

/* -------------------------------- 视图模型 -------------------------------- */

export interface UsageTile {
  key: 'requests' | 'tokens' | 'cost' | 'saved'
  label: string
  value: string
  color: string
  bg: string
}

export interface UsageModelRow {
  name: string
  percent: string
  /** 占比条填充百分比（0~100）—— 设计帧填充宽度取「百分比 × 卡片外层宽 398」而轨道宽 192（设计自身不自洽），实现按百分比 × 轨道宽 */
  barPercent: number
  barColor: string
}

export interface UsageCostRow {
  label: string
  value: string
}

export interface UsageTrendView {
  labels: string[]
  points: TrendPoint[]
  dataUri: string
  axisMax: number
  hasData: boolean
}

export interface UsageOverview {
  navTitle: string
  month: string
  summaryTitle: string
  tiles: UsageTile[]
  trendTitle: string
  trendLegend: string
  trend: UsageTrendView
  modelTitle: string
  modelRows: UsageModelRow[]
  costTitle: string
  costRows: UsageCostRow[]
  costTotal: { label: string; value: string; tone: 'primary' }
  detailText: string
  footerNote: string
  updatedText: string
}

/** 占比归一：服务端可能给 42（百分数）或 0.42（小数）→ 统一成 0~100 的整数 */
export function sharePercent(raw?: UsageModelShareRaw): number | null {
  const value = numOf(raw?.share, raw?.percent, raw?.ratio)
  if (value === undefined) return null
  const pct = Math.abs(value) <= 1 ? value * 100 : value
  return Math.max(0, Math.min(100, Math.round(pct)))
}

/**
 * 整页视图模型。
 * 关键口径（均记台账 missing-prd，不臆造）：
 *   · 费用 = amount_total / amount / cost_usd；「较上月节省」= mom_saved_amount / mom_saving / saved_amount
 *   · 逐日序列单位换算成「亿」（图例「Token（亿）」），纵轴按峰值取 nice 上限
 *   · 成本合计 = cost.total / total_cost / amount_total；三行明细缺失则渲染占位符
 *   · 平台服务费费率 = cost.platform_fee_rate / fee_rate，缺省用设计常量 8%
 */
export function buildUsageOverview(raw: UsageOverviewRaw = {}): UsageOverview {
  const totalTokens = numOf(raw.total_tokens, raw.tokens)
  const amount = numOf(raw.amount_total, raw.amount, raw.cost_usd)

  const tileValues: string[] = [
    formatCount(numOf(raw.request_count)),
    formatTokens(totalTokens),
    formatAmount(amount),
    formatAmount(numOf(raw.mom_saved_amount, raw.mom_saving, raw.saved_amount))
  ]
  const tileLabels = ['请求数', 'Token', '费用', '较上月节省']
  const tileKeys: UsageTile['key'][] = ['requests', 'tokens', 'cost', 'saved']
  const tiles: UsageTile[] = tileKeys.map((key, index) => ({
    key,
    label: tileLabels[index],
    value: tileValues[index],
    color: TILE_COLORS[index].color,
    bg: TILE_COLORS[index].bg
  }))

  const daily = Array.isArray(raw.daily) ? raw.daily : []
  const dailyValues = daily.map((item) => {
    const tokens = numOf(item?.total_tokens, item?.tokens)
    /* 逐日缺 token 字段 → 该日按 0 参与折线（仅用于几何，保证横轴标签与数据点一一对应），不影响上方汇总占位符口径 */
    return (tokens ?? 0) / 1e8
  })
  const points = trendPoints(dailyValues)
  const axisMax = points.length ? niceCeil(Math.max(...points.map((p) => p.value))) : 0
  const trend: UsageTrendView = {
    labels: daily.map((item) => dayLabel(strOf(item?.stat_date, item?.date, item?.day))),
    points,
    dataUri: trendDataUri(points),
    axisMax,
    hasData: points.length > 0
  }

  const modelRows: UsageModelRow[] = (Array.isArray(raw.models) ? raw.models : []).map((item, index) => {
    const pct = sharePercent(item)
    return {
      name: strOf(item?.model_name, item?.name),
      percent: pct === null ? PLACEHOLDER : formatPercent(pct),
      barPercent: pct ?? 0,
      barColor: MODEL_BAR_COLORS[Math.min(index, MODEL_BAR_COLORS.length - 1)]
    }
  })

  const cost = raw.cost ?? {}
  const inputCost = numOf(cost.input, cost.input_cost, cost.prompt_cost, raw.input_cost)
  const outputCost = numOf(cost.output, cost.output_cost, cost.completion_cost, raw.output_cost)
  const platformFee = numOf(cost.platform_fee, cost.service_fee, raw.platform_fee)
  const feeRate = numOf(cost.platform_fee_rate, cost.fee_rate, raw.platform_fee_rate)
  const costTotalValue =
    numOf(cost.total, cost.total_cost, raw.total_cost, raw.amount_total, raw.amount, raw.cost_usd) ??
    (inputCost !== undefined && outputCost !== undefined && platformFee !== undefined
      ? inputCost + outputCost + platformFee
      : undefined)

  return {
    navTitle: NAV_TITLE,
    month: formatMonthLabel(raw.month),
    summaryTitle: SUMMARY_TITLE,
    tiles,
    trendTitle: TREND_TITLE,
    trendLegend: TREND_LEGEND,
    trend,
    modelTitle: MODEL_TITLE,
    modelRows,
    costTitle: COST_TITLE,
    costRows: [
      { label: '输入 Token 成本', value: formatAmount(inputCost) },
      { label: '输出 Token 成本', value: formatAmount(outputCost) },
      { label: platformFeeLabel(feeRate), value: formatAmount(platformFee) }
    ],
    costTotal: { label: COST_TOTAL_LABEL, value: formatAmount(costTotalValue), tone: 'primary' },
    detailText: DETAIL_ENTRY_TEXT,
    footerNote: FOOTER_NOTE,
    updatedText: `${UPDATED_PREFIX}${strOf(raw.updated_at, raw.refreshed_at) || PLACEHOLDER}`
  }
}
