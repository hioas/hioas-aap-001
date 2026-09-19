/**
 * 序号 11【报价管理】模型定价-详情（page-11）— 页面单测（TDD 切片 3）
 *
 * 文案真源：.calicat/raw/pages/page-11/design.tree.json（430 宽 · 设计总高 1541 · 无 TabBar）
 *   断言里的中文**手抄自设计树**（不引用实现常量，避免自证）：
 *     模型定价 / 保存 / 始终匹配（默认档位）· 输入 $2.50 输出 $10.00 / 1M token
 *     档位 / base / 按 token / 添加计费分支 / Token 价格 / $/1M token / 媒体定价
 *     输入价格 / 输出价格 / 缓存读取价格 / 缓存写入价格 / 1 小时缓存写入价格
 *     图像输入价格 / 图片缓存输入价格 / 图像输出价格 / 音频输入价格 / 音频输出价格
 *     请求规则计费 / 条件满足时，最终价格乘以 X；多条命中的倍率会相乘；小于 1 的值为折扣。 / 规则组 #1
 *     时间 / 小时 / Asia/Shanghai / 大于等于 / 值 / 新增参数/Header / 新增时间条件 / 倍率 / 1.0
 *     匹配条件时，最终费用 = 基础费用 × 倍率 / 新增规则组 / 保存价格
 *     （设计树里「点击展开，配置计费请求规则」visible=false → 折叠态提示，首屏不应渲染）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 06/15/17-spec/18-API + 设计稿控件语义
 *   分类：返回/跳转 = navigation · 两个保存 = api(PUT /quotes/items/{itemId}) · 勾选/输入/折叠/规则组增删 = client-only
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ModelPricingPage from '@/pages/model-pricing/index.vue'
import { getCalls, pushResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 设计稿样例明细行（值逐值抄自 design.tree.json：输入 2.50 / 输出 10.00 / 其余 0） */
const ITEM = {
  item_id: 'qi1',
  quote_id: 'q9',
  model_name: 'gpt-4o',
  tier: 'base',
  billing_mode: '按 token',
  input_price: 2.5,
  output_price: 10,
  cache_read_price: 0,
  cache_write_price: 0,
  cache_write_1h_price: 0,
  image_input_price: 0,
  image_cache_input_price: 0,
  image_output_price: 0,
  audio_input_price: 0,
  audio_output_price: 0,
  request_rules: [{ tz: 'Asia/Shanghai', multiplier: 1.0 }]
}

async function mountPage() {
  storage.set('aap_quote_item_id', 'qi1')
  pushResponse(ok(ITEM))
  const wrapper = mount(ModelPricingPage)
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

function saveRequests() {
  return requests().filter((r) => r.method === 'PUT')
}

function toasts() {
  return getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
}

describe('序号 11 · 结构与设计稿文案一致', () => {
  it('顶栏：模型名 + 「模型定价」+ 右侧「保存」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="nav-title"]').text()).toBe('gpt-4o')
    expect(wrapper.find('[data-testid="nav-subtitle"]').text()).toBe('模型定价')
    expect(wrapper.find('[data-testid="save-top"]').text()).toBe('保存')
  })

  it('卡1：蓝色序号「1」+ 模型名 + 档位摘要（设计原文）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="model-badge"]').text()).toBe('1')
    expect(wrapper.find('[data-testid="model-name"]').text()).toBe('gpt-4o')
    expect(wrapper.find('[data-testid="tier-summary"]').text()).toBe(
      '始终匹配（默认档位）· 输入 $2.50 输出 $10.00 / 1M token'
    )
  })

  it('卡2：「档位」标签 + 档位值 + 计价方式 + 「添加计费分支」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="tier-label"]').text()).toBe('档位')
    expect(wrapper.find('[data-testid="tier-input"]').element).toHaveProperty('value', 'base')
    expect(wrapper.find('[data-testid="mode-select"]').text()).toContain('按 token')
    expect(wrapper.find('[data-testid="btn-add-branch"]').text()).toContain('添加计费分支')
  })

  it('卡3：「Token 价格」+ 单位「$/1M token」+ 5 个 Token 单价字段（逐字）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="token-card-title"]').text()).toBe('Token 价格')
    expect(wrapper.find('[data-testid="unit-label"]').text()).toBe('$/1M token')
    const labels = wrapper.findAll('[data-testid^="price-label-"]').map((n) => n.text())
    expect(labels).toEqual(['输入价格', '输出价格', '缓存读取价格', '缓存写入价格', '1 小时缓存写入价格'])
  })

  it('卡3 内「媒体定价」小节：5 个媒体单价字段（逐字）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="media-title"]').text()).toBe('媒体定价')
    const labels = wrapper.findAll('[data-testid^="media-label-"]').map((n) => n.text())
    expect(labels).toEqual(['图像输入价格', '图片缓存输入价格', '图像输出价格', '音频输入价格', '音频输出价格'])
  })

  it('卡4：「请求规则计费」+ 说明 + 规则组 #1 全部字段（逐字）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="rule-card-title"]').text()).toBe('请求规则计费')
    expect(wrapper.find('[data-testid="rule-note"]').text()).toBe(
      '条件满足时，最终价格乘以 X；多条命中的倍率会相乘；小于 1 的值为折扣。'
    )
    expect(wrapper.find('[data-testid="rule-group-title-1"]').text()).toBe('规则组 #1')
    expect(wrapper.find('[data-testid="rule-field-1"]').text()).toContain('时间')
    expect(wrapper.find('[data-testid="rule-granularity-1"]').text()).toContain('小时')
    expect(wrapper.find('[data-testid="rule-tz-1"]').text()).toContain('Asia/Shanghai')
    expect(wrapper.find('[data-testid="rule-op-1"]').text()).toContain('大于等于')
    expect(wrapper.find('[data-testid="rule-value-1"]').attributes('placeholder')).toBe('值')
    expect(wrapper.find('[data-testid="rule-multiplier-label-1"]').text()).toBe('倍率')
    expect((wrapper.find('[data-testid="rule-multiplier-1"]').element as HTMLInputElement).value).toBe('1.0')
    expect(wrapper.find('[data-testid="rule-group-note-1"]').text()).toBe('匹配条件时，最终费用 = 基础费用 × 倍率')
    expect(wrapper.find('[data-testid="btn-add-param-1"]').text()).toContain('新增参数/Header')
    expect(wrapper.find('[data-testid="btn-add-time-1"]').text()).toContain('新增时间条件')
    expect(wrapper.find('[data-testid="btn-add-group"]').text()).toContain('新增规则组')
  })

  it('折叠态提示「点击展开，配置计费请求规则」在设计树里 visible=false → 首屏不渲染', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="rule-hint"]').exists()).toBe(false)
  })

  it('底部操作条：「保存价格」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="save-bottom"]').text()).toContain('保存价格')
  })

  it('首屏无 TabBar（设计稿本页无 TabBar）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.tabbar').exists()).toBe(false)
  })
})

describe('序号 11 · 勾选态与「启用」语义（设计稿只有输入/输出勾选）', () => {
  it('输入/输出已勾选，其余 8 个未勾选（媒体 5 个全部未勾选）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="check-input_price"]').classes()).toContain('check--on')
    expect(wrapper.find('[data-testid="check-output_price"]').classes()).toContain('check--on')
    for (const key of ['cache_read_price', 'cache_write_price', 'cache_write_1h_price']) {
      expect(wrapper.find(`[data-testid="check-${key}"]`).classes()).not.toContain('check--on')
    }
    for (const key of [
      'image_input_price',
      'image_cache_input_price',
      'image_output_price',
      'audio_input_price',
      'audio_output_price'
    ]) {
      expect(wrapper.find(`[data-testid="check-${key}"]`).classes()).not.toContain('check--on')
    }
  })

  it('点「缓存读取价格」勾选框 → 勾选（client-only，不发请求）', async () => {
    const wrapper = await mountPage()
    const before = requests().length
    await tap(wrapper, 'check-cache_read_price')
    expect(wrapper.find('[data-testid="check-cache_read_price"]').classes()).toContain('check--on')
    expect(requests().length).toBe(before)
  })

  it('勾选后该价按 0 计入提交体（勾选 = 启用）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'check-cache_read_price')
    await tap(wrapper, 'save-bottom')
    expect(saveRequests().at(-1)?.data).toMatchObject({ cache_read_price: 0 })
  })

  it('未勾选的字段不出现在提交体里', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'save-top')
    const body = saveRequests().at(-1)?.data as Record<string, unknown>
    expect(body.input_price).toBe(2.5)
    expect(body.output_price).toBe(10)
    expect('cache_read_price' in body).toBe(false)
    expect('image_output_price' in body).toBe(false)
  })
})

describe('序号 11 · 输入与联动（client-only）', () => {
  it('改输入价格 → 摘要里的 $ 值跟着变（设计摘要由单价拼出）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="price-input_price"]').setValue('3.5')
    await flushPromises()
    expect(wrapper.find('[data-testid="tier-summary"]').text()).toBe(
      '始终匹配（默认档位）· 输入 $3.50 输出 $10.00 / 1M token'
    )
  })

  it('改档位 → 参与提交体，且不发请求', async () => {
    const wrapper = await mountPage()
    const before = requests().length
    await wrapper.find('[data-testid="tier-input"]').setValue('t0_0_512K')
    await flushPromises()
    expect(requests().length).toBe(before)
    await tap(wrapper, 'save-top')
    expect(saveRequests().at(-1)?.data).toMatchObject({ tier: 't0_0_512K' })
  })

  /**
   * 缺陷 13：后端 **V15「请求规则仅管理端可设置」**，供应商侧提交 `request_rules` 会被
   * E-1001 拒（实测 `PUT /quotes/items/{id}` 直接失败 → 供应商无法报价）。
   * 旧用例把「改倍率 → 参与提交体」当成期望，那正是缺陷本身；现改为断言**不进请求体**，
   * 但页面上倍率仍可编辑（UI 保留，规则由管理端维护）。
   */
  it('改倍率 → 页面可编辑，但**不进提交体**（V15 仅管理端可写）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="rule-multiplier-1"]').setValue('1.5')
    await flushPromises()
    // UI 仍反映用户输入
    expect((wrapper.find('[data-testid="rule-multiplier-1"]').element as HTMLInputElement).value).toBe('1.5')
    await tap(wrapper, 'save-top')
    const body = saveRequests().at(-1)?.data as Record<string, unknown>
    expect('request_rules' in body).toBe(false)
  })

  it('「添加计费分支」是 client-only（不发请求，仅登记 missing-prd）', async () => {
    const wrapper = await mountPage()
    const before = requests().length
    await tap(wrapper, 'btn-add-branch')
    expect(requests().length).toBe(before)
  })

  it('「新增规则组」→ 出现「规则组 #2」（client-only）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'btn-add-group')
    expect(wrapper.find('[data-testid="rule-group-title-2"]').text()).toBe('规则组 #2')
    expect(requests().length).toBe(1) // 仅首屏 GET
  })

  it('删除「规则组 #1」→ 重新编号回 #1（不会降到 0 组）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'btn-add-group')
    await tap(wrapper, 'rule-delete-1')
    expect(wrapper.findAll('[data-testid^="rule-group-title-"]').map((n) => n.text())).toEqual(['规则组 #1'])
    await tap(wrapper, 'rule-delete-1')
    expect(wrapper.findAll('[data-testid^="rule-group-title-"]').map((n) => n.text())).toEqual(['规则组 #1'])
  })

  it('折叠请求规则 → 规则组收起、显示设计里的折叠提示（client-only）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'collapse-rule')
    expect(wrapper.find('[data-testid="rule-group-1"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="rule-hint"]').text()).toBe('点击展开，配置计费请求规则')
    await tap(wrapper, 'collapse-rule')
    expect(wrapper.find('[data-testid="rule-group-1"]').exists()).toBe(true)
  })
})

describe('序号 11 · 保存（PUT /api/v1/quotes/items/{itemId}）', () => {
  it('点顶栏「保存」→ PUT /api/v1/quotes/items/qi1 并提示「保存成功」', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'save-top')
    const req = saveRequests().at(-1)
    expect(req?.url).toBe('/api/v1/quotes/items/qi1')
    expect(toasts()).toContain('保存成功')
  })

  it('底部「保存价格」→ 同一接口', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'save-bottom')
    expect(saveRequests().at(-1)?.url).toBe('/api/v1/quotes/items/qi1')
  })

  it('输入价格清空 → 提示「请输入输入价格」且不发写请求（06-PRD §1.2 必填）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="price-input_price"]').setValue('')
    await flushPromises()
    await tap(wrapper, 'save-top')
    expect(saveRequests()).toHaveLength(0)
    expect(toasts()).toContain('请输入输入价格')
  })

  it('倍率填 0 → 提示「倍率必须大于 0」且不发写请求（06-PRD §4.2）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="rule-multiplier-1"]').setValue('0')
    await flushPromises()
    await tap(wrapper, 'save-top')
    expect(saveRequests()).toHaveLength(0)
    expect(toasts()).toContain('倍率必须大于 0')
  })

  it('服务端拒绝（E-1403 倍率非法）→ 透传服务端文案，不跳转', async () => {
    const wrapper = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-1403', message: '倍率非法', data: null } })
    await tap(wrapper, 'save-top')
    expect(toasts()).toContain('倍率非法')
    expect(getCalls('navigateTo')).toHaveLength(0)
  })

  it('返回 → navigateBack，且不发请求', async () => {
    const wrapper = await mountPage()
    const before = requests().length
    await tap(wrapper, 'back')
    expect(getCalls('navigateBack')).toHaveLength(1)
    expect(requests().length).toBe(before)
  })
})

describe('序号 11 · 入参回落（无 itemId 时用 quoteId 取明细行）', () => {
  it('只有 quoteId → GET /api/v1/quotes/q9/items 取首行渲染', async () => {
    storage.set('aap_quote_id', 'q9')
    pushResponse(ok({ items: [ITEM] }))
    const wrapper = mount(ModelPricingPage)
    await flushPromises()
    expect(requests()[0].url).toBe('/api/v1/quotes/q9/items')
    expect(wrapper.find('[data-testid="model-name"]').text()).toBe('gpt-4o')
  })
})
