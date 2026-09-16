/**
 * 序号 8【报价管理】报价单列表（page-8-2）— 视图模型单测（TDD 切片 1）
 *
 * 设计真源：.calicat/raw/pages/page-8-2/design.tree.json
 *   筛选行 6 chip：全部/草稿/已提交/已驳回/待签署/已完成（active #2563EB 白字；inactive #F1F5F9/#64748B，chip 高 30 r10，间距 9）
 *   卡片：标题 15px SemiBold #0F172A · 状态胶囊（22 高 r11，dot 8×6 + 11px）· 报价单号 13px #334155 + 单号 10px #94A3B8
 *   元信息 11px #94A3B8「2 个模型 · CNY · 更新于 06-14 15:20」· 操作行链接 13px #2563EB（图标 16px）
 *   状态胶囊色：草稿 #F1F5F9/#94A3B8/#64748B · 已提交 #EFF6FF/#2563EB · 已驳回 #FEF2F2/#DC2626/#B91C1C ·
 *              待签署 #FFFBEB/#FF9500 · 已完成 #F0FDF4/#16A34A/#15803D
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Quote」Tag → /quotes（前缀 /api/v1）
 * 状态真源：.calicat/prd/17-…spec QuoteStatus DRAFT/SUBMITTED/REVIEWING/REJECTED/APPROVED/CONVERTED（+10-PRD IN_REVIEW/CONTRACT_CREATED）
 * 字段真源：.calicat/prd/10-报价与合同结算PRD §3.1 Quote（quote_no/status/currency/remark/…）、§3.2 QuoteItem
 */
import { describe, expect, it } from 'vitest'
import {
  FILTERS,
  META_SEPARATOR,
  PAGE_SIZE,
  PAGE_TITLE,
  QUOTE_NO_LABEL,
  STATUS_META,
  buildQuotesModel,
  filterStatusQuery,
  formatUpdatedAt,
  metaParts,
  statusKeyOf
} from '@/utils/quotes-model'
import {
  DESIGN_CARD_ACTIONS,
  DESIGN_CARD_STATUSES,
  DESIGN_FILTERS,
  DESIGN_META,
  DESIGN_META_PARTS,
  DESIGN_QUOTE_NO,
  DESIGN_QUOTE_NO_LABEL,
  DESIGN_TITLE
} from '../fixtures/quotes-fixture'

const quote = (over: Record<string, unknown> = {}) => ({
  id: 'q1',
  title: '2024Q3 主线路报价',
  quote_no: 'QT-20240615-0007',
  status: 'DRAFT',
  currency: 'CNY',
  item_count: 2,
  updated_at: '2026-06-14T15:20:31Z',
  ...over
})

describe('序号 8 · 文案常量与设计稿一致', () => {
  it('页面标题 / 单号标签与设计稿一致', () => {
    expect(PAGE_TITLE).toBe(DESIGN_TITLE)
    expect(QUOTE_NO_LABEL).toBe(DESIGN_QUOTE_NO_LABEL)
  })

  it('6 个筛选 chip 文案与顺序与设计稿一致', () => {
    expect(FILTERS.map((f) => f.label)).toEqual(DESIGN_FILTERS)
  })

  it('分页大小取 18-API 约定默认 20 内的列表页取值 10（与序号 3 一致）', () => {
    expect(PAGE_SIZE).toBe(10)
  })

  it('状态胶囊 5 态文案与设计稿一致', () => {
    expect(Object.values(STATUS_META).map((m) => m.label)).toEqual(DESIGN_CARD_STATUSES)
  })

  it('状态胶囊色值逐项取自设计稿', () => {
    expect(STATUS_META.draft).toMatchObject({ bg: '#f1f5f9', dot: '#94a3b8', text: '#64748b' })
    expect(STATUS_META.submitted).toMatchObject({ bg: '#eff6ff', dot: '#2563eb', text: '#2563eb' })
    expect(STATUS_META.rejected).toMatchObject({ bg: '#fef2f2', dot: '#dc2626', text: '#b91c1c' })
    expect(STATUS_META.pending_sign).toMatchObject({ bg: '#fffceb', dot: '#ff9500', text: '#ff9500' })
    expect(STATUS_META.completed).toMatchObject({ bg: '#f0fdf4', dot: '#16a34a', text: '#15803d' })
  })

  it('元信息行还原成设计里的 5 个节点（节点之间是 8px 间距，不是空格字符）', () => {
    expect(META_SEPARATOR).toBe('·')
    expect(metaParts(DESIGN_META)).toEqual(DESIGN_META_PARTS)
    expect(metaParts('2 个模型 · CNY · 更新于 06-14 15:20')).toEqual([
      '2 个模型', '·', 'CNY', '·', '更新于 06-14 15:20'
    ])
  })
})

describe('序号 8 · 服务端状态 → 设计稿 5 态', () => {
  it('17-spec QuoteStatus 六个取值全部可映射', () => {
    expect(statusKeyOf('DRAFT')).toBe('draft')
    expect(statusKeyOf('SUBMITTED')).toBe('submitted')
    expect(statusKeyOf('REVIEWING')).toBe('submitted')
    expect(statusKeyOf('REJECTED')).toBe('rejected')
    expect(statusKeyOf('APPROVED')).toBe('pending_sign')
    expect(statusKeyOf('CONVERTED')).toBe('completed')
  })

  it('10-PRD / 14-领域模型 的别名取值同样可映射（IN_REVIEW / UNDER_REVIEW / CONTRACT_CREATED / VOID）', () => {
    expect(statusKeyOf('IN_REVIEW')).toBe('submitted')
    expect(statusKeyOf('UNDER_REVIEW')).toBe('submitted')
    expect(statusKeyOf('CONTRACT_CREATED')).toBe('pending_sign')
    expect(statusKeyOf('VOID')).toBe('void')
  })

  it('大小写不敏感；未知/缺失返回 undefined（由页面原样直显，不臆造）', () => {
    expect(statusKeyOf('draft')).toBe('draft')
    expect(statusKeyOf('SOMETHING_NEW')).toBeUndefined()
    expect(statusKeyOf('')).toBeUndefined()
    expect(statusKeyOf(null)).toBeUndefined()
  })
})

describe('序号 8 · 筛选 chip → 接口 status 查询（推断值，已记 missing-prd）', () => {
  it('「全部」不带 status 过滤', () => {
    expect(filterStatusQuery('all')).toBeUndefined()
  })

  it('5 个状态 chip 各自给出 status 取值集合', () => {
    expect(filterStatusQuery('draft')).toEqual(['DRAFT'])
    expect(filterStatusQuery('submitted')).toEqual(['SUBMITTED', 'REVIEWING'])
    expect(filterStatusQuery('rejected')).toEqual(['REJECTED'])
    expect(filterStatusQuery('pending_sign')).toEqual(['APPROVED', 'CONTRACT_CREATED'])
    expect(filterStatusQuery('completed')).toEqual(['CONVERTED'])
  })
})

describe('序号 8 · 更新时间为「MM-DD HH:mm」（设计稿「更新于 06-14 15:20」）', () => {
  it('RFC3339 → MM-DD HH:mm，取服务端字符串本身，不做时区换算', () => {
    expect(formatUpdatedAt('2026-06-14T15:20:31Z')).toBe('06-14 15:20')
    expect(formatUpdatedAt('2026-01-02 03:04:05')).toBe('01-02 03:04')
  })

  it('缺失/非法 → 占位符（不显示 NaN）', () => {
    expect(formatUpdatedAt('')).toBe('—')
    expect(formatUpdatedAt(null)).toBe('—')
    expect(formatUpdatedAt('not-a-date')).toBe('—')
  })
})

describe('序号 8 · 卡片视图模型', () => {
  it('标题 / 单号 / 元信息与设计稿格式一致', () => {
    const m = buildQuotesModel({ total: 1, items: [quote()] })
    expect(m.rows).toHaveLength(1)
    expect(m.rows[0].title).toBe('2024Q3 主线路报价')
    expect(m.rows[0].quoteNo).toBe(DESIGN_QUOTE_NO)
    expect(m.rows[0].metaText).toBe(DESIGN_META)
  })

  it('元信息「N 个模型」用明细行数派生（QuoteItem 无计数字段 → missing-prd）', () => {
    const m = buildQuotesModel({ total: 1, items: [quote({ item_count: undefined, items: [{}, {}, {}] })] })
    expect(m.rows[0].metaText).toContain('3 个模型')
  })

  it('币种取服务端值（PRD 写 USD、设计稿示例 CNY → 不静默改，原样展示）', () => {
    const m = buildQuotesModel({ total: 2, items: [quote({ id: 'a', currency: 'USD' }), quote({ id: 'b', currency: 'CNY' })] })
    expect(m.rows[0].metaText).toContain('USD')
    expect(m.rows[1].metaText).toContain('CNY')
  })

  it('状态胶囊文案与配色随状态变化', () => {
    const m = buildQuotesModel({
      total: 5,
      items: [
        quote({ id: '1', status: 'DRAFT' }),
        quote({ id: '2', status: 'SUBMITTED' }),
        quote({ id: '3', status: 'REJECTED' }),
        quote({ id: '4', status: 'APPROVED' }),
        quote({ id: '5', status: 'CONVERTED' })
      ]
    })
    expect(m.rows.map((r) => r.statusLabel)).toEqual(DESIGN_CARD_STATUSES)
    expect(m.rows.map((r) => r.statusKey)).toEqual(['draft', 'submitted', 'rejected', 'pending_sign', 'completed'])
    expect(m.rows[0].statusBg).toBe('#f1f5f9')
    expect(m.rows[3].statusDot).toBe('#ff9500')
    expect(m.rows[4].statusText).toBe('#15803d')
  })

  it('未覆盖状态原样直显（不落到某个已知态上）', () => {
    const m = buildQuotesModel({ total: 1, items: [quote({ status: 'SOMETHING_NEW' })] })
    expect(m.rows[0].statusLabel).toBe('SOMETHING_NEW')
    expect(m.rows[0].statusKey).toBeUndefined()
    expect(m.rows[0].statusBg).toBe('#f1f5f9')
  })

  it('逐卡操作与设计稿一致（只有待签署多「签署」、已完成多「合同」）', () => {
    const m = buildQuotesModel({
      total: 5,
      items: [
        quote({ id: '1', status: 'DRAFT' }),
        quote({ id: '2', status: 'SUBMITTED' }),
        quote({ id: '3', status: 'REJECTED' }),
        quote({ id: '4', status: 'APPROVED' }),
        quote({ id: '5', status: 'CONVERTED' })
      ]
    })
    expect(m.rows.map((r) => r.actions.map((a) => a.label))).toEqual(DESIGN_CARD_ACTIONS)
  })

  it('「报价」→ 新增报价单页；「预览」→ 报价预览页（画布序号 12-v1 / 12）', () => {
    const m = buildQuotesModel({ total: 1, items: [quote({ id: 'q7', status: 'DRAFT' })] })
    const quoteAction = m.rows[0].actions.find((a) => a.label === '报价')
    const previewAction = m.rows[0].actions.find((a) => a.label === '预览')
    expect(quoteAction).toMatchObject({ kind: 'navigation', url: '/pages/quote-form/index?quoteId=q7' })
    expect(previewAction).toMatchObject({ kind: 'navigation', url: '/pages/quote-preview/index?quoteId=q7' })
  })

  it('「签署」/「合同」→ 合同页（画布序号 15），带 contractId 时透传', () => {
    const sign = buildQuotesModel({ total: 1, items: [quote({ id: 'q8', status: 'APPROVED', contract_id: 'ct8' })] })
    const contract = buildQuotesModel({ total: 1, items: [quote({ id: 'q9', status: 'CONVERTED', contract_id: 'ct9' })] })
    expect(sign.rows[0].actions.find((a) => a.label === '签署')).toMatchObject({
      kind: 'navigation',
      url: '/pages/contract/index?contractId=ct8'
    })
    expect(contract.rows[0].actions.find((a) => a.label === '合同')).toMatchObject({
      kind: 'navigation',
      url: '/pages/contract/index?contractId=ct9'
    })
  })

  it('「删除」是 api 类交互（DELETE /quotes/{quoteId}，已记 missing-prd）', () => {
    const m = buildQuotesModel({ total: 1, items: [quote({ id: 'q1' })] })
    const del = m.rows[0].actions.find((a) => a.label === '删除')
    expect(del).toMatchObject({ kind: 'api', api: 'deleteQuote' })
    expect(del?.url).toBeUndefined()
  })

  it('缺字段不编造：无标题 → 占位符，无 id → 回退下标', () => {
    const m = buildQuotesModel({ total: 1, items: [{ quote_no: 'QT-1' }] })
    expect(m.rows[0].title).toBe('—')
    expect(m.rows[0].id).toBe('row-0')
    expect(m.rows[0].quoteNo).toBe('QT-1')
  })

  it('空列表 / 无响应 → 0 行 + 空态文案', () => {
    expect(buildQuotesModel({ total: 0, items: [] }).rows).toHaveLength(0)
    expect(buildQuotesModel(null).rows).toHaveLength(0)
    expect(buildQuotesModel(null).emptyText).toBe('暂无报价单')
  })

  it('active 默认「全部」，可切换并按 chip 取 status 查询', () => {
    const m = buildQuotesModel({ total: 0, items: [] }, 'pending_sign')
    expect(m.active).toBe('pending_sign')
    expect(m.activeStatusQuery).toEqual(['APPROVED', 'CONTRACT_CREATED'])
  })
})
