/**
 * 「提交接入凭证」页面视图模型 — 序号 4（page-4-2）纯逻辑
 *
 * 设计真源：.calicat/raw/pages/page-4-2/design.tree.json
 * 字段依据：15-数据模型ER与数据字典.md「aap_credential」
 *   alias / base_url / api_key_mask / primary_flag / model_list / declared_vendor /
 *   declared_rpm / declared_context_window
 *   ⚠️ 字段级 schema 未在 18-API 卡片定义（该卡为接口结构摘要，完整 openapi.yaml 不在本仓库）
 *      → 已记台账 missing-prd；此处字段名一律取数据字典，不臆造。
 * 业务规则：17-spec R-04（base_url 去尾斜杠保留 /v1）；SSRF（R-07/E-1201）由服务端判定，
 *   前端只做协议与主机的形态校验（E-1001 家族）。
 */

/** 设计稿原文：凭证名称下方的建议提示（设计 id=cb6464de，非硬校验） */
export const ALIAS_HINT = '建议 6–24 字'
/** 设计稿原文：BaseURL 卡片安全提示（设计 id=263e0794） */
export const ANCHOR_NOTE = '凭证仅用于平台检测与转发调用，全程加密存储，不会对外泄露。'
/** 设计稿原文：APIKey 卡片提示（设计 id=db669f42） */
export const APIKEY_HINT = '如已轮换密钥，请在此更新后重新检测'
/** 设计稿原文：模型清单说明行（设计 id=5d8ad627） */
export const MODEL_SECTION_NOTE = '按厂商勾选，自动生成本次接入检测清单'
/** 设计稿原文：模型清单底部提示（设计 id=05ed9600，2 个厂商时逐字一致） */
export const CATALOG_MORE_TEXT = '仅展示 2 个厂商，查看更多厂商 ›'
/** 设计稿原文：已配置标签（设计 id=157197ab） */
export const CONFIGURED_LABEL = '已配置'

/** 「加载模型列表」按钮文案（**用户口径 2026-09-23**，设计稿无此按钮）。
 *  行为：调凭证 → 后端真打 {base_url}/models → 拉取渠道模型清单。
 *  等价 new-api 渠道编辑页的「获取模型列表」。 */
export const LOAD_MODELS_LABEL = '加载模型列表'

/** 「保存」按钮文案。**用户口径 2026-09-23 改名**：原「保存草稿」→「保存」。
 *  （设计稿原文为「保存草稿」，用户已覆盖。） */
export const SAVE_LABEL = '保存'

/** 「提交」按钮文案。**用户口径 2026-09-23 改名**：原「提交检测」→「提交」。
 *  （设计稿原文为「提交检测」，用户已覆盖。） */
export const SUBMIT_LABEL = '提交'

/** 建议区间（设计稿为「建议」而非校验规则：PRD 未定义 alias 长度约束） */
const ALIAS_MIN = 6
const ALIAS_MAX = 24

export interface ModelEntryRaw {
  model_name?: string
  model_id?: string
  context_window?: number
  rpm?: number
}

export interface VendorGroupRaw {
  vendor?: string
  models?: ModelEntryRaw[]
}

export interface CredentialDetailRaw {
  id?: string
  alias?: string
  base_url?: string
  api_key_mask?: string
  primary_flag?: boolean
  declared_vendor?: string
  declared_rpm?: number
  declared_context_window?: number
  model_list?: ModelEntryRaw[]
  /**
   * 可选模型目录（厂商分组）。
   * ⚠️ 18-API 卡片未定义该字段与供应商侧目录接口 → 记 missing-prd；
   *    缺失时退化为「declared_vendor + model_list」单分组，不伪造模型。
   */
  model_catalog?: VendorGroupRaw[]
}

export interface ModelOption {
  key: string
  name: string
  specText: string
  checked: boolean
}

export interface VendorGroup {
  vendor: string
  models: ModelOption[]
}

export interface CredentialFormModel {
  alias: string
  baseUrl: string
  apiKeyMask: string
  isPrimary: boolean
  vendors: VendorGroup[]
  selectedCount: number
  /** 「已选 N 个」（设计 id=599103a2） */
  selectedCountText: string
  /** 底部提示按实际厂商数生成；无目录时不展示（见 hasCatalog） */
  catalogMoreText: string
  hasCatalog: boolean
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function num(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

/** 规格文案「128K · 500 RPM」：上下文按千位；缺项不编造 */
export function formatModelSpec(contextWindow?: number, rpm?: number): string {
  const parts: string[] = []
  const ctx = num(contextWindow)
  if (ctx !== undefined) {
    if (ctx >= 1000) {
      const k = Math.round((ctx / 1000) * 10) / 10
      parts.push(`${k}K`)
    } else {
      parts.push(`${ctx}K`)
    }
  }
  const r = num(rpm)
  if (r !== undefined) parts.push(`${r} RPM`)
  return parts.join(' · ')
}

function optionOf(raw: ModelEntryRaw, vendor: string, checkedNames: Set<string>): ModelOption | null {
  const name = text(raw?.model_name) || text(raw?.model_id)
  if (!name) return null
  return {
    key: `${vendor}::${name}`,
    name,
    specText: formatModelSpec(raw?.context_window, raw?.rpm),
    checked: checkedNames.has(name)
  }
}

/**
 * 由**凭证详情**构造模型清单候选。
 *
 * ⚠️ 保留 `model_catalog` 分支的理由（我一度删掉它，被既有测试拦下）：
 *    它是**凭证详情上的**字段，不是管理端那个 `/catalog/models` 目录 API
 *    —— 用户否定的只是后者（「不是管理端提供的模型列表」）。
 *    后端目前不产出该字段（credential 包内实测 0 处），故实际走 `model_list` 分支；
 *    但既有用例编码了「详情带目录时按厂商分组」的行为，属既定契约，不擅自改。
 */
function buildVendors(raw: CredentialDetailRaw | null | undefined): VendorGroup[] {
  const list = Array.isArray(raw?.model_list) ? raw!.model_list! : []
  const checkedNames = new Set(list.map((m) => text(m?.model_name) || text(m?.model_id)).filter(Boolean))

  const catalog = Array.isArray(raw?.model_catalog) ? raw!.model_catalog! : []
  if (catalog.length > 0) {
    return catalog
      .map((group) => {
        const vendor = text(group?.vendor)
        const models = (Array.isArray(group?.models) ? group!.models! : [])
          .map((m) => optionOf(m, vendor, checkedNames))
          .filter((m): m is ModelOption => m !== null)
        return { vendor, models }
      })
      .filter((g) => g.models.length > 0)
  }

  // 无目录：按 declared_vendor 单分组展示已选模型（不伪造候选模型）
  if (list.length === 0) return []
  const vendor = text(raw?.declared_vendor)
  const models = list
    .map((m) => optionOf(m, vendor, checkedNames))
    .filter((m): m is ModelOption => m !== null)
  return models.length > 0 ? [{ vendor, models }] : []
}

export function countSelected(vendors: VendorGroup[]): number {
  return vendors.reduce((sum, g) => sum + g.models.filter((m) => m.checked).length, 0)
}


/**
 * 用**渠道拉取的模型清单**构造可勾选候选。
 *
 * 用户口径（2026-09-23）：「用户填入 url 和 apikey 后…加载按钮…调用凭证，拉取模型清单」。
 * 真源 = `POST /credentials/{id}/precheck` 返回的 `models`
 *        （后端 upstreamProbe **真打** {base_url}/models，等价 new-api 的「获取模型列表」）。
 *
 * ⚠️ 与已删除的 `buildVendorsFromCatalog` 的区别：那份来自**管理端维护的目录**，
 *    已被用户明确否定（「不是管理端提供的模型列表」）。本份来自**凭证自己的渠道**。
 *
 * 拉回来的模型默认**全部勾选**（与 new-api 一致：拉到的即可用）。
 * 渠道清单是扁平的名字列表、不含厂商分组信息，故按单分组展示（不臆造厂商）。
 */
export function buildVendorsFromChannel(models: string[], vendorLabel = '渠道模型'): VendorGroup[] {
  const seen = new Set<string>()
  const list: string[] = []
  for (const raw of models ?? []) {
    const name = String(raw ?? '').trim()
    if (!name || seen.has(name)) continue
    seen.add(name)
    list.push(name)
  }
  if (list.length === 0) return []
  return [
    {
      vendor: vendorLabel,
      models: list.map((name) => ({
        key: `${vendorLabel}::${name}`,
        name,
        specText: '',
        checked: true
      }))
    }
  ]
}

export function buildCredentialForm(raw?: CredentialDetailRaw | null): CredentialFormModel {
  const vendors = buildVendors(raw)
  const selectedCount = countSelected(vendors)
  const hasCatalog = Array.isArray(raw?.model_catalog) && raw!.model_catalog!.length > 0
  return {
    alias: text(raw?.alias),
    baseUrl: text(raw?.base_url),
    apiKeyMask: text(raw?.api_key_mask),
    isPrimary: raw?.primary_flag === true,
    vendors,
    selectedCount,
    selectedCountText: `已选 ${selectedCount} 个`,
    catalogMoreText: `仅展示 ${vendors.length} 个厂商，查看更多厂商 ›`,
    hasCatalog
  }
}

/** 勾选/取消（返回新数组，不改原引用） */
export function toggleModel(vendors: VendorGroup[], key: string): VendorGroup[] {
  return vendors.map((group) => ({
    vendor: group.vendor,
    models: group.models.map((m) => (m.key === key ? { ...m, checked: !m.checked } : { ...m }))
  }))
}

/** R-04：去首尾空白 + 去尾斜杠（保留 /v1 这类路径段） */
export function normalizeBaseUrl(url?: string): string {
  const trimmed = text(url).trim()
  if (!trimmed) return ''
  return trimmed.replace(/\/+$/, '')
}

/** 前端形态校验：仅协议与主机；SSRF 内网/环回拒绝由服务端 E-1201 判定 */
export function validateBaseUrl(url?: string): string | null {
  const value = text(url).trim()
  if (!value) return '请输入 BaseURL'
  if (!/^https?:\/\//i.test(value)) return 'BaseURL 需以 http:// 或 https:// 开头'
  const rest = value.replace(/^https?:\/\//i, '')
  if (!rest || rest.startsWith('/')) return '请输入完整的 BaseURL'
  return null
}

export function isAliasInSuggestedRange(alias?: string): boolean {
  const len = [...text(alias).trim()].length
  return len >= ALIAS_MIN && len <= ALIAS_MAX
}

export interface SavePayloadInput {
  alias: string
  baseUrl: string
  apiKey?: string
  vendors: VendorGroup[]
}

export interface CredentialSavePayload {
  alias: string
  base_url: string
  /**
   * 模型清单。
   *
   * ⚠️ 缺陷 11（2026-09-19 H5 联调 + curl 实测确证）：**必须是对象数组**，不是字符串数组。
   * 契约 `docs/backend/json-schema/requests/credential-create.schema.json` 里
   * `model_list.items` 是 `$ref: model-entry.schema.json`；后端入参是
   * `List<Map<String,Object>>`（`CredentialController.CredentialRequest`）。
   *
   * 此前这里写的是 `string[]`，实测：
   *   `[{"model_name":"gpt-4o"}]` → `code=0` ✓
   *   `["gpt-4o"]`               → `E-1001 请求体不是合法 JSON 或字段类型不匹配` ✗
   * 即**供应商只要勾选任何一个模型，保存凭证就会失败**。此前没暴露是因为缺陷 10
   * （前端丢弃预检返回的 models）让它恒为空数组 `[]`，而空数组能通过反序列化。
   */
  model_list: ModelEntryRaw[]
  api_key?: string
}

/** 保存请求体：未改密钥则不携带 api_key（不臆造字段） */
export function buildSavePayload(input: SavePayloadInput): CredentialSavePayload {
  const names: string[] = []
  for (const group of input.vendors) {
    for (const m of group.models) {
      if (m.checked && !names.includes(m.name)) names.push(m.name)
    }
  }
  const payload: CredentialSavePayload = {
    alias: text(input.alias).trim(),
    base_url: normalizeBaseUrl(input.baseUrl),
    // 发对象数组（缺陷 11）；后端按 model-entry 解析
    model_list: names.map((name) => ({ model_name: name }))
  }
  const key = text(input.apiKey).trim()
  if (key) payload.api_key = key
  return payload
}
