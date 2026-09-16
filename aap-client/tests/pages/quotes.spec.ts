/**
 * 序号 8【报价管理】报价单列表（page-8-2）— 页面单测
 *
 * 文案与结构真源：.calicat/raw/pages/page-8-2/design.tree.json（430 宽 / 设计总高 1206；
 *   顶部导航 0..89 · 筛选行 90..143 · 列表卡 178 高 · 卡间距 12 · 操作行 60 高左对齐 · 底部 TabBar 84 高）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/17-spec/18-API + 画布页码（台账目标路由列）
 * 接口真源：GET /api/v1/quotes · DELETE /api/v1/quotes/{quoteId}（18-API「Quote」Tag）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuotesPage from '@/pages/quotes/index.vue'
import { getCalls, pushResponse, setModalAnswer, setNextResponse } from '../setup'
import {
  DESIGN_ACTIONS,
  DESIGN_CARD_ACTIONS,
  DESIGN_CARD_STATUSES,
  DESIGN_FILTERS,
  DESIGN_META,
  DESIGN_META_PARTS,
  DESIGN_NEW_QUOTE,
  DESIGN_QUOTE_NO,
  DESIGN_QUOTE_NO_LABEL,
  DESIGN_TABS,
  DESIGN_TITLE
} from '../fixtures/quotes-fixture'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 与设计稿同文案的 5 张卡（状态按设计稿样例：草稿/已提交/已驳回/待签署/已完成） */
const QUOTES = {
  total: 5,
  items: [
    { id: 'q1', title: '2024Q3 主线路报价', quote_no: 'QT-20240615-0007', status: 'DRAFT', currency: 'CNY', item_count: 2, updated_at: '2026-06-14T15:20:31Z' },
    { id: 'q2', title: '2024Q3 主线路报价', quote_no: 'QT-20240615-0007', status: 'SUBMITTED', currency: 'CNY', item_count: 2, updated_at: '2026-06-14T15:20:31Z' },
    { id: 'q3', title: '2024Q3 主线路报价', quote_no: 'QT-20240615-0007', status: 'REJECTED', currency: 'CNY', item_count: 2, updated_at: '2026-06-14T15:20:31Z' },
    { id: 'q4', title: '2024Q3 主线路报价', quote_no: 'QT-20240615-0007', status: 'APPROVED', currency: 'CNY', item_count: 2, updated_at: '2026-06-14T15:20:31Z', contract_id: 'ct4' },
    { id: 'q5', title: '2024Q3 主线路报价', quote_no: 'QT-20240615-0007', status: 'CONVERTED', currency: 'CNY', item_count: 2, updated_at: '2026-06-14T15:20:31Z', contract_id: 'ct5' }
  ]
}

async function mountPage() {
  pushResponse(ok(QUOTES))
  const wrapper = mount(QuotesPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

describe('序号 8 · 结构与设计稿一致', () => {
  it('顶部导航：标题「报价单」+ 按钮「新建报价」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.quotes__title').text()).toBe(DESIGN_TITLE)
    expect(wrapper.find('[data-testid="new-quote"]').text()).toContain(DESIGN_NEW_QUOTE)
  })

  it('筛选行 6 个 chip，文案与顺序与设计稿一致，默认选中「全部」', async () => {
    const wrapper = await mountPage()
    const chips = wrapper.findAll('[data-testid^="filter-"]')
    expect(chips.map((c) => c.text())).toEqual(DESIGN_FILTERS)
    expect(wrapper.find('.filter-chip--active').text()).toBe('全部')
  })

  it('卡片数与接口条数一致；首卡标题/单号/元信息与设计稿一致', async () => {
    const wrapper = await mountPage()
    const cards = wrapper.findAll('[data-testid="quote-card"]')
    expect(cards).toHaveLength(5)
    expect(cards[0].find('.quote-card__title').text()).toBe('2024Q3 主线路报价')
    expect(cards[0].find('.quote-card__no-label').text()).toBe(DESIGN_QUOTE_NO_LABEL)
    expect(cards[0].find('.quote-card__no-value').text()).toBe(DESIGN_QUOTE_NO)
    expect(cards[0].findAll('.quote-card__meta-part').map((t) => t.text()).join(' ')).toBe(DESIGN_META)
  })

  it('元信息行按设计拆成 5 个节点（3 段文本 + 2 个分隔点），分隔点用更浅的灰', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('.quote-card__meta-row')
    expect(rows).toHaveLength(5)
    expect(rows[0].findAll('.quote-card__meta-text').map((t) => t.text())).toEqual(['2 个模型', 'CNY', '更新于 06-14 15:20'])
    const seps = rows[0].findAll('.quote-card__meta-sep')
    expect(seps.map((t) => t.text())).toEqual(['·', '·'])
    /* 视觉顺序必须是 文本 · 文本 · 文本（设计里节点顺序如此） */
    expect(rows[0].findAll('.quote-card__meta-part').map((t) => t.text())).toEqual(DESIGN_META_PARTS)
    /* 分隔点单独着色（design fd63dfdb/9cafcec1 #CBD5E1）→ 走专属类，不靠行内样式 */
    expect(seps[0].classes()).toContain('quote-card__meta-sep')
    expect(seps[0].classes()).not.toContain('quote-card__meta-text')
  })

  it('5 张卡的状态胶囊文案与设计稿逐张一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('.quote-card__status-text').map((t) => t.text())).toEqual(DESIGN_CARD_STATUSES)
  })

  it('状态胶囊色值取自设计稿（草稿灰 / 已提交蓝 / 已驳回红 / 待签署橙 / 已完成绿）', async () => {
    const wrapper = await mountPage()
    const chips = wrapper.findAll('.quote-card__status')
    expect(chips.map((c) => c.attributes('style'))).toEqual([
      expect.stringContaining('rgb(241, 245, 249)'),
      expect.stringContaining('rgb(239, 246, 255)'),
      expect.stringContaining('rgb(254, 242, 242)'),
      expect.stringContaining('rgb(255, 252, 235)'), /* design c426702b fills rgba(255,252,235,1) = #FFFCEB（修前误取 #FFFBEB） */
      expect.stringContaining('rgb(240, 253, 244)')
    ])
    const dots = wrapper.findAll('.quote-card__status-dot')
    expect(dots.map((d) => d.attributes('style'))).toEqual([
      expect.stringContaining('rgb(148, 163, 184)'),
      expect.stringContaining('rgb(37, 99, 235)'),
      expect.stringContaining('rgb(220, 38, 38)'),
      expect.stringContaining('rgb(255, 149, 0)'),
      expect.stringContaining('rgb(22, 163, 74)')
    ])
    expect(wrapper.findAll('.quote-card__status-text').map((t) => t.attributes('style'))).toEqual([
      expect.stringContaining('rgb(100, 116, 139)'),
      expect.stringContaining('rgb(37, 99, 235)'),
      expect.stringContaining('rgb(185, 28, 28)'),
      expect.stringContaining('rgb(255, 149, 0)'),
      expect.stringContaining('rgb(21, 128, 61)')
    ])
  })

  it('逐卡操作与设计稿一致（只有待签署多「签署」、已完成多「合同」）', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="quote-card"]')
    expect(rows.map((r) => r.findAll('.quote-action__label').map((l) => l.text()))).toEqual(DESIGN_CARD_ACTIONS)
    // 操作文案取自设计稿全集：报价/预览/签署/合同/删除
    const all = new Set(wrapper.findAll('.quote-action__label').map((l) => l.text()))
    for (const label of all) expect(DESIGN_ACTIONS).toContain(label)
  })

  it('底部 TabBar 4 项与设计稿一致，当前高亮「报价」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('[data-testid^="tab-"]').map((t) => t.text())).toEqual(DESIGN_TABS)
    expect(wrapper.find('.tabbar__label--active').text()).toBe('报价')
  })
})

describe('序号 8 · 数据来自接口', () => {
  it('挂载即请求 GET /api/v1/quotes（page=1 pageSize=10，不带 status）', async () => {
    await mountPage()
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    const req = calls[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/quotes')
    expect(req.method).toBe('GET')
    expect(req.data).toMatchObject({ page: 1, pageSize: 10 })
  })

  it('列表内容全部来自接口响应（不硬编码设计稿数据）', async () => {
    pushResponse(
      ok({
        total: 1,
        items: [{ id: 'x1', title: 'unit-线路 A', quote_no: 'QT-9999', status: 'DRAFT', currency: 'USD', item_count: 7, updated_at: '2026-01-02T03:04:05Z' }]
      })
    )
    const wrapper = mount(QuotesPage)
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('unit-线路 A')
    expect(wrapper.find('.quote-card__meta-row').findAll('.quote-card__meta-part').map((t) => t.text()).join(' '))
      .toBe('7 个模型 · USD · 更新于 01-02 03:04')
    expect(wrapper.findAll('[data-testid="quote-card"]')).toHaveLength(1)
  })
})

describe('序号 8 · 交互（分类见台账）', () => {
  it('「新建报价」→ 新增报价单页 /pages/quote-models/index（画布 9，用户拍板对齐原型）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'new-quote')
    const nav = getCalls('navigateTo').at(-1)
    expect((nav?.args[0] as Record<string, unknown>).url).toBe('/pages/quote-models/index')
  })

  it('「报价」→ /pages/quote-form/index?quoteId=…', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'action-quote-q1')
    expect((getCalls('navigateTo').at(-1)?.args[0] as Record<string, unknown>).url).toBe('/pages/quote-form/index?quoteId=q1')
  })

  it('「预览」→ /pages/quote-preview/index?quoteId=…（画布 12）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'action-preview-q2')
    expect((getCalls('navigateTo').at(-1)?.args[0] as Record<string, unknown>).url).toBe('/pages/quote-preview/index?quoteId=q2')
  })

  it('待签署卡的「签署」→ /pages/contract/index?contractId=…（画布 15）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'action-sign-q4')
    expect((getCalls('navigateTo').at(-1)?.args[0] as Record<string, unknown>).url).toBe('/pages/contract/index?contractId=ct4')
  })

  it('已完成卡的「合同」→ /pages/contract/index?contractId=…', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'action-contract-q5')
    expect((getCalls('navigateTo').at(-1)?.args[0] as Record<string, unknown>).url).toBe('/pages/contract/index?contractId=ct5')
  })

  it('草稿卡没有「签署/合同」动作（设计稿逐卡不同）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="action-sign-q1"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="action-contract-q1"]').exists()).toBe(false)
  })

  it('「删除」→ 二次确认后 DELETE /api/v1/quotes/{id}，并重新拉列表', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({})) // DELETE 的响应
    pushResponse(ok({ total: 4, items: QUOTES.items.slice(1) })) // 删除后重新拉列表的响应
    await tap(wrapper, 'action-delete-q1')
    expect(getCalls('showModal')).toHaveLength(1)
    const reqs = getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
    const delIndex = reqs.findIndex((r) => r.method === 'DELETE')
    expect(delIndex).toBeGreaterThan(-1)
    expect(reqs[delIndex].url).toBe('/api/v1/quotes/q1')
    // 删除后重新拉列表：GET 共 2 次，且发生在 DELETE 之后
    const getIndexes = reqs.map((r, i) => (r.method === 'GET' ? i : -1)).filter((i) => i >= 0)
    expect(getIndexes).toHaveLength(2)
    expect(getIndexes[1]).toBeGreaterThan(delIndex)
    expect(wrapper.findAll('[data-testid="quote-card"]')).toHaveLength(4)
  })

  it('删除确认框取消 → 不发 DELETE、不刷新列表', async () => {
    const wrapper = await mountPage()
    setModalAnswer(false)
    await tap(wrapper, 'action-delete-q1')
    expect(getCalls('showModal')).toHaveLength(1)
    expect(getCalls('request').filter((c) => (c.args[0] as Record<string, unknown>).method === 'DELETE')).toHaveLength(0)
    expect(getCalls('request').filter((c) => (c.args[0] as Record<string, unknown>).method === 'GET')).toHaveLength(1)
    expect(wrapper.findAll('[data-testid="quote-card"]')).toHaveLength(5)
  })

  it('删除接口失败 → toast 提示且列表保持原样', async () => {
    const wrapper = await mountPage()
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    await tap(wrapper, 'action-delete-q1')
    expect(getCalls('showToast').length).toBeGreaterThan(0)
    expect(wrapper.findAll('[data-testid="quote-card"]')).toHaveLength(5)
    expect(wrapper.text()).toContain('2024Q3 主线路报价')
  })

  it('点「已驳回」chip → 重新请求并带 status=REJECTED，chip 高亮切换', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ total: 1, items: [QUOTES.items[2]] }))
    await tap(wrapper, 'filter-rejected')
    const gets = getCalls('request').filter((c) => (c.args[0] as Record<string, unknown>).method === 'GET')
    expect(gets).toHaveLength(2)
    expect((gets[1].args[0] as Record<string, unknown>).data).toMatchObject({ page: 1, pageSize: 10, status: 'REJECTED' })
    expect(wrapper.find('.filter-chip--active').text()).toBe('已驳回')
    expect(wrapper.findAll('[data-testid="quote-card"]')).toHaveLength(1)
  })

  it('点「已提交」chip → status=SUBMITTED,REVIEWING；再点「全部」→ 不带 status', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ total: 2, items: QUOTES.items.slice(0, 2) }))
    await tap(wrapper, 'filter-submitted')
    let gets = getCalls('request').filter((c) => (c.args[0] as Record<string, unknown>).method === 'GET')
    expect((gets[1].args[0] as Record<string, unknown>).data).toMatchObject({ status: 'SUBMITTED,REVIEWING' })

    pushResponse(ok(QUOTES))
    await tap(wrapper, 'filter-all')
    gets = getCalls('request').filter((c) => (c.args[0] as Record<string, unknown>).method === 'GET')
    expect((gets[2].args[0] as Record<string, unknown>).data).not.toHaveProperty('status')
    expect(wrapper.findAll('[data-testid="quote-card"]')).toHaveLength(5)
  })

  it('重复点同一个 chip 不重复请求（省流量，避免闪动）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'filter-all')
    expect(getCalls('request').filter((c) => (c.args[0] as Record<string, unknown>).method === 'GET')).toHaveLength(1)
  })

  it('底部 TabBar：工作台 / 报告 / 我的 跳转，报价（当前页）不跳转', async () => {
    const wrapper = await mountPage()
    const cases: Array<[string, string]> = [
      ['tab-工作台', '/pages/workbench/index'],
      ['tab-报告', '/pages/report/index'],
      ['tab-我的', '/pages/mine/index']
    ]
    for (const [testid, url] of cases) {
      await tap(wrapper, testid)
      expect((getCalls('navigateTo').at(-1)?.args[0] as Record<string, unknown>).url, testid).toBe(url)
    }
    const before = getCalls('navigateTo').length
    await tap(wrapper, 'tab-报价')
    expect(getCalls('navigateTo').length).toBe(before)
  })
})

describe('序号 8 · 失败与非 happy-path', () => {
  it('列表接口失败 → toast + 空态 + 不显示假数据（骨架文案保留）', async () => {
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    const wrapper = mount(QuotesPage)
    await flushPromises()
    expect(getCalls('showToast').length).toBeGreaterThan(0)
    expect(wrapper.find('.quotes__title').text()).toBe(DESIGN_TITLE)
    expect(wrapper.findAll('[data-testid="quote-card"]')).toHaveLength(0)
    expect(wrapper.find('[data-testid="quotes-empty"]').text()).toBe('暂无报价单')
  })

  it('空列表 → 空态文案，筛选行与 TabBar 仍在', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    const wrapper = mount(QuotesPage)
    await flushPromises()
    expect(wrapper.find('[data-testid="quotes-empty"]').text()).toBe('暂无报价单')
    expect(wrapper.findAll('[data-testid^="filter-"]')).toHaveLength(6)
    expect(wrapper.findAll('[data-testid^="tab-"]')).toHaveLength(4)
  })
})
