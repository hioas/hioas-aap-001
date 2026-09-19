/**
 * 序号 11「模型定价-详情」（page-11）视图模型
 *
 * 文案真源：.calicat/raw/pages/page-11/design.tree.json（430 宽 · 设计总高 1541 · 无 TabBar）
 *   本文件里的中文常量**逐字抄自设计树**，页面不得改写（硬约束 5）。
 * 业务真源：
 *   06-报价模型与计费编译规则 §1.2 单价字段表（单位 $/1M tokens 真实单价；input/output 必填，缓存与媒体价可选）
 *   06-PRD §1.3 时段价规则（tz 等）· §1.4 阶梯价规则（tier/档位）· §4.2 边界冲突检测（单价为负、倍率 ≤0 或 NaN → 拒绝）
 *   15-数据模型 ER：aap_quote_item（quote_id、model_name、input/output_price ≥0、cache_read/write/write_1h_price…）
 *   17-spec：错误码 E-1401 时段重叠 / E-1402 阶梯空洞 / E-1403 倍率非法（服务端拒绝，前端只透传 message）
 * 接口真源：18-API设计OpenAPI.md「Quote」→ /quotes、/{quoteId}/items、/items/{itemId}
 *
 * ⚠️ 记 missing-prd（不臆造，已同步台账与状态文件）：
 *   1) 单个价格字段的「启用」勾选**没有 PRD 字段** → 本实现取「值 > 0 视为已启用」（与设计稿样例完全一致：
 *      输入 2.50 / 输出 10.00 勾选，其余 0 未勾选），提交时未勾选字段直接省略；
 *   2) 「计价方式」（设计值「按 token」）选项集合在 22 份 PRD 与 18-API 零命中 → 只渲染设计值/服务端值，不造选项；
 *   3) 「添加计费分支」「新增参数/Header」「新增时间条件」「新增规则组」的**新增项字段级 schema**无依据
 *      → 仅本地操作 + 提交已有结构（规则组 6 字段为设计稿直接可见的 6 个控件）；
 *   4) 请求规则条件枚举（时间/小时/大于等于）与 06-PRD §1.3 的 peak_ranges 不是同一套口径 → 只回显
 *      设计默认值（时间/小时/Asia/Shanghai/大于等于）与服务端值；
 *   5) 媒体价 5 个字段名中仅 image_input_price 在 06-PRD 出现（PRD 只写 image/audio 价与 audio_* 通配）
 *      → 其余 4 个键名（image_cache_input_price / image_output_price / audio_input_price / audio_output_price）
 *      为推断，已记 missing-prd。
 */

export interface PriceFieldDef {
  key: string
  label: string
}

export interface PriceField extends PriceFieldDef {
  group: 'token' | 'media'
  /** 勾选 = 启用（PRD 无该字段 → 见文件头 missing-prd 1） */
  enabled: boolean
  /** 页面输入的原始串（不即时格式化，避免打字被吞） */
  value: string
}

export interface RequestRuleGroup {
  no: number
  field: string
  granularity: string
  tz: string
  op: string
  value: string
  multiplier: string
}

export interface QuoteItemRaw {
  item_id?: string
  id?: string
  quote_id?: string
  quoteId?: string
  model_name?: string
  modelName?: string
  tier?: string
  billing_mode?: string
  request_rules?: Array<Record<string, unknown>>
  [key: string]: unknown
}

export interface ItemViewModel {
  itemId: string
  quoteId: string
  modelName: string
  badgeNo: number
  tier: string
  billingMode: string
  priceFields: PriceField[]
  ruleGroups: RequestRuleGroup[]
}

export interface PricingState {
  priceFields: PriceField[]
  ruleGroups: RequestRuleGroup[]
  tier?: string
  billingMode?: string
}

/* ---------- 文案（逐字抄自 design.tree.json） ---------- */

export const PAGE_SUBTITLE = '模型定价'
export const NAV_SAVE_TEXT = '保存'
export const BOTTOM_SAVE_TEXT = '保存价格'

export const TIER_LABEL = '档位'
export const MODE_FALLBACK = '按 token'
export const ADD_BRANCH_TEXT = '添加计费分支'

export const TOKEN_CARD_TITLE = 'Token 价格'
export const PRICE_UNIT_LABEL = '$/1M token'
export const MEDIA_TITLE = '媒体定价'

export const RULE_CARD_TITLE = '请求规则计费'
export const RULE_NOTE = '条件满足时，最终价格乘以 X；多条命中的倍率会相乘；小于 1 的值为折扣。'
export const RULE_GROUP_PREFIX = '规则组 #'
export const RULE_HINT = '点击展开，配置计费请求规则'
export const ADD_PARAM_TEXT = '新增参数/Header'
export const ADD_TIME_TEXT = '新增时间条件'
export const MULTIPLIER_LABEL = '倍率'
export const MULTIPLIER_NOTE = '匹配条件时，最终费用 = 基础费用 × 倍率'
export const ADD_RULE_GROUP_TEXT = '新增规则组'
export const VALUE_PLACEHOLDER = '值'

export const TIER_SUMMARY_PREFIX = '始终匹配（默认档位）'

export const DEFAULT_RULE_FIELD = '时间'
export const DEFAULT_RULE_GRANULARITY = '小时'
export const DEFAULT_RULE_TZ = 'Asia/Shanghai'
export const DEFAULT_RULE_OP = '大于等于'
export const DEFAULT_MULTIPLIER = '1.0'

/** 必填单价（06-PRD §1.2 ✅） */
export const REQUIRED_PRICE_KEYS = ['input_price', 'output_price']

export const TOKEN_PRICE_FIELDS: PriceFieldDef[] = [
  { key: 'input_price', label: '输入价格' },
  { key: 'output_price', label: '输出价格' },
  { key: 'cache_read_price', label: '缓存读取价格' },
  { key: 'cache_write_price', label: '缓存写入价格' },
  { key: 'cache_write_1h_price', label: '1 小时缓存写入价格' }
]

export const MEDIA_PRICE_FIELDS: PriceFieldDef[] = [
  { key: 'image_input_price', label: '图像输入价格' },
  { key: 'image_cache_input_price', label: '图片缓存输入价格' },
  { key: 'image_output_price', label: '图像输出价格' },
  { key: 'audio_input_price', label: '音频输入价格' },
  { key: 'audio_output_price', label: '音频输出价格' }
]

/** toast 占位文案（设计稿无 toast 稿 → 记 missing-prd） */
export const TOAST_SAVED = '保存成功'
export const TOAST_FAIL = '保存失败，请稍后重试'
export const TOAST_MISSING_ITEM = '未找到模型明细，请返回重试'

export const PRICING_PAGE = '/pages/model-pricing/index'
export const QUOTE_ITEM_ID_KEY = 'aap_quote_item_id'
export const QUOTE_ID_KEY = 'aap_quote_id'

/* ---------- 工具 ---------- */

/** 宽松取数：空串/非数字 → null（不抛异常） */
export function toNumber(v: unknown): number | null {
  if (typeof v === 'number') return Number.isFinite(v) ? v : null
  if (typeof v === 'string') {
    const s = v.trim()
    if (!s) return null
    const n = Number(s)
    return Number.isFinite(n) ? n : null
  }
  return null
}

/** 0 → "0"；其余两位小数（与设计稿样例逐值一致：2.50 / 10.00 / 0） */
export function formatPrice(v: unknown): string {
  const n = toNumber(v)
  if (n === null || n === 0) return '0'
  return n.toFixed(2)
}

/** 倍率显示：整数补一位小数（设计稿 1.0），非整数原样 */
export function formatMultiplier(v: unknown): string {
  const n = toNumber(v)
  if (n === null) return ''
  return Number.isInteger(n) ? n.toFixed(1) : String(n)
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v.trim() : v === undefined || v === null ? '' : String(v)
}

/** 单价字段：值 > 0 视为「已勾选/启用」（见文件头 missing-prd 1） */
export function buildPriceFields(raw?: QuoteItemRaw | null): PriceField[] {
  const r = raw ?? {}
  const build = (defs: PriceFieldDef[], group: 'token' | 'media'): PriceField[] =>
    defs.map((d) => {
      const n = toNumber(r[d.key])
      return {
        key: d.key,
        label: d.label,
        group,
        enabled: n !== null && n > 0,
        value: formatPrice(r[d.key])
      }
    })
  return [...build(TOKEN_PRICE_FIELDS, 'token'), ...build(MEDIA_PRICE_FIELDS, 'media')]
}

export function togglePriceField(fields: PriceField[], key: string): PriceField[] {
  return fields.map((f) => (f.key === key ? { ...f, enabled: !f.enabled } : f))
}

export function setPriceValue(fields: PriceField[], key: string, value: string): PriceField[] {
  return fields.map((f) => (f.key === key ? { ...f, value } : f))
}

/** 卡1 摘要：设计原文 = 固定语 + 输入/输出价（两位小数） */
export function tierSummaryText(fields: PriceField[]): string {
  const price = (key: string): string => {
    const hit = fields.find((f) => f.key === key)
    const n = toNumber(hit?.value)
    return (n === null ? 0 : n).toFixed(2)
  }
  return `${TIER_SUMMARY_PREFIX}· 输入 $${price('input_price')} 输出 $${price('output_price')} / 1M token`
}

export function ruleGroupTitle(group: RequestRuleGroup): string {
  return `${RULE_GROUP_PREFIX}${group.no}`
}

function newRuleGroup(no: number, raw?: Record<string, unknown>): RequestRuleGroup {
  const r = raw ?? {}
  return {
    no,
    field: readString(r.field) || DEFAULT_RULE_FIELD,
    granularity: readString(r.granularity) || DEFAULT_RULE_GRANULARITY,
    tz: readString(r.tz) || DEFAULT_RULE_TZ,
    op: readString(r.op) || DEFAULT_RULE_OP,
    value: readString(r.value),
    multiplier: formatMultiplier(r.multiplier) || DEFAULT_MULTIPLIER
  }
}

function renumber(groups: RequestRuleGroup[]): RequestRuleGroup[] {
  return groups.map((g, i) => ({ ...g, no: i + 1 }))
}

/** 规则组：服务端给几组就几组；缺省渲染设计稿那一组（设计可见 1 组） */
export function buildRuleGroups(raw?: QuoteItemRaw | null): RequestRuleGroup[] {
  const list = raw?.request_rules
  if (!Array.isArray(list) || list.length === 0) return [newRuleGroup(1)]
  return renumber(list.map((r, i) => newRuleGroup(i + 1, r)))
}

export function addRuleGroup(groups: RequestRuleGroup[]): RequestRuleGroup[] {
  return renumber([...groups, newRuleGroup(groups.length + 1)])
}

/** 删除后重新编号；不允许删到 0 组（设计稿固定至少 1 组） */
export function removeRuleGroup(groups: RequestRuleGroup[], no: number): RequestRuleGroup[] {
  const left = groups.filter((g) => g.no !== no)
  if (left.length === 0) return renumber(groups.slice(0, 1))
  return renumber(left)
}

export type RuleField = 'field' | 'granularity' | 'tz' | 'op' | 'value' | 'multiplier'

export function setRuleValue(
  groups: RequestRuleGroup[],
  no: number,
  field: RuleField,
  value: string
): RequestRuleGroup[] {
  return groups.map((g) => (g.no === no ? { ...g, [field]: value } : g))
}

/** 校验：必填价空/非法/负数（06-PRD §1.2、§4.2）；倍率 ≤0 或非数字（§4.2、E-1403）。返回首个错误。 */
export function validateItem(state: PricingState): string[] {
  for (const def of [...TOKEN_PRICE_FIELDS, ...MEDIA_PRICE_FIELDS]) {
    const f = state.priceFields.find((x) => x.key === def.key)
    if (!f || !f.enabled) continue
    const s = f.value.trim()
    if (!s) {
      if (REQUIRED_PRICE_KEYS.includes(def.key)) return [`请输入${def.label}`]
      continue
    }
    const n = toNumber(s)
    if (n === null) return [`请输入正确的${def.label}`]
    if (n < 0) return [`${def.label}不能为负数`]
  }
  for (const g of state.ruleGroups) {
    const s = g.multiplier.trim()
    if (!s) return ['请输入倍率']
    const m = toNumber(s)
    if (m === null) return ['请输入正确的倍率']
    if (m <= 0) return ['倍率必须大于 0']
  }
  return []
}

/**
 * 提交体：只带启用字段（未启用直接省略），附档位/计价方式。
 *
 * ⚠️ **不带 `request_rules`**（缺陷 13）：后端 **V15 明确「请求规则仅管理端可设置」**，
 * 供应商写 → `E-1001`（字段级定位到 `request_rules`，见 `QuoteService` 类注释）。
 * 而本页**默认就渲染一个规则组**，此前只要 `ruleGroups.length` 就带上它 →
 * 供应商在默认状态下**永远保存不了价格**（实测 `PUT /quotes/items/{id}` 直接被拒）→ 无法报价。
 * 规则组 UI 保留（设计稿有），但**不进请求体**；规则由管理端维护。
 */
export function buildItemPayload(state: PricingState): Record<string, unknown> {
  const payload: Record<string, unknown> = {}
  for (const f of state.priceFields) {
    if (!f.enabled) continue
    const n = toNumber(f.value.trim())
    payload[f.key] = n === null ? 0 : n
  }
  if (state.tier) payload.tier = state.tier
  if (state.billingMode) payload.billing_mode = state.billingMode
  return payload
}

export function buildItemViewModel(raw?: QuoteItemRaw | null): ItemViewModel {
  const r = raw ?? {}
  return {
    itemId: readString(r.item_id ?? r.id),
    quoteId: readString(r.quote_id ?? r.quoteId),
    modelName: readString(r.model_name ?? r.modelName),
    // 设计稿卡片序号固定为「1」（画布该帧只展示一个模型），非业务字段
    badgeNo: 1,
    tier: readString(r.tier),
    billingMode: readString(r.billing_mode) || MODE_FALLBACK,
    priceFields: buildPriceFields(r),
    ruleGroups: buildRuleGroups(r)
  }
}
