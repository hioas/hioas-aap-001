/**
 * 序号 15【合同与通知】合同签署 2（page-15-2）· /pages/contract/index — 视图模型
 *
 * 设计真源：`.calicat/raw/pages/page-15-2/design.tree.json`（430 宽 · 顶栏 96 + 7 卡 + 底栏 84 · 总高 1231）
 *   本文件里的文案常量**逐字抄自该设计树**，不得改写（硬约束 §2）。
 * 状态机真源：10-PRD §4.2「CREATED→PENDING_SIGN→SUPPLIER_SIGNED→SIGNED→ARCHIVED；可 VOIDED 作废」
 * 接口真源：18-API「Contract」Tag → /contracts、/{id}、/contracts/{id}/file、/sign（前缀 /api/v1；
 *   卡片只列路径未列方法与字段级 schema → 本文件按 REST 语义容错读取，记 missing-prd）。
 *
 * ✅ 设计 / PRD 冲突**已拍板**（决策 D7，用户 2026-09-16「保留 a 电子签入口」）：
 *   设计帧写「本合同采用电子签章，签署后即时生效并具备法律效力。」+「签署方式：短信验证码签署」，
 *   而 10-PRD §4.2 / 17-spec R-41 / 数据字典 Contract(sign_channel) 都写「合同线下、线上电子签一期不做」。
 *   → **保留电子签入口**（设计稿优先，与序号 1/11 同口径）；PRD 的「一期不做线上电子签」作为偏差留痕，
 *   线下签署并行存在（`sign_channel` 枚举 ONLINE/OFFLINE 保留、默认值不动）。本文件按设计帧实现，不再改只读。
 */

/* ------------------------------------------------------------------ 设计常量（逐字抄自设计树） */

export const PAGE_TITLE = '合同签署'
export const CARD_BASIC = '合同基本信息'
export const CARD_FEE = '费用与分成'
export const CARD_TERMS = '关键条款'
export const CARD_SIGN = '签署信息'
export const CARD_RECORDS = '签署记录'
export const TIP_TEXT = '本合同采用电子签章，签署后即时生效并具备法律效力。'
export const BTN_PDF = 'PDF'
export const BTN_SIGN = '去签署'

export const LABEL_SUPPLIER = '供应商'
export const LABEL_MODE = '合作模式'
export const LABEL_VALID = '生效期'
export const LABEL_SETTLE = '结算账期'
export const LABEL_FEE_RATE = '平台服务费率'
export const LABEL_CURRENCY = '结算币种'
export const LABEL_MIN_AMOUNT = '最低结算额'
export const LABEL_SIGNER = '签署人'
export const LABEL_PHONE = '手机号'
export const LABEL_SIGN_METHOD = '签署方式'

/** 设计帧的顶栏编号是**单个**文本图层（含「编号 」前缀）→ 必须连前缀一起渲染（同序号 7 报告编号教训） */
export const CONTRACT_NO_PREFIX = '编号 '

/** 缺值占位（设计帧没有空态，占位符为推断；与序号 8/9/12-v3 同口径） */
export const EMPTY_VALUE = '—'

export const CONTRACT_ID_KEY = 'aap_contract_id'

/* ------------------------------------------------------------------ 交互文案（设计帧无 toast/弹窗稿 → 占位，记台账） */

export const TOAST_LOAD_FAIL = '合同加载失败'
export const TOAST_SIGNED = '签署申请已提交'
export const TOAST_NO_FILE = '合同文件尚未生成'
export const TOAST_NO_CONTRACT = '合同信息尚未加载'
export const TOAST_FILE_FAIL = '合同文件获取失败'
export const CONFIRM_SIGN_TITLE = '确认签署'
export const CONFIRM_SIGN_CONTENT = '确认对当前合同发起签署？'

/* ------------------------------------------------------------------ 状态与色（设计帧 + 10-PRD §4.2） */

export type ContractStatus = 'CREATED' | 'PENDING_SIGN' | 'SUPPLIER_SIGNED' | 'SIGNED' | 'ARCHIVED' | 'VOIDED'

export interface StatusChip {
  label: string
  bg: string
  /** 文字色 */
  text: string
}

/** 中性灰（未知状态直显，不编造中文标签） */
const NEUTRAL: StatusChip = { label: '', bg: '#f1f5f9', text: '#64748b' }

/** 设计帧「待签署」标：bg #FFFBEB / 文字 #B45309（= tokens $color-warning-weak-2 / $color-warning-text-3） */
const AMBER: Omit<StatusChip, 'label'> = { bg: '#fffbeb', text: '#b45309' }
const GREEN: Omit<StatusChip, 'label'> = { bg: '#ecfdf5', text: '#15803d' }
const BLUE: Omit<StatusChip, 'label'> = { bg: '#eff6ff', text: '#2563eb' }
const GRAY: Omit<StatusChip, 'label'> = { bg: '#f1f5f9', text: '#64748b' }

const STATUS_LABEL: Record<ContractStatus, string> = {
  CREATED: '待签署',
  PENDING_SIGN: '待签署',
  SUPPLIER_SIGNED: '待确认',
  SIGNED: '已签署',
  ARCHIVED: '已归档',
  VOIDED: '已作废'
}

export function statusChip(status: unknown): StatusChip {
  const key = String(status ?? '').trim().toUpperCase()
  if (!(key in STATUS_LABEL)) {
    // 未知/空 → 原样直显 + 中性灰（不猜中文标签）
    return { ...NEUTRAL, label: String(status ?? '') }
  }
  const label = STATUS_LABEL[key as ContractStatus]
  const tone = key === 'SIGNED' ? GREEN : key === 'ARCHIVED' || key === 'VOIDED' ? GRAY : key === 'SUPPLIER_SIGNED' ? BLUE : AMBER
  return { ...tone, label }
}

/** 签署记录圆点色（设计帧：记录1 绿 #16A34A / 记录2 琥珀 #F59E0B；void 灰为派生推断） */
export type RecordTone = 'success' | 'pending' | 'void'

export const TONE_DOT: Record<RecordTone, string> = {
  success: '#16a34a',
  pending: '#f59e0b',
  void: '#94a3b8'
}

export function recordTone(tone: unknown): RecordTone {
  const key = String(tone ?? '').trim().toLowerCase()
  return key === 'success' || key === 'void' ? key : 'pending'
}

/* ------------------------------------------------------------------ 纯函数 */

/** 顶栏编号（含前缀）；无编号时返回空串（不渲染半个前缀） */
export function navNoText(contractNo: unknown): string {
  const no = String(contractNo ?? '').trim()
  return no ? `${CONTRACT_NO_PREFIX}${no}` : ''
}

/** 设计帧句式：请在 2024-06-20 前完成签署，逾期将自动作废 */
export function deadlineText(deadline: unknown): string {
  const day = String(deadline ?? '').trim()
  return day ? `请在 ${day} 前完成签署，逾期将自动作废` : ''
}

/**
 * 手机号脱敏：设计帧为「138 **** 6621」；R-48 / 18-API 为「138****6621」（口径不一致，已记台账）。
 * 优先用服务端 signer_phone_masked（见 buildContractView），本函数只在只有原号时兜底。
 */
export function maskPhone(phone: unknown): string {
  const p = String(phone ?? '').trim()
  if (!p) return ''
  if (/^\d{11}$/.test(p)) return `${p.slice(0, 3)} **** ${p.slice(7)}`
  return p
}

/** 关键条款序号：设计帧原文自带「1. 」→ 已带序号的不重复加 */
export function numberClauses(list: unknown): string[] {
  if (!Array.isArray(list)) return []
  return list
    .map((t) => String(t ?? '').trim())
    .filter((t) => t !== '')
    .map((t, i) => (/^\d+[.、]/.test(t) ? t : `${i + 1}. ${t}`))
}

/** 生效期：2024-07-01 至 2025-06-30 */
export function validRangeText(from: unknown, to: unknown): string {
  const a = String(from ?? '').trim()
  const b = String(to ?? '').trim()
  if (a && b) return `${a} 至 ${b}`
  return a || b || EMPTY_VALUE
}

/* ------------------------------------------------------------------ 视图模型 */

export interface ContractRow {
  key: string
  label: string
  value: string
}

export interface SignRecord {
  key: string
  title: string
  time: string
  tone: RecordTone
  dot: string
}

export interface ContractView {
  contractNo: string
  navNo: string
  title: string
  status: StatusChip
  hasStatus: boolean
  deadline: string
  basicRows: ContractRow[]
  feeRows: ContractRow[]
  signRows: ContractRow[]
  clauses: string[]
  records: SignRecord[]
}

/** 服务端合同对象（字段级 schema 未定义 → 容错读取，命中任一别名即可；记 missing-prd） */
export interface ContractRaw {
  contract_id?: string
  contract_no?: string
  id?: string
  title?: string
  name?: string
  contract_name?: string
  status?: string
  sign_deadline?: string
  deadline?: string
  expire_sign_at?: string
  supplier_name?: string
  company_name?: string
  cooperation_mode?: string
  mode?: string
  valid_from?: string
  effective_from?: string
  start_date?: string
  valid_to?: string
  effective_to?: string
  end_date?: string
  settlement_cycle?: string
  settlement_terms?: string
  fee_rate?: string
  platform_fee_rate?: string
  currency?: string
  settlement_currency?: string
  min_settlement_amount?: string
  min_amount?: string
  signer_name?: string
  signer?: string
  signer_phone_masked?: string
  phone_masked?: string
  signer_phone?: string
  sign_method?: string
  sign_channel?: string
  terms?: string[]
  clauses?: string[]
  records?: Array<{ title?: string; time?: string; tone?: string; at?: string }>
}

type Raw = Record<string, unknown>

function first(raw: Raw, keys: string[]): string {
  for (const k of keys) {
    const v = raw[k]
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim()
  }
  return ''
}

function value(raw: Raw, keys: string[]): string {
  return first(raw, keys) || EMPTY_VALUE
}

export function buildContractView(input: ContractRaw | null | undefined): ContractView {
  const raw = (input ?? {}) as Raw
  const statusRaw = first(raw, ['status'])
  const deadline = first(raw, ['sign_deadline', 'deadline', 'expire_sign_at'])

  const basicRows: ContractRow[] = [
    { key: 'supplier', label: LABEL_SUPPLIER, value: value(raw, ['supplier_name', 'company_name']) },
    { key: 'mode', label: LABEL_MODE, value: value(raw, ['cooperation_mode', 'mode']) },
    {
      key: 'valid',
      label: LABEL_VALID,
      value: validRangeText(first(raw, ['valid_from', 'effective_from', 'start_date']), first(raw, ['valid_to', 'effective_to', 'end_date']))
    },
    { key: 'settle', label: LABEL_SETTLE, value: value(raw, ['settlement_cycle', 'settlement_terms']) }
  ]

  const feeRows: ContractRow[] = [
    { key: 'feeRate', label: LABEL_FEE_RATE, value: value(raw, ['fee_rate', 'platform_fee_rate']) },
    { key: 'currency', label: LABEL_CURRENCY, value: value(raw, ['currency', 'settlement_currency']) },
    { key: 'minAmount', label: LABEL_MIN_AMOUNT, value: value(raw, ['min_settlement_amount', 'min_amount']) }
  ]

  const masked = first(raw, ['signer_phone_masked', 'phone_masked'])
  const phone = masked || maskPhone(first(raw, ['signer_phone'])) || EMPTY_VALUE
  const signRows: ContractRow[] = [
    { key: 'signer', label: LABEL_SIGNER, value: value(raw, ['signer_name', 'signer']) },
    { key: 'phone', label: LABEL_PHONE, value: phone },
    { key: 'method', label: LABEL_SIGN_METHOD, value: value(raw, ['sign_method', 'sign_channel']) }
  ]

  const recordsRaw = Array.isArray(raw.records) ? (raw.records as Array<Raw>) : []
  const records: SignRecord[] = recordsRaw
    .map((r, i) => {
      const tone = recordTone(r.tone)
      const title = first(r, ['title', 'name'])
      if (!title) return null
      return {
        key: `r${i}`,
        title,
        time: first(r, ['time', 'at']),
        tone,
        dot: TONE_DOT[tone]
      }
    })
    .filter((r): r is SignRecord => r !== null)

  return {
    contractNo: first(raw, ['contract_no']),
    navNo: navNoText(first(raw, ['contract_no'])),
    title: first(raw, ['title', 'name', 'contract_name']),
    status: statusChip(statusRaw),
    hasStatus: statusRaw !== '',
    deadline: deadlineText(deadline),
    basicRows,
    feeRows,
    signRows,
    clauses: numberClauses(raw.terms ?? raw.clauses),
    records
  }
}

/** 合同 id 解析：优先页面栈 query，其次 storage（与序号 11/12-v3 同口径） */
export function resolveContractId(raw: unknown, fromStorage: unknown): string {
  const fromRaw = String(raw ?? '').trim()
  if (fromRaw) return fromRaw
  return String(fromStorage ?? '').trim()
}
