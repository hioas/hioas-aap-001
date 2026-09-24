/**
 * 序号 21【工作台与我的】我的页（page-21-2）— 交互单测（切片 5）
 *
 * 交互真源：.calicat/raw/pages/page-21-2/interaction.json =「不存在图层交互数据」
 *   → 交互退 18-API + 设计稿控件语义（台账序号 21 的逐元素分类）：
 *   9 个入口行 = navigation（落点见模型；结算账户无落点 → 不跳转，记台账阻塞）
 *   「提现」= missing-prd（18-API 无提现端点；02-PRD「资金结算/提现走线下」与设计稿冲突）→ 占位提示，不发请求
 *   底部 TabBar = navigation（我的 = 当前模块，不跳转）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import MinePage from '@/pages/mine/index.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

async function mountPage() {
  pushResponse(ok({ company_name: '云智科技有限公司', industry_category: 'RESELLER', verified: true, completeness: 100 }))
  pushResponse(ok({ available_balance: 12860, pending_settlement: 3240, total_settled: 86420 }))
  pushResponse(ok({ total: 3, items: [] }))
  pushResponse(ok({ total: 2, items: [] }))
  pushResponse(ok({ total: 1, items: [] }))
  pushResponse(ok({ total: 3, items: [] }))
  pushResponse(ok({ total: 3, items: [] }))
  const wrapper = mount(MinePage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

const navUrls = () => getCalls('navigateTo').map((c) => (c.args[0] as Record<string, unknown>).url)

describe('序号 21 · 9 个入口行的落点（navigation）', () => {
  it.each([
    ['row-quotes', '/pages/quotes/index'],
    ['row-reports', '/pages/report/index'],
    ['row-contracts', '/pages/contract/index'],
    ['row-usage', '/pages/usage/index'],
    ['row-messages', '/pages/messages/index'],
    ['row-profile', '/pages/profile/index'],
    ['row-credentials', '/pages/credentials/index'],
    // 2026-09-25：SET-01/02（供应商端读结算单）落地 → 该行由「无落点」改为真实跳转，
    // 并入本表后 it.each 的「9 个入口行」才名副其实。
    ['row-settlement', '/pages/settlements/index'],
    ['row-settings', '/pages/settings/index']
  ])('点 %s → navigateTo %s', async (testid, url) => {
    const wrapper = await mountPage()
    await tap(wrapper, testid)
    expect(navUrls()).toEqual([url])
  })

  it('单次点击只发一次跳转（不重复导航）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'row-quotes')
    expect(getCalls('navigateTo').length).toBe(1)
  })
})

describe('序号 21 · 提现（missing-prd：占位提示，不发请求、不跳转）', () => {
  it('点「提现」→ 占位 toast，且 0 个写请求 / 0 次跳转', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'wallet-withdraw')
    expect((getCalls('showToast')[0].args[0] as Record<string, unknown>).title).toBe('提现功能暂未开放')
    expect(getCalls('navigateTo').length).toBe(0)
    const methods = getCalls('request').map((c) => (c.args[0] as Record<string, unknown>).method)
    expect(methods.every((m) => m === 'GET')).toBe(true)
  })
})

describe('序号 21 · 底部 TabBar（共享组件 navigation）', () => {
  it('点「工作台」→ /pages/workbench/index', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'tab-工作台')
    expect(navUrls()).toEqual(['/pages/workbench/index'])
  })

  it('点「报价」→ /pages/quotes/index', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'tab-报价')
    expect(navUrls()).toEqual(['/pages/quotes/index'])
  })

  it('点「我的」→ 当前模块，不跳转', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'tab-我的')
    expect(getCalls('navigateTo').length).toBe(0)
  })
})

describe('序号 21 · 页面自身不产生写请求', () => {
  it('整页交互后请求方法仍全为 GET（只读页）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'row-messages')
    await tap(wrapper, 'wallet-withdraw')
    await tap(wrapper, 'row-profile')
    const methods = getCalls('request').map((c) => (c.args[0] as Record<string, unknown>).method)
    expect(methods.length).toBe(7)
    expect(methods.every((m) => m === 'GET')).toBe(true)
  })
})
