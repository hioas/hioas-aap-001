/**
 * 序号 12-v3【报价管理】新增报价单-保存成功（page-29）视图模型 — 纯逻辑
 *
 * 设计真源：.calicat/raw/pages/page-29/design.tree.json（430 宽 · 设计帧 430x1018 · 无 TabBar）
 *   顶部导航 86e36607 padding[48,16,12,16] #FFFFFF：返回 36×36 r18 #F1F5F9 · 标题块 108 宽
 *     （「报价单已创建」18px Bold #0F172A h24 / 「报价单号已自动生成」12px #94A3B8 h18）· 关闭 36×36 r18 #F1F5F9
 *   内容区 3b174f33 padding[16,16,20,16] gap16，四块：
 *     1) 成功头部卡 f5d8ac7d padding[28,16,28,16] r16 #FFFFFF（居中）：
 *        成功图标 64×64 r32 #ECFDF5（remixicon 38px #16A34A）
 *        · 标题容器 padding-top 14：「报价单创建成功」18px Bold #0F172A h24
 *        · 「已保存基本信息并带出模型清单」12px #94A3B8 h18
 *        · 单号容器 padding-top 18：单号展示条 padding[12,14,12,14] r12 bg #F8FAFC 描边 0.8 #BFDBFE
 *          （单号信息 155 宽：「报价单号」11px Medium #94A3B8 h15 + 「QT-20240615-0007」17px Bold #2563EB h23；
 *           复制按钮 h32 r10 bg #EFF6FF padding[0,12,0,12] gap4：图标 14px + 「复制」12px SemiBold #2563EB）
 *     2) 结果摘要卡 7ce5a3a9 padding16 r16 #FFFFFF：标题行（竖条 5×16 r2 #2563EB + 「结果摘要」15px Bold h20）
 *        · 行容器 padding-top 14 → 摘要行-名称 padding[10,0,10,0]（「报价单名称」13px #94A3B8 / 值 13px SemiBold #0F172A）
 *        · 摘要行-密钥 padding[10,0,10,0]（右：环境小标 h18 r9 bg #EFF6FF 10px SemiBold #2563EB + 脱敏 key 13px SemiBold）
 *        · 摘要行-模型数 padding[10,0,10,0]（右：模型数标 h18 r9 bg #ECFDF5 10px SemiBold #16A34A）
 *        · 摘要行-单号 padding[10,0,10,0]（右：绿勾 13px #16A34A + 单号 13px SemiBold #2563EB）
 *        · 摘要行-状态 padding[10,0,0,0]（右：状态标 h20 r10 bg #F1F5F9：点 7×6 #94A3B8 + 「草稿」11px SemiBold #64748B）
 *     3) 带出模型卡 cec63018 padding16 r16 #FFFFFF：标题行（图标 16px #2563EB + 「已带出模型」14px SemiBold
 *        + 占位 + 「共 5 个 / 勾选 3 个」11px #94A3B8）
 *        · 标签组（padding-top 12，gap8）：勾选标签 h28 r14 bg #EFF6FF 12px SemiBold #2563EB
 *        · 标签组2（padding-top 8，gap8）：未勾选标签 h28 r14 bg #F8FAFC 描边 0.8 #F1F5F9 12px Medium #94A3B8
 *     4) 下一步提示卡 0282549e padding[12,14,12,14] gap8 r14 bg #EFF6FF：图标 16px #2563EB + 文案 11px #1D4ED8
 *   底部操作条 a17976f7 padding[12,16,28,16] #FFFFFF：主按钮 fill×48 r12 #2563EB（图标 18px + 「继续设置模型报价」15px SemiBold #FFFFFF）
 *     · 次按钮容器 padding-top 10：次按钮 fill×48 r12 #FFFFFF 描边 0.8 #E2E8F0（「返回报价单列表」14px SemiBold #64748B）
 *
 * 交互真源：page-29 的 interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 *   取数 = api(GET /quotes/{quoteId} 详情；GET /credentials/{id} 凭证 model_list) · 复制 = client-only(uni.setClipboardData)
 *   返回 = navigation(navigateBack) · 关闭 / 返回报价单列表 = navigation(reLaunch 报价单列表) ·
 *   继续设置模型报价 = navigation(navigateTo /pages/model-pricing/index?quoteId=，复用序号 11 目标路由)
 *
 * ⚠️ 未定义/缺口（逐条写进 .agents/state/aap-feature-status.csv 序号 12-v3 备注，均不臆造）：
 *   1) 18-API 卡片只列路径未列方法与字段级 schema → GET /quotes/{quoteId}、GET /credentials/{id} 的方法为
 *      REST 语义推断；报价单名称（name/title/quote_name）、credential_alias、api_key_mask 等字段名为容错读取（missing-prd）。
 *   2) 「共 M 个 / 勾选 N 个」的两个数字来源未定义 → M 取凭证 model_list 长度（或报价单明细行数），
 *      N 取报价单明细行数（无明细行时回退凭证 model_list 的 selected 标记）。
 *   3) 环境小标「生产环境」与 page-apikey 的「沙箱 / 专用」同族，22 份 PRD **零命中** →
 *      消费服务端 env_tag，缺字段不渲染（不猜环境）。
 *   4) 脱敏 key 原样展示服务端值（api_key_mask / 17-spec 的 api_key_masked），不做本地二次脱敏。
 *   5) 「关闭」与「返回报价单列表」同落 /pages/quotes/index（reLaunch 清栈，避免回到已提交的表单页）；
 *      设计无交互数据 → 目标为推断（台账待拍板）。
 *   6) 复制成功后的 toast 文案设计稿与 22 份 PRD 均无稿 → 占位（missing-prd）。
 *   7) 本页的入口（谁跳过来）尚未接线：序号 12-v1/12-v2 的「保存并继续」现仍直接跳模型定价页 →
 *      待人类拍板后再改已验收页面，本轮只实现本页（不静默解决，见台账序号 12-v3 备注①）。
 */
import { PLACEHOLDER } from './format'
import { NEUTRAL_META, STATUS_META, statusKeyOf, type QuoteChipKey } from './quotes-model'

/* ---------- 设计文案（逐字抄自 design.tree.json） ---------- */

export const PAGE_TITLE = '报价单已创建'
export const PAGE_SUBTITLE = '报价单号已自动生成'
export const SUCCESS_TITLE = '报价单创建成功'
export const SUCCESS_DESC = '已保存基本信息并带出模型清单'
export const QUOTE_NO_LABEL = '报价单号'
export const COPY_TEXT = '复制'
export const SUMMARY_TITLE = '结果摘要'
export const ROW_NAME = '报价单名称'
export const ROW_CRED = '凭证名称'
export const ROW_MODELS = '参与报价模型'
export const ROW_STATUS = '当前状态'
export const CARD_MODELS = '已带出模型'
export const TIP_TEXT = '下一步可为勾选模型设置输入/输出单价，设置完成即可提交审核。'
export const BTN_PRIMARY = '继续设置模型报价'
export const BTN_SECONDARY = '返回报价单列表'

/* ---------- 路由与页面入参（键名与既有页面一致） ---------- */

export const QUOTE_ID_KEY = 'aap_quote_id'
export const CREDENTIAL_ID_KEY = 'aap_credential_id'
export const MODEL_PRICING_PAGE = '/pages/model-pricing/index'
export const QUOTES_LIST_PAGE = '/pages/quotes/index'

/** toast 占位（设计稿与 22 份 PRD 均无稿 → missing-prd 6） */
export const TOAST_COPIED = '报价单号已复制'
export const TOAST_NO_QUOTE_NO = '暂无可复制的报价单号'
export const TOAST_FAIL = '加载失败，请稍后重试'

/* ---------- 类型 ---------- */

/** 凭证 model_list 单项（沿用序号 9/12 的字段名，字段级 schema missing-prd） */
export interface SuccessModelRaw {
  model_name?: string
  name?: string
  selected?: boolean
  [key: string]: unknown
}

/** 报价单详情响应（18-API /quotes/{quoteId}；字段名容错读取，missing-prd） */
export interface QuoteSuccessRaw {
  quote_id?: string
  quoteId?: string
  id?: string
  quote_no?: string
  quote_no_text?: string
  status?: string
  name?: string
  title?: string
  quote_name?: string
  credential_id?: string
  credentialId?: string
  credential_alias?: string
  credential_name?: string
  api_key_mask?: string
  api_key_masked?: string
  items?: Array<{ model_name?: string; modelName?: string; name?: string }> | null
  [key: string]: unknown
}

/** 凭证详情响应（18-API /credentials/{id}） */
export interface CredentialSuccessRaw {
  id?: string
  alias?: string
  name?: string
  api_key_mask?: string
  api_key_masked?: string
  env_tag?: string
  model_list?: SuccessModelRaw[] | null
  [key: string]: unknown
}

export interface SuccessModelTag {
  key: string
  name: string
  selected: boolean
}

export interface SuccessStatus {
  key: QuoteChipKey | 'void' | 'unknown'
  label: string
  bg: string
  dot: string
  text: string
}

export interface QuoteSuccessView {
  quoteNo: string
  hasQuoteNo: boolean
  quoteName: string
  credAlias: string
  credMask: string
  /** 环境小标（服务端 env_tag；缺失为空串 → 页面不渲染） */
  credEnvTag: string
  /** 报价单里的模型（按 items 长度；无 items 时按凭证 selected 数） */
  selectedCount: number
  selectedCountText: string
  modelTotalText: string
  status: SuccessStatus
  models: SuccessModelTag[]
}

/* ---------- 纯函数 ---------- */

function str(v: unknown): string {
  return typeof v === 'string' ? v.trim() : v === undefined || v === null ? '' : String(v).trim()
}

/** 「已勾选 N 个」（设计原文格式） */
export function selectedCountText(count: number): string {
  return `已勾选 ${Math.max(0, Math.floor(count || 0))} 个`
}

/** 「共 M 个 / 勾选 N 个」（设计原文格式） */
export function modelTotalText(total: number, selected: number): string {
  return `共 ${Math.max(0, Math.floor(total || 0))} 个 / 勾选 ${Math.max(0, Math.floor(selected || 0))} 个`
}

/** 报价单明细行的模型名（去空；用于判定勾选态） */
export function itemNames(items?: QuoteSuccessRaw['items']): string[] {
  if (!Array.isArray(items)) return []
  return items.map((it) => str(it?.model_name ?? it?.modelName ?? it?.name)).filter((n) => !!n)
}

/**
 * 已带出模型标签：
 *   - 勾选态优先由报价单明细行（items）判定；items 为空时回退凭证 model_list 的 selected 标记；
 *   - 顺序沿用凭证 model_list（= 系统带出顺序），明细行里多出来的模型追加到末尾（不丢数据）；
 *   - 同名只保留一个（key 去重）、无名项丢弃、非数组返回空。
 */
export function buildModelTags(all?: SuccessModelRaw[] | null, items?: string[]): SuccessModelTag[] {
  const names = Array.isArray(items) ? items.filter((n) => !!n) : []
  const useItems = names.length > 0
  const picked = useItems ? new Set(names) : null
  const tags: SuccessModelTag[] = []
  const seen = new Set<string>()

  if (Array.isArray(all)) {
    for (const raw of all) {
      const name = str(raw?.model_name ?? raw?.name)
      if (!name || seen.has(name)) continue
      seen.add(name)
      tags.push({ key: name, name, selected: picked ? picked.has(name) : raw?.selected === true })
    }
  }

  if (picked) {
    for (const name of names) {
      if (seen.has(name)) continue
      seen.add(name)
      tags.push({ key: name, name, selected: true })
    }
  }
  return tags
}

/** 服务端 QuoteStatus → 设计稿 5 态胶囊（复用序号 8）；未映射的原样直显中性灰 */
export function resolveStatus(raw?: string | null): SuccessStatus {
  const key = statusKeyOf(raw)
  if (key && key !== 'void') {
    const meta = STATUS_META[key]
    return { key, label: meta.label, bg: meta.bg, dot: meta.dot, text: meta.text }
  }
  const value = str(raw)
  if (!value) {
    // 服务端未给状态：新建报价单初始为 DRAFT（10-PRD §4.1）
    const meta = STATUS_META.draft
    return { key: 'draft', label: meta.label, bg: meta.bg, dot: meta.dot, text: meta.text }
  }
  if (key === 'void') {
    const meta = NEUTRAL_META
    return { key, label: '作废', bg: meta.bg, dot: meta.dot, text: meta.text }
  }
  return { key: 'unknown', label: value, bg: NEUTRAL_META.bg, dot: NEUTRAL_META.dot, text: NEUTRAL_META.text }
}

export interface BuildSuccessInput {
  quote?: QuoteSuccessRaw | null
  credential?: CredentialSuccessRaw | null
  /** query/storage 里的凭证 id（报价单响应未带 credential_id 时使用） */
  fallbackCredentialId?: string
}

/** 取数 → 页面视图模型（缺数据显示占位「—」，绝不照抄设计样例值） */
export function buildSuccessView(input: BuildSuccessInput): QuoteSuccessView {
  const quote = input.quote ?? null
  const cred = input.credential ?? null

  const quoteNo = str(quote?.quote_no ?? quote?.quote_no_text)
  const quoteName = str(quote?.name ?? quote?.title ?? quote?.quote_name) || PLACEHOLDER

  const credAlias =
    str(cred?.alias ?? cred?.name ?? quote?.credential_alias ?? quote?.credential_name) || PLACEHOLDER
  const credMask = str(cred?.api_key_mask ?? cred?.api_key_masked ?? quote?.api_key_mask ?? quote?.api_key_masked)
  const credEnvTag = str(cred?.env_tag)

  const models = buildModelTags(cred?.model_list, itemNames(quote?.items))
  const fallbackNames = itemNames(quote?.items)
  const selectedCount = models.length
    ? models.filter((m) => m.selected).length
    : fallbackNames.length
  const total = models.length || fallbackNames.length

  return {
    quoteNo,
    hasQuoteNo: !!quoteNo,
    quoteName,
    credAlias,
    credMask,
    credEnvTag,
    selectedCount,
    selectedCountText: selectedCountText(selectedCount),
    modelTotalText: modelTotalText(total, selectedCount),
    status: resolveStatus(quote?.status),
    models
  }
}

/** 凭证 id 解析：报价单响应优先，其次 query/storage */
export function resolveCredentialId(quote?: QuoteSuccessRaw | null, fallback?: string): string {
  return str(quote?.credential_id ?? quote?.credentialId) || str(fallback)
}
