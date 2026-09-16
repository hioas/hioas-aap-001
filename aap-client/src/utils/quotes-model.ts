/**
 * 序号 8【报价管理】报价单列表（page-8-2）视图模型
 *
 * 设计真源：.calicat/raw/pages/page-8-2/design.tree.json
 *   筛选行 0bf46fd6/33be05d4/d4c61d43/cf22a9a9/ba2b8609/10b7c5cc：全部·草稿·已提交·已驳回·待签署·已完成
 *     （chip 高 30 · r10 · padding 0/12 · 间距 9；active #2563EB 白字 / inactive #F1F5F9 + #64748B）
 *   卡片 9057868c：标题 930bc97e 15px SemiBold #0F172A · 状态胶囊 22 高 r11（dot 8×6 + 11px Medium）
 *     草稿标 bea2086e #F1F5F9/#94A3B8/#64748B · 已提交标 9bc8ae41 #EFF6FF/#2563EB ·
 *     已驳回标 c499f3ee #FEF2F2/#DC2626/#B91C1C · 已通过标（待签署）c426702b #FFFCEB/#FF9500 ·
 *     已通过标（已完成）caf3547f #F0FDF4/#16A34A/#15803D
 *   单号行：70696608「报价单号」13px SemiBold #334155 + f057dca5 单号 10px Medium #94A3B8（间距 8）
 *   元信息 ac24812b…10b7127f 11px #94A3B8：「2 个模型 · CNY · 更新于 06-14 15:20」
 *   操作行 3d09fef9：图标 16px + 文字 13px Medium #2563EB（无红删除；设计稿里「删除」也是蓝 #2563EB）
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Quote」→ /quotes、/{quoteId}（前缀 /api/v1）
 * 状态真源：.calicat/prd/17-零歧义执行规格spec §QuoteStatus = DRAFT/SUBMITTED/REVIEWING/REJECTED/APPROVED/CONVERTED
 *          + .calicat/prd/10-报价与合同结算PRD §4.1（另有 IN_REVIEW / CONTRACT_CREATED / VOID 口径）
 * 字段真源：.calicat/prd/10-报价与合同结算PRD §3.1 Quote（quote_no/status/version/currency/valid_from/valid_to/
 *          remark/reject_reason(码/文本)/submitted_at/contract_id）+ §3.2 QuoteItem
 *
 * ⚠️ 未定义/缺口（已记 .agents/state/aap-feature-status.csv 序号 8 备注，均不臆造）：
 *   1) 卡片标题「2024Q3 主线路报价」在 PRD Quote 无对应字段（10-PRD §3.1 与 17-spec 均只有 quote_no/status/…）
 *      → 前端只消费 title/name（字段级记 missing-prd），缺失时用占位符，不拿单号冒充标题。
 *   2) 「N 个模型」的计数来源未定义 → 优先 item_count，其次 items.length（记 missing-prd）。
 *   3) 「更新于」的时间字段未在 18-API 列出 → 消费 updated_at（审计字段，记 missing-prd）。
 *   4) 18-API 卡片只列路径未列方法/查询参数 → GET /quotes 与 status 过滤值为 REST 语义推断（missing-prd）。
 *   5) 设计 6 个筛选 chip 与 QuoteStatus 6 值不是一一对应：设计无「审核中」chip（REVIEWING 归入「已提交」）；
 *      「待签署/已完成」是合同阶段口径（10-PRD §4.2），Quote 侧只有 APPROVED/CONVERTED → 记冲突待人类拍板。
 *   6) 设计操作行只有 报价/预览/(签署|合同)/删除，无 PRD §4.1 状态-动作矩阵里的 提交/撤回/作废
 *      → 「删除」按 DELETE /quotes/{quoteId} 实现（作废 VOID 口径待拍板）。
 */
import { PLACEHOLDER } from './format'

export const PAGE_TITLE = '报价单'
/** 顶部导航右侧按钮（design id=7ccb56ba） */
export const NEW_QUOTE_TEXT = '新建报价'
/** 单号行标签（design id=70696608） */
export const QUOTE_NO_LABEL = '报价单号'
/** 设计稿无空态稿 → 占位文案（记 missing-prd，不臆造更细的文案） */
export const EMPTY_TEXT = '暂无报价单'
/** 与序号 3 凭证列表一致的单页条数（18-API 分页默认 20 上限 200） */
export const PAGE_SIZE = 10

/** 元信息行分隔点（design fd63dfdb / 9cafcec1：设计里是独立文本节点「·」，节点之间 8px） */
export const META_SEPARATOR = '·'

/**
 * 把 `metaText` 还原成设计里的 5 个节点：['2 个模型', '·', 'CNY', '·', '更新于 06-14 15:20']。
 * 设计里这 5 个节点之间是 **8px 间距**（container padding-left 8），不是空格字符 ——
 * 页面必须按节点渲染，分隔点单独用更浅的灰 #CBD5E1，否则字距与色值都会偏离设计。
 */
export function metaParts(metaText: string): string[] {
  const out: string[] = []
  metaText.split(` ${META_SEPARATOR} `).forEach((seg, i) => {
    if (i) out.push(META_SEPARATOR)
    out.push(seg)
  })
  return out
}

/** 页面路由（目标来自台账 aap-feature-status.csv 的目标路由列 = 画布页码） */
export const QUOTE_FORM_PAGE = '/pages/quote-form/index'
export const QUOTE_PREVIEW_PAGE = '/pages/quote-preview/index'
export const CONTRACT_PAGE = '/pages/contract/index'

export type QuoteStatusKey = 'draft' | 'submitted' | 'rejected' | 'pending_sign' | 'completed' | 'void'
export type QuoteChipKey = 'draft' | 'submitted' | 'rejected' | 'pending_sign' | 'completed'
export type QuoteFilterKey = 'all' | QuoteChipKey

/** 设计稿 5 个状态胶囊（形状与配色逐值取自 design.tree.json） */
export const STATUS_META: Record<QuoteChipKey, { label: string; bg: string; dot: string; text: string }> = {
  draft: { label: '草稿', bg: '#f1f5f9', dot: '#94a3b8', text: '#64748b' },
  submitted: { label: '已提交', bg: '#eff6ff', dot: '#2563eb', text: '#2563eb' },
  rejected: { label: '已驳回', bg: '#fef2f2', dot: '#dc2626', text: '#b91c1c' },
  pending_sign: { label: '待签署', bg: '#fffceb', dot: '#ff9500', text: '#ff9500' },
  completed: { label: '已完成', bg: '#f0fdf4', dot: '#16a34a', text: '#15803d' }
}

/** 设计稿 5 态顺序（卡片样例自上而下 = 草稿/已提交/已驳回/待签署/已完成） */
export const STATUS_ORDER: QuoteChipKey[] = ['draft', 'submitted', 'rejected', 'pending_sign', 'completed']

/** 设计稿外状态（如 VOID 作废）用中性灰：设计无该态，不借用已知态配色 */
export const NEUTRAL_META = { bg: '#f1f5f9', dot: '#94a3b8', text: '#64748b' }

/** 设计稿外但在 PRD 里明确存在的状态文案（10-PRD §4.1 VOID 作废） */
const EXTRA_LABELS: Record<string, string> = { void: '作废' }

/** 筛选 chip（design 顺序：全部 → 草稿 → 已提交 → 已驳回 → 待签署 → 已完成） */
export const FILTERS: Array<{ key: QuoteFilterKey; label: string }> = [
  { key: 'all', label: '全部' },
  { key: 'draft', label: '草稿' },
  { key: 'submitted', label: '已提交' },
  { key: 'rejected', label: '已驳回' },
  { key: 'pending_sign', label: '待签署' },
  { key: 'completed', label: '已完成' }
]

/** 服务端 QuoteStatus → 设计稿 5 态（含 10-PRD/14-领域模型 的别名口径） */
const STATUS_ALIAS: Record<string, QuoteStatusKey> = {
  DRAFT: 'draft',
  SUBMITTED: 'submitted',
  REVIEWING: 'submitted',
  IN_REVIEW: 'submitted',
  UNDER_REVIEW: 'submitted',
  REJECTED: 'rejected',
  APPROVED: 'pending_sign',
  CONTRACT_CREATED: 'pending_sign',
  CONVERTED: 'completed',
  VOID: 'void'
}

export function statusKeyOf(raw?: string | null): QuoteStatusKey | undefined {
  if (!raw || typeof raw !== 'string') return undefined
  return STATUS_ALIAS[raw.trim().toUpperCase()]
}

/**
 * 筛选 chip → GET /quotes 的 status 取值集合（undefined = 不带过滤）。
 * ⚠️ 查询参数名与取值集合为推断（18-API 只列路径），已记 missing-prd。
 */
export function filterStatusQuery(key: QuoteFilterKey): string[] | undefined {
  switch (key) {
    case 'draft':
      return ['DRAFT']
    case 'submitted':
      return ['SUBMITTED', 'REVIEWING']
    case 'rejected':
      return ['REJECTED']
    case 'pending_sign':
      return ['APPROVED', 'CONTRACT_CREATED']
    case 'completed':
      return ['CONVERTED']
    default:
      return undefined
  }
}

/** RFC3339 → 「MM-DD HH:mm」（设计稿「更新于 06-14 15:20」）。只截取服务端字符串，不做时区换算。 */
export function formatUpdatedAt(value?: string | null): string {
  if (!value || typeof value !== 'string') return PLACEHOLDER
  const m = value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (!m) return PLACEHOLDER
  return `${m[2]}-${m[3]} ${m[4]}:${m[5]}`
}

/** 操作行链接（设计稿：图标 16px + 13px 文字，四/三个动作） */
export type QuoteActionKey = 'quote' | 'preview' | 'sign' | 'contract' | 'delete'

export const ACTION_LABELS: Record<QuoteActionKey, string> = {
  quote: '报价',
  preview: '预览',
  sign: '签署',
  contract: '合同',
  delete: '删除'
}

export interface QuoteAction {
  key: QuoteActionKey
  label: string
  kind: 'navigation' | 'api'
  /** kind=navigation：目标路由（带 id 入参） */
  url?: string
  /** kind=api：调用标识（页面侧映射到 quoteApi） */
  api?: 'deleteQuote'
}

/** GET /quotes 行（字段名取自 10-PRD §3.1 Quote / §3.2 QuoteItem；field-level schema 记 missing-prd） */
export interface QuoteRowRaw {
  id?: string
  /** ⚠️ PRD Quote 无标题字段 → 仅在服务端返回时消费（missing-prd） */
  title?: string
  name?: string
  /** 10-PRD §3.1 quote_no（Q{yyyyMMdd}{6位序列}） */
  quote_no?: string
  /** 17-spec QuoteStatus */
  status?: string
  /** 10-PRD §3.1 currency（PRD 写 USD；设计稿样例 CNY，原样展示） */
  currency?: string
  /** 明细行条数（missing-prd：优先 item_count，其次 items.length） */
  item_count?: number
  items?: unknown[] | null
  /** 审计字段 updated_at（missing-prd） */
  updated_at?: string
  /** 10-PRD §3.1 contract_id（签署/合同链接入参） */
  contract_id?: string | null
}

export interface QuoteListRaw {
  total?: number
  items?: QuoteRowRaw[] | null
}

export interface QuoteRow {
  id: string
  title: string
  quoteNo: string
  statusKey?: QuoteStatusKey
  statusLabel: string
  statusBg: string
  statusDot: string
  statusText: string
  metaText: string
  actions: QuoteAction[]
}

export interface QuotesModel {
  active: QuoteFilterKey
  activeStatusQuery?: string[]
  filters: Array<{ key: QuoteFilterKey; label: string }>
  rows: QuoteRow[]
  emptyText: string
}

function modelCount(raw: QuoteRowRaw): number {
  if (typeof raw.item_count === 'number' && raw.item_count >= 0) return raw.item_count
  return Array.isArray(raw.items) ? raw.items.length : 0
}

/** 逐卡操作由状态派生（设计稿：草稿/已提交/已驳回 = 报价·预览·删除；待签署多「签署」；已完成多「合同」） */
function actionsOf(id: string, key: QuoteStatusKey | undefined, contractId?: string | null): QuoteAction[] {
  const actions: QuoteAction[] = [
    { key: 'quote', label: ACTION_LABELS.quote, kind: 'navigation', url: `${QUOTE_FORM_PAGE}?quoteId=${id}` },
    { key: 'preview', label: ACTION_LABELS.preview, kind: 'navigation', url: `${QUOTE_PREVIEW_PAGE}?quoteId=${id}` }
  ]
  if (key === 'pending_sign') {
    actions.push({
      key: 'sign',
      label: ACTION_LABELS.sign,
      kind: 'navigation',
      url: contractId ? `${CONTRACT_PAGE}?contractId=${contractId}` : CONTRACT_PAGE
    })
  }
  if (key === 'completed') {
    actions.push({
      key: 'contract',
      label: ACTION_LABELS.contract,
      kind: 'navigation',
      url: contractId ? `${CONTRACT_PAGE}?contractId=${contractId}` : CONTRACT_PAGE
    })
  }
  actions.push({ key: 'delete', label: ACTION_LABELS.delete, kind: 'api', api: 'deleteQuote' })
  return actions
}

function toRow(raw: QuoteRowRaw, index: number): QuoteRow {
  const id = raw.id || `row-${index}`
  const key = statusKeyOf(raw.status)
  // 设计稿 5 态用设计配色；VOID 与未知状态用中性灰 + 原样/PRD 文案（不静默归入某个已知态）
  const meta = key && key !== 'void' ? STATUS_META[key] : NEUTRAL_META
  const label = key ? EXTRA_LABELS[key] ?? STATUS_META[key as QuoteChipKey].label : raw.status?.trim() || PLACEHOLDER
  const title = raw.title || raw.name || PLACEHOLDER
  return {
    id,
    title,
    quoteNo: raw.quote_no || PLACEHOLDER,
    statusKey: key,
    statusLabel: label,
    statusBg: meta.bg,
    statusDot: meta.dot,
    statusText: meta.text,
    metaText: `${modelCount(raw)} 个模型 · ${raw.currency || PLACEHOLDER} · 更新于 ${formatUpdatedAt(raw.updated_at)}`,
    actions: actionsOf(id, key, raw.contract_id)
  }
}

export function buildQuotesModel(raw?: QuoteListRaw | null, active: QuoteFilterKey = 'all'): QuotesModel {
  const items = Array.isArray(raw?.items) ? (raw!.items as QuoteRowRaw[]) : []
  return {
    active,
    activeStatusQuery: filterStatusQuery(active),
    filters: FILTERS,
    rows: items.map(toRow),
    emptyText: EMPTY_TEXT
  }
}
