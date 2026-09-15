/**
 * 序号 9【报价管理】模型报价设置（page-9）— 页面单测
 *
 * 文案真源：.calicat/raw/pages/page-9/design.tree.json（430 宽 · 设计总高 1211 · 无 TabBar）
 *   以下断言里的中文一律**手抄自设计树**（不引用实现常量，避免自证）：
 *     新增报价单 / 填写基本信息并设置模型报价 / 报价主体 / 去新增 / 下拉选择主体公司，可在我的公司中新增
 *     基本信息 / 已完善 / 报价单名称 / 凭证名称 / 模型列表 / 全选模型 / 按凭证实时带出
 *     输入 $2.50 / 输出 $10.00 / 1M token / 已选 / 可选 / 价格均以 $/1M token 计价，勾选后可在下一步设置单价
 *     模型列表随凭证变化自动刷新，切换凭证将重置当前勾选状态，请确认后再保存。/ 存为草稿 / 保存
 *   几何真源（用于后续 DOM 实测对账）：顶栏 90 · 卡 padding16 r16 · 选择框 48 · 输入框 48 · 底栏 padding[12,16,28,16]
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/17-spec/18-API + 台账目标路由列
 * 接口真源：POST /api/v1/quotes · POST /api/v1/quotes/{quoteId}/items · GET /api/v1/credentials（18-API）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuoteSetupPage from '@/pages/quote-models/index.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const PROFILE = {
  id: 'p1',
  company_name: '上海徽石科技国外',
  unified_social_credit_code: '91330106MA2XXXXX8B'
}

const CREDENTIALS = {
  total: 2,
  items: [
    { id: 'c1', alias: '华东主线路 · GPT 通道', detection_status: 'PASS' },
    { id: 'c2', alias: '华北备用通道', detection_status: 'PASS' }
  ]
}

/** 设计稿模型清单（逐字/逐值抄自 design.tree.json 的 5 行） */
const C1_DETAIL = {
  id: 'c1',
  alias: '华东主线路 · GPT 通道',
  api_key_mask: 'sk-prod-••••••••2f9a',
  model_list: [
    { model_name: 'gpt-4o', vendor: 'OpenAI', input_price: 2.5, output_price: 10, selected: true },
    { model_name: 'gpt-4o-mini', vendor: 'OpenAI', input_price: 0.15, output_price: 0.6, selected: true },
    { model_name: 'claude-3-5-sonnet', vendor: 'Anthropic', input_price: 3, output_price: 15, selected: true },
    { model_name: 'gemini-1.5-pro', vendor: 'Google', input_price: 1.25, output_price: 5, selected: false },
    { model_name: 'deepseek-chat', vendor: 'DeepSeek', input_price: 0.14, output_price: 0.28, selected: false }
  ]
}

const C2_DETAIL = {
  id: 'c2',
  alias: '华北备用通道',
  api_key_mask: 'sk-prod-••••••••7788',
  model_list: [
    { model_name: 'gpt-4o', vendor: 'OpenAI', input_price: 2.5, output_price: 10 },
    { model_name: 'gpt-4o-mini', vendor: 'OpenAI', input_price: 0.15, output_price: 0.6 }
  ]
}

async function mountPage() {
  pushResponse(ok(PROFILE))
  pushResponse(ok(CREDENTIALS))
  const wrapper = mount(QuoteSetupPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

/** 走完整交互：打开凭证下拉 → 选 c1 → 面板收起、模型行渲染 */
async function pickCredential(wrapper: ReturnType<typeof mount>, detail = C1_DETAIL) {
  await tap(wrapper, 'cred-select')
  pushResponse(ok(detail))
  await tap(wrapper, `cred-option-${detail.id}`)
}

describe('序号 9 · 结构与设计稿文案一致', () => {
  it('顶部导航：标题 + 副标题（逐字）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.setup__title').text()).toBe('新增报价单')
    expect(wrapper.find('.setup__subtitle').text()).toBe('填写基本信息并设置模型报价')
  })

  it('三张卡标题与右侧标签与设计稿一致', async () => {
    const wrapper = await mountPage()
    const titles = wrapper.findAll('.card__title').map((t) => t.text())
    expect(titles).toEqual(['报价主体', '基本信息', '模型列表'])
    expect(wrapper.find('[data-testid="chip-add-company"]').text()).toContain('去新增')
    expect(wrapper.find('[data-testid="chip-basic-done"]').text()).toContain('已完善')
    expect(wrapper.find('[data-testid="chip-model-count"]').text()).toBe('已选 0 / 0')
  })

  it('报价主体卡片：说明行「* 下拉选择主体公司，可在我的公司中新增」', async () => {
    const wrapper = await mountPage()
    const hint = wrapper.find('[data-testid="subject-hint"]').text()
    expect(hint).toContain('下拉选择主体公司，可在我的公司中新增')
  })

  it('模型列表卡：工具栏「全选模型」「按凭证实时带出」+ 底部说明（逐字）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="select-all"]').text()).toContain('全选模型')
    expect(wrapper.find('[data-testid="source-hint"]').text()).toContain('按凭证实时带出')
    expect(wrapper.find('[data-testid="model-note"]').text()).toBe(
      '价格均以 $/1M token 计价，勾选后可在下一步设置单价'
    )
  })

  it('联动提示卡与底部按钮（逐字）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="tip-text"]').text()).toBe(
      '模型列表随凭证变化自动刷新，切换凭证将重置当前勾选状态，\n请确认后再保存。'
    )
    expect(wrapper.find('[data-testid="btn-draft"]').text()).toBe('存为草稿')
    expect(wrapper.find('[data-testid="btn-save"]').text()).toContain('保存')
  })

  it('首屏无 TabBar（设计稿本页无 TabBar）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.tabbar').exists()).toBe(false)
  })
})

describe('序号 9 · 首屏取数（主体公司 + 凭证列表）', () => {
  it('onMounted 拉取 /provider/profile 与 /credentials 各一次', async () => {
    const wrapper = await mountPage()
    const urls = getCalls('request').map((c) => (c.args[0] as Record<string, unknown>).url)
    expect(urls).toEqual(['/api/v1/provider/profile', '/api/v1/credentials'])
    expect(wrapper.find('[data-testid="subject-select"]').text()).toContain('上海徽石科技国外')
    expect(wrapper.find('[data-testid="subject-select"]').text()).toContain('91330106MA2XXXXX8B')
  })

  it('档案缺字段时显示占位，不编造公司名', async () => {
    pushResponse(ok({}))
    pushResponse(ok({ items: [] }))
    const wrapper = mount(QuoteSetupPage)
    await flushPromises()
    expect(wrapper.find('[data-testid="subject-value"]').text()).toContain('请选择主体公司')
  })

  it('「去新增」→ 跳供应商档案编辑页', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'chip-add-company')
    expect((getCalls('navigateTo').at(-1)?.args[0] as Record<string, unknown>).url).toBe(
      '/pages/profile-edit/index'
    )
  })

  it('返回按钮 → navigateBack', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'back')
    expect(getCalls('navigateBack')).toHaveLength(1)
  })
})

describe('序号 9 · 凭证选择与模型列表（按凭证实时带出）', () => {
  it('点凭证框展开列表，选中凭证后收起并拉详情', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'cred-select')
    expect(wrapper.find('[data-testid="cred-panel"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid^="cred-option-"]').map((n) => n.text())).toEqual([
      '华东主线路 · GPT 通道',
      '华北备用通道'
    ])
    pushResponse(ok(C1_DETAIL))
    await tap(wrapper, 'cred-option-c1')
    expect(wrapper.find('[data-testid="cred-panel"]').exists()).toBe(false)
    const urls = getCalls('request').map((c) => (c.args[0] as Record<string, unknown>).url)
    expect(urls).toContain('/api/v1/credentials/c1')
    expect(wrapper.find('[data-testid="cred-value"]').text()).toContain('华东主线路 · GPT 通道')
  })

  it('模型行按设计稿渲染 5 行：名称/厂商/价格/状态标逐条一致', async () => {
    const wrapper = await mountPage()
    await pickCredential(wrapper)
    const rows = wrapper.findAll('[data-testid^="model-row-"]')
    expect(rows).toHaveLength(5)
    expect(rows.map((r) => r.find('.model__name').text())).toEqual([
      'gpt-4o',
      'gpt-4o-mini',
      'claude-3-5-sonnet',
      'gemini-1.5-pro',
      'deepseek-chat'
    ])
    expect(rows.map((r) => r.find('.model__vendor').text())).toEqual([
      'OpenAI',
      'OpenAI',
      'Anthropic',
      'Google',
      'DeepSeek'
    ])
    expect(rows[0].find('.model__price').text()).toBe('输入 $2.50 / 输出 $10.00 / 1M token')
    expect(rows[4].find('.model__price').text()).toBe('输入 $0.14 / 输出 $0.28 / 1M token')
    expect(rows.map((r) => r.find('.model__status').text())).toEqual([
      '已选',
      '已选',
      '已选',
      '可选',
      '可选'
    ])
  })

  it('凭证说明行：已自动带出该凭证下 5 个可用模型；右上计数 已选 3 / 5', async () => {
    const wrapper = await mountPage()
    await pickCredential(wrapper)
    expect(wrapper.find('[data-testid="cred-hint"]').text()).toBe('已自动带出该凭证下 5 个可用模型')
    expect(wrapper.find('[data-testid="chip-model-count"]').text()).toBe('已选 3 / 5')
  })

  it('价格缺失的行不渲染价格行（不编造价格）', async () => {
    const wrapper = await mountPage()
    await pickCredential(wrapper, {
      id: 'c1',
      alias: 'x',
      model_list: [{ model_name: 'gpt-4o', vendor: 'OpenAI' }]
    })
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(1)
    expect(wrapper.find('.model__price').exists()).toBe(false)
  })

  it('点第 4 行 → 勾选，计数 已选 4 / 5', async () => {
    const wrapper = await mountPage()
    await pickCredential(wrapper)
    await tap(wrapper, 'model-row-gemini-1.5-pro')
    expect(wrapper.find('[data-testid="chip-model-count"]').text()).toBe('已选 4 / 5')
    expect(wrapper.findAll('.model__status')[3].text()).toBe('已选')
  })

  it('全选 → 已选 5 / 5；再点全选 → 已选 0 / 5', async () => {
    const wrapper = await mountPage()
    await pickCredential(wrapper)
    await tap(wrapper, 'select-all')
    expect(wrapper.find('[data-testid="chip-model-count"]').text()).toBe('已选 5 / 5')
    await tap(wrapper, 'select-all')
    expect(wrapper.find('[data-testid="chip-model-count"]').text()).toBe('已选 0 / 5')
  })

  it('切换凭证 → 重新拉模型并重置勾选（设计原文：切换凭证将重置当前勾选状态）', async () => {
    const wrapper = await mountPage()
    await pickCredential(wrapper)
    await tap(wrapper, 'cred-select')
    pushResponse(ok(C2_DETAIL))
    await tap(wrapper, 'cred-option-c2')
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(2)
    expect(wrapper.find('[data-testid="chip-model-count"]').text()).toBe('已选 0 / 2')
    expect(wrapper.find('[data-testid="cred-hint"]').text()).toBe('已自动带出该凭证下 2 个可用模型')
  })

  it('凭证详情拉取失败 → 提示且不渲染模型行', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'cred-select')
    pushResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务繁忙', data: null } })
    await tap(wrapper, 'cred-option-c1')
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(0)
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({ title: '服务繁忙' })
  })
})

describe('序号 9 · 报价单名称与字数提示', () => {
  it('输入名称 → 字数提示随输入变化（设计稿 30 上限）', async () => {
    const wrapper = await mountPage()
    const input = wrapper.find('[data-testid="name-input"]')
    await input.setValue('2024Q3 主线路报价')
    expect(wrapper.find('[data-testid="name-count"]').text()).toBe('12/30')
    await input.setValue('')
    expect(wrapper.find('[data-testid="name-count"]').text()).toBe('0/30')
  })
})

describe('序号 9 · 存为草稿 / 保存（PRD 10 §5.1 V1 · A2）', () => {
  it('存为草稿：不完整表单也发 POST /api/v1/quotes（主体由档案自动带出）', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ quote_id: 'q9' }))
    await tap(wrapper, 'btn-draft')
    const last = getCalls('request').at(-1)?.args[0] as Record<string, unknown>
    expect(last.url).toBe('/api/v1/quotes')
    expect(last.method).toBe('POST')
    expect(last.data).toEqual({ provider_id: 'p1' })
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({ title: '已存为草稿' })
  })

  it('保存：缺名称 → 拦截并提示，不发请求', async () => {
    const wrapper = await mountPage()
    const before = getCalls('request').length
    await tap(wrapper, 'btn-save')
    expect(getCalls('request').length).toBe(before)
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({ title: '请输入报价单名称' })
  })

  it('保存：未选模型 → 提示「请至少选择一个模型」（V1 明细行≥1）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    // c2 的模型清单未标记已选 → 勾选数为 0
    await pickCredential(wrapper, C2_DETAIL)
    await tap(wrapper, 'btn-save')
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({ title: '请至少选择一个模型' })
  })

  it('保存成功：POST /quotes → POST /quotes/{id}/items（3 行明细）→ 提示并进入下一步', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    await pickCredential(wrapper)
    pushResponse(ok({ quote_id: 'q9' }))
    pushResponse(ok({}))
    await tap(wrapper, 'btn-save')

    const reqs = getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
    const createReq = reqs.find((r) => r.url === '/api/v1/quotes' && r.method === 'POST')
    expect(createReq?.data).toEqual({
      name: '2024Q3 主线路报价',
      provider_id: 'p1',
      credential_id: 'c1'
    })
    const itemsReq = reqs.at(-1)
    expect(itemsReq?.url).toBe('/api/v1/quotes/q9/items')
    expect(itemsReq?.method).toBe('POST')
    expect(itemsReq?.data).toEqual({
      items: [{ model_name: 'gpt-4o' }, { model_name: 'gpt-4o-mini' }, { model_name: 'claude-3-5-sonnet' }]
    })
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({ title: '保存成功' })
    expect((getCalls('navigateTo').at(-1)?.args[0] as Record<string, unknown>).url).toBe(
      '/pages/model-pricing/index?quoteId=q9'
    )
  })

  it('创建失败（E-1602）→ 提示服务端 message，不跳转', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    await pickCredential(wrapper)
    pushResponse({ statusCode: 200, data: { code: 'E-1602', message: '未通过检测的凭证不可报价', data: null } })
    await tap(wrapper, 'btn-save')
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({
      title: '未通过检测的凭证不可报价'
    })
    expect(
      getCalls('navigateTo').some(
        (c) => String((c.args[0] as Record<string, unknown>).url).startsWith('/pages/model-pricing')
      )
    ).toBe(false)
  })
})
