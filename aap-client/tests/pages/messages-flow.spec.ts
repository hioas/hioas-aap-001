/**
 * 序号 20【合同与通知】站内信列表（page-20-2）— 交互流水单测（切片 4）
 *
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 18-API + 设计稿控件语义：
 *   筛选 chip        = api（GET /notifications?unread=|category=，参数名为推断）
 *   「全部已读」      = api（逐条 POST /notifications/{id}/read；18-API 无批量接口 → 不臆造）
 *   消息卡           = api（标记已读，仅未读卡）+ navigation（biz_type 映射落点，未知不跳转）
 *   TabBar           = navigation（我的 = 本模块不跳转）
 * 全部交互分类见 .agents/state/aap-feature-status.csv 序号 20 行。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import MessagesPage from '@/pages/messages/index.vue'
import { getCalls, pushResponse, setNextResponse } from '../setup'
import { DESIGN_MESSAGES } from '../fixtures/messages-fixture'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const NOW = new Date('2026-06-16T10:30:00+08:00')
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
})
afterEach(() => {
  vi.useRealTimers()
})

const NOTIFICATIONS = {
  total: 5,
  items: [
    { id: 'n1', title: DESIGN_MESSAGES[0].title, content: DESIGN_MESSAGES[0].content, created_at: '2026-06-16T10:20:00+08:00', event_code: 'DETECTION_PASSED', biz_type: 'REPORT', biz_id: 'r1' },
    { id: 'n2', title: DESIGN_MESSAGES[1].title, content: DESIGN_MESSAGES[1].content, created_at: '2026-06-16T08:30:00+08:00', event_code: 'QUOTE_REJECTED', biz_type: 'QUOTE', biz_id: 'q1' },
    { id: 'n3', title: DESIGN_MESSAGES[2].title, content: DESIGN_MESSAGES[2].content, created_at: '2026-06-15T18:20:00+08:00', event_code: 'CONTRACT_SIGN_REMINDER', biz_type: 'CONTRACT', biz_id: 'ct1' },
    { id: 'n4', title: DESIGN_MESSAGES[3].title, content: DESIGN_MESSAGES[3].content, created_at: '2026-06-13T10:30:00+08:00', read_at: '2026-06-13T12:00:00+08:00', biz_type: 'BILL' },
    { id: 'n5', title: DESIGN_MESSAGES[4].title, content: DESIGN_MESSAGES[4].content, created_at: '2026-06-11T10:30:00+08:00', read_at: '2026-06-11T11:00:00+08:00', event_code: 'SYSTEM_NOTICE' }
  ]
}

async function mountPage() {
  pushResponse(ok(NOTIFICATIONS))
  const wrapper = mount(MessagesPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

const requests = () =>
  getCalls('request').map((c) => {
    const a = c.args[0] as { url: string; method?: string; data?: Record<string, unknown> }
    return { url: a.url, method: a.method ?? 'GET', data: a.data ?? {} }
  })

describe('序号 20 · 筛选 chip（api）', () => {
  it('点「未读」→ GET /notifications 带 unread=true，chip 高亮切换', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ total: 3, items: [NOTIFICATIONS.items[0]] }))
    await tap(wrapper, 'filter-unread')
    const last = requests().at(-1)!
    expect(last.url).toBe('/api/v1/notifications')
    expect(last.data.unread).toBe('true')
    expect(last.data.page).toBe(1)
    expect(wrapper.find('.chip--active').text()).toBe('未读')
  })

  it('点「订单」→ category=ORDER；点「系统」→ category=SYSTEM', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ total: 1, items: [NOTIFICATIONS.items[3]] }))
    await tap(wrapper, 'filter-order')
    expect(requests().at(-1)!.data.category).toBe('ORDER')
    pushResponse(ok({ total: 1, items: [NOTIFICATIONS.items[4]] }))
    await tap(wrapper, 'filter-system')
    expect(requests().at(-1)!.data.category).toBe('SYSTEM')
    expect(wrapper.find('.chip--active').text()).toBe('系统')
  })

  it('再点「全部」→ 不带任何筛选参数', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ total: 1, items: [] }))
    await tap(wrapper, 'filter-order')
    pushResponse(ok(NOTIFICATIONS))
    await tap(wrapper, 'filter-all')
    const last = requests().at(-1)!
    expect(last.data.unread).toBeUndefined()
    expect(last.data.category).toBeUndefined()
  })

  it('点击当前已选中的 chip 不重复发请求', async () => {
    const wrapper = await mountPage()
    const before = requests().length
    await tap(wrapper, 'filter-all')
    expect(requests().length).toBe(before)
  })
})

describe('序号 20 · 「全部已读」（api：逐条 POST /notifications/{id}/read）', () => {
  it('对 3 条未读逐一 POST，成功后重新拉列表', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({}))
    pushResponse(ok({}))
    pushResponse(ok({}))
    pushResponse(ok(NOTIFICATIONS))
    await tap(wrapper, 'read-all')
    const posts = requests().filter((r) => r.method === 'POST')
    expect(posts.map((p) => p.url)).toEqual([
      '/api/v1/notifications/n1/read',
      '/api/v1/notifications/n2/read',
      '/api/v1/notifications/n3/read'
    ])
    expect(requests().at(-1)!.method).toBe('GET')
  })

  it('无未读时不发任何请求（不臆造批量接口）', async () => {
    pushResponse(ok({ total: 1, items: [{ id: 'n9', title: 'T', content: 'C', read_at: '2026-06-16T09:00:00+08:00' }] }))
    const wrapper = mount(MessagesPage)
    await flushPromises()
    const before = requests().length
    await tap(wrapper, 'read-all')
    expect(requests().length).toBe(before)
  })

  it('标记失败 → toast 提示且不刷新（不假装成功）', async () => {
    const wrapper = await mountPage()
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    const before = requests().length
    await tap(wrapper, 'read-all')
    expect(getCalls('showToast').map((c) => (c.args[0] as { title: string }).title)).toContain('操作失败，请稍后重试')
    // 首个 POST 失败即中止：不再继续发剩下的写请求，也不重新拉列表
    expect(requests().length).toBe(before + 1)
  })
})

describe('序号 20 · 消息卡（api + navigation）', () => {
  it('点未读卡 → POST 标记已读 → 按落点跳转（报告页带 reportId）', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({}))
    pushResponse(ok(NOTIFICATIONS))
    await tap(wrapper, 'message-row')
    const posts = requests().filter((r) => r.method === 'POST')
    expect(posts.map((p) => p.url)).toEqual(['/api/v1/notifications/n1/read'])
    const nav = getCalls('navigateTo').map((c) => (c.args[0] as { url: string }).url)
    expect(nav).toContain('/pages/report/index?reportId=r1')
  })

  it('点未读的合同提醒卡 → 跳合同详情并带 contractId', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({}))
    pushResponse(ok(NOTIFICATIONS))
    const rows = wrapper.findAll('[data-testid="message-row"]')
    await rows[2].trigger('tap')
    await flushPromises()
    expect(getCalls('navigateTo').map((c) => (c.args[0] as { url: string }).url)).toContain(
      '/pages/contract/index?contractId=ct1'
    )
  })

  it('点已读卡 → 不重复标记（无 POST），但有落点仍跳转', async () => {
    pushResponse(
      ok({
        total: 1,
        items: [
          { id: 'n7', title: 'T', content: 'C', created_at: '2026-06-16T09:00:00+08:00', read_at: '2026-06-16T09:10:00+08:00', biz_type: 'CONTRACT', biz_id: 'ct9', event_code: 'CONTRACT_SIGNED' }
        ]
      })
    )
    const wrapper = mount(MessagesPage)
    await flushPromises()
    const before = requests().length
    await tap(wrapper, 'message-row')
    expect(requests().length).toBe(before)
    expect(getCalls('navigateTo').map((c) => (c.args[0] as { url: string }).url)).toContain(
      '/pages/contract/index?contractId=ct9'
    )
  })

  it('已读且无落点（biz_type 未知）→ 不发请求、不跳转', async () => {
    pushResponse(
      ok({ total: 1, items: [{ id: 'n8', title: 'T', content: 'C', read_at: '2026-06-16T09:10:00+08:00', event_code: 'SYSTEM_NOTICE' }] })
    )
    const wrapper = mount(MessagesPage)
    await flushPromises()
    const before = requests().length
    await tap(wrapper, 'message-row')
    expect(requests().length).toBe(before)
    expect(getCalls('navigateTo')).toHaveLength(0)
  })
})

describe('序号 20 · 底部 TabBar（navigation）', () => {
  it('点「工作台」/「报告」/「报价」→ 各自路由', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'tab-工作台')
    await tap(wrapper, 'tab-报告')
    await tap(wrapper, 'tab-报价')
    expect(getCalls('navigateTo').map((c) => (c.args[0] as { url: string }).url)).toEqual([
      '/pages/workbench/index',
      '/pages/report/index',
      '/pages/quotes/index'
    ])
  })

  it('点「我的」（当前模块高亮项）→ 不跳转', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'tab-我的')
    expect(getCalls('navigateTo')).toHaveLength(0)
  })
})
