/**
 * 序号 22【工作台与我的】我的与用量概览（page-22-2）— 切片 3：页面结构与文案
 *
 * 设计真源：.calicat/raw/pages/page-22-2/design.tree.json（430 宽 · 设计总高 1138 · 无 TabBar）
 *   顶部导航「用量概览」17px + 月份选择「2024-06」
 *   本月汇总（请求数 1.24M / Token 3.86B / 费用 ¥12,860 / 较上月节省 ¥2,140）
 *   近 7 日用量趋势（图例 Token（亿）+ 横轴 6-08…6-14 + 折线 data-URI）
 *   模型用量分布（gpt-4o-mini 42% / claude-3-5-sonnet 31% / gpt-4o 21% / 其他 6%）
 *   成本构成（输入 ¥4,120 / 输出 ¥8,240 / 平台服务费（8%）¥500 / 合计 ¥12,860）
 *   明细入口「查看逐日 / 逐模型明细」· 底部说明两行
 * 接口真源：18-API「Usage」Tag → GET /api/v1/usage/summary（month 参数为 REST 推断，missing-prd）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UsagePage from '@/pages/usage/index.vue'
import { LOAD_FAIL_TEXT } from '@/utils/usage-model'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 与设计帧逐值对齐的一份响应（7 日 0.23~1.92 亿 · 4 个模型占比 · 成本三行 + 合计） */
const RAW = {
  month: '2024-06',
  request_count: 1_240_000,
  total_tokens: 3_860_000_000,
  amount_total: 12_860,
  mom_saved_amount: 2_140,
  updated_at: '2024-06-14 16:20',
  daily: [
    { stat_date: '2024-06-08', total_tokens: 23_000_000 },
    { stat_date: '2024-06-09', total_tokens: 65_000_000 },
    { stat_date: '2024-06-10', total_tokens: 50_000_000 },
    { stat_date: '2024-06-11', total_tokens: 110_000_000 },
    { stat_date: '2024-06-12', total_tokens: 137_000_000 },
    { stat_date: '2024-06-13', total_tokens: 164_000_000 },
    { stat_date: '2024-06-14', total_tokens: 192_000_000 }
  ],
  models: [
    { model_name: 'gpt-4o-mini', share: 42 },
    { model_name: 'claude-3-5-sonnet', share: 31 },
    { model_name: 'gpt-4o', share: 21 },
    { model_name: '其他', share: 6 }
  ],
  cost: { input: 4_120, output: 8_240, platform_fee: 500, platform_fee_rate: 8, total: 12_860 }
}

async function mountPage(raw: unknown = RAW) {
  pushResponse(ok(raw))
  const wrapper = mount(UsagePage)
  await flushPromises()
  return wrapper
}

const texts = (wrapper: ReturnType<typeof mount>, selector: string) =>
  wrapper.findAll(selector).map((el) => el.text())

const req = (index = 0) => getCalls('request')[index].args[0] as Record<string, unknown>

describe('序号 22 · 取数与顶部导航', () => {
  it('首屏只发一个只读 GET /api/v1/usage/summary（带月份维度）', async () => {
    await mountPage()
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    expect(req().url).toBe('/api/v1/usage/summary')
    expect(req().method).toBe('GET')
    expect((req().data as Record<string, unknown>).month).toMatch(/^\d{4}-\d{2}$/)
  })

  it('标题「用量概览」与月份胶囊（月份取服务端返回，设计帧 2024-06）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.usage').exists()).toBe(true)
    expect(wrapper.find('[data-testid="usage-title"]').text()).toBe('用量概览')
    expect(wrapper.find('[data-testid="month-value"]').text()).toBe('2024-06')
  })

  it('无月份返回时回落当前月（YYYY-MM）', async () => {
    const wrapper = await mountPage({ request_count: 1 })
    expect(wrapper.find('[data-testid="month-value"]').text()).toMatch(/^\d{4}-\d{2}$/)
  })
})

describe('序号 22 · 本月汇总四宫格', () => {
  it('卡片标题与四格文案逐字对齐设计帧', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="summary-title"]').text()).toBe('本月汇总')
    expect(texts(wrapper, '[data-testid="tile-label"]')).toEqual(['请求数', 'Token', '费用', '较上月节省'])
    expect(texts(wrapper, '[data-testid="tile-value"]')).toEqual(['1.24M', '3.86B', '¥12,860', '¥2,140'])
  })

  it('四格取色为行级数据驱动（内联样式可断）', async () => {
    const wrapper = await mountPage()
    const tiles = wrapper.findAll('[data-testid="tile"]')
    expect(tiles.map((t) => (t.element as HTMLElement).style.background)).toEqual([
      'rgb(239, 246, 255)',
      'rgb(236, 253, 245)',
      'rgb(255, 247, 237)',
      'rgb(250, 245, 255)'
    ])
    expect(wrapper.findAll('[data-testid="tile-value"]').map((t) => (t.element as HTMLElement).style.color)).toEqual([
      'rgb(29, 78, 216)',
      'rgb(21, 128, 61)',
      'rgb(180, 83, 9)',
      'rgb(124, 58, 237)'
    ])
  })
})

describe('序号 22 · 近 7 日用量趋势卡', () => {
  it('标题 / 图例 / 7 个横轴标签', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="trend-title"]').text()).toBe('近 7 日用量趋势')
    expect(wrapper.find('[data-testid="trend-legend"]').text()).toBe('Token（亿）')
    expect(texts(wrapper, '[data-testid="trend-label"]')).toEqual([
      '6-08',
      '6-09',
      '6-10',
      '6-11',
      '6-12',
      '6-13',
      '6-14'
    ])
  })

  it('折线以 SVG base64 data-URI 交给 <image>（mp-weixin 不支持内联 svg）', async () => {
    const wrapper = await mountPage()
    const chart = wrapper.find('[data-testid="trend-chart"]')
    expect(chart.exists()).toBe(true)
    expect(String(chart.attributes('src'))).toMatch(/^data:image\/svg\+xml;base64,/)
    expect(wrapper.find('[data-testid="trend-empty"]').exists()).toBe(false)
  })

  it('无逐日数据 → 不画线，图表区显示占位符', async () => {
    const wrapper = await mountPage({ month: '2024-06' })
    expect(wrapper.find('[data-testid="trend-empty"]').text()).toBe('—')
  })
})

describe('序号 22 · 模型用量分布卡', () => {
  it('4 行名称与百分比逐字对齐设计帧', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="model-title"]').text()).toBe('模型用量分布')
    expect(texts(wrapper, '[data-testid="model-name"]')).toEqual([
      'gpt-4o-mini',
      'claude-3-5-sonnet',
      'gpt-4o',
      '其他'
    ])
    expect(texts(wrapper, '[data-testid="model-percent"]')).toEqual(['42%', '31%', '21%', '6%'])
  })

  it('占比条填充宽度 = 百分比 × 轨道宽（设计自身不自洽已记台账）', async () => {
    const wrapper = await mountPage()
    const fills = wrapper.findAll('[data-testid="model-bar-fill"]')
    expect(fills.map((f) => (f.element as HTMLElement).style.width)).toEqual(['42%', '31%', '21%', '6%'])
    expect(fills.map((f) => (f.element as HTMLElement).style.background)).toEqual([
      'rgb(37, 99, 235)',
      'rgb(34, 197, 94)',
      'rgb(245, 158, 11)',
      'rgb(148, 163, 184)'
    ])
  })
})

describe('序号 22 · 成本构成卡', () => {
  it('三行成本项 + 合计行（合计取 cost.total）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="cost-title"]').text()).toBe('成本构成')
    expect(texts(wrapper, '[data-testid="cost-label"]')).toEqual([
      '输入 Token 成本',
      '输出 Token 成本',
      '平台服务费（8%）'
    ])
    expect(texts(wrapper, '[data-testid="cost-value"]')).toEqual(['¥4,120', '¥8,240', '¥500'])
    expect(wrapper.find('[data-testid="cost-total-label"]').text()).toBe('合计')
    expect(wrapper.find('[data-testid="cost-total-value"]').text()).toBe('¥12,860')
  })

  it('费率缺失时用设计帧常量 8%', async () => {
    const wrapper = await mountPage({ month: '2024-06', cost: { input: 1, output: 2, platform_fee: 3 } })
    expect(texts(wrapper, '[data-testid="cost-label"]')[2]).toBe('平台服务费（8%）')
  })
})

describe('序号 22 · 明细入口与底部说明', () => {
  it('入口文案与底部两行说明', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="detail-entry"]').text()).toContain('查看逐日 / 逐模型明细')
    expect(wrapper.find('[data-testid="footer-note"]').text()).toBe('数据每小时更新一次，最终以结算账单为准')
    expect(wrapper.find('[data-testid="footer-updated"]').text()).toBe('更新时间：2024-06-14 16:20')
  })

  it('只读页：无输入控件、无 TabBar', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('input').length).toBe(0)
    expect(wrapper.find('[data-testid="tab-工作台"]').exists()).toBe(false)
  })
})

describe('序号 22 · 取数失败', () => {
  it('接口失败 → 数值占位符 + 提示，不编造数字', async () => {
    setNextResponse({ statusCode: 200, data: { code: 'E-3001', message: '用量聚合未完成' } })
    const wrapper = mount(UsagePage)
    await flushPromises()
    expect(texts(wrapper, '[data-testid="tile-value"]')).toEqual(['—', '—', '—', '—'])
    const toast = getCalls('showToast')[0].args[0] as Record<string, unknown>
    expect(toast.title).toBe(LOAD_FAIL_TEXT)
  })
})
