/**
 * 序号 3【工作台与我的】凭证列表-有数据（page-3）视图模型
 *
 * 设计真源：.calicat/raw/pages/page-3/design.tree.json
 *   状态统计行 9da021fa（待检测 3 · 检测中 2 · 不通过 1 · 通过 4）
 *   状态点色值：待检测 4f9fb4ed #94A3B8 / 检测中 0508c90e #2563EB / 不通过 fe5d0365 #EF4444 / 通过 8bf7024e #16A34A
 *   查看列「报告」02c95f41（fontFill #2563EB），仅出现在 通过/不通过 行
 *   底部说明 3bf43b00「仅展示最近接入的 10 条凭证记录」
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Credential」Tag → GET /credentials（前缀 /api/v1）
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md
 *   aap_credential（alias / model_list / created_at）+ aap_detection_job（status QUEUED…、result PASS/FAIL/MANUAL_REVIEW）
 *
 * ⚠️ 未定义/缺口（已记 .agents/state/aap-feature-status.csv 备注列，均不臆造）：
 *   1) 18-API 卡为摘要，GET /credentials 的字段级 schema 未定义（完整 openapi.yaml 不在本仓库）
 *      → 响应字段名按 15-数据字典 aap_credential 映射，记 missing-prd。
 *   2) 设计稿 4 态（待检测/检测中/不通过/通过）与 09-PRD R-25 五分支（PASS/FAIL/MANUAL_REVIEW/不可测…）不是一一对应，
 *      故前端只消费服务端派生的 detection_status（4 态枚举），不自行判定 MANUAL_REVIEW 归哪一态；该字段级定义记 missing-prd。
 *   3) 展示时区未定义 → 只截取服务端时间字符串的日期时间部分，不做时区换算。
 */
import { PLACEHOLDER } from './format'

/** 设计稿 4 态（状态统计行 左→右） */
export type CredentialStatusKey = 'pending' | 'detecting' | 'rejected' | 'passed'

export const STATUS_ORDER: CredentialStatusKey[] = ['pending', 'detecting', 'rejected', 'passed']

export const CREDENTIAL_STATUS_META: Record<CredentialStatusKey, { label: string; color: string }> = {
  pending: { label: '待检测', color: '#94a3b8' },
  detecting: { label: '检测中', color: '#2563eb' },
  rejected: { label: '不通过', color: '#ef4444' },
  passed: { label: '通过', color: '#16a34a' }
}

/** 「查看」列文案（设计稿 02c95f41），只有拿到报告的行才有 */
export const REPORT_TEXT = '报告'

/** 列表只展示最近接入的 N 条（设计稿底部说明 + 18-API pageSize 约定） */
export const PAGE_SIZE = 10

/** GET /credentials 响应（字段名取自数据字典 aap_credential / aap_detection_job） */
export interface CredentialRowRaw {
  id?: string
  /** aap_credential.alias */
  alias?: string
  /** aap_credential.model_list（jsonb 数组，长度 = 设计稿「模型数」） */
  model_list?: unknown[] | null
  /** aap_credential.created_at（RFC3339 UTC） */
  created_at?: string
  /** 服务端由检测任务派生的 4 态（PENDING/RUNNING/PASS/FAIL），字段级定义 missing-prd */
  detection_status?: string
  /** 最近一次检测报告 id（detection_job 1:1 report） */
  latest_report_id?: string | null
}

export interface CredentialListRaw {
  /** 命中总数（18-API 分页约定） */
  total?: number
  items?: CredentialRowRaw[] | null
}

export interface CredentialChip {
  key: CredentialStatusKey
  label: string
  color: string
  count: number
}

export interface CredentialRow {
  id: string
  alias: string
  timeText: string
  modelCountText: string
  statusKey: CredentialStatusKey
  statusColor: string
  /** 无报告时 undefined（设计稿该单元格留空） */
  reportText?: string
  reportId?: string
}

export interface CredentialsModel {
  totalText: string
  chips: CredentialChip[]
  rows: CredentialRow[]
  footerText: string
}

const STATUS_ALIAS: Record<string, CredentialStatusKey> = {
  PENDING: 'pending',
  RUNNING: 'detecting',
  PASS: 'passed',
  FAIL: 'rejected'
}

/** 服务端检测态 → 设计稿 4 态；未知/缺失落 pending（不臆造更严重的结论） */
export function statusKeyOf(raw?: string | null): CredentialStatusKey {
  if (!raw) return 'pending'
  return STATUS_ALIAS[raw.toUpperCase()] ?? 'pending'
}

/** 「报告」列：只有 通过/不通过 行有（设计稿 1/4/5/7/9 行） */
function hasReport(key: CredentialStatusKey): boolean {
  return key === 'passed' || key === 'rejected'
}

/** RFC3339 → 「YYYY-MM-DD HH:mm:ss」（设计稿 4814565e）；非法/缺失 → 占位符 */
export function formatDateTime(value?: string | null): string {
  if (!value || typeof value !== 'string') return PLACEHOLDER
  const m = value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/)
  if (!m) return PLACEHOLDER
  return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}:${m[6]}`
}

function modelCount(raw: CredentialRowRaw): number {
  const list = raw.model_list
  return Array.isArray(list) ? list.length : 0
}

function toRow(raw: CredentialRowRaw, index: number): CredentialRow {
  const statusKey = statusKeyOf(raw.detection_status)
  const reportId = raw.latest_report_id ?? undefined
  const showReport = hasReport(statusKey) && !!reportId
  return {
    id: raw.id || `row-${index}`,
    alias: raw.alias || PLACEHOLDER,
    timeText: formatDateTime(raw.created_at),
    modelCountText: String(modelCount(raw)),
    statusKey,
    statusColor: CREDENTIAL_STATUS_META[statusKey].color,
    reportText: showReport ? REPORT_TEXT : undefined,
    reportId: showReport ? reportId : undefined
  }
}

/**
 * 构建页面视图模型。
 * - totalText：「共 N 条」用接口 total，缺省退化为已返回行数（不编造更大的数）
 * - chips：4 态计数按当前返回列表统计（设计稿 3+2+1+4 = 共 10 条 = 单页行数）
 */
export function buildCredentialsModel(raw?: CredentialListRaw | null): CredentialsModel {
  const items = Array.isArray(raw?.items) ? (raw!.items as CredentialRowRaw[]) : []
  const rows = items.map(toRow)
  const counts: Record<CredentialStatusKey, number> = { pending: 0, detecting: 0, rejected: 0, passed: 0 }
  for (const r of rows) counts[r.statusKey] += 1

  const total = typeof raw?.total === 'number' && raw.total >= 0 ? raw.total : rows.length

  return {
    totalText: `共 ${total} 条`,
    chips: STATUS_ORDER.map((key) => ({
      key,
      label: CREDENTIAL_STATUS_META[key].label,
      color: CREDENTIAL_STATUS_META[key].color,
      count: counts[key]
    })),
    rows,
    footerText: `仅展示最近接入的 ${PAGE_SIZE} 条凭证记录`
  }
}
