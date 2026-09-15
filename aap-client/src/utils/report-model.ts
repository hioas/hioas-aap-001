/**
 * 序号 6【检测验真】大模型检测报告 · 多维度专业版（page-6）视图模型
 *
 * 设计真源：.calicat/raw/pages/page-6/design.tree.json（430 宽）
 *   顶部导航 b362b5a2（白底 · padding 48/16/12/16 · 「检测报告」17px Bold #0F172A · 报告编号 11px #94A3B8）
 *   结论封面卡 4e855266（白 r18 padding 20）· 综合分 40px（通过=绿 #16A34A）· 结论标签 #F0FDF4 r14 h28（12px #15803D）
 *   状态四格 950cbd49（值 15px #0F172A，第 4 格绿 #16A34A · 标签 10px #94A3B8）
 *   关键指标卡 c13761bd（6 项，2 列；子卡 #F8FAFC r12 padding 12；标签 10.5px #94A3B8，值 19px #0F172A，副行 10px）
 *   维度总览卡 7530b31a（雷达图区 6cf10c3b 高 258；均分行 33713878：色点 9×8 r4 + 条底 200×6 r3 + 分值 12px；
 *     图例 7a5c9636 三项 10.5px #94A3B8）
 *   明细卡 7806d174（说明行 8485b93b 11px #94A3B8；分组标题行：色条 5×14 r2 + 标题 13px + 「均分 x · n 项」11px；
 *     明细行 fcc0b162：名称 150（12px #334155 + 度量 10px #94A3B8）+ 条底 162×6 r3 + 分值 30（12px #0F172A））
 *   风险发现卡 658a45d1（4 条：padding 12 r12，#F0FDF4 / #FFFBEB / #FFFBEB / #F1F5F9）
 *   原始证据卡 9844215a（6 行：键 88 宽 11px #0F172A，值 11px #64748B，行距 padding-top 10/16）
 *   免责声明卡 30918987（标题 12px + 正文 11px）· 底部操作条 e096bd63（导出 126×48 白底描边；填写报价 fill 48 高 #2563EB）
 * 交互真源：page-6 interaction.json =「不存在图层交互数据」→ 退 PRD 09/17-spec/18-API/21-验收 + 画布 30 页清单
 *
 * ⚠️ 缺口（全部记入 .agents/state/aap-feature-status.csv 序号 6 备注，均不臆造）：
 *   1) 设计 7 组 55 项（A·时延与性能 … G·真实源证据）与 09-PRD §2 的 D1–D8 探测项**不是同一套编号/口径**
 *      → 分组与项名以服务端返回为准（本文件只负责渲染与派生统计），设计示例值仅作测试夹具。
 *   2) 明细说明行「46 项计入总分 · 7 项仅证据 · 1 项未申报 · 1 项不可测」由**返回条数派生**（设计数字自洽性已核对）。
 *   3) 一票否决口径冲突：设计「行为指纹相似度 < 0.70 直接判不通过」vs 09-PRD §3「默认 D7<40 否决」
 *      → 说明文案按设计稿原文直显（不静默改写），冲突已记台账待人类拍板。
 *   4) 置信度措辞：设计「较高」vs 09-PRD §定位声明「高/中/低」→ 服务端 confidence_label 优先，缺失时按设计口径展示。
 *   5) 18-API 只列路径未列方法 → /reports/{reportId} 与 /{reportId}/export 的 GET 为 REST 语义推断（missing-prd）。
 *   6) 导出 PDF 的响应体结构（url/file_name）在 18-API 无字段级 schema → missing-prd；小程序内不做文件落地，只提示。
 */
import { PLACEHOLDER } from './format'

/** 设计稿原文（顶部 / 各卡标题 / 按钮 / 图例 / 说明，不得改写） */
export const PAGE_TITLE = '检测报告'
export const VERDICT_TITLE = '综合检测结论'
export const SCORE_LABEL = '综合评分'
export const SCORE_MAX_LABEL = '满分 100'
export const KEY_METRICS_TITLE = '关键指标'
export const KEY_METRICS_SUB = '核心 6 项实时值'
export const DIM_TITLE = '维度总览'
export const DIM_SUB = '六大维度均分'
export const DETAIL_TITLE = '全维度明细'
export const DETAIL_SCORE_HINT = '打分 0–100'
export const RISK_TITLE = '关键发现与风险'
export const EVIDENCE_TITLE = '原始证据（节选）'
export const EVIDENCE_SUB = '可导出'
export const DISCLAIMER_TITLE = '本报告基于抽样检测生成'
export const EXPORT_TEXT = '导出 PDF'
export const QUOTE_TEXT = '填写报价'

/** 设计稿原文说明（服务端未提供时的回退） */
export const DEFAULT_DISCLAIMER =
  '本引擎输出的是证据与置信度，不是"真 / 假"判决，请勿理解为"已验证该模型为正品"。检测结论仅代表检测时点状态，不构成对上游长期稳定性与合规性的担保。报告有效期 30 天，异常可申请复测。'
export const DEFAULT_VETO_NOTE =
  '一票否决项：行为指纹相似度 < 0.70 将直接判定不通过。本项得分按 5 条子证据线加权（行为 0.35 / Tokenizer 0.25 / 自我认知 0.15 / 概率 0.15 / 上下文 0.10）。'
export const DEFAULT_WEIGHT_NOTE =
  '总分 = Σ(检测项得分 × 权重)；默认权重：指纹 0.35、P50 0.15、TTFT/一致性/RPM/TPM/缓存各 0.10；真实源仅证据不计分。置信度：可测子项 ≥4 且一致 → 高。'

/** 状态四格标签（design 950cbd49 逐字） */
export const STATUS_CELL_LABELS = ['通过项', '不可测', '置信度', '一票否决']

/** 图例（design 7a5c9636 逐字与取色） */
export const LEGEND_ITEMS: { text: string; color: string }[] = [
  { text: '计入总分', color: '#16A34A' },
  { text: '仅证据', color: '#64748B' },
  { text: '不可测 / 未申报', color: '#D97706' }
]

/** 分组色（design：色条 5×14 r2 / 色点 9×8 r4，A–G 取色） */
export const GROUP_COLORS: Record<string, string> = {
  A: '#2563EB',
  B: '#0891B2',
  C: '#16A34A',
  D: '#7C3AED',
  E: '#D97706',
  F: '#E11D48',
  G: '#64748B'
}

/** 雷达轴短名（design 6cf10c3b 逐字：性能/吞吐/一致性/指纹/计费/安全） */
export const RADAR_SHORT_LABELS: Record<string, string> = {
  A: '性能',
  B: '吞吐',
  C: '一致性',
  D: '指纹',
  E: '计费',
  F: '安全'
}

/**
 * 维度总览「分组均分行」的名称（design 33713878 逐字）。
 * ⚠️ 设计稿这里用的是**短名**，与明细卡的分组标题并不是同一个串
 * （例：C 行「一致与可靠」 vs 明细分组「C · 一致性与可靠性」；E 行「计量与计费」 vs 「E · 计量与缓存计费」）
 * → 短名固定按设计稿直显；非 A–F 编号（服务端自定义分组）回退分组名。
 */
export const DIM_SHORT_NAMES: Record<string, string> = {
  A: '时延与性能',
  B: '吞吐与限速',
  C: '一致与可靠',
  D: '模型指纹',
  E: '计量与计费',
  F: '安全与合规'
}

/** 页面入参 storage 键（navigateTo 无 query 时兜底） */
export const REPORT_ID_KEY = 'aap_report_id'

/** 前端提示文案（设计稿无此场景） */
export const MISSING_REPORT_TOAST = '缺少报告标识'
export const EXPORT_READY_TOAST = '导出链接已生成，请在浏览器中打开'
export const LOAD_FAIL_TOAST = '加载失败，请稍后重试'

/** 「填写报价」目标路由：画布序号 12-v1「新增报价单-初始态」= /pages/quote-form/index */
export const QUOTE_ROUTE = '/pages/quote-form/index'

/* ------------------------------- 原始数据结构 ------------------------------- */

export interface ReportKeyMetricRaw {
  key?: string
  label?: string
  value?: string
  unit?: string
  sub?: string
  tone?: string
}

export interface ReportSectionItemRaw {
  code?: string
  name?: string
  metric?: string
  score?: number | null
  status?: string | null
  value?: string | null
}

export interface ReportSectionRaw {
  code?: string
  name?: string
  avg?: number | null
  /** false = 该组仅证据不计分（设计 G 组） */
  scored?: boolean | null
  /** 组内提示（18-API 未定义 → missing-prd） */
  note?: string | null
  items?: ReportSectionItemRaw[] | null
}

export interface ReportFindingRaw {
  title?: string
  body?: string
  tone?: string
}

export interface ReportEvidenceRaw {
  key?: string
  value?: string
}

export interface ReportRaw {
  report_no?: string | null
  channel_name?: string | null
  total_score?: number | null
  result?: string | null
  confidence?: string | null
  confidence_label?: string | null
  pass_count?: number | null
  item_total?: number | null
  unmeasurable_count?: number | null
  veto_triggered?: boolean | null
  verdict?: string | null
  provider_name?: string | null
  provider_code?: string | null
  api_key_masked?: string | null
  model_list?: string[] | null
  detected_at?: string | null
  trigger_type?: string | null
  duration_text?: string | null
  cost_estimate_usd?: number | null
  cost_actual_usd?: number | null
  key_metrics?: ReportKeyMetricRaw[] | null
  sections?: ReportSectionRaw[] | null
  findings?: ReportFindingRaw[] | null
  evidence?: ReportEvidenceRaw[] | null
  disclaimer?: string | null
  veto_note?: string | null
  weight_note?: string | null
}

export interface ReportExportRaw {
  url?: string
  file_name?: string
}

/* ------------------------------- 视图模型结构 ------------------------------- */

export type ToneKey = 'success' | 'warning' | 'danger' | 'info' | 'muted'
export type ItemStatusKey = 'scored' | 'evidence' | 'not_declared' | 'not_measurable' | 'other'

export interface ReportMetricView {
  label: string
  value: string
  unit: string
  sub: string
  subTone: 'success' | 'muted'
}

export interface ReportStatusCell {
  value: string
  label: string
  tone: 'default' | 'success' | 'danger'
}

export interface ReportInfoRow {
  label: string
  value: string
}

export interface ReportDimRow {
  code: string
  name: string
  score: number | null
  scoreText: string
  barPercent: number
  color: string
}

export interface ReportItemRow {
  code: string
  label: string
  metric: string
  scoreText: string
  barPercent: number
  color: string
  statusKey: ItemStatusKey
}

export interface ReportSectionView {
  code: string
  title: string
  meta: string
  color: string
  /** 组内提示（设计：分组 D 的「指纹提示」盒 id=239a99e9） */
  note?: string
  items: ReportItemRow[]
}

export interface ReportFindingView {
  title: string
  body: string
  tone: ToneKey
}

export interface ReportRadarGeometry {
  points: string
  dots: { x: number; y: number }[]
  rings: string[]
  axes: { x1: number; y1: number; x2: number; y2: number }[]
}

export interface ReportModel {
  reportNo: string
  verdictTitle: string
  channelText: string
  scoreText: string
  scoreSectionLabel: string
  scoreMaxLabel: string
  resultLabel: string
  resultTone: ToneKey
  verdict: string
  statusCells: ReportStatusCell[]
  infoRows: ReportInfoRow[]
  metrics: ReportMetricView[]
  dims: ReportDimRow[]
  radar: { labels: string[]; values: (number | null)[]; geometry: ReportRadarGeometry }
  sections: ReportSectionView[]
  detailSummary: string
  itemCountText: string
  findings: ReportFindingView[]
  evidenceRows: { key: string; value: string }[]
  disclaimer: string
  vetoNote: string
  weightNote: string
}

/* --------------------------------- 工具函数 --------------------------------- */

function str(v: unknown): string {
  return typeof v === 'string' ? v.trim() : ''
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

/** 0–100 分值（越界裁剪）；非数字返回 null */
function scoreOf(v: unknown): number | null {
  const n = num(v)
  if (n === null) return null
  return Math.min(100, Math.max(0, n))
}

/** 金额：整数不带小数，非整数保留 2 位（设计稿：预估 $1.86（实际 $1.72）） */
export function moneyText(v: unknown): string {
  const n = num(v)
  if (n === null) return ''
  return `$${Number.isInteger(n) ? String(n) : n.toFixed(2)}`
}

/** 结果三态（09-PRD §3：通过 / 未通过 / 人工复核） */
const RESULT_META: Record<string, { label: string; tone: ToneKey }> = {
  PASS: { label: '通过', tone: 'success' },
  FAILED: { label: '未通过', tone: 'danger' },
  FAIL: { label: '未通过', tone: 'danger' },
  MANUAL_REVIEW: { label: '人工复核', tone: 'warning' }
}

/** 置信度（设计稿措辞「较高」；服务端 confidence_label 优先） */
const CONFIDENCE_LABELS: Record<string, string> = {
  HIGH: '较高',
  MEDIUM: '中',
  LOW: '低'
}

/** 明细行状态词（设计稿逐字；PRD 未覆盖的状态原样直显，不臆造中文） */
const ITEM_STATUS_META: Record<string, { key: ItemStatusKey; text: string }> = {
  EVIDENCE_ONLY: { key: 'evidence', text: '仅证据' },
  NOT_DECLARED: { key: 'not_declared', text: '未申报' },
  NOT_REPORTED: { key: 'not_declared', text: '未申报' },
  UNDECLARED: { key: 'not_declared', text: '未申报' },
  NOT_MEASURABLE: { key: 'not_measurable', text: '不可测' },
  UNMEASURABLE: { key: 'not_measurable', text: '不可测' }
}

/* --------------------------------- 雷达几何 --------------------------------- */
export interface RadarOptions {
  size?: number
  radius?: number
  ringCount?: number
}

/**
 * 六轴雷达几何（设计 6cf10c3b：4 圈网格 + 6 条轴线 + 6 个顶点圆点）。
 * 轴 0 在正上方，顺时针每 60° 一轴（与设计标签位置一致：性能↑ / 吞吐↗ / 一致性↘ / 指纹↓ / 计费↙ / 安全↖）。
 * 分值缺失或越界按 0 处理（不臆造数值）。
 */
export function radarGeometry(values: (number | null)[], options: RadarOptions = {}): ReportRadarGeometry {
  const size = options.size ?? 176
  const radius = options.radius ?? 78
  const ringCount = options.ringCount ?? 4
  const c = size / 2
  const n = values.length
  const step = (Math.PI * 2) / n

  const at = (i: number, r: number) => {
    const angle = -Math.PI / 2 + i * step
    return {
      x: Math.round((c + r * Math.cos(angle)) * 10) / 10,
      y: Math.round((c + r * Math.sin(angle)) * 10) / 10
    }
  }

  const dots = values.map((v, i) => at(i, (radius * (scoreOf(v) ?? 0)) / 100))

  const ringAt = (r: number) =>
    values
      .map((_v, i) => {
        const p = at(i, r)
        return `${p.x},${p.y}`
      })
      .join(' ')

  const rings: string[] = []
  for (let k = 1; k <= ringCount; k += 1) rings.push(ringAt((radius * k) / ringCount))

  const axes = values.map((_v, i) => {
    const p = at(i, radius)
    return { x1: c, y1: c, x2: p.x, y2: p.y }
  })

  return {
    points: dots.map((d) => `${d.x},${d.y}`).join(' '),
    dots,
    rings,
    axes
  }
}

/* ------------------------------- 雷达 SVG 出图 ------------------------------- */

/**
 * ASCII base64（不依赖 btoa / Buffer：小程序与 H5 都能跑）。
 * SVG 源全部是 ASCII（数值与属性名），因此无需 UTF-8 处理。
 */
export function base64Ascii(input: string): string {
  const table = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  let out = ''
  for (let i = 0; i < input.length; i += 3) {
    const c1 = input.charCodeAt(i)
    const c2 = i + 1 < input.length ? input.charCodeAt(i + 1) : NaN
    const c3 = i + 2 < input.length ? input.charCodeAt(i + 2) : NaN
    const b1 = c1 >> 2
    const b2 = ((c1 & 3) << 4) | (Number.isNaN(c2) ? 0 : c2 >> 4)
    const b3 = Number.isNaN(c2) ? 64 : ((c2 & 15) << 2) | (Number.isNaN(c3) ? 0 : c3 >> 6)
    const b4 = Number.isNaN(c3) ? 64 : c3 & 63
    out += table[b1] + table[b2] + (b3 === 64 ? '=' : table[b3]) + (b4 === 64 ? '=' : table[b4])
  }
  return out
}

/**
 * 生成雷达图 SVG 文本（design 6cf10c3b：4 圈网格 + 3 条交叉轴线 + 数据多边形 + 6 个顶点圆点）。
 * 网格 #E2E8F0 / 轴线 #E2E8F0 / 数据面 rgba(37,99,235,0.16) / 顶点 #2563EB r3 —— 取色自设计稿。
 */
export function radarSvg(geometry: ReportRadarGeometry, size = 176): string {
  const rings = geometry.rings
    .map((r) => `<polygon points="${r}" fill="none" stroke="#E2E8F0" stroke-width="1"/>`)
    .join('')
  const axes = geometry.axes
    .map((a) => `<line x1="${a.x1}" y1="${a.y1}" x2="${a.x2}" y2="${a.y2}" stroke="#E2E8F0" stroke-width="1"/>`)
    .join('')
  const face = `<polygon points="${geometry.points}" fill="rgba(37,99,235,0.16)" stroke="#2563EB" stroke-width="1.5"/>`
  const dots = geometry.dots
    .map((d) => `<circle cx="${d.x}" cy="${d.y}" r="3" fill="#2563EB"/>`)
    .join('')
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">` +
    `${rings}${axes}${face}${dots}</svg>`
  )
}

/**
 * 雷达图 data-URI。
 * ⚠️ mp-weixin **不支持内联 svg 标签**（wxss/wxml 无 svg），矢量图只能交给 <image>；
 * 因此这里把 SVG 编码成 base64 data-URI（小程序与 H5 均支持 data:image 资源）。
 */
export function radarDataUri(geometry: ReportRadarGeometry, size = 176): string {
  return `data:image/svg+xml;base64,${base64Ascii(radarSvg(geometry, size))}`
}

/* --------------------------------- 模型构建 --------------------------------- */

function toMetric(raw: ReportKeyMetricRaw): ReportMetricView {
  return {
    label: str(raw.label),
    value: str(raw.value),
    unit: str(raw.unit),
    sub: str(raw.sub),
    subTone: str(raw.tone) === 'success' ? 'success' : 'muted'
  }
}

function toItem(raw: ReportSectionItemRaw, index: number, sectionScored: boolean, color: string): ReportItemRow {
  const code = str(raw.code) || `item-${index + 1}`
  const name = str(raw.name)
  const status = str(raw.status).toUpperCase()
  const score = scoreOf(raw.score)
  const meta = status ? ITEM_STATUS_META[status] : undefined
  const value = str(raw.value)

  let statusKey: ItemStatusKey
  if (meta) {
    statusKey = meta.key
  } else if (status) {
    statusKey = 'other'
  } else if (!sectionScored) {
    statusKey = 'evidence'
  } else {
    statusKey = score === null ? 'other' : 'scored'
  }

  let scoreText: string
  if (meta) scoreText = meta.text
  else if (status) scoreText = status // 未覆盖状态原样直显（不臆造中文）
  else if (!sectionScored) scoreText = value || '仅证据'
  else if (score !== null) scoreText = String(score)
  else scoreText = PLACEHOLDER

  return {
    code,
    label: name ? `${code} ${name}` : code,
    metric: str(raw.metric),
    scoreText,
    barPercent: statusKey === 'scored' && score !== null ? Math.round(score) : 0,
    color,
    statusKey
  }
}

function toSection(raw: ReportSectionRaw, index: number): ReportSectionView {
  const code = str(raw.code) || String.fromCharCode(65 + index)
  const name = str(raw.name)
  const scored = raw.scored !== false
  const color = GROUP_COLORS[code] ?? '#64748B'
  const items = (Array.isArray(raw.items) ? raw.items : []).map((i, idx) => toItem(i, idx, scored, color))
  const avg = scoreOf(raw.avg)
  const meta = !scored
    ? `仅证据 · ${items.length} 项`
    : avg !== null
    ? `均分 ${Math.round(avg)} · ${items.length} 项`
    : `${items.length} 项`
  return {
    code,
    title: name ? `${code} · ${name}` : code,
    meta,
    color,
    items
  }
}

function countByStatus(sections: ReportSectionView[], key: ItemStatusKey): number {
  return sections.reduce((sum, s) => sum + s.items.filter((i) => i.statusKey === key).length, 0)
}

function infoRowsOf(raw: ReportRaw): ReportInfoRow[] {
  const provider = str(raw.provider_name)
  const code = str(raw.provider_code)
  const providerText = provider && code ? `${provider}（Provider #${code}）` : provider || code
  const models = Array.isArray(raw.model_list) ? raw.model_list.map(str).filter(Boolean).join(' · ') : ''
  const detectedAt = str(raw.detected_at)
  const trigger = str(raw.trigger_type)
  const timeText = [detectedAt, trigger ? `触发方式：${trigger}` : ''].filter(Boolean).join(' · ')
  const duration = str(raw.duration_text)
  const estimate = moneyText(raw.cost_estimate_usd)
  const actual = moneyText(raw.cost_actual_usd)
  const costText = estimate || actual ? `预估 ${estimate || PLACEHOLDER}（实际 ${actual || PLACEHOLDER}）` : ''
  return [
    { label: '供应商', value: providerText },
    { label: '凭证', value: str(raw.api_key_masked) },
    { label: '模型清单', value: models },
    { label: '检测时间', value: timeText },
    { label: '耗时 / 成本', value: [duration, costText].filter(Boolean).join(' · ') }
  ]
}

function statusCellsOf(raw: ReportRaw): ReportStatusCell[] {
  const pass = num(raw.pass_count)
  const total = num(raw.item_total)
  const unmeasurable = num(raw.unmeasurable_count)
  const confidenceLabel = str(raw.confidence_label) || CONFIDENCE_LABELS[str(raw.confidence).toUpperCase()] || ''
  const veto = raw.veto_triggered

  const passText = `${pass ?? '—'}/${total ?? '—'}`
  const unmeasurableText = unmeasurable !== null ? `${unmeasurable} 项` : PLACEHOLDER
  const vetoCell: ReportStatusCell =
    veto === true
      ? { value: '已触发', label: STATUS_CELL_LABELS[3], tone: 'danger' }
      : veto === false
      ? { value: '未触发', label: STATUS_CELL_LABELS[3], tone: 'success' }
      : { value: PLACEHOLDER, label: STATUS_CELL_LABELS[3], tone: 'default' }

  return [
    { value: passText, label: STATUS_CELL_LABELS[0], tone: 'default' },
    { value: unmeasurableText, label: STATUS_CELL_LABELS[1], tone: 'default' },
    { value: confidenceLabel || PLACEHOLDER, label: STATUS_CELL_LABELS[2], tone: 'default' },
    vetoCell
  ]
}

function findingsOf(raw: ReportRaw): ReportFindingView[] {
  const tones: ToneKey[] = ['success', 'warning', 'warning', 'info']
  return (Array.isArray(raw.findings) ? raw.findings : []).map((f, i) => {
    const tone = str(f.tone)
    return {
      title: str(f.title),
      body: str(f.body),
      tone: (['success', 'warning', 'danger', 'info', 'muted'] as ToneKey[]).includes(tone as ToneKey)
        ? (tone as ToneKey)
        : tones[Math.min(i, tones.length - 1)]
    }
  })
}

/** 构建页面视图模型（缺字段一律留空/占位，不臆造） */
export function buildReportModel(raw?: ReportRaw | null): ReportModel {
  const source: ReportRaw = raw ?? {}
  const sections = (Array.isArray(source.sections) ? source.sections : []).map(toSection)

  // 维度总览取「计分的六个维度组」：优先进设计稿 A–F 编号，否则取前 6 个计分组
  let dimSections = sections.filter((s) => RADAR_SHORT_LABELS[s.code])
  if (dimSections.length === 0) {
    dimSections = (Array.isArray(source.sections) ? source.sections : [])
      .filter((s) => s.scored !== false)
      .slice(0, 6)
      .map(toSection)
  }

  const dims: ReportDimRow[] = dimSections.map((s) => {
    const rawSection = (Array.isArray(source.sections) ? source.sections : []).find((x) => str(x.code) === s.code)
    const score = scoreOf(rawSection?.avg)
    return {
      code: s.code,
      name: DIM_SHORT_NAMES[s.code] ?? ((rawSection ? str(rawSection.name) : '') || s.title),
      score,
      scoreText: score === null ? PLACEHOLDER : String(Math.round(score)),
      barPercent: score === null ? 0 : Math.round(score),
      color: s.color
    }
  })

  const radarValues = dims.map((d) => d.score)
  const total = sections.reduce((sum, s) => sum + s.items.length, 0)
  const scored = countByStatus(sections, 'scored')
  const evidence = countByStatus(sections, 'evidence')
  const notDeclared = countByStatus(sections, 'not_declared')
  const notMeasurable = countByStatus(sections, 'not_measurable')

  const totalScore = scoreOf(source.total_score)
  const resultMeta = RESULT_META[str(source.result).toUpperCase()]
  const vetoNote = str(source.veto_note) || DEFAULT_VETO_NOTE

  // 组内提示：服务端 section.note 优先；设计稿只在「D · 模型指纹（核心项）」组内放了一票否决说明（id=239a99e9）
  const rawSections = Array.isArray(source.sections) ? source.sections : []
  sections.forEach((s) => {
    const rawNote = str(rawSections.find((x) => str(x.code) === s.code)?.note)
    const note = rawNote || (s.code === 'D' ? vetoNote : '')
    if (note) s.note = note
  })

  return {
    reportNo: str(source.report_no),
    verdictTitle: VERDICT_TITLE,
    channelText: str(source.channel_name),
    scoreText: totalScore === null ? PLACEHOLDER : String(Math.round(totalScore)),
    scoreSectionLabel: SCORE_LABEL,
    scoreMaxLabel: SCORE_MAX_LABEL,
    resultLabel: resultMeta ? resultMeta.label : str(source.result) || PLACEHOLDER,
    resultTone: resultMeta ? resultMeta.tone : 'muted',
    verdict: str(source.verdict),
    statusCells: statusCellsOf(source),
    infoRows: infoRowsOf(source),
    metrics: (Array.isArray(source.key_metrics) ? source.key_metrics : []).map(toMetric),
    dims,
    radar: {
      labels: dims.map((d) => RADAR_SHORT_LABELS[d.code] ?? d.name),
      values: radarValues,
      geometry: radarGeometry(radarValues)
    },
    sections,
    detailSummary: [
      `${scored} 项计入总分`,
      `${evidence} 项仅证据`,
      `${notDeclared} 项未申报`,
      `${notMeasurable} 项不可测`,
      DETAIL_SCORE_HINT
    ].join(' · '),
    itemCountText: `共 ${total} 项`,
    findings: findingsOf(source),
    evidenceRows: (Array.isArray(source.evidence) ? source.evidence : []).map((e) => ({
      key: str(e.key),
      value: str(e.value)
    })),
    disclaimer: str(source.disclaimer) || DEFAULT_DISCLAIMER,
    vetoNote,
    weightNote: str(source.weight_note) || DEFAULT_WEIGHT_NOTE
  }
}
