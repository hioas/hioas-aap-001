/**
 * 序号 21【工作台与我的】我的页（page-21-2 / /pages/mine/index）— 视图模型
 *
 * 真源：
 *  - 设计：.calicat/raw/pages/page-21-2/design.tree.json
 *      （430 宽 · 设计总高 990 = 头部 128 + 12 + 钱包卡 192 + 12 + 报价入口卡 299 + 12 + 主体与证照卡 235 + 16 + TabBar 84）
 *      文案逐字：我的钱包 / 可提现余额 / ¥12,860.00 / 提现 / 待结算 / ¥3,240 / 累计结算 / ¥86,420 /
 *      我的报价单 3 个 · 检测报告 2 份 · 我的合同 待签署 1 · 用量与对账 · 我的消息 待阅读 3 ·
 *      主体档案 100% · 接入凭证 3 条 · 结算账户 已绑定 · 账号与设置
 *  - 接口：18-API设计OpenAPI.md（前缀 /api/v1）
 *      Provider /provider/profile · Quote /quotes · Report /reports · Contract /contracts ·
 *      Credential /credentials · Audit/Notification /notifications · Payment /payments
 *
 * ⚠️ 缺口（一律记台账/状态文件，不臆造）：
 *  1. 钱包三金额（可提现余额 / 待结算 / 累计结算）在 22 份 PRD 零命中，18-API 也无钱包汇总端点
 *     → 本模型按 GET /payments 响应里的汇总字段**容错读取**（available_balance/pending_settlement/total_settled
 *     及 balance/pending/settled 等别名，含嵌套 summary/wallet），缺字段渲染占位「—」，不编造 0；
 *  2. 「提现」18-API 无端点，且 02-需求澄清 One-Pager 明写「供应商侧资金结算/提现（走线下）」
 *     → **设计稿有按钮 / PRD 说走线下 = 设计-PRD 冲突**，按设计稿保留按钮，点击只做占位提示（记台账待拍板）；
 *  3. 「已认证」在 22 份 PRD 零命中 → 服务端 verified/is_verified 布尔优先，其次 status==='PUBLISHED'
 *     （17-spec ProviderStatus 11 态里的发布态）；
 *  4. 各入口右侧计数无汇总接口 → 由各模块列表接口逐项取数（quotes/reports/contracts/credentials/notifications），
 *     计数缺失渲染占位「—」，不冒充 0；
 *  5. 「结算账户」—— 2026-09-25 起**已有落点**：后端补上 SET-01/02（供应商端读结算单）后
 *     新增 /pages/settlements/index。此前它在 22 份 PRD 零命中、画布也无对应页 → target 空串（阻塞）。
 *     右侧「已绑定」文案仍无 PRD 依据，保留原样（不臆造）。
 */
import { industryLabel } from './profile-model'

/* ============================== 路由 ============================== */

import {
  CONTRACT_PAGE,
  CREDENTIALS_PAGE,
  MESSAGES_PAGE,
  MINE_PAGE,
  PROFILE_PAGE,
  QUOTES_PAGE,
  REPORT_PAGE,
  SETTINGS_PAGE,
  SETTLEMENT_PAGE,
  USAGE_PAGE,
  WORKBENCH_PAGE
} from './routes'

export {
  CONTRACT_PAGE,
  CREDENTIALS_PAGE,
  MESSAGES_PAGE,
  MINE_PAGE,
  PROFILE_PAGE,
  QUOTES_PAGE,
  REPORT_PAGE,
  SETTINGS_PAGE,
  SETTLEMENT_PAGE,
  USAGE_PAGE,
  WORKBENCH_PAGE
}

/* ============================== 设计文案（逐字，不得改写） ============================== */

export const WALLET_TITLE = '我的钱包'
export const WALLET_AVAILABLE_LABEL = '可提现余额'
export const WITHDRAW_TEXT = '提现'
export const PENDING_LABEL = '待结算'
export const SETTLED_LABEL = '累计结算'
export const VERIFIED_TEXT = '已认证'
export const BOUND_TEXT = '已绑定'
export const EMPTY_VALUE = '—'

/** 失败提示文案：设计稿无 toast 稿 → 占位（与序号 20 同口径，记台账） */
export const LOAD_FAIL_TEXT = '数据加载失败，请稍后重试'
/** 「提现」占位提示（18-API 无提现端点 + PRD「走线下」→ 不臆造流程，只做占位提示） */
export const WITHDRAW_PLACEHOLDER_TEXT = '提现功能暂未开放'

/** 钱包卡标题行右侧 chevron 目标：画布无「钱包/资金」页 → 无落点（记台账阻塞） */
export const WALLET_TARGET = ''

/* ============================== 中性工具 ============================== */

const str = (value: unknown): string => {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return ''
}

const firstStr = (...values: unknown[]): string => {
  for (const v of values) {
    const s = str(v)
    if (s) return s
  }
  return ''
}

const toNumber = (value: unknown): number | null => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const s = str(value)
  if (!s) return null
  const cleaned = s.replace(/[¥,\s]/g, '')
  if (!/^-?\d+(\.\d+)?$/.test(cleaned)) return null
  const n = Number(cleaned)
  return Number.isFinite(n) ? n : null
}

const group = (int: string): string => int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')

/**
 * 金额显示：
 *  - 服务端已带「¥」的字符串 **原样直出**（避免二次格式化把服务端口径改掉）；
 *  - 数字 / 数字字符串 → `¥{千分位}`，decimals=2 时补两位小数（设计：可提现余额两位、待结算/累计结算整数）；
 *  - 缺失 / 非法 → 占位「—」（不编造 0）。
 */
export function formatMoney(value: unknown, decimals: 0 | 2): string {
  if (typeof value === 'string' && value.includes('¥')) return value.trim()
  const n = toNumber(value)
  if (n === null) return EMPTY_VALUE
  const abs = Math.abs(n)
  const fixed = abs.toFixed(decimals)
  const [int, dec] = fixed.split('.')
  const text = `¥${group(int)}${dec ? `.${dec}` : ''}`
  return n < 0 ? `-${text}` : text
}

/** 列表响应容错取数：total 优先，其次 items/list/records 长度，裸数组取长度；无数据 → null（不冒充 0） */
export function countOf(res: unknown): number | null {
  if (Array.isArray(res)) return res.length
  if (!res || typeof res !== 'object') return null
  const src = res as Record<string, unknown>
  if (typeof src.total === 'number' && Number.isFinite(src.total)) return src.total
  const total = toNumber(src.total)
  if (total !== null) return total
  for (const key of ['items', 'list', 'records', 'rows']) {
    const value = src[key]
    if (Array.isArray(value)) return value.length
  }
  return null
}

/** 计数文案：缺值占位「—」，0 如实渲染 */
const suffixText = (suffix: string) => (count: number | null | undefined): string =>
  count === null || count === undefined ? EMPTY_VALUE : `${count}${suffix}`

/** 我的报价单「3 个」 */
export const quotesCountText = (count: number | null | undefined): string =>
  count === null || count === undefined ? EMPTY_VALUE : `${count} 个`

/** 检测报告「2 份」 */
export const reportsCountText = (count: number | null | undefined): string =>
  count === null || count === undefined ? EMPTY_VALUE : `${count} 份`

/** 我的合同「待签署 1」 */
export const contractsCountText = (count: number | null | undefined): string =>
  count === null || count === undefined ? EMPTY_VALUE : `待签署 ${count}`

/** 我的消息「待阅读 3」 */
export const messagesCountText = (count: number | null | undefined): string =>
  count === null || count === undefined ? EMPTY_VALUE : `待阅读 ${count}`

/** 接入凭证「3 条」 */
export const credentialsCountText = suffixText(' 条')

/** 主体档案「100%」 */
export const completenessText = (count: number | null | undefined): string =>
  count === null || count === undefined ? EMPTY_VALUE : `${count}%`

/* ============================== 用户头部 ============================== */

export interface MineProfileSource {
  company_name?: string
  companyName?: string
  industry_category?: string
  status?: string
  verified?: boolean
  is_verified?: boolean
  certified?: boolean
  completeness?: number | string
}

const TYPE_LABELS: Record<string, string> = {
  ORIGINAL: '原厂',
  RESELLER: '渠道商',
  AGGREGATOR: '中转商'
}

export interface MineHeadView {
  company: string
  typeLabel: string
  verified: boolean
  completeness: string
}

/** 头部：企业名 + 类型 chip + 已认证 chip（未知类型码不出 chip，不臆造标签） */
export function buildMineHead(profile?: MineProfileSource | null): MineHeadView {
  const src = profile ?? {}
  const code = str(src.industry_category).toUpperCase()
  const label = TYPE_LABELS[code] ?? industryLabel(code)
  return {
    company: firstStr(src.company_name, src.companyName) || EMPTY_VALUE,
    typeLabel: TYPE_LABELS[code] ?? '',
    verified: resolveVerified(src),
    completeness: completenessText(toNumber(src.completeness))
  }
}

/** 已认证：布尔字段优先（verified/is_verified/certified），其次 status=PUBLISHED */
export function resolveVerified(profile?: MineProfileSource | null): boolean {
  const src = profile ?? {}
  for (const key of ['verified', 'is_verified', 'certified'] as const) {
    const value = src[key]
    if (typeof value === 'boolean') return value
  }
  return str(src.status).toUpperCase() === 'PUBLISHED'
}

/* ============================== 我的钱包 ============================== */

export interface MineWalletSource {
  available_balance?: unknown
  availableBalance?: unknown
  balance?: unknown
  withdrawable?: unknown
  withdrawable_balance?: unknown
  pending_settlement?: unknown
  pendingSettlement?: unknown
  pending?: unknown
  total_settled?: unknown
  totalSettled?: unknown
  settled?: unknown
  summary?: Record<string, unknown>
  wallet?: Record<string, unknown>
}

export interface MineWalletView {
  available: string
  pending: string
  settled: string
}

const walletScopes = (src?: MineWalletSource | null): Record<string, unknown>[] => {
  if (!src || typeof src !== 'object') return []
  const out: Record<string, unknown>[] = [src as Record<string, unknown>]
  for (const key of ['summary', 'wallet'] as const) {
    const nested = (src as Record<string, unknown>)[key]
    if (nested && typeof nested === 'object') out.push(nested as Record<string, unknown>)
  }
  return out
}

const pick = (scopes: Record<string, unknown>[], keys: string[]): unknown => {
  for (const scope of scopes) {
    for (const key of keys) {
      const value = scope[key]
      if (value !== undefined && value !== null && str(value) !== '') return value
    }
  }
  return undefined
}

/**
 * 钱包三金额（可提现余额两位小数 / 待结算 / 累计结算整数）。
 * 字段名与归属为推断（missing-prd）：18-API 无钱包汇总 schema → 容错读取，缺失占位「—」。
 */
export function buildWallet(src?: MineWalletSource | null): MineWalletView {
  const scopes = walletScopes(src)
  return {
    available: formatMoney(
      pick(scopes, ['available_balance', 'availableBalance', 'balance', 'withdrawable', 'withdrawable_balance']),
      2
    ),
    pending: formatMoney(pick(scopes, ['pending_settlement', 'pendingSettlement', 'pending']), 0),
    settled: formatMoney(pick(scopes, ['total_settled', 'totalSettled', 'settled']), 0)
  }
}

/* ============================== 入口行 ============================== */

export type MineRowKey =
  | 'quotes'
  | 'reports'
  | 'contracts'
  | 'usage'
  | 'messages'
  | 'profile'
  | 'credentials'
  | 'settlement'
  | 'settings'

export type MineRowGroup = 'quote' | 'profile'
export type MineValueTone = 'muted' | 'warning' | 'plain' | 'success'

export interface MineRowView {
  key: MineRowKey
  label: string
  group: MineRowGroup
  value: string
  valueTone: MineValueTone
  /** 值是否渲染为胶囊（设计：主体档案「100%」h20 r10 绿底） */
  pill: boolean
  iconBg: string
  iconColor: string
  /** CSS 形状占位类型（图标方案：R-26 禁 emoji / 无图标资源 → 占位，记台账） */
  glyph: string
  target: string
}

/** 入口行静态定义（label/图标取色/落点，逐行来自设计帧 fontFill/fills） */
const ROW_DEFS: Omit<MineRowView, 'value' | 'valueTone'>[] = [
  // 我的报价入口卡（design cda20980）
  { key: 'quotes', label: '我的报价单', group: 'quote', pill: false, iconBg: '#EFF6FF', iconColor: '#2563EB', glyph: 'quote', target: QUOTES_PAGE },
  { key: 'reports', label: '检测报告', group: 'quote', pill: false, iconBg: '#ECFDF5', iconColor: '#16A34A', glyph: 'report', target: REPORT_PAGE },
  { key: 'contracts', label: '我的合同', group: 'quote', pill: false, iconBg: '#FFF7ED', iconColor: '#D97706', glyph: 'contract', target: CONTRACT_PAGE },
  { key: 'usage', label: '用量与对账', group: 'quote', pill: false, iconBg: '#FAF5FF', iconColor: '#7C3AED', glyph: 'usage', target: USAGE_PAGE },
  { key: 'messages', label: '我的消息', group: 'quote', pill: false, iconBg: 'rgba(255,149,0,0.03)', iconColor: '#FF9500', glyph: 'message', target: MESSAGES_PAGE },
  // 主体与证照卡（design cd8b4c81）
  { key: 'profile', label: '主体档案', group: 'profile', pill: true, iconBg: '', iconColor: '#94A3B8', glyph: 'profile', target: PROFILE_PAGE },
  { key: 'credentials', label: '接入凭证', group: 'profile', pill: false, iconBg: '', iconColor: '#94A3B8', glyph: 'credential', target: CREDENTIALS_PAGE },
  { key: 'settlement', label: '结算账户', group: 'profile', pill: false, iconBg: '', iconColor: '#94A3B8', glyph: 'account', target: SETTLEMENT_PAGE },
  { key: 'settings', label: '账号与设置', group: 'profile', pill: false, iconBg: '', iconColor: '#94A3B8', glyph: 'settings', target: SETTINGS_PAGE }
]

/** 值色：我的合同 = 警示橙 · 我的消息 = 纯黑 · 主体档案 = 成功绿 · 其余灰（design fontFill 逐值） */
const VALUE_TONES: Partial<Record<MineRowKey, MineValueTone>> = {
  contracts: 'warning',
  messages: 'plain',
  profile: 'success'
}

export interface MineCounts {
  quotes?: number | null
  reports?: number | null
  contracts?: number | null
  credentials?: number | null
  unread?: number | null
}

export interface MineModelInput {
  profile?: MineProfileSource | null
  wallet?: MineWalletSource | null
  counts?: MineCounts
}

export interface MineModel {
  head: MineHeadView
  wallet: MineWalletView
  rows: MineRowView[]
}

/** 组装页面模型：头部 + 钱包 + 9 个入口行（值缺失一律占位，不臆造业务数字） */
export function buildMineModel(input: MineModelInput = {}): MineModel {
  const head = buildMineHead(input.profile)
  const counts = input.counts ?? {}
  const values: Record<MineRowKey, string> = {
    quotes: quotesCountText(counts.quotes),
    reports: reportsCountText(counts.reports),
    contracts: contractsCountText(counts.contracts),
    usage: '',
    messages: messagesCountText(counts.unread),
    profile: head.completeness,
    credentials: credentialsCountText(counts.credentials),
    settlement: BOUND_TEXT,
    settings: ''
  }
  const rows = ROW_DEFS.map((def) => ({
    ...def,
    value: values[def.key],
    valueTone: VALUE_TONES[def.key] ?? 'muted'
  }))
  return { head, wallet: buildWallet(input.wallet), rows }
}

/** 按 key 取行（页面模板与用例共用） */
export function rowByKey(model: MineModel | null | undefined, key: MineRowKey): MineRowView | undefined {
  return model?.rows.find((row) => row.key === key)
}
