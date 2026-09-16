/**
 * 序号 12-v2【报价管理】新增报价单-APIKey 下拉展开（page-apikey）— 交互与接口（TDD 切片 3，先红）
 *
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 *   返回 = navigation(navigateBack) · 帮助 = client-only
 *   候选项 = api(GET /credentials) · 选中 = api(GET /credentials/{id} 带出模型清单)
 *   前往「我的设置」新建凭证 = navigation('/pages/settings/index')（画布第 23 页；台账序号 23 未实现）
 *   存为草稿 = api(POST /quotes)（A2 草稿无限暂存，不拦截必填）· 保存并继续 = api(POST /quotes [+ /{id}/items])
 *   接口路径真源：.calicat/prd/18-API设计OpenAPI.md（前缀 /api/v1，方法为 REST 语义推断 → missing-prd）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuoteFormApikeyPage from '@/pages/quote-form/apikey.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const CRED_LIST = {
  items: [
    { id: 'c1', alias: '生产环境密钥', api_key_mask: 'sk-prod-••••••••2f9a', is_primary: true, model_list: new Array(12).fill({}) },
    { id: 'c2', alias: '测试环境密钥', api_key_mask: 'sk-test-••••••••7b31', env_tag: '沙箱', model_list: new Array(8).fill({}) }
  ],
  total: 2
}

const CRED_DETAIL = {
  id: 'c1',
  alias: '生产环境密钥',
  api_key_mask: 'sk-prod-••••••••2f9a',
  model_list: [
    { model_name: 'gpt-4o', vendor: 'OpenAI', input_price: 2.5, output_price: 10, selected: true },
    { model_name: 'gpt-4o-mini', vendor: 'OpenAI', input_price: 0.15, output_price: 0.6, selected: false }
  ]
}

async function mountPage() {
  pushResponse(ok(CRED_LIST))
  const wrapper = mount(QuoteFormApikeyPage)
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

function requestsTo(suffix: string, method?: string) {
  return requests().filter((r) => String(r.url).endsWith(suffix) && (method ? String(r.method) === method : true))
}

function toasts() {
  return getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
}

function navUrls() {
  return getCalls('navigateTo').map((c) => String((c.args[0] as Record<string, unknown>).url))
}

/** 选凭证：面板已在展开态 → 直接点候选项 → 拉详情带出模型 */
async function pick(wrapper: ReturnType<typeof mount>, id = 'c1') {
  pushResponse(ok(CRED_DETAIL))
  await tap(wrapper, `cred-option-${id}`)
}

describe('序号 12-v2 · 下拉选中（api）', () => {
  it('点候选项 c1 → 面板收起、选择框显示别名、GET /credentials/c1 带出模型行、chip 由「待带出」变「已选 1 / 2」', async () => {
    const wrapper = await mountPage()
    await pick(wrapper, 'c1')
    expect(requestsTo('/credentials/c1')[0]?.method).toBe('GET')
    expect(wrapper.find('[data-testid="cred-value"]').text()).toBe('生产环境密钥')
    expect(wrapper.find('[data-testid="cred-panel"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="cred-select"]').attributes('data-open')).toBe('false')
    expect(wrapper.find('[data-testid="chip-model"]').text()).toBe('已选 1 / 2')
    expect(wrapper.find('[data-testid="model-empty"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(2)
  })

  it('再次展开：候选项不重复请求（缓存），已选项高亮 + 对勾，其余行显示环境标', async () => {
    const wrapper = await mountPage()
    await pick(wrapper, 'c1')
    await tap(wrapper, 'cred-select')
    expect(wrapper.find('[data-testid="cred-panel"]').exists()).toBe(true)
    expect(requests().filter((r) => String(r.url).endsWith('/credentials'))).toHaveLength(1)
    expect(wrapper.find('[data-testid="cred-option-c1"]').attributes('data-selected')).toBe('true')
    expect(wrapper.find('[data-testid="cred-check-c1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="cred-option-c2"]').attributes('data-selected')).toBe('false')
    expect(wrapper.find('[data-testid="cred-check-c2"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="cred-tag-c2"]').text()).toBe('沙箱')
  })

  it('详情拉取失败 → toast 服务端 message 且保持空态（不编造模型）', async () => {
    const wrapper = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-2001', message: '凭证明细获取失败' } })
    await tap(wrapper, 'cred-option-c2')
    expect(toasts()).toEqual(['凭证明细获取失败'])
    expect(wrapper.find('[data-testid="model-empty"]').exists()).toBe(true)
  })
})

describe('序号 12-v2 · 面板底部操作与页面导航', () => {
  it('点「前往「我的设置」新建凭证」→ navigateTo /pages/settings/index（本页无写请求）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'cred-create')
    expect(navUrls()).toEqual(['/pages/settings/index'])
    expect(requestsTo('/quotes')).toHaveLength(0)
  })

  it('点返回 → navigateBack(delta 1)（无设计稿交互数据，按设计稿返回按钮语义）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'back')
    expect(getCalls('navigateBack')).toHaveLength(1)
    expect((getCalls('navigateBack')[0].args[0] as Record<string, unknown>).delta).toBe(1)
  })

  it('帮助按钮 = client-only（PRD 无对应说明页 → 不臆造动作）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'help')
    expect(getCalls('navigateTo')).toHaveLength(0)
    expect(requests()).toHaveLength(1)
  })
})

describe('序号 12-v2 · 保存链路（复用序号 12-v1 口径）', () => {
  it('未选凭证点「保存并继续」→ toast「请选择凭证」，不发写请求', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    await tap(wrapper, 'btn-save')
    expect(toasts()).toEqual(['请选择凭证'])
    expect(requestsTo('/quotes')).toHaveLength(0)
  })

  it('选凭证 + 勾选模型 → POST /quotes 与 /quotes/q9/items → 跳保存成功页', async () => {
    const wrapper = await mountPage()
    await pick(wrapper, 'c1')
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    pushResponse(ok({ quote_id: 'q9', quote_no: 'QT-20240614-0009', status: 'DRAFT' }))
    pushResponse(ok({}))
    await tap(wrapper, 'btn-save')
    const posts = requestsTo('/quotes', 'POST')
    expect(posts).toHaveLength(1)
    expect(posts[0].data).toEqual({ name: '2024Q3 主线路报价', credential_id: 'c1' })
    expect(requestsTo('/quotes/q9/items', 'POST')).toHaveLength(1)
    expect(toasts()).toEqual(['保存成功'])
    expect(navUrls()).toEqual(['/pages/quote-form/success?quoteId=q9'])
  })

  it('存为草稿 → POST /quotes（不拦截必填）+ 返回上一页', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ quote_id: 'q10', status: 'DRAFT' }))
    await tap(wrapper, 'btn-draft')
    expect(requestsTo('/quotes', 'POST')).toHaveLength(1)
    expect(toasts()).toEqual(['已存为草稿'])
    expect(getCalls('navigateBack')).toHaveLength(1)
  })
})
