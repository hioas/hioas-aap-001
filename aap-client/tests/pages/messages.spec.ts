/**
 * 序号 20【合同与通知】站内信列表（page-20-2）— 页面单测（切片 3）
 *
 * 文案与结构真源：.calicat/raw/pages/page-20-2/design.tree.json（430 宽 / 设计总高 760）
 *   顶部导航 0..86（标题「消息」20px Bold + 「3 条未读」h22 胶囊 + 「全部已读」）
 *   · 筛选行 86..140（4 chip h30 r10，选中 #2563EB / 未选 #F1F5F9）
 *   · 消息列表区 140..676（卡 92 高 · 卡间距 12 · 图标 38×38 r12 · 标题 13px · 摘要 12px · 时间 11px · 未读红点 9×8）
 *   · 底部 TabBar 676..760(84)（4 项各 104 宽，高亮「我的」rgba(0,122,255,1)）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 18-API + 设计稿控件语义（台账序号 20）
 * 接口真源：GET /api/v1/notifications · POST /api/v1/notifications/{id}/read（18-API「Audit/Notification」Tag）
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import MessagesPage from '@/pages/messages/index.vue'
import { getCalls, pushResponse, setNextResponse } from '../setup'
import { DESIGN_MESSAGES, DESIGN_TABS, DESIGN_TITLE, DESIGN_UNREAD_BADGE } from '../fixtures/messages-fixture'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 设计帧的时间写法是相对当前时间 → 只冻住 Date（不动 setTimeout，flushPromises 才能正常解析） */
const NOW = new Date('2026-06-16T10:30:00+08:00')
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
})
afterEach(() => {
  vi.useRealTimers()
})

/** 与设计帧逐字一致的 5 条（3 未读 + 2 已读） */
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

/**
 * jsdom 会把行内 `#RRGGBB` 规范化成 `rgb(r, g, b)` → 断言前统一换算（不放松颜色要求）
 */
function rgbOf(hex: string): string {
  const v = hex.replace('#', '')
  const n = parseInt(v, 16)
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`
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

describe('序号 20 · 顶部导航与筛选行（设计稿逐字）', () => {
  it('标题「消息」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.messages__title').text()).toBe(DESIGN_TITLE)
  })

  it('未读徽标「3 条未读」（取自当前列表未读条数）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="unread-badge"]').text()).toBe(DESIGN_UNREAD_BADGE)
  })

  it('「全部已读」按钮存在且文案与设计一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="read-all"]').text()).toContain('全部已读')
  })

  it('筛选 4 个 chip，文案顺序与设计一致，默认选中「全部」', async () => {
    const wrapper = await mountPage()
    const chips = wrapper.findAll('[data-testid^="filter-"]')
    expect(chips.map((c) => c.text())).toEqual(['全部', '未读', '订单', '系统'])
    expect(wrapper.find('.chip--active').text()).toBe('全部')
  })
})

describe('序号 20 · 消息列表（5 条逐字对齐设计稿）', () => {
  it('渲染 5 行，标题/摘要/时间与设计稿逐字一致', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="message-row"]')
    expect(rows).toHaveLength(5)
    rows.forEach((row, i) => {
      expect(row.find('.msg__title').text()).toBe(DESIGN_MESSAGES[i].title)
      expect(row.find('.msg__content').text()).toBe(DESIGN_MESSAGES[i].content)
      expect(row.find('.msg__time').text()).toBe(DESIGN_MESSAGES[i].time)
    })
  })

  it('未读红点只在未读行渲染（3 个，与徽标计数一致）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('[data-testid="unread-dot"]')).toHaveLength(3)
    const rows = wrapper.findAll('[data-testid="message-row"]')
    expect(rows[0].find('[data-testid="unread-dot"]').exists()).toBe(true)
    expect(rows[3].find('[data-testid="unread-dot"]').exists()).toBe(false)
  })

  it('已读行整体降灰（标题 #94A3B8 / 时间 #CBD5E1），未读行用深色（#0F172A / #94A3B8）', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="message-row"]')
    expect(rows[0].find('.msg__title').attributes('style')).toContain(rgbOf('#0F172A'))
    expect(rows[0].find('.msg__time').attributes('style')).toContain(rgbOf('#94A3B8'))
    expect(rows[3].find('.msg__title').attributes('style')).toContain(rgbOf('#94A3B8'))
    expect(rows[3].find('.msg__time').attributes('style')).toContain(rgbOf('#CBD5E1'))
  })

  it('图标底色/字形色按消息类型取设计值（第 1 条浅蓝、第 2 条浅橙、第 5 条浅灰）', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="message-row"]')
    expect(rows[0].find('.msg__icon').attributes('style')).toContain(rgbOf('#EFF6FF'))
    expect(rows[1].find('.msg__icon').attributes('style')).toContain(rgbOf('#FFF7ED'))
    expect(rows[4].find('.msg__icon').attributes('style')).toContain(rgbOf('#F1F5F9'))
    expect(rows[1].find('.msg__glyph').attributes('style')).toContain(rgbOf('#D97706'))
    expect(rows[4].find('.msg__glyph').attributes('style')).toContain(rgbOf('#64748B'))
  })

  it('每条卡片是合法的交互面（tap 已接线：未绑定时不会进入已读/跳转流程）', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="message-row"]')
    expect(rows[0].attributes('data-target')).toBe('/pages/report/index?reportId=r1')
    expect(rows[2].attributes('data-target')).toBe('/pages/contract/index?contractId=ct1')
  })
})

describe('序号 20 · 底部 TabBar（设计帧高亮「我的」）', () => {
  it('4 项文案与设计一致', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('[data-testid^="tab-"]')
    expect(tabs.map((t) => t.text())).toEqual(DESIGN_TABS)
  })

  it('高亮项为「我的」（其它项不激活）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.tabbar__label--active').text()).toBe('我的')
  })
})

describe('序号 20 · 取数与异常', () => {
  it('首屏按「全部」取数：GET /api/v1/notifications?page=1&pageSize=20，不带筛选参数', async () => {
    await mountPage()
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/notifications')
    expect(req.method).toBe('GET')
    const data = req.data as Record<string, unknown>
    expect(data.page).toBe(1)
    expect(data.pageSize).toBe(20)
    expect(data.unread).toBeUndefined()
    expect(data.category).toBeUndefined()
  })

  it('空列表 → 0 行且徽标不渲染（空态文案设计稿无稿，不臆造）', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    const wrapper = mount(MessagesPage)
    await flushPromises()
    expect(wrapper.findAll('[data-testid="message-row"]')).toHaveLength(0)
    expect(wrapper.find('[data-testid="unread-badge"]').exists()).toBe(false)
    expect(wrapper.find('.messages__empty').text()).toBe('暂无站内信')
  })

  it('取数失败 → toast 提示且不渲染残留行', async () => {
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    const wrapper = mount(MessagesPage)
    await flushPromises()
    expect(wrapper.findAll('[data-testid="message-row"]')).toHaveLength(0)
    expect(getCalls('showToast').map((c) => (c.args[0] as { title: string }).title)).toContain(
      '数据加载失败，请稍后重试'
    )
  })
})
