/**
 * 序号 12【报价管理】报价预览与提交 2（page-12-2）— 页面单测（TDD 切片 3，先红）
 *
 * 文案真源：.calicat/raw/pages/page-12-2/design.tree.json（430 宽 · 设计总高 1027 · 无 TabBar）
 *   断言里的中文**手抄自设计树**（不引用实现常量，避免自证）：
 *     报价预览 / 返回编辑 / 提交报价 / 我确认以上价格真实有效，并同意《报价服务条款》
 *     提交后进入运营审核，审核通过将自动编译计费表达式并同步渠道。
 *     时段价 + 阶梯价 / 阶梯价 / 仅基础价 / 输入 / 输出 / 缓存读 / 缓存写
 *     ¥1.2 ¥3.6 ¥0.6 / ¥2.0 ¥8.0 ¥0.2 / ¥4.0 ¥12.0 ¥5.0
 *     高峰 09:00–12:00 / 18:00–22:00 上浮 1.2 倍，其余时段 0.85 倍 / 3 档阶梯：0–100万 / 100–500万 / 500万以上
 *     3 档阶梯已启用，末档覆盖至不限量 / 请求规则计费：命中条件时按倍率计费，多条命中相乘
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/17-spec/18-API + 设计稿控件语义
 *   分类：返回/返回编辑 = navigation(navigateBack) · 提交报价 = api(POST /quotes/{id}/submit) ·
 *         确认勾选框 = client-only（提交门禁；未勾选拦截且不发请求）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuotePreviewPage from '@/pages/quote-preview/index.vue'
import { getCalls, pushResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 设计稿样例（三个模型 + 各自规则；文案与数值逐值抄自 design.tree.json） */
const DETAIL = {
  quote_id: 'q7',
  quote_no: 'Q20240614000007',
  status: 'DRAFT',
  items: [
    {
      item_id: 'qi1',
      model_name: 'gpt-4o-mini',
      input_price: 1.2,
      output_price: 3.6,
      cache_read_price: 0.6,
      price_time_rules: {
        tz: 'Asia/Shanghai',
        peak_ranges: [
          { start: '09:00', end: '12:00' },
          { start: '18:00', end: '22:00' }
        ],
        peak_multiplier: 1.2,
        offpeak_multiplier: 0.85
      },
      price_tier_rules: {
        tier_field: 'len',
        tiers: [
          { min: 0, max: 1000000, label: '0–100万' },
          { min: 1000000, max: 5000000, label: '100–500万' },
          { min: 5000000, max: null, label: '500万以上' }
        ]
      },
      request_rules: [{ multiplier: 6 }]
    },
    {
      item_id: 'qi2',
      model_name: 'claude-3-5-sonnet',
      input_price: 2,
      output_price: 8,
      cache_read_price: 0.2,
      price_tier_rules: {
        tier_field: 'len',
        tiers: [{ min: 0, max: null }, { min: 0, max: null }, { min: 0, max: null }]
      },
      request_rules: [{ multiplier: 2 }]
    },
    {
      item_id: 'qi3',
      model_name: 'gpt-4o',
      input_price: 4,
      output_price: 12,
      cache_write_price: 5,
      request_rules: [{ multiplier: 6 }]
    }
  ]
}

async function mountPage(detail: unknown = DETAIL) {
  storage.set('aap_quote_id', 'q7')
  pushResponse(ok(detail))
  const wrapper = mount(QuotePreviewPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

function requests() {
  return getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
}

function submitRequests() {
  return requests().filter((r) => String(r.url).endsWith('/submit'))
}

function toasts() {
  return getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
}

function texts(wrapper: ReturnType<typeof mount>, testid: string) {
  return wrapper.findAll(`[data-testid="${testid}"]`).map((n) => n.text())
}

describe('序号 12 · 结构与设计稿文案一致', () => {
  it('顶部导航只有「报价预览」（设计稿无副标题）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="nav-title"]').text()).toBe('报价预览')
    expect(wrapper.text()).not.toContain('模型定价')
  })

  it('三张模型卡按设计顺序渲染', async () => {
    const wrapper = await mountPage()
    expect(texts(wrapper, 'model-name')).toEqual(['gpt-4o-mini', 'claude-3-5-sonnet', 'gpt-4o'])
  })

  it('右上角标签文案与配色（蓝 / 绿 / 灰）', async () => {
    const wrapper = await mountPage()
    expect(texts(wrapper, 'model-tag')).toEqual(['时段价 + 阶梯价', '阶梯价', '仅基础价'])
    expect(
      wrapper.findAll('[data-testid="model-tag"]').map((n) => n.attributes('data-tone'))
    ).toEqual(['primary', 'success', 'neutral'])
  })

  it('每张卡三列价格：标签与数值与设计稿逐值一致', async () => {
    const wrapper = await mountPage()
    expect(texts(wrapper, 'price-label')).toEqual([
      '输入',
      '输出',
      '缓存读',
      '输入',
      '输出',
      '缓存读',
      '输入',
      '输出',
      '缓存写'
    ])
    expect(texts(wrapper, 'price-value')).toEqual([
      '¥1.2',
      '¥3.6',
      '¥0.6',
      '¥2.0',
      '¥8.0',
      '¥0.2',
      '¥4.0',
      '¥12.0',
      '¥5.0'
    ])
  })

  it('规则行：卡1 三行 / 卡2 两行 / 卡3 一行，文案逐字与设计稿一致', async () => {
    const wrapper = await mountPage()
    expect(texts(wrapper, 'rule-line')).toEqual([
      '高峰 09:00–12:00 / 18:00–22:00 上浮 1.2 倍，其余时段 0.85 倍',
      '3 档阶梯：0–100万 / 100–500万 / 500万以上',
      '请求规则计费：命中条件时按倍率计费，多条命中相乘',
      '3 档阶梯已启用，末档覆盖至不限量',
      '请求规则计费：命中条件时按倍率计费，多条命中相乘',
      '请求规则计费：命中条件时按倍率计费，多条命中相乘'
    ])
  })

  it('确认行与黄色提示条文案逐字一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="confirm-text"]').text()).toBe(
      '我确认以上价格真实有效，并同意《报价服务条款》'
    )
    expect(wrapper.find('[data-testid="submit-hint"]').text()).toBe(
      '提交后进入运营审核，审核通过将自动编译计费表达式并同步渠道。'
    )
  })

  it('确认勾选框默认已勾选（设计稿为蓝底白勾）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="confirm-check"]').attributes('data-checked')).toBe('true')
  })

  it('底部操作条：返回编辑 + 提交报价', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="btn-back-edit"]').text()).toContain('返回编辑')
    expect(wrapper.find('[data-testid="btn-submit"]').text()).toContain('提交报价')
  })

  it('进入页面即取报价单详情 → GET /api/v1/quotes/q7', async () => {
    await mountPage()
    expect(requests().map((r) => [r.method, r.url])).toEqual([['GET', '/api/v1/quotes/q7']])
  })
})

describe('序号 12 · 交互：确认门禁与提交', () => {
  it('勾选框可切换：已勾选 → 取消勾选 → 再勾选', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'confirm-check')
    expect(wrapper.find('[data-testid="confirm-check"]').attributes('data-checked')).toBe('false')
    await tap(wrapper, 'confirm-check')
    expect(wrapper.find('[data-testid="confirm-check"]').attributes('data-checked')).toBe('true')
  })

  it('未勾选确认时点「提交报价」→ 仅提示，不发提交请求', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'confirm-check')
    await tap(wrapper, 'btn-submit')
    expect(toasts()).toEqual(['请先确认报价条款'])
    expect(submitRequests()).toEqual([])
  })

  it('已确认时点「提交报价」→ POST /api/v1/quotes/q7/submit（不带请求体）→ 提示已提交并跳列表', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ quote_id: 'q7', status: 'SUBMITTED' }))
    await tap(wrapper, 'btn-submit')
    const submit = submitRequests()
    expect(submit).toHaveLength(1)
    expect(submit[0].method).toBe('POST')
    expect(submit[0].data).toBeUndefined()
    expect(toasts()).toEqual(['已提交审核'])
    const nav = getCalls('navigateTo').map((c) => String((c.args[0] as Record<string, unknown>).url))
    expect(nav).toEqual(['/pages/quotes/index'])
  })

  it('服务端拒绝（E-1601 状态非法流转）→ 透传 message，不跳转', async () => {
    const wrapper = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-1601', message: '状态非法流转', data: null } })
    await tap(wrapper, 'btn-submit')
    expect(toasts()).toEqual(['状态非法流转'])
    expect(getCalls('navigateTo')).toEqual([])
  })

  it('没有明细行时点「提交报价」→ 拦截且不发请求', async () => {
    const wrapper = await mountPage({ quote_id: 'q7', status: 'DRAFT', items: [] })
    await tap(wrapper, 'btn-submit')
    expect(toasts()).toEqual(['暂无模型报价，无法提交'])
    expect(submitRequests()).toEqual([])
  })

  it('「返回编辑」与顶栏返回都走 navigateBack（不臆造前一页路由）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'btn-back-edit')
    await tap(wrapper, 'nav-back')
    expect(getCalls('navigateBack')).toHaveLength(2)
  })

  it('取数失败 → 透传服务端 message', async () => {
    storage.set('aap_quote_id', 'q7')
    pushResponse({ statusCode: 200, data: { code: 'E-1001', message: '参数校验失败', data: null } })
    mount(QuotePreviewPage)
    await flushPromises()
    expect(toasts()).toEqual(['参数校验失败'])
  })
})

describe('序号 12 · 设计骨架类（430 宽 DOM 实测口径 / 设计 PNG 佐证）', () => {
  /* 设计稿逐卡不同，不静默统一：
       · 卡1（39fed800）只有 effects drop_shadow(0,6,20,rgba(15,23,42,.06))，**未声明 stroke**
       · 卡2/卡3/确认卡 stroke{align:center,thickness:1,#EEF2F7}，**未声明 effects**
       PNG 佐证：卡1 下方 381..391 有投影染色、其余卡下方是纯页面底色；x=16 处卡1 无描边像素。 */
  it('卡1 带投影类（无描边类），卡2/卡3/确认卡带中心描边类', async () => {
    const wrapper = await mountPage()
    const cards = wrapper.findAll('.card')
    expect(cards).toHaveLength(4)
    expect(cards[0].classes()).toContain('card--lead')
    expect(cards[0].classes()).not.toContain('card--ring')
    expect(cards[1].classes()).toContain('card--ring')
    expect(cards[2].classes()).toContain('card--ring')
    expect(cards[3].classes()).toContain('card--ring')
  })

  /* 请求规则行 40 高（设计 PNG 321..360 / 553..592 / 729..768），峰谷/阶梯行 44 */
  it('请求规则行带紧凑类，峰谷/阶梯行不带（卡1 [否,否,是] · 卡2 [否,是] · 卡3 [是]）', async () => {
    const wrapper = await mountPage()
    const compact = wrapper.findAll('.rule').map((n) => n.classes().includes('rule--compact'))
    expect(compact).toEqual([false, false, true, false, true, true])
  })
})
