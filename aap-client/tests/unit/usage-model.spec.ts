/**
 * 序号 22【工作台与我的】我的与用量概览（page-22-2 / /pages/usage/index）— 切片 1：视图模型（纯函数）
 *
 * 设计真源：.calicat/raw/pages/page-22-2/design.tree.json（430 宽 · 设计总高 1138 · 无 TabBar）
 *   顶部导航 0..96（「用量概览」17px Bold + 月份选择 pill h30 r10 #F1F5F9「2024-06」）
 *   本月汇总卡 108..336（标题 14px + 四宫格 72×2 行，gap 9，行距 8）
 *   近 7 日用量趋势卡 348..570（标题行 20 + 图例「Token（亿）」+ 图 150）
 *   模型用量分布卡 582..766（4 行 h18，行距 12：名称 131 + 轨道 h10 + 百分比）
 *   成本构成卡 778..985（成本项 3 行 h18 + 合计行 h41 r10 #F8FAFC）
 *   明细入口卡 997..1057（图标 18px + 13px 文案 + chevron）
 *   底部说明 1057..1138（11px 两行，padding 24/0/24/0）
 * 接口真源：18-API「Usage」Tag（GET /usage/summary，前缀 /api/v1）；字段级 schema 未定义 → missing-prd。
 */
import { describe, expect, it } from 'vitest'
import {
  COST_TITLE,
  DETAIL_ENTRY_TEXT,
  FOOTER_NOTE,
  MODEL_TITLE,
  NAV_TITLE,
  PLATFORM_FEE_RATE_DEFAULT,
  SUMMARY_TITLE,
  TREND_GEOMETRY,
  TREND_LEGEND,
  TREND_TITLE,
  UPDATED_PREFIX,
  buildUsageOverview,
  dayLabel,
  formatMonthLabel,
  niceCeil,
  platformFeeLabel,
  trendDataUri,
  trendPoints,
  usageTrendSvg,
  type UsageOverviewRaw
} from '@/utils/usage-model'
import { PLACEHOLDER } from '@/utils/format'

/** 与设计帧逐值对齐的响应（7 日 0.23~1.92 亿 → 设计帧折线 y 坐标 117.78..29.28） */
const RAW: UsageOverviewRaw = {
  month: '2024-06',
  request_count: 1240000,
  total_tokens: 3860000000,
  amount_total: 12860,
  mom_saved_amount: 2140,
  updated_at: '2024-06-14 16:20',
  daily: [
    { stat_date: '2024-06-08', total_tokens: 23000000 },
    { stat_date: '2024-06-09', total_tokens: 65000000 },
    { stat_date: '2024-06-10', total_tokens: 50000000 },
    { stat_date: '2024-06-11', total_tokens: 110000000 },
    { stat_date: '2024-06-12', total_tokens: 137000000 },
    { stat_date: '2024-06-13', total_tokens: 164000000 },
    { stat_date: '2024-06-14', total_tokens: 192000000 }
  ],
  models: [
    { model_name: 'gpt-4o-mini', share: 42 },
    { model_name: 'claude-3-5-sonnet', share: 31 },
    { model_name: 'gpt-4o', share: 21 },
    { model_name: '其他', share: 6 }
  ],
  cost: { input: 4120, output: 8240, platform_fee: 500, platform_fee_rate: 8, total: 12860 }
}

describe('序号 22 · 设计文案常量（逐字来自设计帧，不得改写）', () => {
  it.each([
    [NAV_TITLE, '用量概览'],
    [SUMMARY_TITLE, '本月汇总'],
    [TREND_TITLE, '近 7 日用量趋势'],
    [TREND_LEGEND, 'Token（亿）'],
    [MODEL_TITLE, '模型用量分布'],
    [COST_TITLE, '成本构成'],
    [DETAIL_ENTRY_TEXT, '查看逐日 / 逐模型明细'],
    [FOOTER_NOTE, '数据每小时更新一次，最终以结算账单为准'],
    [UPDATED_PREFIX, '更新时间：']
  ])('%s', (actual, expected) => {
    expect(actual).toBe(expected)
  })
})

describe('序号 22 · 月份 / 日期标签', () => {
  it('formatMonthLabel：YYYY-MM 原样，非法值回退当前月', () => {
    expect(formatMonthLabel('2024-06')).toBe('2024-06')
    expect(formatMonthLabel('2024-6')).toBe('2024-06')
    expect(formatMonthLabel('')).toMatch(/^\d{4}-\d{2}$/)
    expect(formatMonthLabel(null)).toMatch(/^\d{4}-\d{2}$/)
  })

  it('dayLabel：设计帧横轴为 M-DD（6-08 … 6-14），个位日补零', () => {
    expect(dayLabel('2024-06-08')).toBe('6-08')
    expect(dayLabel('2024-06-14')).toBe('6-14')
  })
})

describe('序号 22 · 近 7 日趋势几何（设计帧 plot x 30..338 · y 25.28..129.69 · 图高 150）', () => {
  it('几何常量取自设计帧', () => {
    expect(TREND_GEOMETRY).toEqual({ width: 358, height: 150, left: 30, right: 338, top: 25.28, bottom: 129.69 })
  })

  it('niceCeil：取 {1,2,2.5,5,10}×10^k 中 ≥ max 的最小值', () => {
    expect(niceCeil(1.92)).toBe(2)
    expect(niceCeil(2.4)).toBe(2.5)
    expect(niceCeil(3)).toBe(5)
    expect(niceCeil(12)).toBe(20)
    expect(niceCeil(0.6)).toBe(1)
    expect(niceCeil(1)).toBe(1)
    expect(niceCeil(0)).toBe(1)
  })

  it('trendPoints：首末点贴 plot 左右边界，y 按「值/轴上限」线性映射', () => {
    const values = RAW.daily!.map((d) => (d.total_tokens as number) / 1e8)
    const points = trendPoints(values)
    expect(points.length).toBe(7)
    expect(points[0].x).toBeCloseTo(30, 5)
    expect(points[6].x).toBeCloseTo(338, 5)
    // 纵轴上限 = niceCeil(1.92) = 2 亿 → 末点 y = 129.69 − 0.96×104.41 = 29.46（设计帧 29.28）
    expect(points[6].y).toBeCloseTo(29.46, 2)
    expect(points[0].y).toBeCloseTo(117.68, 2)
    expect(Math.max(...points.map((p) => p.y))).toBeLessThanOrEqual(TREND_GEOMETRY.bottom)
    expect(Math.min(...points.map((p) => p.y))).toBeGreaterThanOrEqual(TREND_GEOMETRY.top)
    // 单调递增的序列 → y 单调下降
    expect(points[0].y).toBeGreaterThan(points[6].y)
  })

  it('trendPoints：值 0 贴底线、值 = 轴上限贴顶线', () => {
    const points = trendPoints([0, 2])
    expect(points.length).toBe(2)
    expect(points[0].y).toBeCloseTo(TREND_GEOMETRY.bottom, 5)
    expect(points[1].y).toBeCloseTo(TREND_GEOMETRY.top, 5)
  })

  it('trendPoints：空序列 / 全 0 → 无点（不画线，不编造数字）', () => {
    expect(trendPoints([])).toEqual([])
    expect(trendPoints([0, 0, 0])).toEqual([])
  })

  it('usageTrendSvg：4 条横向网格线（末条 #E2E8F0）+ 面积 + 折线 + 末点加大 #1D4ED8', () => {
    const values = RAW.daily!.map((d) => (d.total_tokens as number) / 1e8)
    const svg = usageTrendSvg(trendPoints(values))
    expect(svg).toContain('viewBox="0 0 358 150"')
    expect(svg.match(/<line /g)?.length).toBe(4)
    expect(svg).toContain('stroke="#F1F5F9"')
    expect(svg).toContain('stroke="#E2E8F0"')
    expect(svg).toContain('<polygon')
    expect(svg).toContain('rgba(191,219,254,0.35)')
    expect(svg).toContain('<polyline')
    expect(svg).toContain('stroke="#2563EB"')
    expect(svg.match(/<circle /g)?.length).toBe(7)
    expect(svg).toContain('r="5" fill="#1D4ED8"')
  })

  it('trendDataUri：base64 data-URI（mp-weixin 不能渲染内联 svg，只能交给 <image>）', () => {
    const uri = trendDataUri(trendPoints([0.23, 1.92]))
    expect(uri.startsWith('data:image/svg+xml;base64,')).toBe(true)
    expect(uri.length).toBeGreaterThan(64)
  })
})

describe('序号 22 · 平台服务费标签', () => {
  it('费率取自服务端，缺省用设计帧常量 8%', () => {
    expect(platformFeeLabel(8)).toBe('平台服务费（8%）')
    expect(platformFeeLabel(5)).toBe('平台服务费（5%）')
    expect(platformFeeLabel(undefined)).toBe(`平台服务费（${PLATFORM_FEE_RATE_DEFAULT}%）`)
    expect(PLATFORM_FEE_RATE_DEFAULT).toBe(8)
  })
})

describe('序号 22 · 整页视图模型', () => {
  const model = buildUsageOverview(RAW)

  it('顶部：标题与月份', () => {
    expect(model.navTitle).toBe('用量概览')
    expect(model.month).toBe('2024-06')
  })

  it('本月汇总四宫格：值/标签/取色逐值来自设计帧', () => {
    expect(model.tiles).toEqual([
      { key: 'requests', label: '请求数', value: '1.24M', color: '#1D4ED8', bg: '#EFF6FF' },
      { key: 'tokens', label: 'Token', value: '3.86B', color: '#15803D', bg: '#ECFDF5' },
      { key: 'cost', label: '费用', value: '¥12,860', color: '#B45309', bg: '#FFF7ED' },
      { key: 'saved', label: '较上月节省', value: '¥2,140', color: '#7C3AED', bg: '#FAF5FF' }
    ])
    expect(model.summaryTitle).toBe('本月汇总')
  })

  it('趋势卡：7 个横轴标签 + data-URI + 图例', () => {
    expect(model.trend.labels).toEqual(['6-08', '6-09', '6-10', '6-11', '6-12', '6-13', '6-14'])
    expect(model.trend.hasData).toBe(true)
    expect(model.trend.dataUri.startsWith('data:image/svg+xml;base64,')).toBe(true)
    expect(model.trendLegend).toBe('Token（亿）')
  })

  it('模型用量分布：名称/百分比/条色逐值来自设计帧（条长 = 百分比 × 轨道宽）', () => {
    expect(model.modelRows).toEqual([
      { name: 'gpt-4o-mini', percent: '42%', barPercent: 42, barColor: '#2563EB' },
      { name: 'claude-3-5-sonnet', percent: '31%', barPercent: 31, barColor: '#22C55E' },
      { name: 'gpt-4o', percent: '21%', barPercent: 21, barColor: '#F59E0B' },
      { name: '其他', percent: '6%', barPercent: 6, barColor: '#94A3B8' }
    ])
  })

  it('成本构成：三行成本项 + 合计行（合计值 14px ExtraBold 蓝）', () => {
    expect(model.costRows).toEqual([
      { label: '输入 Token 成本', value: '¥4,120' },
      { label: '输出 Token 成本', value: '¥8,240' },
      { label: '平台服务费（8%）', value: '¥500' }
    ])
    expect(model.costTotal).toEqual({ label: '合计', value: '¥12,860', tone: 'primary' })
  })

  it('底部说明：固定说明 + 更新时间（取自服务端，缺失渲染占位符）', () => {
    expect(model.footerNote).toBe('数据每小时更新一次，最终以结算账单为准')
    expect(model.updatedText).toBe('更新时间：2024-06-14 16:20')
    expect(buildUsageOverview({}).updatedText).toBe(`更新时间：${PLACEHOLDER}`)
  })

  it('字段缺失一律渲染占位符，不编造 0', () => {
    const empty = buildUsageOverview({})
    expect(empty.tiles.map((t) => t.value)).toEqual([PLACEHOLDER, PLACEHOLDER, PLACEHOLDER, PLACEHOLDER])
    expect(empty.trend.hasData).toBe(false)
    expect(empty.modelRows).toEqual([])
    expect(empty.costTotal.value).toBe(PLACEHOLDER)
  })

  it('字段别名容错：stat_date/tokens、model_name/name、cost 扁平化', () => {
    const alt = buildUsageOverview({
      month: '2024-07',
      request_count: 20000,
      tokens: 1000000000,
      amount: 500,
      mom_saving: 100,
      updated_at: '2024-07-01 08:00',
      daily: [{ day: '2024-07-01', tokens: 100000000 }],
      models: [
        { name: 'gpt-4o-mini', percent: 80 },
        { name: 'gpt-4o', percent: 20 }
      ],
      input_cost: 200,
      output_cost: 250,
      platform_fee: 50,
      total_cost: 500
    })
    expect(alt.month).toBe('2024-07')
    expect(alt.tiles[0].value).toBe('0.02M')
    expect(alt.trend.labels).toEqual(['7-01'])
    expect(alt.modelRows.map((r) => r.name)).toEqual(['gpt-4o-mini', 'gpt-4o'])
    expect(alt.costRows.map((r) => r.value)).toEqual(['¥200', '¥250', '¥50'])
    expect(alt.costTotal.value).toBe('¥500')
    expect(alt.updatedText).toBe('更新时间：2024-07-01 08:00')
  })
})
