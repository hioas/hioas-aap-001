/**
 * 序号 21【工作台与我的】我的页（page-21-2）— 页面单测（切片 4：结构 / 文案 / 取色）
 *
 * 文案与结构真源：.calicat/raw/pages/page-21-2/design.tree.json
 *   430 宽 · 设计总高 990 = 用户头部 128 + 12 + 钱包卡 192 + 12 + 报价入口卡 299 + 12 + 主体与证照卡 235 + 16 + TabBar 84
 *   · 用户头部（padding 48/16/24/16 · #1D4ED8）：头像 56 r28 · 云智科技有限公司 18px 白 ·
 *     渠道商 chip（白底 #1D4ED8 11px）· 已认证 chip（#DBEAFE 底 + 绿点 9×7 + #1E40AF 11px）
 *   · 钱包卡（padding 20 · r18 · 描边 #EEF2F7）：我的钱包 14px + chevron / 可提现余额 11px + ¥12,860.00 24px /
 *     提现 h38 r10 #2563EB / 待结算 ¥3,240 · 竖分隔 · 累计结算 ¥86,420
 *   · 报价入口卡（padding 8/20）：5 行 h56（图标 32 r10 + 文字 13px + 右侧值 12px + chevron）
 *   · 主体与证照卡（padding 8/20）：4 行（图标无底色 18px #94A3B8 + 文字 13px + 右侧值/胶囊 + chevron）
 *   · 底部 TabBar 84（共享组件，高亮「我的」#2563EB）
 * 接口真源（18-API，前缀 /api/v1）：/provider/profile、/payments、/quotes、/reports、/contracts、
 *   /credentials、/notifications（本页只读，无写请求）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import MinePage from '@/pages/mine/index.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 与设计帧逐字一致的 7 段响应（顺序 = 页面发起顺序） */
const PROFILE = { company_name: '云智科技有限公司', industry_category: 'RESELLER', verified: true, completeness: 100 }
const WALLET = { available_balance: 12860, pending_settlement: 3240, total_settled: 86420 }
const QUOTES = { total: 3, items: [] }
const REPORTS = { total: 2, items: [] }
const CONTRACTS = { total: 1, items: [] }
const CREDENTIALS = { total: 3, items: [] }
const NOTIFICATIONS = { total: 3, items: [] }

async function mountPage(overrides: Record<string, unknown> = {}) {
  pushResponse(ok(overrides.profile ?? PROFILE))
  pushResponse(ok(overrides.wallet ?? WALLET))
  pushResponse(ok(overrides.quotes ?? QUOTES))
  pushResponse(ok(overrides.reports ?? REPORTS))
  pushResponse(ok(overrides.contracts ?? CONTRACTS))
  pushResponse(ok(overrides.credentials ?? CREDENTIALS))
  pushResponse(ok(overrides.notifications ?? NOTIFICATIONS))
  const wrapper = mount(MinePage)
  await flushPromises()
  return wrapper
}

function rgbOf(hex: string): string {
  const v = hex.replace('#', '')
  const n = parseInt(v, 16)
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`
}

const textOf = (wrapper: ReturnType<typeof mount>) => wrapper.text()

describe('序号 21 · 页面骨架与顶部用户头部', () => {
  it('根容器 430 宽（与设计帧同宽）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.mine').exists()).toBe(true)
  })

  it('企业名取 /provider/profile 的 company_name', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="mine-company"]').text()).toBe('云智科技有限公司')
  })

  it('类型 chip = 渠道商（industry_category=RESELLER）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="mine-type"]').text()).toBe('渠道商')
  })

  it('已认证 chip（green dot + 文案）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="mine-verified"]').text()).toBe('已认证')
    expect(wrapper.find('.head__dot').exists()).toBe(true)
  })

  it('未认证时不出「已认证」chip（不臆造状态）', async () => {
    const wrapper = await mountPage({ profile: { company_name: '云智科技有限公司', industry_category: 'RESELLER', status: 'DETECTING' } })
    expect(wrapper.find('[data-testid="mine-verified"]').exists()).toBe(false)
  })

  it('头部头像 56×56（设计 rgba(255,255,255,1) 圆）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.head__avatar').exists()).toBe(true)
    expect(wrapper.find('.head__avatar-glyph').exists()).toBe(true)
  })
})

describe('序号 21 · 我的钱包卡', () => {
  it('标题与三个标签逐字一致', async () => {
    const wrapper = await mountPage()
    const text = textOf(wrapper)
    expect(text).toContain('我的钱包')
    expect(text).toContain('可提现余额')
    expect(text).toContain('待结算')
    expect(text).toContain('累计结算')
    expect(text).toContain('提现')
  })

  it('三金额取自 /payments 汇总字段（两位小数 / 整数）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="wallet-available"]').text()).toBe('¥12,860.00')
    expect(wrapper.find('[data-testid="wallet-pending"]').text()).toBe('¥3,240')
    expect(wrapper.find('[data-testid="wallet-settled"]').text()).toBe('¥86,420')
  })

  it('金额缺失 → 占位「—」（不冒充 0）', async () => {
    const wrapper = await mountPage({ wallet: {} })
    expect(wrapper.find('[data-testid="wallet-available"]').text()).toBe('—')
    expect(wrapper.find('[data-testid="wallet-pending"]').text()).toBe('—')
    expect(wrapper.find('[data-testid="wallet-settled"]').text()).toBe('—')
  })

  it('两列之间有竖分隔（设计 2×32 #E2E8F0）', async () => {
    const wrapper = await mountPage()
    const divider = wrapper.find('.wallet__divider')
    expect(divider.exists()).toBe(true)
    expect(divider.attributes('style')).toContain(rgbOf('#E2E8F0'))
  })

  it('提现按钮在钱包卡内、文案为设计原文（底色 #2563EB 由 tokens 落在 CSS，颜色证据见 H5 computed-style）', async () => {
    const wrapper = await mountPage()
    const button = wrapper.find('[data-testid="wallet-withdraw"]')
    expect(button.exists()).toBe(true)
    expect(button.text()).toBe('提现')
    expect(button.classes()).toContain('withdraw')
  })
})

describe('序号 21 · 两张入口卡（9 行）', () => {
  it('行文案与设计逐字一致且顺序不变', async () => {
    const wrapper = await mountPage()
    const labels = wrapper.findAll('[data-testid^="row-"] .row__label').map((n) => n.text())
    expect(labels).toEqual([
      '我的报价单',
      '检测报告',
      '我的合同',
      '用量与对账',
      '我的消息',
      '主体档案',
      '接入凭证',
      '结算账户',
      '账号与设置'
    ])
  })

  it('右侧值逐行与设计一致（计数来自各列表接口；无值行不渲染值节点）', async () => {
    const wrapper = await mountPage()
    const keys = ['quotes', 'reports', 'contracts', 'usage', 'messages', 'profile', 'credentials', 'settlement', 'settings']
    const valueOf = (key: string) => {
      const node = wrapper.find(`[data-testid="row-${key}"] .row__value`)
      if (node.exists()) return node.text()
      const pill = wrapper.find(`[data-testid="row-${key}"] .row__pill`)
      return pill.exists() ? pill.text() : ''
    }
    expect(keys.map(valueOf)).toEqual(['3 个', '2 份', '待签署 1', '', '待阅读 3', '100%', '3 条', '已绑定', ''])
  })

  it('无值行不渲染值元素（用量与对账 / 账号与设置）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="row-usage"] .row__value').exists()).toBe(false)
    expect(wrapper.find('[data-testid="row-settings"] .row__value').exists()).toBe(false)
  })

  it('图标底色逐行与设计一致（报价卡彩色底 / 证照卡无底色、字形统一 #94A3B8）', async () => {
    const wrapper = await mountPage()
    const iconBg = (key: string) => wrapper.find(`[data-testid="row-${key}"] .row__icon`).attributes('style') ?? ''
    const glyphColor = (key: string) =>
      wrapper.find(`[data-testid="row-${key}"] .row__glyph`).attributes('style') ?? ''
    expect(iconBg('quotes')).toContain(rgbOf('#EFF6FF'))
    expect(iconBg('reports')).toContain(rgbOf('#ECFDF5'))
    expect(iconBg('contracts')).toContain(rgbOf('#FFF7ED'))
    expect(iconBg('usage')).toContain(rgbOf('#FAF5FF'))
    expect(iconBg('messages')).toContain('rgba(255, 149, 0, 0.03)')
    // 证照卡 4 行：设计里没有彩色图标底（图标直接画在卡上）→ 不渲染 .row__icon
    for (const key of ['profile', 'credentials', 'settlement', 'settings']) {
      expect(wrapper.find(`[data-testid="row-${key}"] .row__icon`).exists()).toBe(false)
      expect(glyphColor(key)).toContain(rgbOf('#94A3B8'))
    }
  })

  it('值色：我的合同橙 / 我的消息纯黑 / 其余灰', async () => {
    const wrapper = await mountPage()
    const style = (key: string) => wrapper.find(`[data-testid="row-${key}"] .row__value`).attributes('style') ?? ''
    expect(style('contracts')).toContain(rgbOf('#D97706'))
    expect(style('messages')).toContain(rgbOf('#000000'))
    expect(style('quotes')).toContain(rgbOf('#94A3B8'))
    expect(style('credentials')).toContain(rgbOf('#94A3B8'))
  })

  it('主体档案的值渲染为胶囊（结构与文案；绿底 #ECFDF5 / 绿字 #15803D 由 tokens 落在 CSS → 颜色证据见 H5 computed-style）', async () => {
    const wrapper = await mountPage()
    const pill = wrapper.find('[data-testid="row-profile"] .row__pill')
    expect(pill.exists()).toBe(true)
    expect(pill.text()).toBe('100%')
    expect(wrapper.find('[data-testid="row-profile"] .row__pill-text').exists()).toBe(true)
  })

  it('银行/设置行没有胶囊', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="row-credentials"] .row__pill').exists()).toBe(false)
    expect(wrapper.find('[data-testid="row-settlement"] .row__pill').exists()).toBe(false)
  })

  it('报价卡与证照卡各有 3 条行分隔线（设计树 kids：横分隔1~3 / 横分隔4~6 —— 第 4/5 行之间无分隔）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('.card--entries .row__sep').length).toBe(3)
    expect(wrapper.findAll('.card--records .row__sep').length).toBe(3)
  })
})

describe('序号 21 · 底部 TabBar（共享组件）', () => {
  it('4 项且高亮「我的」，高亮色 = 本帧 #2563EB', async () => {
    const wrapper = await mountPage()
    const items = wrapper.findAll('[data-testid^="tab-"]')
    expect(items.map((i) => i.find('.tabbar__label').text())).toEqual(['工作台', '报告', '报价', '我的'])
    expect(wrapper.find('.tabbar__label--active').text()).toBe('我的')
    expect(wrapper.find('.tabbar__label--active').attributes('style')).toContain(rgbOf('#2563EB'))
  })
})

describe('序号 21 · 取数与只读性', () => {
  it('首屏只读：7 个 GET、0 个写请求，路径与过滤条件与真源一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.mine').exists()).toBe(true)
    const calls = getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
    expect(calls.map((c) => c.url)).toEqual([
      '/api/v1/provider/profile',
      '/api/v1/payments',
      '/api/v1/quotes',
      '/api/v1/reports',
      '/api/v1/contracts',
      '/api/v1/credentials',
      '/api/v1/notifications'
    ])
    expect(calls.every((c) => c.method === 'GET')).toBe(true)
    expect((calls[4].data as Record<string, unknown>).status).toBe('PENDING_SIGN')
    expect((calls[6].data as Record<string, unknown>).unread).toBe('true')
  })

  it('计数接口只取一页（pageSize=1，只为拿 total）', async () => {
    await mountPage()
    const calls = getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
    for (const i of [2, 3, 4, 5, 6]) {
      expect((calls[i].data as Record<string, unknown>).pageSize).toBe(1)
    }
  })

  it('接口失败：提示占位文案，页面仍渲染（占位「—」，不崩）', async () => {
    pushResponse({ statusCode: 500, data: { code: 'E-5001', message: 'boom' } })
    pushResponse({ statusCode: 500, data: { code: 'E-5001', message: 'boom' } })
    pushResponse({ statusCode: 500, data: { code: 'E-5001', message: 'boom' } })
    pushResponse({ statusCode: 500, data: { code: 'E-5001', message: 'boom' } })
    pushResponse({ statusCode: 500, data: { code: 'E-5001', message: 'boom' } })
    pushResponse({ statusCode: 500, data: { code: 'E-5001', message: 'boom' } })
    pushResponse({ statusCode: 500, data: { code: 'E-5001', message: 'boom' } })
    const wrapper = mount(MinePage)
    await flushPromises()
    expect(wrapper.find('.mine').exists()).toBe(true)
    expect(wrapper.find('[data-testid="mine-company"]').text()).toBe('—')
    const toast = getCalls('showToast')[0]?.args[0] as Record<string, unknown>
    expect(toast?.title).toBe('数据加载失败，请稍后重试')
  })

  it('只读页无输入控件', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('input').length).toBe(0)
  })
})
