/**
 * 序号 21【工作台与我的】我的页（page-21-2 / /pages/mine/index）— 视图模型单测（切片 1）
 *
 * 文案/结构真源：.calicat/raw/pages/page-21-2/design.tree.json
 *   （430 宽 · 设计总高 990 · 用户头部 128 · 钱包卡 192 · 报价入口卡 299 · 主体与证照卡 235 · TabBar 84）
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md
 *   Provider /provider/profile · Quote /quotes · Report /reports · Contract /contracts ·
 *   Credential /credentials · Usage · Audit/Notification /notifications · Payment /payments（前缀 /api/v1）
 *
 * ⚠️ 缺口（一律记台账序号 21 备注，不臆造）：
 *   1. 钱包三金额（可提现余额/待结算/累计结算）在 22 份 PRD 零命中、18-API 无钱包汇总端点 →
 *      按 GET /payments 响应里的汇总字段容错读取，缺字段渲染占位「—」；
 *   2. 「提现」18-API 无端点，且 02-需求澄清 One-Pager 写「供应商侧资金结算/提现（走线下）」→
 *      设计稿有按钮、PRD 说明走线下 = 设计/PRD 冲突（记台账，不静默解决）；
 *   3. 「已认证」在 22 份 PRD 零命中 → 服务端 verified 字段优先，其次 status=PUBLISHED；
 *   4. 各入口右侧计数（N 个 / N 份 / 待签署 N / 待阅读 N / N 条 / N%）无汇总接口 → 由各模块列表接口取数。
 */
import { describe, expect, it } from 'vitest'
import {
  BOUND_TEXT,
  CREDENTIALS_PAGE,
  EMPTY_VALUE,
  MESSAGES_PAGE,
  MINE_PAGE,
  PENDING_LABEL,
  PROFILE_PAGE,
  QUOTES_PAGE,
  REPORT_PAGE,
  SETTINGS_PAGE,
  SETTLED_LABEL,
  USAGE_PAGE,
  VERIFIED_TEXT,
  WALLET_AVAILABLE_LABEL,
  WALLET_TITLE,
  WITHDRAW_TEXT,
  buildMineHead,
  buildMineModel,
  buildWallet,
  completenessText,
  contractsCountText,
  countOf,
  credentialsCountText,
  formatMoney,
  messagesCountText,
  quotesCountText,
  reportsCountText,
  rowByKey
} from '@/utils/mine-model'

describe('序号 21 · 设计文案常量（design.tree.json 逐字）', () => {
  it('钱包卡文案', () => {
    expect(WALLET_TITLE).toBe('我的钱包')
    expect(WALLET_AVAILABLE_LABEL).toBe('可提现余额')
    expect(WITHDRAW_TEXT).toBe('提现')
    expect(PENDING_LABEL).toBe('待结算')
    expect(SETTLED_LABEL).toBe('累计结算')
  })

  it('头部/证照文案', () => {
    expect(VERIFIED_TEXT).toBe('已认证')
    expect(BOUND_TEXT).toBe('已绑定')
    expect(EMPTY_VALUE).toBe('—')
  })

  it('路由常量（画布已实现页 + 未实现页登记在册）', () => {
    expect(MINE_PAGE).toBe('/pages/mine/index')
    expect(QUOTES_PAGE).toBe('/pages/quotes/index')
    expect(REPORT_PAGE).toBe('/pages/report/index')
    expect(MESSAGES_PAGE).toBe('/pages/messages/index')
    expect(PROFILE_PAGE).toBe('/pages/profile/index')
    expect(CREDENTIALS_PAGE).toBe('/pages/credentials/index')
    expect(USAGE_PAGE).toBe('/pages/usage/index')
    expect(SETTINGS_PAGE).toBe('/pages/settings/index')
  })
})

describe('序号 21 · formatMoney（设计帧三种写法）', () => {
  it('可提现余额 → 两位小数千分位「¥12,860.00」', () => {
    expect(formatMoney(12860, 2)).toBe('¥12,860.00')
  })

  it('待结算 → 整数千分位「¥3,240」', () => {
    expect(formatMoney(3240, 0)).toBe('¥3,240')
  })

  it('累计结算 → 整数千分位「¥86,420」', () => {
    expect(formatMoney(86420, 0)).toBe('¥86,420')
  })

  it('字符串金额（服务端直出）原样保留，不重复格式化', () => {
    expect(formatMoney('¥12,860.00', 2)).toBe('¥12,860.00')
  })

  it('数字字符串按数值格式化', () => {
    expect(formatMoney('3240', 0)).toBe('¥3,240')
  })

  it('缺值/非法值 → 占位「—」（不编造 0）', () => {
    expect(formatMoney(undefined, 2)).toBe(EMPTY_VALUE)
    expect(formatMoney(null, 0)).toBe(EMPTY_VALUE)
    expect(formatMoney('', 0)).toBe(EMPTY_VALUE)
    expect(formatMoney('abc', 0)).toBe(EMPTY_VALUE)
  })

  it('0 是合法金额', () => {
    expect(formatMoney(0, 0)).toBe('¥0')
    expect(formatMoney(0, 2)).toBe('¥0.00')
  })
})

describe('序号 21 · 计数文案（设计帧逐字）', () => {
  it('我的报价单 → 「3 个」', () => {
    expect(quotesCountText(3)).toBe('3 个')
  })

  it('检测报告 → 「2 份」', () => {
    expect(reportsCountText(2)).toBe('2 份')
  })

  it('我的合同 → 「待签署 1」', () => {
    expect(contractsCountText(1)).toBe('待签署 1')
  })

  it('我的消息 → 「待阅读 3」', () => {
    expect(messagesCountText(3)).toBe('待阅读 3')
  })

  it('接入凭证 → 「3 条」', () => {
    expect(credentialsCountText(3)).toBe('3 条')
  })

  it('主体档案 → 「100%」', () => {
    expect(completenessText(100)).toBe('100%')
    expect(completenessText(72)).toBe('72%')
  })

  it('计数缺失 → 占位「—」（不冒充 0）', () => {
    expect(quotesCountText(undefined)).toBe(EMPTY_VALUE)
    expect(reportsCountText(null)).toBe(EMPTY_VALUE)
    expect(contractsCountText(undefined)).toBe(EMPTY_VALUE)
    expect(messagesCountText(undefined)).toBe(EMPTY_VALUE)
    expect(credentialsCountText(undefined)).toBe(EMPTY_VALUE)
    expect(completenessText(undefined)).toBe(EMPTY_VALUE)
  })

  it('计数为 0 时如实渲染', () => {
    expect(quotesCountText(0)).toBe('0 个')
    expect(messagesCountText(0)).toBe('待阅读 0')
  })
})

describe('序号 21 · countOf（列表响应容错取数）', () => {
  it('total 优先', () => {
    expect(countOf({ total: 7, items: [1, 2, 3] })).toBe(7)
  })

  it('无 total → 取 items/list/records 长度', () => {
    expect(countOf({ items: [1, 2] })).toBe(2)
    expect(countOf({ list: [1, 2, 3] })).toBe(3)
    expect(countOf({ records: [1] })).toBe(1)
  })

  it('裸数组', () => {
    expect(countOf([1, 2, 3, 4])).toBe(4)
  })

  it('无响应 → null（占位，不当成 0）', () => {
    expect(countOf(null)).toBeNull()
    expect(countOf(undefined)).toBeNull()
    expect(countOf({})).toBeNull()
  })

  it('total 为 0 时是 0，不是 null', () => {
    expect(countOf({ total: 0, items: [] })).toBe(0)
  })
})

describe('序号 21 · buildMineHead（用户头部）', () => {
  it('公司名取 company_name（snake_case 数据字典口径）', () => {
    expect(buildMineHead({ company_name: '云智科技有限公司' }).company).toBe('云智科技有限公司')
  })

  it('兼容 companyName（camel 容错）', () => {
    expect(buildMineHead({ companyName: '云智科技有限公司' }).company).toBe('云智科技有限公司')
  })

  it('供应商类型码 → 设计稿标签（复用 profile-model.industryLabel 口径）', () => {
    expect(buildMineHead({ industry_category: 'RESELLER' }).typeLabel).toBe('渠道商')
    expect(buildMineHead({ industry_category: 'ORIGINAL' }).typeLabel).toBe('原厂')
    expect(buildMineHead({ industry_category: 'AGGREGATOR' }).typeLabel).toBe('中转商')
  })

  it('未知/缺失类型 → 空串（不臆造标签、也不编造空 chip）', () => {
    expect(buildMineHead({}).typeLabel).toBe('')
    expect(buildMineHead({ industry_category: 'UNKNOWN' }).typeLabel).toBe('')
  })

  it('已认证：verified / is_verified 布尔优先', () => {
    expect(buildMineHead({ verified: true }).verified).toBe(true)
    expect(buildMineHead({ is_verified: true }).verified).toBe(true)
    expect(buildMineHead({ verified: false }).verified).toBe(false)
  })

  it('已认证：无布尔字段时退 status=PUBLISHED（PRD 供应商状态机第 10 态）', () => {
    expect(buildMineHead({ status: 'PUBLISHED' }).verified).toBe(true)
    expect(buildMineHead({ status: 'DETECTING' }).verified).toBe(false)
  })

  it('缺档案 → 公司名占位「—」、无 chip', () => {
    const head = buildMineHead(null)
    expect(head.company).toBe(EMPTY_VALUE)
    expect(head.typeLabel).toBe('')
    expect(head.verified).toBe(false)
  })

  it('完整度随头部一起给（用于主体档案行）', () => {
    expect(buildMineHead({ completeness: 100 }).completeness).toBe('100%')
  })
})

describe('序号 21 · buildWallet（钱包三金额）', () => {
  it('读取汇总字段（available_balance / pending_settlement / total_settled）', () => {
    const wallet = buildWallet({
      available_balance: 12860,
      pending_settlement: 3240,
      total_settled: 86420
    })
    expect(wallet.available).toBe('¥12,860.00')
    expect(wallet.pending).toBe('¥3,240')
    expect(wallet.settled).toBe('¥86,420')
  })

  it('兼容 balance / pending / settled 别名', () => {
    const wallet = buildWallet({ balance: 12860, pending: 3240, settled: 86420 })
    expect(wallet.available).toBe('¥12,860.00')
    expect(wallet.pending).toBe('¥3,240')
    expect(wallet.settled).toBe('¥86,420')
  })

  it('兼容嵌套 summary 与 camel 命名', () => {
    const wallet = buildWallet({ summary: { availableBalance: 1, pendingSettlement: 2, totalSettled: 3 } })
    expect(wallet.available).toBe('¥1.00')
    expect(wallet.pending).toBe('¥2')
    expect(wallet.settled).toBe('¥3')
  })

  it('缺字段 → 逐项占位「—」', () => {
    const wallet = buildWallet(null)
    expect(wallet.available).toBe(EMPTY_VALUE)
    expect(wallet.pending).toBe(EMPTY_VALUE)
    expect(wallet.settled).toBe(EMPTY_VALUE)
  })

  it('字符串金额直出（服务端已带 ¥ 与千分位）', () => {
    const wallet = buildWallet({ available_balance: '¥12,860.00' })
    expect(wallet.available).toBe('¥12,860.00')
  })
})

describe('序号 21 · buildMineModel（两卡入口行）', () => {
  const model = () =>
    buildMineModel({
      profile: { company_name: '云智科技有限公司', industry_category: 'RESELLER', verified: true, completeness: 100 },
      wallet: { available_balance: 12860, pending_settlement: 3240, total_settled: 86420 },
      counts: { quotes: 3, reports: 2, contracts: 1, credentials: 3, unread: 3 }
    })

  it('9 个入口行按设计顺序（报价卡 5 行 + 证照卡 4 行）', () => {
    expect(model().rows.map((r) => r.label)).toEqual([
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

  it('分组：前 5 行属报价入口卡、后 4 行属主体与证照卡', () => {
    const rows = model().rows
    expect(rows.slice(0, 5).every((r) => r.group === 'quote')).toBe(true)
    expect(rows.slice(5).every((r) => r.group === 'profile')).toBe(true)
  })

  it('右侧值逐行与设计一致', () => {
    const rows = model().rows
    expect(rows.map((r) => r.value)).toEqual(['3 个', '2 份', '待签署 1', '', '待阅读 3', '100%', '3 条', '已绑定', ''])
  })

  it('图标底色/字形色逐行与设计一致', () => {
    const rows = model().rows
    expect(rows.map((r) => r.iconBg)).toEqual([
      '#EFF6FF',
      '#ECFDF5',
      '#FFF7ED',
      '#FAF5FF',
      'rgba(255,149,0,0.03)',
      '',
      '',
      '',
      ''
    ])
    expect(rows.map((r) => r.iconColor)).toEqual([
      '#2563EB',
      '#16A34A',
      '#D97706',
      '#7C3AED',
      '#FF9500',
      '#94A3B8',
      '#94A3B8',
      '#94A3B8',
      '#94A3B8'
    ])
  })

  it('落点：已实现页给路由，未实现页也登记（不静默丢）', () => {
    const rows = model().rows
    expect(rowByKey(model(), 'quotes')?.target).toBe(QUOTES_PAGE)
    expect(rowByKey(model(), 'reports')?.target).toBe(REPORT_PAGE)
    expect(rowByKey(model(), 'messages')?.target).toBe(MESSAGES_PAGE)
    expect(rowByKey(model(), 'profile')?.target).toBe(PROFILE_PAGE)
    expect(rowByKey(model(), 'credentials')?.target).toBe(CREDENTIALS_PAGE)
    // 序号 22 / 23 未实现：目标路由预置（跳转由 uni 侧降级，台账已记）
    expect(rowByKey(model(), 'usage')?.target).toBe(USAGE_PAGE)
    expect(rowByKey(model(), 'settings')?.target).toBe(SETTINGS_PAGE)
  })

  it('结算账户无落点 → target 空串（画布无结算账户页，记台账阻塞）', () => {
    // 2026-09-25：结算单页（SET-01/02）落地，「结算账户」入口由「无落点」改为真实跳转。
    // 原先这里断言 target === ''（无落点阻塞）—— 缺口关闭，断言同步收紧。
    expect(rowByKey(model(), 'settlement')?.target).toBe('/pages/settlements/index')
  })

  it('值色：我的合同「待签署 1」= 警示橙、我的消息 = 纯黑、主体档案 = 绿胶囊、其余灰', () => {
    expect(rowByKey(model(), 'contracts')?.valueTone).toBe('warning')
    expect(rowByKey(model(), 'messages')?.valueTone).toBe('plain')
    expect(rowByKey(model(), 'profile')?.valueTone).toBe('success')
    expect(rowByKey(model(), 'quotes')?.valueTone).toBe('muted')
    expect(rowByKey(model(), 'credentials')?.valueTone).toBe('muted')
  })

  it('主体档案的值是胶囊（h20 r10 绿底）', () => {
    expect(rowByKey(model(), 'profile')?.pill).toBe(true)
    expect(rowByKey(model(), 'credentials')?.pill).toBe(false)
  })

  it('钱包与头部一起产出', () => {
    const m = model()
    expect(m.head.company).toBe('云智科技有限公司')
    expect(m.head.verified).toBe(true)
    expect(m.wallet.available).toBe('¥12,860.00')
    expect(m.wallet.pending).toBe('¥3,240')
    expect(m.wallet.settled).toBe('¥86,420')
  })

  it('空数据也能渲染（每行占位、无值行保持无值）', () => {
    const m = buildMineModel({})
    expect(m.rows.length).toBe(9)
    expect(rowByKey(m, 'quotes')?.value).toBe(EMPTY_VALUE)
    expect(rowByKey(m, 'usage')?.value).toBe('')
  })
})
