/**
 * 页面 2【工作台与我的】工作台 · 方案B 数据台（浅色版）— 页面单测（序号 2 / page-2-b）
 *
 * 文案与结构真源：.calicat/raw/pages/page-2-b/design.tree.json（430 宽；顶部栏/收益总览卡/模型调用量卡/快捷入口卡/待办卡/底部TabBar）
 * 交互真源：interaction.json 为「不存在图层交互数据」→ 退 PRD 17-spec / 18-API
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkbenchPage from '@/pages/workbench/index.vue'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const PROFILE = { companyName: '云智科技有限公司', providerCode: 'P0001', status: 'ACTIVE' }

const SUMMARY = {
  request_count: 1_240_000,
  total_tokens: 3_860_000_000,
  prompt_tokens: 1_740_000_000,
  completion_tokens: 1_160_000_000,
  cache_read_tokens: 580_000_000,
  image_input_tokens: 150_000_000,
  audio_input_tokens: 230_000_000,
  video_input_tokens: 230_000_000,
  cache_hit_rate: 0.15,
  mom_rate: 0.125,
  models: [
    { model_name: 'gpt-4o-mini', request_count: 1_240_000, total_tokens: 1_740_000_000, amount: 54_200 },
    { model_name: 'claude-3-5-sonnet', request_count: 860_000, total_tokens: 1_160_000_000, amount: 39_800 },
    { model_name: 'gpt-4o', request_count: 420_000, total_tokens: 580_000_000, amount: 26_400 },
    { model_name: '其他模型', request_count: 80_000, total_tokens: 100_000_000, amount: 8_240 }
  ]
}

async function mountWorkbench() {
  pushResponse(ok(PROFILE))
  pushResponse(ok(SUMMARY))
  const wrapper = mount(WorkbenchPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

describe('页面 2 · 结构与设计稿一致', () => {
  it('顶部栏、两张数据卡、快捷入口、待办、TabBar 文案齐全', async () => {
    const wrapper = await mountWorkbench()
    const text = wrapper.text()
    for (const t of [
      '云智科技有限公司',
      '本月词元用量',
      '模型调用量',
      '按收入贡献排序',
      '待处理',
      '全部',
      '工作台'
    ]) {
      expect(text, `缺少文案：${t}`).toContain(t)
    }
  })

  it('顶部栏日期为「数据台 · YYYY-MM-DD」（design: 数据台 · 2024-06-14）', async () => {
    const wrapper = await mountWorkbench()
    expect(wrapper.text()).toMatch(/数据台 · \d{4}-\d{2}-\d{2}/)
  })

  it('环比标、环形图中心、图例 6 行、底行三指标文案逐条与设计稿一致', async () => {
    const wrapper = await mountWorkbench()
    const text = wrapper.text()
    for (const t of [
      '12.5%',
      '总词元',
      '输入词元',
      '输出词元',
      '缓存命中',
      '图片',
      '音频',
      '视频',
      /* 决策 D3：百分比由接口数值按「最大余数法 + 分母 max(total, Σ六类)」算出，
         设计稿的 45/30/15（合计 106%）只作视觉参考，不再逐字照抄 */
      '42% · 1.74B',
      '28% · 1.16B',
      '14% · 0.58B',
      '4% · 0.15B',
      '6% · 0.23B',
      '调用请求',
      'Token',
      '缓存命中率',
      '15%'
    ]) {
      expect(text, `缺少文案：${t}`).toContain(t)
    }
  })

  it('模型调用量卡 4 行（序号/名称/金额/调用量·占比）与底行合计', async () => {
    const wrapper = await mountWorkbench()
    const text = wrapper.text()
    for (const t of [
      'gpt-4o-mini',
      '¥54,200',
      '1.24M · 42%',
      'claude-3-5-sonnet',
      '¥39,800',
      '0.86M · 31%',
      'gpt-4o',
      '¥26,400',
      '0.42M · 21%',
      '其他模型',
      '¥8,240',
      '0.08M · 6%',
      '合计 ¥128,640 · 4 个模型',
      '明细'
    ]) {
      expect(text, `缺少文案：${t}`).toContain(t)
    }
  })

  it('快捷入口 4 个（D2 删「钱包」后）、待办 2 条、底部 TabBar 4 个', async () => {
    const wrapper = await mountWorkbench()
    expect(wrapper.findAll('.quick__item')).toHaveLength(4)
    expect(wrapper.findAll('.todo')).toHaveLength(2)
    expect(wrapper.findAll('.tabbar__item')).toHaveLength(4)
    expect(wrapper.find('.tabbar__label--active').text()).toContain('工作台')
  })

  it('待办两条文案与设计稿一致（含全角括号）', async () => {
    const wrapper = await mountWorkbench()
    const text = wrapper.text()
    expect(text).toContain('合同待签署（06-20 前）')
    expect(text).toContain('1 条报价单被驳回')
  })
})

describe('页面 2 · 数据来自接口', () => {
  it('挂载即请求 /provider/profile 与 /api/v1/usage/summary', async () => {
    await mountWorkbench()
    const urls = getCalls('request').map((c) => (c.args[0] as Record<string, unknown>).url)
    expect(urls).toEqual(['/api/v1/provider/profile', '/api/v1/usage/summary'])
  })

  it('数字全部来自接口响应（不硬编码设计稿数字）', async () => {
    pushResponse(ok(PROFILE))
    pushResponse(
      ok({
        request_count: 2_000_000,
        total_tokens: 1_000_000_000,
        prompt_tokens: 500_000_000,
        completion_tokens: 300_000_000,
        cache_read_tokens: 100_000_000,
        mom_rate: -0.05,
        cache_hit_rate: 0.1,
        models: [{ model_name: 'unit-model', request_count: 2_000_000, total_tokens: 1_000_000_000, amount: 1_000 }]
      })
    )
    const wrapper = mount(WorkbenchPage)
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('1.00B')
    expect(text).toContain('2.00M')
    expect(text).toContain('unit-model')
    expect(text).toContain('¥1,000')
    expect(text).not.toContain('3.86B')
    expect(text).not.toContain('gpt-4o-mini')
  })

  it('模型数为 1 时合计文案为「合计 ¥1,000 · 1 个模型」', async () => {
    pushResponse(ok(PROFILE))
    pushResponse(
      ok({
        request_count: 10,
        total_tokens: 100,
        prompt_tokens: 100,
        completion_tokens: 0,
        cache_read_tokens: 0,
        models: [{ model_name: 'only', request_count: 10, total_tokens: 100, amount: 1_000 }]
      })
    )
    const wrapper = mount(WorkbenchPage)
    await flushPromises()
    expect(wrapper.text()).toContain('合计 ¥1,000 · 1 个模型')
  })
})

describe('页面 2 · 图例百分比统一口径（决策 D3）', () => {
  /** 解析 .ring 的 conic-gradient 各段（颜色 + 宽度百分比） */
  function ringStops(wrapper: ReturnType<typeof mount>) {
    const style = wrapper.find('.ring').attributes('style') ?? ''
    const re = /(#[0-9a-f]{6})\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%/g
    const out: Array<{ color: string; width: number; from: number; to: number }> = []
    let m: RegExpExecArray | null
    while ((m = re.exec(style)) !== null) {
      out.push({ color: m[1], width: Number(m[3]) - Number(m[2]), from: Number(m[2]), to: Number(m[3]) })
    }
    return out
  }

  function legendPercents(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll('.legend__value').map((w) => Number.parseInt(w.text(), 10))
  }

  it('环形图分段 = 图例整数百分比（同分母同一份计算，视觉与数字永不打架）', async () => {
    const wrapper = await mountWorkbench()
    const stops = ringStops(wrapper)
    const legend = legendPercents(wrapper)
    expect(legend).toEqual([42, 28, 14, 4, 6, 6])
    expect(stops.map((s) => s.width)).toEqual(legend)
    expect(stops.map((s) => s.color)).toEqual(['#1d4ed8', '#3b82f6', '#16a34a', '#5856d6', '#f59e0b', '#af52de'])
    /* 逐段首尾相接：第 i 段 from = 前 i 段之和，最后一段收在 100% */
    let cursor = 0
    for (const s of stops) {
      expect(s.from).toBe(cursor)
      cursor = s.to
    }
    expect(cursor).toBe(100)
    expect(stops.reduce((sum, s) => sum + s.width, 0)).toBeLessThanOrEqual(100)
  })

  it('接口只给总量、六类全缺 → 六行图例全占位符，环形图退轨道色（不画 0% 的假环）', async () => {
    pushResponse(ok(PROFILE))
    pushResponse(ok({ request_count: 1_000, total_tokens: 3_860_000_000 }))
    const wrapper = mount(WorkbenchPage)
    await flushPromises()
    expect(wrapper.findAll('.legend__value').map((w) => w.text())).toEqual(['—', '—', '—', '—', '—', '—'])
    /* jsdom 会把 inline style 归一化为 rgb() 形式，色值仍是设计稿轨道色 #f1f5f9 */
    expect(wrapper.find('.ring').attributes('style')).toContain('rgb(241, 245, 249)')
    expect(ringStops(wrapper)).toHaveLength(0)
  })
})

describe('页面 2 · 交互（分类见台账）', () => {
  it('快捷入口仅 4 项：评测/报价/合同/明细各自跳转（「钱包」按决策 D2 整项删除）', async () => {
    const wrapper = await mountWorkbench()
    /* aap-decisions.md D2（用户 2026-09-16 拍板）：设计画布无「钱包」页 → 快捷入口里这一项整项删除，
       不是改成 toast、也不是隐藏；同时模板里不应再出现「钱包」二字。 */
    expect(wrapper.findAll('[data-testid^="quick-"]').map((w) => w.attributes('data-testid'))).toEqual([
      'quick-评测',
      'quick-报价',
      'quick-合同',
      'quick-明细'
    ])
    expect(wrapper.text()).not.toContain('钱包')
    const cases: Array<[string, string]> = [
      ['quick-评测', '/pages/credentials/index'],
      ['quick-报价', '/pages/quotes/index'],
      ['quick-合同', '/pages/contract/index'],
      ['quick-明细', '/pages/usage/index']
    ]
    for (const [testid, url] of cases) {
      await tap(wrapper, testid)
      const nav = getCalls('navigateTo').at(-1)
      expect((nav?.args[0] as Record<string, unknown>).url, `${testid} 应跳转 ${url}`).toBe(url)
    }
  })

  it('「钱包」入口被删干净：节点不存在、文案里也没有「钱包」、无任何 toast', async () => {
    const wrapper = await mountWorkbench()
    expect(wrapper.find('[data-testid="quick-钱包"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid^="quick-"]')).toHaveLength(4)
    expect(wrapper.text()).not.toContain('钱包')
    expect(getCalls('showToast')).toHaveLength(0)
  })

  it('模型卡「明细」跳转用量概览；待办「全部」跳转消息；两条待办各自跳转', async () => {
    const wrapper = await mountWorkbench()
    const cases: Array<[string, string]> = [
      ['model-detail', '/pages/usage/index'],
      ['todo-all', '/pages/messages/index'],
      ['todo-合同待签署（06-20 前）', '/pages/contract/index'],
      ['todo-1 条报价单被驳回', '/pages/quotes/index']
    ]
    for (const [testid, url] of cases) {
      await tap(wrapper, testid)
      const nav = getCalls('navigateTo').at(-1)
      expect((nav?.args[0] as Record<string, unknown>).url, `${testid} 应跳转 ${url}`).toBe(url)
    }
  })

  it('底部 TabBar 点击：报告→报告页、报价→报价单列表、我的→我的', async () => {
    const wrapper = await mountWorkbench()
    const cases: Array<[string, string]> = [
      ['tab-报告', '/pages/report/index'],
      ['tab-报价', '/pages/quotes/index'],
      ['tab-我的', '/pages/mine/index']
    ]
    for (const [testid, url] of cases) {
      await tap(wrapper, testid)
      const nav = getCalls('navigateTo').at(-1)
      expect((nav?.args[0] as Record<string, unknown>).url).toBe(url)
    }
  })

  it('点击当前 Tab（工作台）不跳转', async () => {
    const wrapper = await mountWorkbench()
    const before = getCalls('navigateTo').length
    await tap(wrapper, 'tab-工作台')
    expect(getCalls('navigateTo').length).toBe(before)
  })
})

describe('页面 2 · 失败与非happy-path', () => {
  it('用量接口失败 → 提示 + 页面骨架保留 + 数值占位（不显示假数字）', async () => {
    pushResponse(ok(PROFILE))
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    const wrapper = mount(WorkbenchPage)
    await flushPromises()
    const text = wrapper.text()
    expect(getCalls('showToast').length).toBeGreaterThan(0)
    expect(text).toContain('本月词元用量')
    expect(text).toContain('云智科技有限公司')
    expect(text).not.toContain('3.86B')
  })

  it('无模型数据 → 模型卡显示空态文案，仍显示合计占位', async () => {
    pushResponse(ok(PROFILE))
    pushResponse(ok({ request_count: 0, total_tokens: 0, models: [] }))
    const wrapper = mount(WorkbenchPage)
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('暂无模型调用数据')
    expect(text).toContain('合计 —')
  })
})
