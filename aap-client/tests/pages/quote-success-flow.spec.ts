/**
 * 序号 12-v3【报价管理】新增报价单-保存成功（page-29）— 交互与导航（TDD 切片 3，先红）
 *
 * 交互真源：page-29 interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 *   复制 = client-only(uni.setClipboardData) · 返回 = navigation(navigateBack)
 *   关闭 / 返回报价单列表 = navigation(reLaunch /pages/quotes/index)
 *   继续设置模型报价 = navigation(navigateTo /pages/model-pricing/index?quoteId=，复用序号 11 目标路由)
 * 本页只读（无写接口）：全部请求必须是 GET（新建动作在上游 12-v1/12-v2 已完成）。
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuoteSuccessPage from '@/pages/quote-form/success.vue'
import { getCalls, pushResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const QUOTE = {
  quote_id: 'q9',
  quote_no: 'QT-20240615-0007',
  status: 'DRAFT',
  name: '2024Q3 主线路报价',
  credential_id: 'c1',
  items: [{ model_name: 'gpt-4o' }]
}

const CRED = {
  id: 'c1',
  alias: '生产环境密钥',
  api_key_mask: 'sk-prod-••2f9a',
  env_tag: '生产环境',
  model_list: [{ model_name: 'gpt-4o', selected: true }]
}

async function mountLoaded() {
  storage.set('aap_quote_id', 'q9')
  pushResponse(ok(QUOTE))
  pushResponse(ok(CRED))
  const wrapper = mount(QuoteSuccessPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

function toasts() {
  return getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
}

function navUrls() {
  return getCalls('navigateTo').map((c) => String((c.args[0] as Record<string, unknown>).url))
}

function relaunchUrls() {
  return getCalls('reLaunch').map((c) => String((c.args[0] as Record<string, unknown>).url))
}

function methods() {
  return getCalls('request').map((c) => String((c.args[0] as Record<string, unknown>).method))
}

describe('序号 12-v3 · 复制报价单号（client-only）', () => {
  it('点「复制」→ setClipboardData(单号) 且 toast「报价单号已复制」', async () => {
    const wrapper = await mountLoaded()
    await tap(wrapper, 'copy')
    const calls = getCalls('setClipboardData')
    expect(calls).toHaveLength(1)
    expect((calls[0].args[0] as Record<string, unknown>).data).toBe('QT-20240615-0007')
    expect(toasts()).toEqual(['报价单号已复制'])
  })

  it('无单号（无 quoteId 直接进入）→ 不写剪贴板，只提示（不复制空串）', async () => {
    const wrapper = mount(QuoteSuccessPage)
    await flushPromises()
    await tap(wrapper, 'copy')
    expect(getCalls('setClipboardData')).toHaveLength(0)
    expect(toasts()).toEqual(['暂无可复制的报价单号'])
  })
})

describe('序号 12-v3 · 导航（设计稿三个出口）', () => {
  it('「继续设置模型报价」→ navigateTo /pages/model-pricing/index?quoteId=q9', async () => {
    const wrapper = await mountLoaded()
    await tap(wrapper, 'btn-primary')
    expect(navUrls()).toEqual(['/pages/model-pricing/index?quoteId=q9'])
  })

  it('无 quoteId 时「继续设置模型报价」→ 不带 query 的模型定价页', async () => {
    const wrapper = mount(QuoteSuccessPage)
    await flushPromises()
    await tap(wrapper, 'btn-primary')
    expect(navUrls()).toEqual(['/pages/model-pricing/index'])
  })

  it('「返回报价单列表」→ reLaunch /pages/quotes/index（清栈，不回表单页）', async () => {
    const wrapper = await mountLoaded()
    await tap(wrapper, 'btn-secondary')
    expect(relaunchUrls()).toEqual(['/pages/quotes/index'])
  })

  it('关闭（×）→ reLaunch /pages/quotes/index（与「返回报价单列表」同目标）', async () => {
    const wrapper = await mountLoaded()
    await tap(wrapper, 'close')
    expect(relaunchUrls()).toEqual(['/pages/quotes/index'])
  })

  it('返回（←）→ navigateBack(delta 1)', async () => {
    const wrapper = await mountLoaded()
    await tap(wrapper, 'back')
    expect(getCalls('navigateBack')).toHaveLength(1)
    expect((getCalls('navigateBack')[0].args[0] as Record<string, unknown>).delta).toBe(1)
  })
})

describe('序号 12-v3 · 只读页（不得发写请求）', () => {
  it('加载 + 全部按钮点击后，请求方法只有 GET', async () => {
    const wrapper = await mountLoaded()
    await tap(wrapper, 'copy')
    await tap(wrapper, 'btn-primary')
    await tap(wrapper, 'btn-secondary')
    await tap(wrapper, 'close')
    expect(methods()).toEqual(['GET', 'GET'])
  })
})
