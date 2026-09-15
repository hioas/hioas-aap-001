/**
 * 序号 5【检测验真】检测进行中 2（page-5-2）视图模型
 *
 * 设计真源：.calicat/raw/pages/page-5-2/design.tree.json（430 宽，129 图层）
 *   顶部导航 c2a2498d（返回 24px #334155 · 「检测进行中」17px Bold #0F172A · chip「进行中」#EFF6FF/#2563EB + 9×7 圆点）
 *   总进度卡片 88f1ee17（白 r18 padding 20 · 「总进度」15px #0F172A · 「58%」20px Bold #2563EB ·
 *     进度条 61993aa5 高 10 轨道 #E2E8F0 r5 填充 #2563EB 209/358（=58%）·
 *     元信息行 dac2c177「已完成 7 / 12 个检测项」12px #64748B /「预计剩余 42 分钟」12px #94A3B8 ·
 *     成本保护行 257b52bf #ECFDF5 r12 padding 12 · 图标 #16A34A · 标题 12px SemiBold #15803D · 副文案 11px #16A34A）
 *   分项进度卡片 2138c3d3（白 r18 padding 20 描边 #EEF2F7 · 「分项检测」15px SemiBold ·
 *     D1–D8 8 行：32×32 图标块 r10 + 名称 13px SemiBold + 详情 11px #94A3B8 + 状态 chip h22 r11 padding 0 8px）
 *   提示卡片 c960eff4（白 r18 padding 16/20 描边 #EEF2F7 · 图标 #D97706 · 12px #64748B）
 *   底部操作条 ed66b6f1（白 padding 12/16/24/16 · 按钮 h48 r12 #F1F5F9 · 图标 #64748B · 「查看历史检测报告」14px Medium #475569）
 * 交互真源：page-5-2 interaction.json =「不存在图层交互数据」→ 退 PRD 09/14/15/17-spec/18-API + 画布 30 页清单
 *
 * ⚠️ 缺口（已记 .agents/state/aap-feature-status.csv 备注列，均不臆造）：
 *   1) 设计 8 行名（网络连通性/鉴权有效性/模型清单一致性/上下文长度/稳定性与错误率/计费口径核验/合规与内容安全/
 *      峰值并发压测）在 22 份 PRD 中零命中；09-PRD §2 的 D1–D8 是 TTFT/P50/一致性/RPM/TPM/缓存命中/模型指纹/真实源
 *      → 设计示例名 ≠ 规范项名；行名以服务端 probe_name 为准，缺失回退 09-PRD §2 短名，再缺失回退 probe_code。
 *   2) 设计「已完成 7 / 12 个检测项」= 12 项，而画布该卡片只有 8 行（设计内部不自洽）→ 进度优先取服务端
 *      progress{percent,finished,total,eta_minutes}（18-API 无字段级 schema → missing-prd；「预计剩余」在 PRD 零命中），
 *      字段缺失/越界时按返回的检测项条数派生（7/12 与 58% 恰好满足 done/total 四舍五入，说明设计即按此口径）。
 *   3) ProbeStatus（17-spec：SUCCESS/FAILED/SKIPPED/NOT_MEASURABLE）无 RUNNING/QUEUED，而设计有「进行中/排队中」
 *      → 以「服务端 status → 设计三态」字典映射；未覆盖状态（FAILED 等）chip 原样直显，不臆造中文。
 *   4) 设计无失败/完成态（无徽章文案、无后续动作）→ 未覆盖状态原样直显；是否需要跳转报告页由人类拍板（本页不自动跳转）。
 *   5) 轮询间隔 5s 为前端取值（PRD 未定义）→ missing-prd，常量集中在此便于调整。
 *   6) 详情行「已通过 · 236ms」中的度量摘要需服务端给 detail（结果表 metrics 为 jsonb，键名未定义）→ missing-prd。
 */
import { PLACEHOLDER } from './format'

/** 设计稿原文（顶部/区块/成本保护/提示/按钮，不得改写） */
export const PAGE_TITLE = '检测进行中'
export const TOTAL_LABEL = '总进度'
export const SECTION_LABEL = '分项检测'
export const COST_TITLE = '检测期间已启用成本保护'
export const COST_SUB = '本次检测由平台承担费用，不会计入你的账单'
export const TIP_TEXT = '检测期间你可以先完善供应商档案，检测完成后会自动通知你，无需停留本页。'
export const HISTORY_TEXT = '查看历史检测报告'

/** 前端提示文案（设计稿无此场景：缺入参 / 无落地页） */
export const MISSING_JOB_TOAST = '缺少检测任务标识'
export const HISTORY_TOAST = '历史检测报告可在凭证列表中查看'

/** 页面入参 storage 键（navigateTo 无 query 时兜底） */
export const JOB_ID_KEY = 'aap_detection_job_id'

/** 轮询间隔（PRD 未定义，前端取值 → missing-prd） */
export const POLL_INTERVAL_MS = 5000

/** 逐项结果行状态：完成 / 进行中 / 排队中 / 未覆盖（原样直显） */
export type ProbeStateKey = 'done' | 'running' | 'queued' | 'other'

interface ProbeStateMeta {
  key: ProbeStateKey
  chipText: string
  /** 详情行去掉度量摘要后的部分（设计：完成=「已通过」/ 进行中=「进行中」/ 排队中=「排队中」） */
  stateText: string
}

/**
 * 服务端 status → 设计三态。
 * done 侧依据 17-spec ProbeStatus=SUCCESS；running/queued 两态为队列态（09-PRD §5 分项并行 + 17-spec 单项超时）。
 * 未列出的状态不映射（原样直显），避免臆造中文结论。
 */
const PROBE_STATE_MAP: Record<string, ProbeStateMeta> = {
  SUCCESS: { key: 'done', chipText: '完成', stateText: '已通过' },
  RUNNING: { key: 'running', chipText: '进行中', stateText: '进行中' },
  IN_PROGRESS: { key: 'running', chipText: '进行中', stateText: '进行中' },
  QUEUED: { key: 'queued', chipText: '排队中', stateText: '排队中' },
  PENDING: { key: 'queued', chipText: '排队中', stateText: '排队中' }
}

/** 09-PRD §2「检测项规格（8 项）」短名（probe_name 缺失时的回退，非设计示例名） */
export const PRD_PROBE_NAMES: Record<string, string> = {
  D1: 'TTFT',
  D2: 'P50 延迟',
  D3: '一致性',
  D4: 'RPM',
  D5: 'TPM',
  D6: '缓存命中',
  D7: '模型指纹',
  D8: '真实源'
}

/** 任务状态 → 顶部徽章文案（设计只有「进行中」；排队态取 04-PRD 流程「排队中」） */
const JOB_CHIP_LABELS: Record<string, string> = {
  QUEUED: '排队中',
  RUNNING: '进行中',
  PARTIAL: '进行中',
  PARTIAL_DONE: '进行中'
}

/** 轮询判定：队列态继续轮询，终态/未知状态停止（避免对未知状态无限打接口） */
const POLLING_STATUSES = new Set(['QUEUED', 'RUNNING', 'PARTIAL', 'PARTIAL_DONE'])

export function shouldPoll(status?: string | null): boolean {
  if (!status || typeof status !== 'string') return false
  return POLLING_STATUSES.has(status.toUpperCase())
}

/** 检测任务详情（15-数据字典 aap_detection_job；progress 为 18-API 未定义的进度对象，missing-prd） */
export interface DetectionJobProgressRaw {
  /** 总进度百分比（0–100） */
  percent?: number
  /** 已完成检测项数 */
  finished?: number
  /** 检测项总数 */
  total?: number
  /** 预计剩余分钟数 */
  eta_minutes?: number
}

export interface DetectionJobRaw {
  id?: string
  job_no?: string
  credential_id?: string
  status?: string
  trigger_type?: string
  started_at?: string
  finished_at?: string
  total_score?: number | null
  result?: string | null
  confidence?: string | null
  cost_estimate_usd?: number | null
  cost_actual_usd?: number | null
  error_code?: string | null
  error_msg?: string | null
  progress?: DetectionJobProgressRaw | null
}

/** 逐项检测结果（15-数据字典 aap_detection_result） */
export interface DetectionResultItemRaw {
  probe_code?: string
  /** 检测项展示名（设计示例：网络连通性…；PRD 未定义该字段 → missing-prd） */
  probe_name?: string
  status?: string
  score?: number | null
  metrics?: Record<string, unknown> | null
  evidence?: unknown
  explanation?: string | null
  weight_used?: number | null
  /** 详情行的度量摘要（设计示例：「236ms」/「2/2 模型已核验」；字段级 missing-prd） */
  detail?: string | null
}

export interface DetectionResultsRaw {
  job_id?: string
  total?: number
  items?: DetectionResultItemRaw[] | null
}

export interface DetectingRow {
  code: string
  /** 「D1 网络连通性」 */
  label: string
  /** 「已通过 · 236ms」 */
  detailText: string
  /** 状态 chip 文案 */
  chipText: string
  stateKey: ProbeStateKey
}

export interface DetectingModel {
  chipLabel: string
  percent: number
  percentText: string
  finishedText: string
  /** 无服务端 eta 时不渲染（设计稿有该行，但无数据来源 → missing-prd） */
  etaText?: string
  rows: DetectingRow[]
}

function isFiniteNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

function str(v: unknown): string {
  return typeof v === 'string' ? v.trim() : ''
}

/** 行名：服务端 probe_name 优先 → 09-PRD §2 短名 → probe_code */
function labelOf(raw: DetectionResultItemRaw, code: string): string {
  const name = str(raw.probe_name) || PRD_PROBE_NAMES[code] || ''
  return name ? `${code} ${name}` : code
}

function toRow(raw: DetectionResultItemRaw, index: number): DetectingRow {
  const code = str(raw.probe_code) || `probe-${index}`
  const status = str(raw.status).toUpperCase()
  const meta: ProbeStateMeta | undefined = status ? PROBE_STATE_MAP[status] : PROBE_STATE_MAP.QUEUED
  const detail = str(raw.detail)
  // 未覆盖状态：状态词留空（不臆造中文），只剩服务端给的度量摘要
  const stateKey: ProbeStateKey = meta ? meta.key : 'other'
  const stateText = meta ? meta.stateText : ''
  return {
    code,
    label: labelOf(raw, code),
    detailText: [stateText, detail].filter(Boolean).join(' · ') || PLACEHOLDER,
    chipText: meta ? meta.chipText : status || PLACEHOLDER,
    stateKey
  }
}

/**
 * 构建页面视图模型。
 * 进度口径：服务端 progress 合法字段优先，缺失/越界时按返回的检测项条数派生（done/total 四舍五入）。
 */
export function buildDetectingModel(
  job?: DetectionJobRaw | null,
  results?: DetectionResultsRaw | null
): DetectingModel {
  const items = Array.isArray(results?.items) ? (results!.items as DetectionResultItemRaw[]) : []
  const rows = items.map(toRow)
  const doneCount = rows.filter((r) => r.stateKey === 'done').length

  const progress = job?.progress ?? undefined
  const pPercent = progress?.percent
  const pFinished = progress?.finished
  const pTotal = progress?.total

  const serverPercentValid = isFiniteNumber(pPercent) && pPercent >= 0 && pPercent <= 100
  const serverCountsValid =
    isFiniteNumber(pFinished) &&
    isFiniteNumber(pTotal) &&
    Number.isInteger(pFinished) &&
    Number.isInteger(pTotal) &&
    pFinished >= 0 &&
    pTotal >= 1 &&
    pFinished <= pTotal

  const finished = serverCountsValid ? pFinished : doneCount
  const total = serverCountsValid ? pTotal : rows.length
  const percent = serverPercentValid ? Math.round(pPercent) : total > 0 ? Math.round((finished / total) * 100) : 0

  const eta = progress?.eta_minutes
  const etaText = isFiniteNumber(eta) && eta >= 0 ? `预计剩余 ${Math.round(eta)} 分钟` : undefined

  const status = str(job?.status).toUpperCase()

  return {
    chipLabel: JOB_CHIP_LABELS[status] ?? status,
    percent,
    percentText: `${percent}%`,
    finishedText: `已完成 ${finished} / ${total} 个检测项`,
    etaText,
    rows
  }
}
