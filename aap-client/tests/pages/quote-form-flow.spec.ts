/**
 * 序号 12-v1【报价管理】新增报价单-初始态（page-26）— 交互与接口（TDD 切片 3，先红）
 *
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 *   分类：返回 = navigation(navigateBack) · 帮助 = client-only（PRD 无对应说明页，不臆造动作）
 *         凭证选择 = api(GET /credentials → 选中 GET /credentials/{id} 带出模型清单)
 *         名称输入/清除/勾选模型 = client-only · 单号只读 = client-only（系统生成）
 *         存为草稿 = api(POST /quotes) · 保存并继续 = api(POST /quotes [+ /{id}/items]) → navigation(模型定价)
 *   接口路径真源：.calicat/prd/18-API设计OpenAPI.md（前缀 /api/v1，方法为 REST 语义推断 → missing-prd）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuoteFormPage from '@/pages/quote-form/index.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 凭证列表 mock（字段名取 15-数据字典 aap_credential；字段级 schema missing-prd） */
const CRED_LIST = {
  items: [
    { id: 'c1', alias: '主线路 Key' },
    { id: 'c2', alias: '备用 Key' }
  ],
  total: 2
}

/** 凭证详情 mock：模型清单（设计稿「选择凭证后自动带出可用模型列表」） */
const CRED_DETAIL = {
  id: 'c1',
  alias: '主线路 Key',
  base_url: 'https://api.example.com',
  api_key_mask: 'sk-a***5678',
  model_list: [
    { model_name: 'gpt-4o', vendor: 'OpenAI', input_price: 2.5, output_price: 10, selected: true },
    { model_name: 'gpt-4o-mini', vendor: 'OpenAI', input_price: 0.15, output_price: 0.6, selected: false }
  ]
}

function mountPage() {
  return mount(QuoteFormPage)
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

function requests() {
  return getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
}

function requestsTo(suffix: string, method?: string) {
  return requests().filter(
    (r) => String(r.url).endsWith(suffix) && (method ? String(r.method) === method : true)
  )
}

function toasts() {
  return getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
}

function navUrls() {
  return getCalls('navigateTo').map((c) => String((c.args[0] as Record<string, unknown>).url))
}

/** 选凭证：开面板 → 拉列表 → 选中 → 拉详情带出模型 */
async function pickCredential(wrapper: ReturnType<typeof mount>, id = 'c1') {
  pushResponse(ok(CRED_LIST))
  pushResponse(ok(CRED_DETAIL))
  await tap(wrapper, 'cred-select')
  await tap(wrapper, `cred-option-${id}`)
}

describe('序号 12-v1 · 凭证选择（api）', () => {
  it('点选择框 → GET /credentials 开面板并渲染候选项', async () => {
    const wrapper = mountPage()
    pushResponse(ok(CRED_LIST))
    await tap(wrapper, 'cred-select')
    const reqs = requestsTo('/credentials')
    expect(reqs).toHaveLength(1)
    expect(reqs[0].method).toBe('GET')
    expect(String(reqs[0].url)).toBe('/api/v1/credentials')
    expect(wrapper.find('[data-testid="cred-panel"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="cred-option-c1"]').text()).toBe('主线路 Key')
  })

  it('选中凭证 → GET /credentials/{id} 带出模型清单，chip 由「待带出」变「已选 1 / 2」', async () => {
    const wrapper = mountPage()
    await pickCredential(wrapper)
    expect(requestsTo('/credentials/c1')[0]?.method).toBe('GET')
    expect(wrapper.find('[data-testid="cred-value"]').text()).toBe('主线路 Key')
    expect(wrapper.find('[data-testid="chip-model"]').text()).toBe('已选 1 / 2')
    expect(wrapper.find('[data-testid="model-empty"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(2)
    expect(wrapper.find('[data-testid="model-row-gpt-4o"]').text()).toContain('输入 $2.50 / 输出 $10.00 / 1M token')
  })

  it('详情拉取失败 → toast 服务端 message 且保持空态（不编造模型）', async () => {
    const wrapper = mountPage()
    pushResponse(ok(CRED_LIST))
    pushResponse({ statusCode: 200, data: { code: 'E-2001', message: '凭证明细获取失败' } })
    await tap(wrapper, 'cred-select')
    await tap(wrapper, 'cred-option-c2')
    expect(toasts()).toEqual(['凭证明细获取失败'])
    expect(wrapper.find('[data-testid="model-empty"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(0)
  })

  it('勾选模型行 → client-only 切换，chip 计数同步', async () => {
    const wrapper = mountPage()
    await pickCredential(wrapper)
    await tap(wrapper, 'model-row-gpt-4o-mini')
    expect(wrapper.find('[data-testid="chip-model"]').text()).toBe('已选 2 / 2')
    expect(requestsTo('/quotes')).toHaveLength(0)
  })
})

describe('序号 12-v1 · 名称输入（client-only）', () => {
  it('输入即时更新字数提示（设计占位 0/30）', async () => {
    const wrapper = mountPage()
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    expect(wrapper.find('[data-testid="name-count"]').text()).toBe('12/30')
  })

  it('清除按钮清空名称并归零计数', async () => {
    const wrapper = mountPage()
    await wrapper.find('[data-testid="name-input"]').setValue('abc')
    await tap(wrapper, 'name-clear')
    expect(wrapper.find('[data-testid="name-count"]').text()).toBe('0/30')
  })
})

describe('序号 12-v1 · 存为草稿（api，A2 草稿无限暂存 → 不拦截）', () => {
  it('POST /quotes 带 name + credential_id，toast 后返回上一页', async () => {
    const wrapper = mountPage()
    await pickCredential(wrapper)
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    pushResponse(ok({ quote_id: 'q9', quote_no: 'QT-20240614-0009' }))
    pushResponse(ok({}))
    await tap(wrapper, 'btn-draft')
    const posts = requestsTo('/quotes', 'POST')
    expect(posts).toHaveLength(1)
    expect(posts[0].data).toEqual({ name: '2024Q3 主线路报价', credential_id: 'c1' })
    expect(requestsTo('/quotes/q9/items', 'POST')).toHaveLength(1)
    expect(toasts()).toEqual(['已存为草稿'])
    expect(getCalls('navigateBack')).toHaveLength(1)
  })

  it('空表单也能存草稿（不做必填拦截），请求体为空对象', async () => {
    const wrapper = mountPage()
    pushResponse(ok({ quote_id: 'q10' }))
    await tap(wrapper, 'btn-draft')
    const posts = requestsTo('/quotes', 'POST')
    expect(posts).toHaveLength(1)
    expect(posts[0].data).toEqual({})
    expect(getCalls('navigateBack')).toHaveLength(1)
  })
})

describe('序号 12-v1 · 保存并继续（api + navigation，10-PRD §5.1 校验）', () => {
  it('名称为空 → toast「请输入报价单名称」且不发请求', async () => {
    const wrapper = mountPage()
    await tap(wrapper, 'btn-save')
    expect(toasts()).toEqual(['请输入报价单名称'])
    expect(requestsTo('/quotes')).toHaveLength(0)
    expect(getCalls('navigateTo')).toHaveLength(0)
  })

  it('未选凭证 → toast「请选择凭证」且不发请求', async () => {
    const wrapper = mountPage()
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    await tap(wrapper, 'btn-save')
    expect(toasts()).toEqual(['请选择凭证'])
    expect(requestsTo('/quotes')).toHaveLength(0)
  })

  it('未勾选模型 → toast「请至少选择一个模型」（V1 明细行≥1）', async () => {
    const wrapper = mountPage()
    pushResponse(ok(CRED_LIST))
    pushResponse(ok({ ...CRED_DETAIL, model_list: [{ model_name: 'gpt-4o', selected: false }] }))
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    await tap(wrapper, 'cred-select')
    await tap(wrapper, 'cred-option-c1')
    await tap(wrapper, 'btn-save')
    expect(toasts()).toEqual(['请至少选择一个模型'])
    expect(requestsTo('/quotes')).toHaveLength(0)
  })

  it('校验通过 → POST /quotes + 明细行，toast 后进入「保存成功页」（quote-form/success）', async () => {
    const wrapper = mountPage()
    await pickCredential(wrapper)
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    pushResponse(ok({ quote_id: 'q9' }))
    pushResponse(ok({}))
    await tap(wrapper, 'btn-save')
    const posts = requestsTo('/quotes', 'POST')
    expect(posts).toHaveLength(1)
    const itemPosts = requestsTo('/quotes/q9/items', 'POST')
    expect(itemPosts).toHaveLength(1)
    expect(itemPosts[0].data).toEqual({ items: [{ model_name: 'gpt-4o' }] })
    expect(toasts()).toEqual(['保存成功'])
    expect(navUrls()).toEqual(['/pages/quote-form/success?quoteId=q9'])
  })

  it('保存失败 → toast 服务端 message，不跳转', async () => {
    const wrapper = mountPage()
    await pickCredential(wrapper)
    await wrapper.find('[data-testid="name-input"]').setValue('2024Q3 主线路报价')
    pushResponse({ statusCode: 200, data: { code: 'E-1602', message: '未通过检测不可报价' } })
    await tap(wrapper, 'btn-save')
    expect(toasts()).toEqual(['未通过检测不可报价'])
    expect(getCalls('navigateTo')).toHaveLength(0)
  })
})

describe('序号 12-v1 · 导航（navigation / client-only）', () => {
  it('返回按钮 → navigateBack', async () => {
    const wrapper = mountPage()
    await tap(wrapper, 'back')
    expect(getCalls('navigateBack')).toHaveLength(1)
  })

  it('帮助按钮为 client-only（PRD 无说明页 → 不跳转）', async () => {
    const wrapper = mountPage()
    await tap(wrapper, 'help')
    expect(getCalls('navigateTo')).toHaveLength(0)
    expect(getCalls('navigateBack')).toHaveLength(0)
    expect(getCalls('showToast')).toHaveLength(0)
  })
})
