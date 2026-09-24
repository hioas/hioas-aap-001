/**
 * 结算单视图模型（SET-01 列表 / SET-02 详情）。
 *
 * 为什么有这一层：页面只做渲染，取数与口径解析放这里，便于单测固定口径 ——
 * 金额口径必须与后端 SettlementService 一致（净额 = 总额 − 平台费），前端**不重新推导**。
 *
 * 真源缺口背景：`.calicat/prd/12-供应商端PRD.md` 是空壳（18 字节一行标题），
 * 客户端 PRD 全文不提结算/对账 ⇒ 供应商侧此前零结算端点。后端按 D-SETTLE-02 补上
 * SET-01/02 后，本模块负责把它渲染成供应商看得懂的形态。
 */

export const STATEMENT_STATUS_LABEL: Record<string, string> = {
  DRAFT: '待平台确认',
  CONFIRMED: '已出账',
  VOID: '已作废'
}

export interface SettlementLineView {
  key: string
  channel: string
  model: string
  tokens: string
  amount: string
}

export interface SettlementListView {
  id: string
  no: string
  period: string
  total: string
  fee: string
  net: string
  status: string
  statusLabel: string
  /** 状态色（tone → 具体色值由调用方决定；这里只给语义） */
  tone: 'warn' | 'success' | 'muted'
}

const num = (v: unknown): number | null => {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

/** 金额展示：0 与「无数据」必须区分开（缺值渲染占位，不编造 0） */
export function money(v: unknown): string {
  const n = num(v)
  if (n === null) return '—'
  return `¥${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/** 周期展示：YYYY-MM-DD ~ YYYY-MM-DD（后端给 RFC3339，含时区） */
export function period(from: unknown, to: unknown): string {
  const cut = (v: unknown) => (typeof v === 'string' && v.length >= 10 ? v.slice(0, 10) : '')
  const a = cut(from)
  const b = cut(to)
  if (!a && !b) return '—'
  return `${a || '?'} ~ ${b || '?'}`
}

function pickItems(raw: unknown): unknown[] {
  if (!raw || typeof raw !== 'object') return []
  const o = raw as Record<string, unknown>
  for (const key of ['items', 'list', 'records']) {
    if (Array.isArray(o[key])) return o[key] as unknown[]
  }
  return Array.isArray(raw) ? (raw as unknown[]) : []
}

/**
 * 列表映射。
 *
 * 净额口径：**优先用后端 net_amount**；后端没给才用 总额 − 平台费 现算（与后端同一算式）。
 * 任一项缺值都返回占位「—」，不把缺失算成 0。
 */
export function toSettlementList(raw: unknown): SettlementListView[] {
  return pickItems(raw).map((item, index) => {
    const o = (item || {}) as Record<string, unknown>
    const status = String(o.status ?? '')
    const total = num(o.total_amount)
    const fee = num(o.platform_fee)
    const net = num(o.net_amount) ?? (total === null || fee === null ? null : total - fee)
    const tone: SettlementListView['tone'] =
      status === 'CONFIRMED' ? 'success' : status === 'VOID' ? 'muted' : 'warn'
    return {
      id: String(o.id ?? index),
      no: String(o.statement_no ?? o.id ?? '—'),
      period: period(o.period_from, o.period_to),
      total: money(o.total_amount),
      fee: money(o.platform_fee),
      net: money(net),
      status,
      statusLabel: STATEMENT_STATUS_LABEL[status] ?? status ?? '—',
      tone
    }
  })
}

/** 明细行映射（维度：渠道 × 模型） */
export function toSettlementLines(raw: unknown): SettlementLineView[] {
  const o = (raw || {}) as Record<string, unknown>
  const lines = Array.isArray(o.lines) ? (o.lines as unknown[]) : []
  return lines.map((item, index) => {
    const l = (item || {}) as Record<string, unknown>
    const tokens = num(l.total_tokens)
    return {
      key: String(l.id ?? index),
      channel: String(l.channel_id ?? '—'),
      model: String(l.model_name ?? '—'),
      tokens: tokens === null ? '—' : tokens.toLocaleString('zh-CN'),
      amount: money(l.amount)
    }
  })
}

/** 详情主行（列表字段 + 关联打款笔数） */
export function toSettlementDetail(raw: unknown): SettlementListView & { payments: number } {
  const o = (raw || {}) as Record<string, unknown>
  const list = toSettlementList({ items: [o] })
  const payments = Array.isArray(o.payments) ? (o.payments as unknown[]).length : 0
  return { ...(list[0] as SettlementListView), payments }
}
