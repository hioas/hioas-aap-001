/**
 * 序号 10【档案与凭证】供应商档案编辑（page-10-2 / 编辑主体档案）— 视图模型 / 校验 / 提交体
 *
 * 文案真源：.calicat/raw/pages/page-10-2/design.tree.json（430 宽 · 设计总高 1409 · 无 TabBar）
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Provider」→ /provider/profile、/provider/qualifications、
 *          /provider/qualifications/{id}（前缀 /api/v1）。
 *          ⚠️ 该卡片**只列路径未列方法** → GET/PUT/POST/DELETE 为 REST 语义推断（与序号 3/4/8/9 同一缺口）。
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md `aap_provider`
 *          （provider_no / account_id / short_code / company_name / unified_social_credit_code /
 *            industry_category(ORIGINAL|RESELLER|AGGREGATOR) / contact_name / contact_phone_cipher|mask /
 *            contact_email / status / recheck_interval_days …）
 *          + 17-spec §3 Provider（qualification_files）
 * 校验真源：17-spec §R R-01 手机号 `^1[3-9]\d{9}$`；统一社会信用代码 GB 32100-2015 未定义 → 只校验 18 位字母数字。
 *
 * ⚠️ 记入台账（.agents/state/aap-feature-status.csv 序号 10）的缺口，一律**不臆造**：
 *   1) 「所在地区（省/市）」「详细地址」「官网」「职务」「公司简介」「完整度」在 22 份 PRD 与数据字典**零命中** →
 *      前端按 province / city / address / website / contact_title / company_intro / completeness 消费，
 *      **字段名与归属均为推断**，已标 missing-prd。
 *   2) 「供应商类型」三项映射 industry_category：原厂→ORIGINAL、渠道商→RESELLER、中转商→AGGREGATOR（顺序对应为推断）。
 *   3) 各输入框占位文案（除「官网」外）设计稿为已填态、无占位 → 占位文案为推断；「官网」占位为设计原文。
 *   4) 校验错误文案 / toast 文案设计稿与 PRD 均无 → 占位（与序号 4/8/9 同一处理）。
 *   5) 「保存草稿」在 PRD 无草稿语义（ProviderStatus 无 DRAFT）→ 实现为**本地草稿**（client-only），不臆造服务端字段。
 *   6) 设计稿简介计数写「48/200」而示例文本仅 40 字（设计自身不自洽）→ 按真实长度渲染。
 *   7) 「营业执照」行在未上传态设计稿无空态文案 → 只保留名称 + 「必传」角标，不臆造提示语。
 */

/* ============================== 设计稿文案（逐字，禁改） ============================== */

export const PAGE_TITLE = '编辑主体档案'
export const SECTION_BASIC = '主体信息'
export const SECTION_CONTACT = '联系信息'
export const SECTION_FILES = '资质文件'

export const LABEL_COMPANY = '企业名称 *'
export const LABEL_USCC = '统一社会信用代码 *'
export const LABEL_INDUSTRY = '供应商类型 *'
export const LABEL_REGION = '所在地区 *'
export const LABEL_ADDRESS = '详细地址 *'
export const LABEL_WEBSITE = '官网'
export const LABEL_CONTACT_NAME = '联系人 *'
export const LABEL_CONTACT_TITLE = '职务'
export const LABEL_PHONE = '手机号 *'
export const LABEL_EMAIL = '邮箱'
export const LABEL_INTRO = '公司简介'

export const FILES_TIP = '支持 JPG/PNG/PDF，≤10MB'
export const BTN_DRAFT = '保存草稿'
export const BTN_SAVE = '保存'
export const BADGE_REQUIRED = '必传'
export const BADGE_CONDITIONAL = '条件必传'
export const BADGE_UPLOADED = '已上传'
export const UPLOAD_HINT_SINGLE = '点击上传，仅支持单个文件'

/** 供应商类型（设计稿三项 → 15-数据字典 industry_category 三枚举，顺序对应为推断） */
export const INDUSTRY_OPTIONS = [
  { label: '原厂', code: 'ORIGINAL' },
  { label: '渠道商', code: 'RESELLER' },
  { label: '中转商', code: 'AGGREGATOR' }
] as const

export type IndustryCode = string

/** 资质三行（设计稿固定三行；category 为前端与接口约定的分类码，字段级未定义 → 推断） */
export interface QualificationRow {
  key: string
  name: string
  category: string
  badge?: string
  hint?: string
  desc?: string
  file?: { id: string; fileName: string }
}

export const QUALIFICATION_ROWS: readonly QualificationRow[] = [
  { key: 'biz_license', name: '营业执照', category: 'BUSINESS_LICENSE', badge: BADGE_REQUIRED },
  {
    key: 'upstream_auth',
    name: '上游授权书',
    category: 'UPSTREAM_AUTHORIZATION',
    badge: BADGE_CONDITIONAL,
    hint: UPLOAD_HINT_SINGLE
  },
  { key: 'other', name: '其他选传资质', category: 'OTHER', desc: '增值电信业务许可证、等保备案等' }
]

/** 占位文案（除官网外均为推断，见文件头缺口 3） */
export const PLACEHOLDER_COMPANY = '请输入企业名称'
export const PLACEHOLDER_USCC = '请输入统一社会信用代码'
export const PLACEHOLDER_REGION = '请选择'
export const PLACEHOLDER_ADDRESS = '请输入详细地址'
export const PLACEHOLDER_WEBSITE = '请输入企业官网地址' // 设计原文
export const PLACEHOLDER_CONTACT_NAME = '请输入联系人'
export const PLACEHOLDER_CONTACT_TITLE = '请输入职务'
export const PLACEHOLDER_PHONE = '请输入手机号'
export const PLACEHOLDER_EMAIL = '请输入邮箱'
export const PLACEHOLDER_INTRO = '请输入公司简介'

/* ============================== 约束与错误文案 ============================== */

export const MAX_COMPANY_NAME = 64
export const MAX_USCC = 18
export const MAX_CONTACT_NAME = 32
export const MAX_CONTACT_TITLE = 32
export const MAX_EMAIL = 64
export const MAX_WEBSITE = 128
export const MAX_ADDRESS = 128
export const MAX_INTRO = 200 // 设计稿计数分母「…/200」

export const PHONE_PATTERN = /^1[3-9]\d{9}$/ // R-01
export const USCC_PATTERN = /^[0-9A-Za-z]{18}$/
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const WEBSITE_PATTERN = /^https?:\/\/[^\s]+$/

export const MSG_COMPANY_REQUIRED = '请输入企业名称'
export const MSG_USCC_INVALID = '请输入 18 位统一社会信用代码'
export const MSG_INDUSTRY_REQUIRED = '请选择供应商类型'
export const MSG_REGION_REQUIRED = '请选择所在地区'
export const MSG_ADDRESS_REQUIRED = '请输入详细地址'
export const MSG_CONTACT_REQUIRED = '请输入联系人'
export const MSG_PHONE_REQUIRED = '请输入手机号'
export const MSG_PHONE_INVALID = '请输入正确的手机号'
export const MSG_EMAIL_INVALID = '请输入正确的邮箱'
export const MSG_WEBSITE_INVALID = '请输入正确的官网地址，需以 http:// 或 https:// 开头'
export const MSG_INTRO_TOO_LONG = '公司简介不超过 200 字'

/* ============================== 视图模型 ============================== */

export interface ProfileForm {
  companyName: string
  uscc: string
  industry: IndustryCode
  province: string
  city: string
  address: string
  website: string
  contactName: string
  contactTitle: string
  phone: string
  email: string
  intro: string
}

export function emptyProfileForm(): ProfileForm {
  return {
    companyName: '',
    uscc: '',
    industry: '',
    province: '',
    city: '',
    address: '',
    website: '',
    contactName: '',
    contactTitle: '',
    phone: '',
    email: '',
    intro: ''
  }
}

/** 服务端档案（字段级 schema 未在 18-API 定义 → 按数据字典字段名 + 推断字段名消费） */
export interface ProviderProfileDetail {
  id?: string
  provider_id?: string
  company_name?: string
  unified_social_credit_code?: string
  industry_category?: string
  province?: string
  city?: string
  address?: string
  website?: string
  contact_name?: string
  contact_title?: string
  contact_phone?: string
  contact_email?: string
  company_intro?: string
  completeness?: number
  status?: string
}

function str(value: unknown): string {
  return typeof value === 'string' ? value : value === undefined || value === null ? '' : String(value)
}

/** 服务端档案 → 表单。缺字段一律空串（不显示 undefined / null） */
export function mapProfileToForm(data?: ProviderProfileDetail | null): ProfileForm {
  const d = data ?? {}
  return {
    companyName: str(d.company_name),
    uscc: str(d.unified_social_credit_code),
    industry: str(d.industry_category),
    province: str(d.province),
    city: str(d.city),
    address: str(d.address),
    website: str(d.website),
    contactName: str(d.contact_name),
    contactTitle: str(d.contact_title),
    phone: str(d.contact_phone),
    email: str(d.contact_email),
    intro: str(d.company_intro)
  }
}

/** 分类码 → 设计稿中文标签（三项枚举）；未知码原样返回（不臆造映射） */
export function industryLabel(code: string): string {
  const hit = INDUSTRY_OPTIONS.find((o) => o.code === code)
  return hit ? hit.label : str(code)
}

/** 完整度标签：仅当服务端给了数字才渲染（PRD 无定义，不臆造计算公式） */
export function completenessText(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return ''
  return `${Math.round(value)}%`
}

/** 简介字数计数（设计稿「48/200」；按真实长度，见文件头缺口 6） */
export function bioCounter(text: string): string {
  return `${str(text).length}/${MAX_INTRO}`
}

/** 表单 → 提交体（数据字典字段名；不含只读的完整度） */
export function buildProfilePayload(form: ProfileForm): Record<string, unknown> {
  return {
    company_name: str(form.companyName).trim(),
    unified_social_credit_code: str(form.uscc).trim(),
    industry_category: str(form.industry).trim(),
    province: str(form.province).trim(),
    city: str(form.city).trim(),
    address: str(form.address).trim(),
    website: str(form.website).trim(),
    contact_name: str(form.contactName).trim(),
    contact_title: str(form.contactTitle).trim(),
    contact_phone: str(form.phone).trim(),
    contact_email: str(form.email).trim(),
    company_intro: str(form.intro).trim()
  }
}

/** 保存前校验：返回第一条错误文案；通过返回 undefined */
export function validateProfileForm(form: ProfileForm): string | undefined {
  const company = str(form.companyName).trim()
  if (!company) return MSG_COMPANY_REQUIRED
  if (company.length > MAX_COMPANY_NAME) return `企业名称不超过 ${MAX_COMPANY_NAME} 字`

  const uscc = str(form.uscc).trim()
  if (!USCC_PATTERN.test(uscc)) return MSG_USCC_INVALID

  if (!str(form.industry).trim()) return MSG_INDUSTRY_REQUIRED
  if (!str(form.province).trim() || !str(form.city).trim()) return MSG_REGION_REQUIRED
  if (!str(form.address).trim()) return MSG_ADDRESS_REQUIRED
  if (!str(form.contactName).trim()) return MSG_CONTACT_REQUIRED

  const phone = str(form.phone).trim()
  if (!phone) return MSG_PHONE_REQUIRED
  if (!PHONE_PATTERN.test(phone)) return MSG_PHONE_INVALID

  const email = str(form.email).trim()
  if (email && !EMAIL_PATTERN.test(email)) return MSG_EMAIL_INVALID

  const website = str(form.website).trim()
  if (website && !WEBSITE_PATTERN.test(website)) return MSG_WEBSITE_INVALID

  if (str(form.intro).length > MAX_INTRO) return MSG_INTRO_TOO_LONG

  return undefined
}

/* ============================== 资质文件行 ============================== */

/** 服务端资质条目（字段级 schema 未定义 → 分类码候选 category/code/type，文件名候选 file_name/name） */
export interface QualificationItem {
  id?: string
  category?: string
  code?: string
  type?: string
  file_name?: string
  name?: string
}

function itemCategory(item: QualificationItem): string {
  return str(item.category) || str(item.code) || str(item.type)
}

function itemFileName(item: QualificationItem): string {
  return str(item.file_name) || str(item.name)
}

/** 服务端资质列表 → 设计稿固定的三行（按分类码匹配；不匹配的文件不硬塞进设计稿的行） */
export function buildQualificationRows(items?: QualificationItem[] | null): QualificationRow[] {
  const list = Array.isArray(items) ? items : []
  return QUALIFICATION_ROWS.map((row) => {
    const hit = list.find((item) => itemCategory(item) === row.category && itemFileName(item))
    if (!hit) return { ...row }
    return {
      ...row,
      file: { id: str(hit.id), fileName: itemFileName(hit) }
    }
  })
}

/** 上传提交体：只登记分类 + 文件名 + 字节数（18-API 无文件上传接口 → 文件本体不上传） */
export function uploadPayload(
  row: QualificationRow,
  file: { name?: string; size?: number }
): Record<string, unknown> {
  return {
    category: row.category,
    file_name: str(file?.name),
    file_size: Number(file?.size ?? 0)
  }
}

/** 行是否已上传（决定是否渲染「已上传」角标 + 文件名 + 删除/查看图标） */
export function isUploaded(row: QualificationRow): boolean {
  return Boolean(row.file && row.file.fileName)
}
