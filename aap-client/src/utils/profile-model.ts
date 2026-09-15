/**
 * 序号 10.1【档案与凭证】供应商档案（page-10-1-2 / 主体档案）— 视图模型
 *
 * 文案真源：.calicat/raw/pages/page-10-1-2/design.tree.json（430 宽 · 设计总高 1414 · 无 TabBar）
 * 几何真源（设计截图像素量尺 .agents/state/design-shots/page-10-1-2.png）：
 *   顶栏 0..95(96) · 卡1 108..265(158，无描边 + 投影 0/6/20 rgba(15,23,42,.06)) ·
 *   卡2 278..690(413) · 卡3 703..981(279) · 卡4 995..1313(319) · 底栏 1330..1413(84) · 页高 1414
 *   卡 padding 20 r18 描边 #EEF2F7（盒外 → ring）· 卡间距 12 · 字段 = 标签 16 + 2 + 值 20
 * 接口真源：18-API设计OpenAPI.md「Provider」→ /provider/profile、/provider/qualifications（前缀 /api/v1）；
 *           该卡片**只列路径未列方法** → GET/PUT 为 REST 语义推断（与序号 3/4/8/9/10 同一缺口）。
 * 字段真源：15-数据模型ER与数据字典.md `aap_provider`（company_name / unified_social_credit_code /
 *           industry_category(ORIGINAL|RESELLER|AGGREGATOR) / contact_name / contact_email / status …）
 *
 * ⚠️ 记入台账（.agents/state/aap-feature-status.csv 序号 10.1）的缺口，一律**不臆造**：
 *   1) 「完整度 / 档案完整度」在 22 份 PRD 与数据字典**零命中** → 只在服务端给出数字时渲染
 *      （百分比与进度条填充同源，不自造计算公式）。
 *   2) 「所在地区 / 详细地址 / 官网 / 职务 / 公司简介」在 22 份 PRD 零命中 → 字段名为推断
 *      （province / city / address / website / contact_title / company_intro）。
 *   3) 「闸门提示」文案（含「当前还缺 2 项资质文件」）为设计稿原文常量 —— PRD 无门槛规则与计数口径，
 *      不去派生「还缺 N 项」（missing-prd）。
 *   4) 资质审核状态字段级未定义 → 已上传行统一渲染设计稿的「已通过」绿色角标（无法区分待审核/驳回）。
 *   5) 资质上传日期字段未定义 → 取 uploaded_at / created_at 的日期部分，缺失只写「已上传」。
 *   6) 第 3 行分类码取 `OTHER`（与序号 10 编辑页第三槽位同码，选传类）；资质分类码全 PRD 无定义。
 *   7) 空值占位 `—` 为占位（设计稿无空态样例）。
 *   8) 手机号脱敏：设计稿 `138 **** 6621`（三段带空格）vs R-05 `138****8888` vs 18-API `138****8888`
 *      → 服务端给了 contact_phone_mask 用服务端值，否则按**设计稿格式**本地脱敏（不静默改口径）。
 */
import type { QualificationItem } from './profile-edit-model'

/**
 * 资质条目（字段级 schema 未定义 → 在序号 10 的候选字段之上再补 3 个日期候选；
 * 分类码候选 category/code/type、文件名候选 file_name/name 沿用序号 10 的约定）
 */
export interface QualificationViewItem extends QualificationItem {
  uploaded_at?: unknown
  created_at?: unknown
  date?: unknown
}

/* ============================== 设计稿文案（逐字，禁改） ============================== */

export const PAGE_TITLE = '主体档案'

export const SECTION_COMPLETENESS = '档案完整度'
export const SECTION_BASIC = '主体信息'
export const SECTION_CONTACT = '联系信息'
export const SECTION_FILES = '资质文件'

export const BADGE_LOCKED = '已认证 · 不可编辑'
export const BADGE_APPROVED = '已通过'
export const BADGE_CONDITIONAL = '条件必传'

export const ACTION_EDIT = '编辑'
export const ACTION_MANAGE = '管理'
export const BTN_UPLOAD = '上传新资质'
export const BTN_SAVE = '保存'
export const BTN_COMPLETE = '去补全资质'

export const LABEL_COMPANY = '企业名称'
export const LABEL_USCC = '统一社会信用代码'
export const LABEL_INDUSTRY = '供应商类型'
export const LABEL_REGION = '所在地区'
export const LABEL_ADDRESS = '详细地址'
export const LABEL_WEBSITE = '官网'
export const LABEL_CONTACT_NAME = '联系人'
export const LABEL_CONTACT_TITLE = '职务'
export const LABEL_PHONE = '手机号'
export const LABEL_EMAIL = '邮箱'
export const LABEL_INTRO = '公司简介'

export const GATE_HINT = '档案完整度达到 100% 后，才可发起报价审核。当前还缺 2 项资质文件。'
export const NOTE_BASIC_LOCKED = '主体信息已完成企业认证，如需修改请联系平台运营。'

/** 顶部胶囊前缀（设计稿「完整度 72%」= 前缀 + 百分比） */
export const COMPLETENESS_PREFIX = '完整度 '

/** 空值占位（设计稿无空态样例 → 占位，记 missing-prd） */
export const EMPTY_VALUE = '—'

/** 地区连接符（设计稿「浙江 · 杭州」） */
export const REGION_SEPARATOR = ' · '

/* ============================== 展示模型 ============================== */

export interface ProfileView {
  company: string
  uscc: string
  industryCode: string
  industryLabel: string
  region: string
  address: string
  website: string
  contactName: string
  contactTitle: string
  phone: string
  email: string
  intro: string
  completeness?: number
}

/** 服务端档案（字段级 schema 未在 18-API 定义 → 字段名取数据字典 + 推断字段名） */
export interface ProfileViewSource {
  company_name?: unknown
  unified_social_credit_code?: unknown
  industry_category?: unknown
  province?: unknown
  city?: unknown
  address?: unknown
  website?: unknown
  contact_name?: unknown
  contact_title?: unknown
  contact_phone?: unknown
  contact_phone_mask?: unknown
  contact_email?: unknown
  company_intro?: unknown
  completeness?: unknown
}

function str(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return ''
}

/* ============================== 完整度 ============================== */

/** 完整度百分比：取整并夹到 0..100；非数字视为无值（不臆造公式） */
export function completenessPercent(value: unknown): number | undefined {
  if (typeof value !== 'number' || !Number.isFinite(value)) return undefined
  return Math.min(100, Math.max(0, Math.round(value)))
}

/** 顶部胶囊文案；无值返回空串（整块不渲染） */
export function completenessPillText(value: unknown): string {
  const percent = completenessPercent(value)
  return percent === undefined ? '' : `${COMPLETENESS_PREFIX}${percent}%`
}

/** 进度条填充宽度（CSS 值）；无值 0% */
export function completenessBarWidth(value: unknown): string {
  const percent = completenessPercent(value)
  return `${percent ?? 0}%`
}

/* ============================== 文本格式化 ============================== */

/** 省 · 市（设计稿格式）；缺一侧只显示另一侧 */
export function regionText(province: unknown, city: unknown): string {
  return [str(province), str(city)].filter(Boolean).join(REGION_SEPARATOR)
}

/**
 * 手机号脱敏：11 位数字 → `138 **** 6621`（设计稿格式）；
 * 已带 * 的值原样返回（服务端已脱敏）；其余返回空串（不猜测）。
 */
export function maskPhone(value: unknown): string {
  const raw = str(value)
  if (!raw) return ''
  if (raw.includes('*')) return raw
  if (!/^\d{11}$/.test(raw)) return ''
  return `${raw.slice(0, 3)} **** ${raw.slice(7)}`
}

/** 手机号显示：服务端脱敏字段优先，其次本地按设计稿格式脱敏 */
export function contactPhoneText(profile?: ProfileViewSource | null): string {
  const masked = str(profile?.contact_phone_mask)
  if (masked) return masked
  return maskPhone(profile?.contact_phone)
}

/** 供应商类型码 → 设计稿三项标签；未知码原样返回（不臆造映射） */
export function industryLabel(code: unknown): string {
  const value = str(code)
  switch (value) {
    case 'ORIGINAL':
      return '原厂'
    case 'RESELLER':
      return '渠道商'
    case 'AGGREGATOR':
      return '中转商'
    default:
      return value
  }
}

/** 服务端档案 → 展示模型（缺值一律占位符，不显示 undefined / null） */
export function mapProfileView(profile?: ProfileViewSource | null): ProfileView {
  const src = profile ?? {}
  const code = str(src.industry_category)
  return {
    company: str(src.company_name) || EMPTY_VALUE,
    uscc: str(src.unified_social_credit_code) || EMPTY_VALUE,
    industryCode: code,
    industryLabel: industryLabel(code),
    region: regionText(src.province, src.city) || EMPTY_VALUE,
    address: str(src.address) || EMPTY_VALUE,
    website: str(src.website) || EMPTY_VALUE,
    contactName: str(src.contact_name) || EMPTY_VALUE,
    contactTitle: str(src.contact_title) || EMPTY_VALUE,
    phone: contactPhoneText(src) || EMPTY_VALUE,
    email: str(src.contact_email) || EMPTY_VALUE,
    intro: str(src.company_intro) || EMPTY_VALUE,
    completeness: completenessPercent(src.completeness)
  }
}

/* ============================== 资质三行 ============================== */

/** 设计稿固定的三行（分类码与序号 10 编辑页同槽位；全 PRD 无分类码定义 → 推断） */
interface QualificationViewConfig {
  key: string
  name: string
  category: string
  tone: 'primary' | 'muted'
  emptyText: string
  emptyBadge: string
  chevron: boolean
}

export const QUALIFICATION_VIEW_CONFIG: readonly QualificationViewConfig[] = [
  {
    key: 'biz_license',
    name: '营业执照',
    category: 'BUSINESS_LICENSE',
    tone: 'primary',
    emptyText: '',
    emptyBadge: '',
    chevron: false
  },
  {
    key: 'upstream_auth',
    name: '上游授权书',
    category: 'UPSTREAM_AUTHORIZATION',
    tone: 'primary',
    emptyText: '未上传',
    emptyBadge: BADGE_CONDITIONAL,
    chevron: false
  },
  {
    key: 'other',
    name: '增值电信业务许可证',
    category: 'OTHER',
    tone: 'muted',
    emptyText: '选传 · 可后续补充',
    emptyBadge: '',
    chevron: true
  }
]

export interface QualificationView {
  key: string
  name: string
  tone: 'primary' | 'muted'
  subtitle: string
  badge: string
  badgeTone: 'success' | 'warning' | ''
  chevron: boolean
}

/** 服务端资质负载 → 数组（兼容裸数组 / {items} / 非法负载） */
export function toQualificationItems(payload: unknown): QualificationViewItem[] {
  if (Array.isArray(payload)) return payload as QualificationViewItem[]
  const items = (payload as { items?: unknown } | null | undefined)?.items
  return Array.isArray(items) ? (items as QualificationViewItem[]) : []
}

function itemCategory(item: QualificationViewItem): string {
  return str(item.category) || str(item.code) || str(item.type)
}

function itemFileName(item: QualificationViewItem): string {
  return str(item.file_name) || str(item.name)
}

/** 上传日期（字段级未定义 → 取 uploaded_at / created_at 的日期部分） */
function itemDate(item: QualificationViewItem): string {
  const candidates = [item.uploaded_at, item.created_at, item.date]
  for (const candidate of candidates) {
    const raw = str(candidate)
    const hit = /^(\d{4}-\d{2}-\d{2})/.exec(raw)
    if (hit) return hit[1]
  }
  return ''
}

/** 服务端资质列表 → 设计稿固定的三行（按分类码匹配；不匹配的文件不硬塞进设计稿的行） */
export function qualificationViewRows(items?: QualificationViewItem[] | null): QualificationView[] {
  const list = Array.isArray(items) ? items : []
  return QUALIFICATION_VIEW_CONFIG.map((config) => {
    const hit = list.find((item) => itemCategory(item) === config.category && itemFileName(item))
    if (!hit) {
      return {
        key: config.key,
        name: config.name,
        tone: config.tone,
        subtitle: config.emptyText,
        badge: config.emptyBadge,
        badgeTone: config.emptyBadge ? 'warning' : '',
        chevron: config.chevron
      }
    }
    const date = itemDate(hit)
    return {
      key: config.key,
      name: config.name,
      tone: config.tone,
      subtitle: date ? `已上传${REGION_SEPARATOR}${date}` : '已上传',
      badge: BADGE_APPROVED,
      badgeTone: 'success',
      chevron: config.chevron
    }
  })
}
