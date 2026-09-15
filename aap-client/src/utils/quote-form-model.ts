/**
 * 序号 12-v1【报价管理】新增报价单-初始态（page-26）视图模型 — 纯逻辑
 *
 * 设计真源：.calicat/raw/pages/page-26/design.tree.json（430 宽 · 设计总高 1238 · 无 TabBar）
 *   顶部导航 c36637be padding[48,16,12,16] #FFFFFF：返回 36×36 r18 #F1F5F9 · 标题块 156 宽
 *     （「新增报价单」18px Bold #0F172A h24 / 「填写基本信息并设置模型报价」12px #94A3B8 h18）· 帮助 36×36 r18 #F1F5F9
 *   内容区 935a5fe4 padding[16,16,20,16] gap16，四块：
 *     1) 步骤卡 7acff570 padding16 r16 #FFFFFF：步骤1（圆点 26 #2563EB + 「填写信息」13px SemiBold #0F172A h18
 *        +「名称 / 密钥 / 单号」11px #94A3B8 h15）、连线 2px #E2E8F0（fill）、步骤2（圆点 26 #F1F5F9 + 「2」#94A3B8
 *        +「设置报价」13px SemiBold #94A3B8 +「模型定价」11px #CBD5E1）
 *     2) 基本信息卡 82bbea2b padding16 r16 #FFFFFF：标题行（竖条 5×16 r2 #2563EB + 「基本信息」15px Bold h20 + 占位
 *        + 必填提示〔red 图标 12 + 「为必填项」11px #94A3B8〕）
 *        · 字段「报价单名称 *」：标签行 13px SemiBold #334155 + red「*」；输入框 h48 r12 bg #F8FAFC 描边 0.8 #E2E8F0
 *          （占位「请输入报价单名称，如：2024Q3 主线路报价」14px #CBD5E1 + 清除图标 16px）；字数提示右对齐「0/30」11px #94A3B8
 *        · 分隔线 h1 #F1F5F9（wrapper padding-top 16）
 *        · 字段「报价单号」：标签行 + chip「系统生成」h18 r9 bg #EFF6FF（10px SemiBold #2563EB）
 *          ；只读框 h48 r12 bg #F1F5F9 描边 0.8 #CBD5E1（图标 18 + 「保存后自动生成」14px Medium #94A3B8
 *          + 右侧「QT-XXXXXXXX-XXXX」10px #94A3B8 白底胶囊 h20 r10）；说明行（图标 14 + 「报价单号由系统按日期与序号规则自动生成，无需手动填写」11px #94A3B8）
 *        · 分隔线2
 *        · 字段「凭证名称 *」：标签行；选择框 h48 r12 #FFFFFF 描边 0.8 #E2E8F0（钥匙底 28×28 r8 #F1F5F9 + 图标 15 #64748B
 *          + 「请选择凭证」14px #CBD5E1 + chevron 20px #94A3B8）；说明行（蓝色图标 14 + 「选择凭证后，系统将自动带出该凭证下可用的模型列表」11px #64748B）
 *     3) 模型列表卡 9fabffe3 padding16 r16 #FFFFFF：标题行（竖条 + 「模型列表」15px Bold + 占位
 *        + chip「待带出」h20 r10 bg #F1F5F9 11px Medium #94A3B8）
 *        · 模型空态 h≈168 r12 bg #FAFCFF 描边 0.8 #E2E8F0 padding[28,16,28,16] 居中：空态图标 56×56 r28 #EFF6FF（图标 26px #93C5FD）
 *          + 「尚未加载模型」14px SemiBold #334155 h20 + 「请先在上方选择凭证，系统将自动带出可用模型列表」12px #94A3B8 居中
 *        · 空态底部提示（wrapper padding-top 12）：提示卡 padding[10,12,10,12] r10 bg #EFF6FF（图标 15 #2563EB
 *          + 「带出的模型数量与凭证权限相关，可在「我的设置」中管理凭证权限范围。」11px #1D4ED8）
 *     4) 填写须知卡 f4fab5a4 padding16 r16 #FFFFFF：标题行（图标 18 #64748B + 「填写须知」13px SemiBold #334155）
 *        + 三条（序号点 18×18 r9 #F1F5F9 + 「N」10px Bold #64748B + 文案 12px #64748B；条目间距 8）
 *   底部操作条 0bf8e01d padding[12,16,28,16] #FFFFFF：保存说明（图标 13 + 「保存成功后系统将自动生成报价单号」11px #94A3B8，居中）
 *     + 按钮行（padding-top 10，间距 12）：存草稿 128×48 r12 r16描边 #E2E8F0「存为草稿」14px SemiBold #64748B
 *     + 保存按钮 fill×48 r12 #2563EB（图标 20 + 「保存并继续」15px SemiBold #FFFFFF）
 *
 * 交互真源：page-26 的 interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 *   返回/帮助 = navigation(navigateBack) / client-only · 名称输入与清除 = client-only · 单号只读 = client-only
 *   凭证选择 = api(GET /credentials → 选中 GET /credentials/{id} 带出模型清单；18-API Credential Tag)
 *   存为草稿 = api(POST /quotes，A2 草稿无限暂存) · 保存并继续 = api(POST /quotes) → navigation(模型定价)
 *
 * ⚠️ 未定义/缺口（逐条写进 .agents/state/aap-feature-status.csv 序号 12-v1 备注，均不臆造）：
 *   1) 本帧无「报价主体」控件（序号 9 page-9 已有）→ 请求体只带 name + credential_id；provider_id 不发送
 *      （name / credential_id 的字段名为推断，missing-prd，沿用序号 9 同一口径）。
 *   2) 18-API 只列路径未列方法/请求体 → POST /quotes、GET /credentials/{id} 的方法与字段级 schema 为 REST 语义推断。
 *   3) 已带出模型态在本帧设计稿中不存在（本帧只有空态）→ 模型行样式与「已选 N / M」chip 复用序号 9 同族帧
 *      （page-9）设计与同一纯函数，非本帧臆造。
 *   4) 保存成功后的落点：设计按钮为「保存并继续」，步骤 2 为「设置报价 / 模型定价」→ 复用序号 11 目标路由
 *      /pages/model-pricing/index；画布另有 page-29「新增报价单-保存成功」（台账 12-v3，未实现）为备选，待拍板。
 *   5) 校验/toast 文案设计稿与 22 份 PRD 均无稿 → 占位（阈值锚定 10-PRD §5.1 V1「明细行≥1」）。
 */
import type { QuoteModelRow } from './quote-setup-model'
import { NAME_MAX, countText } from './quote-setup-model'

/** 设计稿原文（逐字取自 design.tree.json，禁止改写） */
export const PAGE_TITLE = '新增报价单'
export const PAGE_SUBTITLE = '填写基本信息并设置模型报价'
export const CARD_BASIC = '基本信息'
export const REQUIRED_HINT = '为必填项'
export const NAME_LABEL = '报价单名称'
export const NAME_PLACEHOLDER = '请输入报价单名称，如：2024Q3 主线路报价'
export const QUOTE_NO_LABEL = '报价单号'
export const QUOTE_NO_TAG = '系统生成'
export const QUOTE_NO_PLACEHOLDER = '保存后自动生成'
export const QUOTE_NO_SAMPLE = 'QT-XXXXXXXX-XXXX'
export const QUOTE_NO_HINT = '报价单号由系统按日期与序号规则自动生成，无需手动填写'
export const CRED_LABEL = '凭证名称'
export const CRED_PLACEHOLDER = '请选择凭证'
export const CRED_HINT = '选择凭证后，系统将自动带出该凭证下可用的模型列表'
export const CARD_MODELS = '模型列表'
export const MODEL_CHIP_PENDING = '待带出'
export const MODEL_EMPTY_TITLE = '尚未加载模型'
export const MODEL_EMPTY_DESC = '请先在上方选择凭证，系统将自动带出可用模型列表'
export const MODEL_EMPTY_TIP = '带出的模型数量与凭证权限相关，可在「我的设置」中管理凭证权限范围。'
export const CARD_NOTICE = '填写须知'
export const NOTICES = [
  '报价单名称建议包含季度或用途，便于后续在列表中检索。',
  '凭证决定可报价的模型范围，选择后模型列表自动刷新。',
  '首次保存成功后，系统将自动生成报价单号并进入设置报价环节。'
]
export const BAR_HINT = '保存成功后系统将自动生成报价单号'
export const BTN_DRAFT = '存为草稿'
export const BTN_SAVE = '保存并继续'
export { NAME_MAX }

/** 台账序号 11 的目标路由（步骤 2「设置报价 / 模型定价」） */
export const MODEL_PRICING_PAGE = '/pages/model-pricing/index'

/**
 * 图标行盒 = 字号 × 1.5（page-10-1-2 实测规则：设计里 remixicon 段落按 1.5 倍行高撑行，不是字号本身）。
 * 本页 page-26 需套用两处：须知标题图标 18 → 27、底栏保存说明图标 13 → 19.5。
 */
export const ICON_LINE_RATIO = 1.5

/** 文本行盒 = 字号 × 1.2（本页 design.tree.json 全部文本节点 lineHeight=1.2） */
export const TEXT_LINE_RATIO = 1.2

export function iconLineBox(fontSize: number): number {
  return fontSize * ICON_LINE_RATIO
}

export function textLineBox(fontSize: number): number {
  return fontSize * TEXT_LINE_RATIO
}

export const STEP_ACTIVE = { no: 1, title: '填写信息', desc: '名称 / 密钥 / 单号' }
export const STEP_INACTIVE = { no: 2, title: '设置报价', desc: '模型定价' }

export interface QuoteFormStep {
  no: number
  title: string
  desc: string
  active: boolean
}

/** 步骤条（设计两个步骤固定顺序；active 决定圆点/文字配色） */
export function stepsFor(active: number): QuoteFormStep[] {
  return [STEP_ACTIVE, STEP_INACTIVE].map((s) => ({ ...s, active: s.no === active }))
}

export interface QuoteFormInitialState {
  name: string
  credentialId: string
  rows: QuoteModelRow[]
}

/** 名称字数提示（真实长度；上限 30 由输入框 maxlength 保障） */
export function nameCountText(name: string): string {
  return `${(name ?? '').length}/${NAME_MAX}`
}

/**
 * 模型列表卡右上 chip：
 *   未选凭证 → 设计原文「待带出」；已选凭证 → 复用序号 9 同族帧的「已选 N / M」（page-26 无已带出态稿）
 */
export function modelChipText(credentialId: string, rows: QuoteModelRow[]): string {
  return credentialId ? countText(rows) : MODEL_CHIP_PENDING
}

/** 单号只读框：无单号时显示设计占位与示例格式（本帧为「系统生成」态） */
export function buildQuoteNoBox(quoteNo: string): { text: string; sample: string } {
  const no = String(quoteNo ?? '').trim()
  return { text: no || QUOTE_NO_PLACEHOLDER, sample: QUOTE_NO_SAMPLE }
}

/** 名称错误文案（设计稿无校验稿 → 占位，missing-prd；沿用序号 9 口径） */
export function nameError(name: string): string {
  const v = (name ?? '').trim()
  if (!v) return '请输入报价单名称'
  if (v.length > NAME_MAX) return `报价单名称最多 ${NAME_MAX} 字`
  return ''
}

/** 保存并继续：全量校验（设计两个必填标记 + 10-PRD §5.1 V1 明细行≥1；顺序固定便于逐条 toast） */
export function validateForSave(state: QuoteFormInitialState): string[] {
  const errors: string[] = []
  const msg = nameError(state.name)
  if (msg) errors.push(msg)
  if (!state.credentialId) errors.push('请选择凭证')
  if (state.rows.filter((r) => r.selected).length < 1) errors.push('请至少选择一个模型')
  return errors
}

/** 报价单主体请求体：仅设计稿确有的字段（name / credential_id 为推断字段名，missing-prd） */
export function buildFormPayload(state: QuoteFormInitialState): Record<string, unknown> {
  const body: Record<string, unknown> = {}
  const name = (state.name ?? '').trim()
  if (name) body.name = name
  if (state.credentialId) body.credential_id = state.credentialId
  return body
}
