/**
 * 序号 9【报价管理】模型报价设置（page-9）视图模型 — 纯逻辑
 *
 * 设计真源：.calicat/raw/pages/page-9/design.tree.json（430 宽 · 设计总高 1211 · 无 TabBar）
 *   顶部 3a66a8bd padding[48,16,12,16]：返回 36×36 #F1F5F9 · 标题 672c8036「新增报价单」18px Bold #0F172A
 *     · 副标题 307dd47e「填写基本信息并设置模型报价」12px #94A3B8 · 帮助 36×36 #F1F5F9（\uf045 #64748B）
 *   内容区 42124f6a padding[16,16,20,16] gap16 · 三张卡 5e64dc90/0b5dd403/ec8f4041 padding16 r16 #FFFFFF
 *     卡1 报价主体：竖条 5×16 #2563EB + 「报价主体」15px Bold + chip caf33d0e（bg #F0F0F0 · \uea13 + 「去新增」10px #189A47）
 *       选择框 d7730eba h48 r12 padding[0,14] 描边 0.8 #2563EB：钥匙底 28×28 r8 #2563EB + 公司名 13px SemiBold
 *         + 统一社会信用代码 11px #94A3B8 + chevron \uea4e 20px #2563EB；说明行 84580e5c「* 下拉选择主体公司…」11px #777777
 *     卡2 基本信息：chip 829d6574（bg #ECFDF5 · \ueb80 + 「已完善」10px #16A34A）
 *       报价单名称标签行 + 输入框 e9c27d3e h48 r12 描边 0.8 #E2E8F0（值 14px Medium + 清除 \ueb96 16px #CBD5E1）
 *         + 右对齐字数提示 b6c33423「13/30」11px #94A3B8
 *       凭证名称标签行 + 选择框 7ac50316（同卡1 样式，钥匙图标 \uee6f）+ 说明 1a873ff9「已自动带出该凭证下 5 个可用模型」11px #16A34A
 *     卡3 模型列表：chip f73af6cd「已选 3 / 5」（bg #EFF6FF · 11px SemiBold #2563EB）
 *       工具栏 6844bc87（bg #F8FAFC r10 padding[10,12]）：「全选模型」12px Medium #334155 + \ueb7d 16px #2563EB
 *         · 「按凭证实时带出」11px #94A3B8 + \uf064 12px
 *       5 行模型（padding[12,0] gap12）：勾选框 20px（选中 \ueb80 #2563EB / 未选 \ueb7d #CBD5E1）
 *         + 名称 14px SemiBold #0F172A + 厂商标（h16 r8 bg #F1F5F9 · 9px Medium #64748B）
 *         + 价格行 11px #94A3B8（模板 595d9b82「输入 $2.50 / 输出 $10.00 / 1M token」）
 *         + 状态标（h20 r10 padding[0,8]：已选 #ECFDF5/#16A34A · 可选 #F1F5F9/#94A3B8）10px SemiBold + chevron \uea6e 18px #CBD5E1
 *       底部说明 0e98f68a「价格均以 $/1M token 计价，勾选后可在下一步设置单价」11px #94A3B8（居中）
 *     卡4 联动提示卡 6e6629c0（bg #EFF6FF r14 padding[12,14] gap8）：\ueeb8 16px #2563EB + 提示 11px #1D4ED8
 *   底部操作条 c0413210 padding[12,16,28,16] #FFFFFF：存为草稿 128×48 r12 描边 #E2E8F0「存为草稿」#64748B
 *     + 保存按钮 fill h48 r12 #2563EB（\uf0b1 + 「保存」15px SemiBold #FFFFFF）
 *
 * 业务真源
 *   10-报价与合同结算PRD §3.2 QuoteItem：model_name 为写入 billing_expr 的 key；单价为真实 $/1M tokens
 *   §4.1 状态机：DRAFT 可编辑/暂存/提交；§5.1 V1「明细行≥1」属**提交时**校验
 *   A2「草稿无限暂存 + 提交全量校验」→ 存为草稿不做必填拦截，保存做全量校验
 *   15-数据字典 aap_quote（provider_id/currency…) · aap_quote_item（唯一 (quote_id, model_name)）
 *   17-spec 名词表：凭证 = base_url + api_key + model_list（模型清单随凭证带出）
 *
 * ⚠️ 未定义/缺口（写进 .agents/state/aap-feature-status.csv 序号 9 备注，均不臆造）：
 *   1) 「报价单名称」在 10-PRD §3.1 Quote 与 15-数据字典 aap_quote **均无对应列**（与序号 8 卡片标题同一缺口）
 *      → 提交体用 `name`（推断字段名，missing-prd），不拿 quote_no 冒充。
 *   2) 18-API 卡片只列路径未列方法/请求体 → POST /quotes 的方法与字段级 schema 为 REST 语义推断。
 *   3) 主体公司来源：18-API 无「我的公司」列表接口，唯一可依的是 /provider/profile（15-数据字典 aap_provider
 *      company_name / unified_social_credit_code）→ 设计稿的「下拉」退化为单主体；「去新增」跳档案编辑页。
 *   4) 凭证与报价单的关联字段未在 aap_quote 定义 → `credential_id` 为推断（missing-prd）。
 *   5) 模型行的参考价（设计「输入 $2.50 / 输出 $10.00 / 1M token」）无接口依据 → 消费凭证模型清单里的
 *      input_price/output_price，缺失时**不渲染价格行**（不编造价格）。
 *   6) 设计稿字数提示「13/30」与示例值实际长度 12 不符（设计内部不自洽）→ 按真实长度计数并实现 30 上限。
 */

/** 设计稿原文（逐字取自 design.tree.json，禁止改写） */
export const PAGE_TITLE = '新增报价单'
export const PAGE_SUBTITLE = '填写基本信息并设置模型报价'
export const CARD_SUBJECT = '报价主体'
export const CHIP_GO_ADD = '去新增'
export const SUBJECT_HINT = '下拉选择主体公司，可在我的公司中新增'
export const CARD_BASIC = '基本信息'
export const CHIP_DONE = '已完善'
export const NAME_LABEL = '报价单名称'
export const CRED_LABEL = '凭证名称'
export const CARD_MODELS = '模型列表'
export const SELECT_ALL_TEXT = '全选模型'
export const SOURCE_HINT = '按凭证实时带出'
export const MODEL_STATUS_SELECTED = '已选'
export const MODEL_STATUS_OPTIONAL = '可选'
export const MODEL_LIST_NOTE = '价格均以 $/1M token 计价，勾选后可在下一步设置单价'
export const TIP_TEXT = '模型列表随凭证变化自动刷新，切换凭证将重置当前勾选状态，\n请确认后再保存。'
export const BTN_DRAFT = '存为草稿'
export const BTN_SAVE = '保存'
/** 凭证未选时的占位（设计稿是已选态，无占位稿 → 占位文案，记 missing-prd） */
export const CRED_PLACEHOLDER = '请选择凭证'
/** 主体公司未选时的占位（同上） */
export const SUBJECT_PLACEHOLDER = '请选择主体公司'
/** 设计稿 chip 文案「去新增」，语义为跳转我的公司/档案编辑 */
export const PROFILE_EDIT_PAGE = '/pages/profile-edit/index'
/** 台账序号 11 的目标路由：保存后进入「模型定价-详情」设置单价（设计原文「在下一步设置单价」） */
export const MODEL_PRICING_PAGE = '/pages/model-pricing/index'

/** 报价单名称上限（设计稿字数提示 30） */
export const NAME_MAX = 30
export const COUNT_TEMPLATE = (n: number, m: number) => `已选 ${n} / ${m}`
export const COUNT_TEMPLATE_ZERO = COUNT_TEMPLATE(0, 0)
export const NAME_COUNT_TEMPLATE = (len: number) => `${len}/${NAME_MAX}`

/** 服务端返回的凭证模型清单条目（字段名取 15-数据字典 model_list；价格字段为 missing-prd 推断） */
export interface ModelRaw {
  model_name?: string
  name?: string
  vendor?: string
  input_price?: number | string
  output_price?: number | string
  selected?: boolean
}

export interface QuoteModelRow {
  /** 稳定 key（重复 model_name 时加序号，保证 v-for 与勾选稳定） */
  key: string
  name: string
  vendor: string
  /** 价格行文案；价格缺失时为空串（页面不渲染该行） */
  priceText: string
  selected: boolean
}

export interface QuoteFormState {
  name: string
  providerId: string
  credentialId: string
  rows: QuoteModelRow[]
}

/** 价格格式化：真实单价 $/1M tokens，保留两位（设计稿样本均为两位） */
export function formatPrice(value: number | string | undefined): string {
  if (value === undefined || value === null || value === '') return ''
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n)) return ''
  return n.toFixed(2)
}

export function priceText(input: number | string | undefined, output: number | string | undefined): string {
  const i = formatPrice(input)
  const o = formatPrice(output)
  if (!i || !o) return ''
  return `输入 $${i} / 输出 $${o} / 1M token`
}

export function buildModelRows(raw: ModelRaw[] | undefined): QuoteModelRow[] {
  if (!Array.isArray(raw)) return []
  const seen = new Map<string, number>()
  const rows: QuoteModelRow[] = []
  for (const item of raw) {
    const name = String(item?.model_name ?? item?.name ?? '').trim()
    if (!name) continue
    const n = (seen.get(name) ?? 0) + 1
    seen.set(name, n)
    rows.push({
      key: n === 1 ? name : `${name}#${n}`,
      name,
      vendor: String(item?.vendor ?? '').trim(),
      priceText: priceText(item?.input_price, item?.output_price),
      selected: item?.selected === true
    })
  }
  return rows
}

export function toggleModel(rows: QuoteModelRow[], key: string): QuoteModelRow[] {
  return rows.map((r) => (r.key === key ? { ...r, selected: !r.selected } : r))
}

export function setAllSelected(rows: QuoteModelRow[], selected: boolean): QuoteModelRow[] {
  return rows.map((r) => ({ ...r, selected }))
}

export function allSelected(rows: QuoteModelRow[]): boolean {
  return rows.length > 0 && rows.every((r) => r.selected)
}

export function selectedCount(rows: QuoteModelRow[]): number {
  return rows.filter((r) => r.selected).length
}

export function countText(rows: QuoteModelRow[]): string {
  return COUNT_TEMPLATE(selectedCount(rows), rows.length)
}

export function selectedNames(rows: QuoteModelRow[]): string[] {
  return rows.filter((r) => r.selected).map((r) => r.name)
}

export function credentialHintText(modelCount: number): string {
  return `已自动带出该凭证下 ${modelCount} 个可用模型`
}

/** 名称字数提示（真实长度；设计稿「13/30」与示例值 12 字不符，按真实计数实现） */
export function nameCountText(name: string): string {
  return NAME_COUNT_TEMPLATE((name ?? '').length)
}

/** 名称错误文案（设计稿无校验稿 → 占位文案，已记 missing-prd） */
export function nameError(name: string): string {
  const v = (name ?? '').trim()
  if (!v) return '请输入报价单名称'
  if (v.length > NAME_MAX) return `报价单名称最多 ${NAME_MAX} 字`
  return ''
}

/** 保存：全量校验（10-PRD §5.1 V1 明细行≥1；顺序固定，便于页面逐条 toast） */
export function validateForSave(state: QuoteFormState): string[] {
  const errors: string[] = []
  const nameMsg = nameError(state.name)
  if (nameMsg) errors.push(nameMsg)
  if (!state.providerId) errors.push('请选择报价主体')
  if (!state.credentialId) errors.push('请选择凭证')
  if (selectedCount(state.rows) < 1) errors.push('请至少选择一个模型')
  return errors
}

/** 存为草稿：A2「草稿无限暂存」→ 不做必填拦截 */
export function validateForDraft(_state: QuoteFormState): string[] {
  return []
}

/** 报价单主体请求体（键依据 15-数据字典 aap_quote；name 为推断字段，missing-prd） */
export function buildQuotePayload(state: QuoteFormState): Record<string, unknown> {
  const body: Record<string, unknown> = {}
  const name = (state.name ?? '').trim()
  if (name) body.name = name
  if (state.providerId) body.provider_id = state.providerId
  if (state.credentialId) body.credential_id = state.credentialId
  return body
}

/** 明细行请求体：本页只带 model_name（单价在下一步设置；V3 属提交时校验） */
export function buildItemsPayload(rows: QuoteModelRow[]): { items: Array<{ model_name: string }> } {
  return { items: rows.filter((r) => r.selected).map((r) => ({ model_name: r.name })) }
}
