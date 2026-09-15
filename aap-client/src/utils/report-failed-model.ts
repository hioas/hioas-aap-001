/**
 * 序号 7【检测验真】检测未通过报告 2（page-7-2）视图模型
 *
 * 设计真源：.calicat/raw/pages/page-7-2/design.tree.json（430 宽）
 *   顶部导航 5cd2c5ba（白底 · padding 48/16/12/16 · 返回 26 宽 · 「检测报告」17px Bold #0F172A ·
 *     报告编号 11px #94A3B8 · 标题前留白 12）
 *   未通过封面卡 07b82bea（白 r18 padding 20）：
 *     封面顶行：综合检测结论 12px Medium #64748B + 华南备线路 · 备用通道 12px #94A3B8
 *     综合分块（padding-top 16）：54 为 38px ExtraBold #DC2626 + 「综合评分 / 满分 100」12px #94A3B8 +
 *       结论标签 #FEF2F2 r14 h28（12px SemiBold #B91C1C）
 *     一票否决条（padding-top 16）：#FEF2F2 r12 padding 12 · 文案 12px #B91C1C
 *     结论措辞（padding-top 12）：文案 12px #475569
 *   分项评分总览卡 35a1df87（白 r18 padding 20 · 1px #EEF2F7）：「分项总览」15px SemiBold ·
 *     8 行（标签 101 宽 12px #475569 · 条底 h8 r4 #E2E8F0 · 条填取分项色 · 分值 12px SemiBold 同色）·
 *     权重说明盒 #F8FAFC r12 padding 12（11px #94A3B8 两行）
 *   D2详情卡 09ddc4ca（白 r18 padding 20 · 1px #FECACA）：「D2 鉴权有效性 · 详情」14px SemiBold +
 *     「12 分」14px Bold #DC2626 + 四行解释 12px #64748B（行高 20，首行 padding-top 8、其余 6）
 *   免责声明卡 1b0391c3（白 r18 padding 16/20 · 1px #EEF2F7）：图标 20px #94A3B8 + 两行文案
 *   底部操作 e60b6a5c（白底 padding 12/16/24/16 · 非圆角、非固定）：导出 PDF 193×44 r12 白底 1px #CBD5E1 +
 *     重新提交检测 flex 44 r12 #2563EB
 * 交互真源：page-7-2 interaction.json =「不存在图层交互数据」→ 退 PRD 09/17-spec/18-API/21-验收 + 画布 30 页清单
 *
 * ⚠️ 缺口（全部记入 .agents/state/aap-feature-status.csv 序号 7 备注，均不臆造）：
 *   1) 设计 D1–D8 名（连通性/鉴权/模型一致性/上下文/稳定性/计费口径/合规安全/并发压测）与 09-PRD §2 的
 *      D1 TTFT / D2 P50-TPS / D3 一致性 / D4 RPM / D5 TPM / D6 缓存命中 / D7 模型指纹 / D8 真实源
 *      **不是同一套口径**（设计「D2 鉴权」在 PRD 的 D 列表里不存在）→ 分项名/分值/否决项一律以服务端返回为准，
 *      本文件只负责渲染与派生；设计示例值仅作测试夹具与 H5 mock。
 *   2) 一票否决维度冲突：设计「D2 鉴权为关键项，未通过直接判未通过」vs 17-spec R-20 / 13-管理端PRD「D7<40 否决」
 *      → 文案按设计稿原文直显（不静默改写），冲突已记台账待人类拍板。
 *   3) 配色阈值：设计样本 89/82 绿、66/61/58/55 琥珀、12/0 红，与 09-PRD §3 pass_score=70、17-spec R-20
 *      否决线 40 完全自洽 → 取 70/40（非 80/40），阈值来源写在 PASS_SCORE / VETO_SCORE 注释。
 *   4) 分项条填宽度：设计 8 行里 6 行 = 分值百分比（D2 29/D3 129/D5 143/D6 154/D7 136 ≈ 分值×条底宽 231），
 *      但 D1 194（89% 应 205）、D4 173（82% 应 189）偏短 → 设计自身不自洽，实现统一按分值百分比（零篡改分值）。
 *      另：D8 分值 0 设计仍画了 4px 红色残段 → 实现按 min-width 4px 还原（样式侧，见页面 scoped 样式）。
 *   5) 报告详情字段级 schema 未在 18-API 定义 → 本文件的 ReportFailedRaw 字段名取自 15-数据字典
 *      （aap_report.report_no/total_score/result、aap_detection_result.probe_code/score）与页面 6 既有口径；
 *      verdict / veto_note / dims[].name / detail.lines 无表可依 → missing-prd。
 *   6) 「重新提交检测」= 09-PRD §5 重测（人工点击）→ POST /detection-jobs（18-API 只列路径未列方法，方法为推断）；
 *      请求体只带 credential_id（15-数据字典 credential 1:N detection_job）；配额/互斥错误码文案用服务端 message。
 */
import { PLACEHOLDER } from './format'

/* --------------------------------- 设计稿原文（不得改写） --------------------------------- */

export const PAGE_TITLE = '检测报告'
/** 顶部右侧「报告编号 DR-…」是设计稿里**单个**文本图层（含前缀），必须连前缀一起还原 */
export const REPORT_NO_PREFIX = '报告编号 '
export const VERDICT_TITLE = '综合检测结论'
export const SCORE_LABEL = '综合评分'
export const SCORE_MAX_LABEL = '满分 100'
export const DIM_TITLE = '分项总览'
export const DETAIL_TITLE = 'D2 鉴权有效性 · 详情'
export const DISCLAIMER_TITLE = '本报告基于抽样检测生成'
export const EXPORT_TEXT = '导出 PDF'
export const RESUBMIT_TEXT = '重新提交检测'

/** 权重说明（design 18dda7b2 逐字，本页为固定说明文案） */
export const WEIGHT_NOTE = 'D2 鉴权为关键项，未通过将直接判定为“未通过”；其余分项仅作参考。'

/** 服务端未给措辞时的设计稿原文回退 */
export const DEFAULT_VETO_NOTE =
  '命中一票否决项：D2 鉴权在检测期间返回 401，模型清单存在 1 项无法调用。'
export const DEFAULT_VERDICT =
  '请核对 APIKey 有效期与模型开放范围后重新提交检测；已通过项无需重复准备。'
export const DEFAULT_DISCLAIMER = '未通过结论仅代表检测时点状态，修正后重新检测即可更新结论。'

/* --------------------------------- 判定阈值与配色 --------------------------------- */

/** 通过线：09-PRD §3「总分 ≥ pass_score（默认 70）」 */
export const PASS_SCORE = 70
/** 一票否决线：17-spec R-20「D7 < 40 一票否决」 */
export const VETO_SCORE = 40
export const COLOR_PASS = '#16A34A'
export const COLOR_WARN = '#F59E0B'
export const COLOR_FAIL = '#DC2626'
export const COLOR_TRACK = '#E2E8F0'

/** 结果三态文案（09-PRD §3：通过 / 未通过 / 人工复核） */
export const RESULT_LABELS: Record<string, string> = {
  PASS: '通过',
  FAIL: '未通过',
  MANUAL_REVIEW: '人工复核'
}
/** 缺失 result 时的默认（本页即「检测未通过报告」） */
export const DEFAULT_RESULT_LABEL = '未通过'

/* --------------------------------- 路由 / storage / 提示 --------------------------------- */

export const REPORT_ID_KEY = 'aap_report_id'
export const CREDENTIAL_ID_KEY = 'aap_credential_id'
export const DETECTING_PAGE = '/pages/detecting/index'
export const MISSING_REPORT_TOAST = '缺少报告标识'
export const MISSING_CREDENTIAL_TOAST = '缺少凭证标识，无法重新提交检测'
export const EXPORT_READY_TOAST = '导出链接已生成，请在浏览器中打开'
export const RESUBMIT_READY_TOAST = '已重新提交检测，正在跳转'
export const LOAD_FAIL_TOAST = '加载失败，请稍后重试'

/* --------------------------------- 原始数据结构 --------------------------------- */

export interface FailedDimRaw {
  code?: string | null
  name?: string | null
  score?: number | null
}

export interface FailedDetailRaw {
  code?: string | null
  title?: string | null
  score?: number | null
  lines?: string[] | null
}

export interface ReportFailedRaw {
  report_no?: string | null
  channel_name?: string | null
  total_score?: number | null
  result?: string | null
  veto_triggered?: boolean | null
  veto_note?: string | null
  verdict?: string | null
  credential_id?: string | null
  dims?: FailedDimRaw[] | null
  detail?: FailedDetailRaw | null
  disclaimer?: string | null
}

/* --------------------------------- 视图模型 --------------------------------- */

export interface FailedDimRow {
  code: string
  label: string
  score: number | null
  scoreText: string
  barPercent: number
  color: string
}

export interface FailedDetailView {
  visible: boolean
  title: string
  scoreText: string
  lines: string[]
}

export interface ReportFailedModel {
  reportNo: string
  channel: string
  scoreText: string
  resultLabel: string
  vetoVisible: boolean
  vetoText: string
  verdictText: string
  dims: FailedDimRow[]
  weightNote: string
  detail: FailedDetailView
  disclaimerTitle: string
  disclaimerText: string
  credentialId: string
}

/* --------------------------------- 纯函数 --------------------------------- */

function str(value: unknown): string {
  return typeof value === 'string' ? value.trim() : value === undefined || value === null ? '' : String(value)
}

function scoreOf(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : null
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0
  if (value <= 0) return 0
  if (value >= 100) return 100
  return value
}

/** 分项条颜色：≥70 绿（通过线）· 40–69 琥珀 · <40 红（否决线）；无分数用条底灰 */
export function scoreColor(score: number | null): string {
  if (score === null) return COLOR_TRACK
  if (score >= PASS_SCORE) return COLOR_PASS
  if (score >= VETO_SCORE) return COLOR_WARN
  return COLOR_FAIL
}

function toDim(raw: FailedDimRaw): FailedDimRow {
  const code = str(raw.code)
  const name = str(raw.name)
  const score = scoreOf(raw.score)
  return {
    code,
    label: name ? `${code} ${name}` : code,
    score,
    scoreText: score === null ? PLACEHOLDER : String(Math.round(score)),
    barPercent: score === null ? 0 : clampPercent(Math.round(score)),
    color: scoreColor(score)
  }
}

function toDetail(raw: FailedDetailRaw | null | undefined): FailedDetailView {
  const lines = Array.isArray(raw?.lines) ? raw!.lines!.map((l) => str(l)).filter((l) => l !== '') : []
  const title = str(raw?.title) || DETAIL_TITLE
  const score = scoreOf(raw?.score)
  return {
    visible: lines.length > 0,
    title,
    scoreText: score === null ? PLACEHOLDER : `${Math.round(score)} 分`,
    lines
  }
}

/** 构建页面视图模型（缺字段留空/占位，不臆造业务值） */
export function buildReportFailedModel(raw?: ReportFailedRaw | null): ReportFailedModel {
  const source: ReportFailedRaw = raw ?? {}
  const total = scoreOf(source.total_score)
  const resultRaw = str(source.result)
  const vetoNote = str(source.veto_note)

  return {
    reportNo: str(source.report_no),
    channel: str(source.channel_name),
    scoreText: total === null ? PLACEHOLDER : String(Math.round(total)),
    resultLabel: RESULT_LABELS[resultRaw] ?? (resultRaw || DEFAULT_RESULT_LABEL),
    vetoVisible: source.veto_triggered === true || vetoNote !== '',
    vetoText: vetoNote || DEFAULT_VETO_NOTE,
    verdictText: str(source.verdict) || DEFAULT_VERDICT,
    dims: (Array.isArray(source.dims) ? source.dims : []).map(toDim),
    weightNote: WEIGHT_NOTE,
    detail: toDetail(source.detail),
    disclaimerTitle: DISCLAIMER_TITLE,
    disclaimerText: str(source.disclaimer) || DEFAULT_DISCLAIMER,
    credentialId: str(source.credential_id)
  }
}
