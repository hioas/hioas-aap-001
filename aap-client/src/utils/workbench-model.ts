/**
 * 工作台视图模型 — 把 GET /usage/summary 的响应映射成设计稿（page-2-b）里的每一块文案。
 *
 * 字段命名依据（不得臆造）：
 *   - 15-数据模型ER与数据字典.md `aap_usage_hourly`：request_count / prompt_tokens / completion_tokens /
 *     cache_read_tokens / total_tokens / quota_raw / cost_usd
 *   - 11-同步与用量统计PRD §4「对账视图指标」：请求数、输入/输出 token、缓存读、缓存命中率、quota、折算金额
 *   - 18-API设计OpenAPI.md「Usage」Tag：GET /usage/summary
 *   - 11-PRD usage_hourly 表另有 image/audio 输入 token（视频在同域内按同类处理）
 * ⚠️ 响应体的精确 schema（字段名/嵌套）未在 18-API 定义 → 台账「备注」记 missing-prd（字段级），
 *    本文件只做「设计稿需要的展示口径」映射，缺字段一律显示占位符，不编造数字。
 */
import {
  PLACEHOLDER,
  formatAmount,
  formatCount,
  formatPercent,
  formatTokens,
  percentOf
} from './format'

/** 用量域原始字段（含设计稿用到的图片/音频/视频输入 token） */
export interface UsageModelRaw {
  model_name: string
  request_count?: number
  total_tokens?: number
  amount?: number
}

export interface UsageSummaryRaw {
  request_count?: number
  total_tokens?: number
  prompt_tokens?: number
  completion_tokens?: number
  cache_read_tokens?: number
  image_input_tokens?: number
  audio_input_tokens?: number
  video_input_tokens?: number
  cache_hit_rate?: number
  mom_rate?: number
  quota_raw?: number
  cost_usd?: number
  amount_total?: number
  models?: UsageModelRaw[]
}

export interface CategoryRow {
  key: string
  label: string
  color: string
  text: string
}

export interface MetricRow {
  label: string
  value: string
  tone: 'default' | 'success'
}

export interface ModelRow {
  rank: number
  name: string
  amountText: string
  callsText: string
  barPercent: number
  badgeBg: string
  barColor: string
}

export interface WorkbenchModel {
  centerLabel: string
  totalText: string
  momText: string
  categories: CategoryRow[]
  metrics: MetricRow[]
  models: ModelRow[]
  footerText: string
}

/** 图例分类：标签/取色/取数字段，顺序与设计稿逐行一致 */
const CATEGORY_DEFS: Array<{ key: string; label: string; color: string; field: keyof UsageSummaryRaw }> = [
  { key: 'prompt', label: '输入词元', color: '#1d4ed8', field: 'prompt_tokens' },
  { key: 'completion', label: '输出词元', color: '#3b82f6', field: 'completion_tokens' },
  { key: 'cache', label: '缓存命中', color: '#16a34a', field: 'cache_read_tokens' },
  { key: 'image', label: '图片', color: '#5856d6', field: 'image_input_tokens' },
  { key: 'audio', label: '音频', color: '#f59e0b', field: 'audio_input_tokens' },
  { key: 'video', label: '视频', color: '#af52de', field: 'video_input_tokens' }
]

/** 模型行配色：设计稿 model1~4 的序号底色与占比条色（rgba→hex） */
const MODEL_TONES = [
  { badgeBg: '#eff6ff', barColor: '#2563eb' },
  { badgeBg: '#ecfdf5', barColor: '#60a5fa' },
  { badgeBg: '#fff7ed', barColor: '#f59e0b' },
  { badgeBg: '#f1f5f9', barColor: '#94a3b8' }
]

/**
 * 模型行合并规则（设计稿第 4 行为「其他模型」）：
 * ≤3 个模型原样展示；>3 个取收入前 3，其余合并为「其他模型」（金额/调用量/词元求和）。
 */
export function mergeModelRows(models?: UsageModelRaw[]): UsageModelRaw[] {
  if (!models || models.length === 0) return []
  const sorted = [...models].sort((a, b) => (b.amount ?? 0) - (a.amount ?? 0))
  if (sorted.length <= 3) return sorted
  const head = sorted.slice(0, 3)
  const tail = sorted.slice(3)
  const rest: UsageModelRaw = {
    model_name: '其他模型',
    amount: tail.reduce((s, m) => s + (m.amount ?? 0), 0),
    request_count: tail.reduce((s, m) => s + (m.request_count ?? 0), 0),
    total_tokens: tail.reduce((s, m) => s + (m.total_tokens ?? 0), 0)
  }
  return [...head, rest]
}

export function buildWorkbenchModel(raw: UsageSummaryRaw = {}): WorkbenchModel {
  const totalTokens = raw.total_tokens
  const rows = mergeModelRows(raw.models)
  const amountTotal = raw.amount_total ?? rows.reduce((s, m) => s + (m.amount ?? 0), 0)
  const hasAmount = rows.length > 0 && rows.some((m) => m.amount !== undefined)

  const categories: CategoryRow[] = CATEGORY_DEFS.map((def) => {
    const value = raw[def.field] as number | undefined
    if (value === undefined || value === null) {
      return { key: def.key, label: def.label, color: def.color, text: PLACEHOLDER }
    }
    const pct = percentOf(value, totalTokens)
    return {
      key: def.key,
      label: def.label,
      color: def.color,
      text: `${pct === null ? PLACEHOLDER : `${pct}%`} · ${formatTokens(value)}`
    }
  })

  const models: ModelRow[] = rows.map((m, i) => {
    const tone = MODEL_TONES[Math.min(i, MODEL_TONES.length - 1)]
    const pct = percentOf(m.amount, amountTotal)
    return {
      rank: i + 1,
      name: m.model_name,
      amountText: formatAmount(m.amount),
      callsText: `${formatCount(m.request_count)} · ${pct === null ? PLACEHOLDER : `${pct}%`}`,
      barPercent: pct ?? 0,
      badgeBg: tone.badgeBg,
      barColor: tone.barColor
    }
  })

  return {
    centerLabel: '总词元',
    totalText: formatTokens(totalTokens),
    momText: formatPercent(raw.mom_rate),
    categories,
    metrics: [
      { label: '调用请求', value: formatCount(raw.request_count), tone: 'default' },
      { label: 'Token', value: formatTokens(totalTokens), tone: 'default' },
      { label: '缓存命中率', value: formatPercent(raw.cache_hit_rate), tone: 'success' }
    ],
    models,
    footerText: hasAmount
      ? `合计 ${formatAmount(amountTotal)} · ${models.length} 个模型`
      : `合计 ${PLACEHOLDER}`
  }
}
