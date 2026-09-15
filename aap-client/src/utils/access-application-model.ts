/**
 * 「接入凭证-表单」（准入表单变体）视图模型与校验 — 序号 4-v1（page-24）纯逻辑
 *
 * 设计真源：.calicat/raw/pages/page-24/design.tree.json（430 宽）
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md §aap_provider（供应商主体）
 *   provider_no / company_name / unified_social_credit_code（唯一）/ industry_category /
 *   contact_name / contact_phone_cipher·contact_phone_mask / status / recheck_interval_days …
 * 资质真源：17-spec §3 Provider(… qualification_files …) + 15 §provider aap_provider_qualification
 * 校验真源：17-spec §5 R-01 手机号 ^1[3-9]\d{9}$（复用 utils/validators.isPhone）
 *         设计占位「请输入 18 位统一社会信用代码」→ 长度 18
 *
 * ⚠️ missing-prd（不臆造，台账序号 4-v1 行已登记，等人拍板）：
 *   1) 「基础检测 / 深度检测 / 合规检测」在 22 份 PRD 中 **零命中**（全仓库 grep 0 命中），
 *      18-API 亦无对应入参/枚举 → 本模型只把它当 **UI 选中态**保留，**不拼进提交体**
 *      （有专门用例把这条钉死：见 tests/unit/access-application-model.spec.ts）。
 *   2) 「备注」在 15-数据字典 aap_provider 中无对应列 → 同样只作 UI 态，不进提交体。
 *   3) 文件类型/尺寸（jpg / png / pdf、≤10MB）取自设计文案；18-API 无文件上传接口
 *      （仅 Contract Tag 有 /contracts/{id}/file），故本页只登记文件名 + 字节数。
 *      （10-PRD C2「文件 PDF/图片 ≤20MB」属合同盖章件域，与本页上限不是同一约束。）
 *   4) 统一社会信用代码字符集（GB 32100-2015 排除 I/O/S/V/Z）PRD 未定义 → 只校验「18 位字母数字」。
 */

import { isPhone, normalize } from './validators'

/* ---------------- 文案（设计稿原文，不得改写） ---------------- */

export const PAGE_TITLE = '接入凭证'
export const PAGE_SUBTITLE = '填写客户信息并提交检测'

export const SECTION_BASIC = '基本信息'
export const SECTION_DETECTION = '检测类型'
export const SECTION_FILES = '凭证资料'
export const SECTION_REMARK = '备注'

export const LABEL_COMPANY = '客户名称'
export const LABEL_USCC = '统一社会信用代码'
export const LABEL_CONTACT = '联系人'
export const LABEL_PHONE = '联系电话'
/** 必填标记（设计稿仅「客户名称」「统一社会信用代码」带星号，色值 #EF4444） */
export const REQUIRED_STAR = '*'

/** 设计占位原文 */
export const PLACEHOLDER_USCC = '请输入 18 位统一社会信用代码'
export const PLACEHOLDER_CONTACT = '请输入联系人姓名'
export const PLACEHOLDER_PHONE = '请输入手机号'
export const PLACEHOLDER_REMARK = '补充说明，例如客户所属行业、检测用途等'
/** ⚠️ 设计稿该框是已填值「深圳市恒信科技有限公司」、无占位文案 → 此占位为推断，已记台账待确认 */
export const PLACEHOLDER_COMPANY = '请输入客户名称'

export const UPLOAD_TIP = '支持 jpg / png / pdf'
export const UPLOAD_MAIN = '点击上传凭证文件'
export const UPLOAD_LIMIT = '单个文件不超过 10MB'

export const SUBMIT_LABEL = '提交接入'
export const SUBMIT_FOOTNOTE = '提交后系统将自动发起检测，预计 5 分钟内完成'

/* ---------------- 检测类型（UI 选中态，无 PRD 枚举依据） ---------------- */

export const DETECTION_TYPES = ['基础检测', '深度检测', '合规检测'] as const
export type DetectionType = (typeof DETECTION_TYPES)[number]
/** 设计稿选中态 = 最左「基础检测」 */
export const DEFAULT_DETECTION_TYPE: DetectionType = '基础检测'

/** 单选切换；枚举外的值一律忽略（不臆造新类型，保持原选中项） */
export function toggleDetectionType(current: string, next: string): DetectionType {
  return (DETECTION_TYPES as readonly string[]).includes(next) ? (next as DetectionType) : (current as DetectionType)
}

/* ---------------- 文件规则 ---------------- */

export const ACCEPT_EXTENSIONS = ['jpg', 'jpeg', 'png', 'pdf'] as const
/** 设计文案「单个文件不超过 10MB」 */
export const MAX_FILE_BYTES = 10 * 1024 * 1024

export const ERR_FILE_TYPE = '仅支持 jpg / png / pdf 格式'
export const ERR_FILE_SIZE = '单个文件不超过 10MB'

export interface UploadFileMeta {
  name: string
  size: number
}

/** 末段扩展名（小写）；无扩展名返回空串 */
export function fileExtension(name: string): string {
  const s = normalize(name)
  const i = s.lastIndexOf('.')
  return i > 0 ? s.slice(i + 1).toLowerCase() : ''
}

export function isAcceptedFile(name: string): boolean {
  return (ACCEPT_EXTENSIONS as readonly string[]).includes(fileExtension(name))
}

/** 文件校验：先类型后尺寸；合法返回 null */
export function validateFile(file: UploadFileMeta): string | null {
  if (!isAcceptedFile(file.name)) return ERR_FILE_TYPE
  if (Number(file.size) > MAX_FILE_BYTES) return ERR_FILE_SIZE
  return null
}

/** 「2.4 MB」/「2 KB」/「512 B」（设计稿示例 2.4 MB） */
export function formatFileSize(bytes: number): string {
  const n = Math.max(0, Number(bytes) || 0)
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`
  if (n >= 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${n} B`
}

/** 追加文件：非法则返回错误且列表不变（不静默丢弃、不静默接受） */
export function addFile(
  files: UploadFileMeta[],
  meta: UploadFileMeta
): { files: UploadFileMeta[]; error: string | null } {
  const error = validateFile(meta)
  if (error) return { files: files.slice(), error }
  return { files: [...files, { name: normalize(meta.name), size: Number(meta.size) || 0 }], error: null }
}

/** 按下标删除；越界返回原列表副本（不抛异常） */
export function removeFileAt(files: UploadFileMeta[], index: number): UploadFileMeta[] {
  if (index < 0 || index >= files.length) return files.slice()
  return files.filter((_, i) => i !== index)
}

/* ---------------- 表单与校验 ---------------- */

export const ERR_COMPANY_REQUIRED = '请输入客户名称'
export const ERR_USCC_REQUIRED = '请输入统一社会信用代码'
export const ERR_USCC_FORMAT = '统一社会信用代码需为 18 位字母数字'
export const ERR_PHONE = '请输入正确的手机号'

export const USCC_LENGTH = 18
/** 18 位数字或大写字母（字符集细分待 PRD 明确） */
export const USCC_RE = /^[0-9A-Z]{18}$/

export function normalizeUscc(v: unknown): string {
  return String(v ?? '')
    .replace(/\s+/g, '')
    .toUpperCase()
}

export function isUscc(v: unknown): boolean {
  return USCC_RE.test(normalizeUscc(v))
}

export interface AccessApplicationForm {
  companyName: string
  uscc: string
  contactName: string
  contactPhone: string
  remark: string
  /** UI 选中态；**不进提交体**（枚举无依据，见文件头 missing-prd ①） */
  detectionType: DetectionType
  files: UploadFileMeta[]
}

export function emptyAccessApplicationForm(): AccessApplicationForm {
  return {
    companyName: '',
    uscc: '',
    contactName: '',
    contactPhone: '',
    remark: '',
    detectionType: DEFAULT_DETECTION_TYPE,
    files: []
  }
}

/**
 * 本地校验（只拦设计稿标了星号的必填项；联系电话为选填，填了才校验格式）。
 * 服务端业务校验（重复申请 E-1104、SSRF 等）一律以服务端 message 为准，前端不重复判定。
 */
export function validateAccessApplication(form: AccessApplicationForm): string | null {
  if (!normalize(form.companyName)) return ERR_COMPANY_REQUIRED
  const uscc = normalizeUscc(form.uscc)
  if (!uscc) return ERR_USCC_REQUIRED
  if (!isUscc(uscc)) return ERR_USCC_FORMAT
  const phone = normalize(form.contactPhone)
  if (phone && !isPhone(phone)) return ERR_PHONE
  return null
}

/** 提交体：字段名一律取 15-数据字典 aap_provider / 17-spec Provider，未填项省略（不发空串） */
export interface AccessApplicationPayload {
  company_name: string
  unified_social_credit_code: string
  contact_name?: string
  contact_phone?: string
  /** 元素结构未在 15/17/18 展开 → 只传最小信息（文件名 + 字节数），记 missing-prd */
  qualification_files?: Array<{ file_name: string; file_size: number }>
}

export function buildAccessApplicationPayload(form: AccessApplicationForm): AccessApplicationPayload {
  const payload: AccessApplicationPayload = {
    company_name: normalize(form.companyName),
    unified_social_credit_code: normalizeUscc(form.uscc)
  }
  const contactName = normalize(form.contactName)
  if (contactName) payload.contact_name = contactName
  const contactPhone = normalize(form.contactPhone)
  if (contactPhone) payload.contact_phone = contactPhone
  if (form.files.length) {
    payload.qualification_files = form.files.map((f) => ({ file_name: f.name, file_size: f.size }))
  }
  return payload
}
