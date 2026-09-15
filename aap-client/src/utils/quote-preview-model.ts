/**
 * 序号 12「报价预览与提交 2」（page-12-2）视图模型
 *
 * 文案真源：.calicat/raw/pages/page-12-2/design.tree.json（430 宽 · 设计总高 1027 · 无 TabBar · 4 张卡 + 白底操作条）
 *   本文件里的中文常量**逐字抄自设计树**，页面不得改写（硬约束 5）。
 * 业务真源：
 *   10-报价与合同结算PRD §3.2 QuoteItem（model_name / input_price / output_price / cache_read_price /
 *     cache_write_price / price_time_rules / price_tier_rules / request_rules）· §3.3 时段价（tz/peak_ranges/倍率）·
 *     §3.4 阶梯价（tier_field/tiers[]/price_strategy）· §3.5 请求级加价 · §4.1 状态机 DRAFT→SUBMITTED ·
 *     §5.1 提交时校验 V1–V17（V1 明细行≥1、V3 输入/输出价必填、V15 request_rules 仅管理端…）
 *   06-报价模型与计费编译规则 §1.2（八大单价真实单价 $/1M tokens）· §1.3 时段语义 start 含 end 不含 ·
 *     §1.4 阶梯 tiers[]（label 参与档位标签）· §2 三道闸门（编译 → 模拟验证 → 人工确认）
 *   17-spec：E-1601 状态非法流转 / E-1602 未通过检测报报价 / E-1407 未确认写入（服务端拒绝，前端透传 message）
 * 接口真源：18-API设计OpenAPI.md「Quote」→ /quotes、/{quoteId}、/{quoteId}/submit（前缀 /api/v1）
 *
 * ⚠️ 记 missing-prd（不臆造，已同步台账与状态文件）：
 *   1) 18-API 卡片只列路径未列方法与请求体 → GET 详情 / POST 提交为 REST 语义推断；`/submit` **无请求体 schema**
 *      → 本实现不发请求体（确认勾选只当前端门禁）；
 *   2) 标签文案派生规则（时段价+阶梯价 / 阶梯价 / 时段价 / 仅基础价）与三种底色为**推断**：
 *      设计稿只给了三个样例（时段+阶梯=蓝、仅阶梯=绿、无规则=灰），本实现按「有时段→蓝、仅阶梯→绿、无→灰」派生；
 *   3) 第三列价格取「有 cache_read_price 取缓存读，否则取 cache_write_price 缓存写」（设计样例如此）；
 *      `cache_write_1h_price` 在设计稿无标签 → 不展示（不臆造标签）；
 *   4) 规则行文案为**派生**而非服务端字段：时段价行由 peak_ranges+倍率拼装；阶梯价行有 label 用
 *      「N 档阶梯：label / label」、无 label 用设计卡2 的措辞「N 档阶梯已启用，末档覆盖至不限量」；
 *   5) 请求规则行文案「请求规则计费：命中条件时按倍率计费，多条命中相乘」在三张卡中**完全相同** →
 *      作为设计常量，仅当 request_rules 非空时渲染（不随规则内容变化）；
 *   6) 确认勾选默认**已勾选**（设计稿勾选框为蓝底白勾）；
 *   7) 未勾选/无明细时的 toast 文案设计稿与 PRD 均无稿 → 占位；
 *   8) 提交成功后跳转目标无依据 → 跳报价单列表 /pages/quotes/index（状态 SUBMITTED 在列表可见）。
 */
import { QUOTE_ID_KEY } from './model-pricing-model'

export { QUOTE_ID_KEY }

/* ---------- 设计文案（逐字抄自 design.tree.json） ---------- */

export const PAGE_TITLE = '报价预览'
export const BACK_EDIT_TEXT = '返回编辑'
export const SUBMIT_TEXT = '提交报价'
export const CONFIRM_TEXT = '我确认以上价格真实有效，并同意《报价服务条款》'
export const HINT_TEXT = '提交后进入运营审核，审核通过将自动编译计费表达式并同步渠道。'
export const REQUEST_RULE_TEXT = '请求规则计费：命中条件时按倍率计费，多条命中相乘'
export const TIER_LABEL_PREFIX = ' 档阶梯：'
export const TIER_FALLBACK_PREFIX = ' 档阶梯已启用，末档覆盖至不限量'
export const TIME_LABEL_PREFIX = '高峰 '
export const TIME_PEAK_LEAD = ' 上浮 '
export const TIME_OFFPEAK_LEAD = '，其余时段 '
export const TIME_MULTIPLIER_UNIT = ' 倍'

export const TAG_TIME_AND_TIER = '时段价 + 阶梯价'
export const TAG_TIER = '阶梯价'
export const TAG_TIME = '时段价'
export const TAG_BASE = '仅基础价'

export const PRICE_LABEL_INPUT = '输入'
export const PRICE_LABEL_OUTPUT = '输出'
export const PRICE_LABEL_CACHE_READ = '缓存读'
export const PRICE_LABEL_CACHE_WRITE = '缓存写'

/** toast 占位（设计稿与 PRD 均无 toast 稿 → 记 missing-prd 7） */
export const TOAST_NEED_CONFIRM = '请先确认报价条款'
export const TOAST_NO_ITEM = '暂无模型报价，无法提交'
export const TOAST_SUBMITTED = '已提交审核'
export const TOAST_FAIL = '操作失败，请稍后重试'
export const TOAST_MISSING_QUOTE = '未找到报价单，请返回重试'

export const QUOTES_LIST_PAGE = '/pages/quotes/index'

/* ---------- 类型 ---------- */

export interface PriceColumn {
  label: string
  value: string
}

export type RuleTone = 'amber' | 'primary'

export interface RuleLine {
  tone: RuleTone
  text: string
}

export type TagTone = 'primary' | 'success' | 'neutral'

export interface ModelTag {
  text: string
  tone: TagTone
}

export interface PreviewCard {
  itemId: string
  modelName: string
  tag: ModelTag
  prices: PriceColumn[]
  rules: RuleLine[]
}

/** 时段价规则（10-PRD §3.3 / 06-PRD §1.3） */
export interface TimeRulesRaw {
  tz?: string
  weekday_scope?: string
  peak_ranges?: Array<{ start?: string; end?: string }>
  peak_multiplier?: number | string
  offpeak_multiplier?: number | string
}

/** 阶梯价规则（10-PRD §3.4 / 06-PRD §1.4） */
export interface TierRulesRaw {
  tier_field?: string
  price_strategy?: string
  tiers?: Array<{ min?: number | null; max?: number | null; label?: string }>
}

export interface QuoteItemLike {
  item_id?: string
  itemId?: string
  id?: string
  model_name?: string
  modelName?: string
  input_price?: number | string
  output_price?: number | string
  cache_read_price?: number | string
  cache_write_price?: number | string
  price_time_rules?: TimeRulesRaw
  price_tier_rules?: TierRulesRaw
  request_rules?: unknown[]
  [key: string]: unknown
}

export interface QuoteDetailLike {
  quote_id?: string
  quoteId?: string
  id?: string
  quote_no?: string
  status?: string
  items?: QuoteItemLike[]
}

export interface SubmitState {
  confirmed: boolean
  itemCount: number
}

/* ---------- 工具 ---------- */

function toNumber(v: unknown): number | null {
  if (typeof v === 'number') return Number.isFinite(v) ? v : null
  if (typeof v === 'string') {
    const s = v.trim()
    if (!s) return null
    const n = Number(s)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v.trim() : v === undefined || v === null ? '' : String(v)
}

function hasItems(v: unknown): boolean {
  return Array.isArray(v) && v.length > 0
}

/** 单价展示：一位小数 + ¥ 前缀（设计样例 ¥1.2 / ¥3.6 / ¥0.6 / ¥2.0 / ¥12.0 全部一位小数） */
export function formatPrice(v: unknown): string {
  const n = toNumber(v)
  return `¥${(n === null ? 0 : n).toFixed(1)}`
}

function formatMultiplier(v: unknown): string {
  const n = toNumber(v)
  return n === null ? '' : String(n)
}

/** 标签派生（见文件头 missing-prd 2） */
export function buildTag(item?: QuoteItemLike | null): ModelTag {
  const r = item ?? {}
  const hasTime = hasItems((r.price_time_rules as TimeRulesRaw | undefined)?.peak_ranges)
  const hasTier = hasItems((r.price_tier_rules as TierRulesRaw | undefined)?.tiers)
  if (hasTime && hasTier) return { text: TAG_TIME_AND_TIER, tone: 'primary' }
  if (hasTier) return { text: TAG_TIER, tone: 'success' }
  if (hasTime) return { text: TAG_TIME, tone: 'primary' }
  return { text: TAG_BASE, tone: 'neutral' }
}

/** 时段价行文案（06-PRD §1.3 派生）；无 peak_ranges → 空串 */
export function timeRuleText(rules?: TimeRulesRaw | null): string {
  const ranges = rules?.peak_ranges
  if (!hasItems(ranges)) return ''
  const list = (ranges as Array<{ start?: string; end?: string }>)
    .map((r) => `${readString(r?.start)}–${readString(r?.end)}`)
    .filter((s) => s !== '–')
    .join(' / ')
  if (!list) return ''
  const peak = formatMultiplier(rules?.peak_multiplier)
  const offpeak = formatMultiplier(rules?.offpeak_multiplier)
  let out = `${TIME_LABEL_PREFIX}${list}`
  if (peak) out += `${TIME_PEAK_LEAD}${peak}${TIME_MULTIPLIER_UNIT}`
  if (offpeak) out += `${TIME_OFFPEAK_LEAD}${offpeak}${TIME_MULTIPLIER_UNIT}`
  return out
}

/** 阶梯价行文案（06-PRD §1.4）：有 label 列标签，无 label 用设计卡2 措辞 */
export function tierRuleText(rules?: TierRulesRaw | null): string {
  const tiers = rules?.tiers
  if (!hasItems(tiers)) return ''
  const list = (tiers as Array<{ label?: string }>).map((t) => readString(t?.label))
  if (list.every((l) => l.length > 0)) {
    return `${list.length}${TIER_LABEL_PREFIX}${list.join(' / ')}`
  }
  return `${(tiers as unknown[]).length}${TIER_FALLBACK_PREFIX}`
}

/** 规则行集合（时段 → 阶梯 → 请求规则，与设计稿顺序一致） */
export function previewRuleLines(item?: QuoteItemLike | null): RuleLine[] {
  const r = item ?? {}
  const lines: RuleLine[] = []
  const time = timeRuleText(r.price_time_rules as TimeRulesRaw | undefined)
  if (time) lines.push({ tone: 'amber', text: time })
  const tier = tierRuleText(r.price_tier_rules as TierRulesRaw | undefined)
  if (tier) lines.push({ tone: 'primary', text: tier })
  if (hasItems(r.request_rules)) lines.push({ tone: 'primary', text: REQUEST_RULE_TEXT })
  return lines
}

/** 价格列：输入/输出 + 第三列缓存价（见文件头 missing-prd 3） */
export function previewPrices(item?: QuoteItemLike | null): PriceColumn[] {
  const r = item ?? {}
  const cols: PriceColumn[] = [
    { label: PRICE_LABEL_INPUT, value: formatPrice(r.input_price) },
    { label: PRICE_LABEL_OUTPUT, value: formatPrice(r.output_price) }
  ]
  const read = toNumber(r.cache_read_price)
  const write = toNumber(r.cache_write_price)
  if (read !== null && read > 0) {
    cols.push({ label: PRICE_LABEL_CACHE_READ, value: formatPrice(read) })
  } else if (write !== null && write > 0) {
    cols.push({ label: PRICE_LABEL_CACHE_WRITE, value: formatPrice(write) })
  }
  return cols
}

/** 整页视图模型：服务端给几行就渲染几张卡（设计稿 3 张为样例） */
export function buildPreviewItems(detail?: QuoteDetailLike | null): PreviewCard[] {
  const items = detail?.items
  if (!Array.isArray(items)) return []
  return items.map((item) => ({
    itemId: readString(item?.item_id ?? item?.itemId ?? item?.id),
    modelName: readString(item?.model_name ?? item?.modelName),
    tag: buildTag(item),
    prices: previewPrices(item),
    rules: previewRuleLines(item)
  }))
}

/** 报价单号/状态等页头信息（18-API 无字段级 schema → 容错读取） */
export function readQuoteId(detail?: QuoteDetailLike | null): string {
  return readString(detail?.quote_id ?? detail?.quoteId ?? detail?.id)
}

/**
 * 规则块的间距类（设计稿逐卡如此，属设计自身不一致，按设计还原）：
 *   卡1（3 条规则）首块 padding-top 12、其余 8；卡2（2 条）首块 12、其后 8；
 *   卡3（**只有 1 条**规则）唯一块的 wrapper padding-top 是 **8**。
 * 用 12 会让卡3 高 168（设计 164）、整页高 1031（设计 1027）—— 该偏差由 DOM 实测抓出（见 evidence/measure-序号12-run1.json）。
 */
export function ruleBlockClass(index: number, count: number): 'card__block--first' | 'card__block--tight' {
  return index === 0 && count > 1 ? 'card__block--first' : 'card__block--tight'
}

/** 本地门禁：服务端 V1–V17 仍为准（10-PRD §5.1） */
export function validateSubmit(state: SubmitState): string[] {
  if (state.itemCount <= 0) return [TOAST_NO_ITEM]
  if (!state.confirmed) return [TOAST_NEED_CONFIRM]
  return []
}

/** 提交请求体：18-API 无 schema（见文件头 missing-prd 1）→ 不发字段 */
export function buildSubmitPayload(_state: SubmitState): Record<string, unknown> {
  return {}
}
