/**
 * 供应商档案接口 — 依据 18-API设计OpenAPI.md「Provider」Tag
 * /provider/profile、/provider/qualifications、/provider/qualifications/{id}（前缀 /api/v1）
 *
 * ⚠️ 缺口（与序号 3/4/8/9 同一处理，记入台账，不臆造端点）：
 *   1) 18-API 该行**只列路径未列方法** → GET / PUT / POST / DELETE 为 REST 语义推断。
 *   2) 字段级 schema 未定义：
 *      · companyName —— 工作台顶部栏公司名用它渲染（缺失显示占位符 «—»，不编造公司名）。
 *      · 省市 / 详细地址 / 官网 / 职务 / 公司简介 / 完整度 在 22 份 PRD 与 15-数据字典零命中 →
 *        前端按 province/city/address/website/contact_title/company_intro/completeness 消费（字段名为推断）。
 *      · 18-API 无文件上传接口 → 上传资质只登记 category/file_name/file_size，**文件本体不上传**。
 */
import { http } from './http'

export interface ProviderProfile {
  companyName?: string
  providerCode?: string
  status?: string
  /** 供应商主体（15-数据字典 aap_provider）：序号 9 报价主体用（字段名 snake_case 与数据字典一致） */
  id?: string
  provider_id?: string
  company_name?: string
  unified_social_credit_code?: string
  /** 供应商类型映射 industry_category（ORIGINAL/RESELLER/AGGREGATOR） */
  industry_category?: string
  /** 以下 6 个字段在 22 份 PRD / 数据字典零命中 → 字段名为推断（missing-prd） */
  province?: string
  city?: string
  address?: string
  website?: string
  contact_name?: string
  contact_title?: string
  contact_phone?: string
  contact_email?: string
  company_intro?: string
  /** 完整度（设计稿右上「72%」）；PRD 无定义 → 仅在有值时渲染，不臆造公式 */
  completeness?: number
}

export const providerApi = {
  profile() {
    return http<ProviderProfile>('/provider/profile')
  },

  /** 保存档案（序号 10「保存」） */
  saveProfile(body: Record<string, unknown>) {
    return http<Record<string, unknown>>('/provider/profile', { method: 'PUT', data: body })
  },

  /** 资质列表（序号 10 资质卡三行的已上传态） */
  qualifications() {
    return http<{ items?: unknown[] } | unknown[]>('/provider/qualifications')
  },

  /** 上传资质（只登记元数据；18-API 无文件上传接口） */
  uploadQualification(body: Record<string, unknown>) {
    return http<Record<string, unknown>>('/provider/qualifications', { method: 'POST', data: body })
  },

  /** 删除资质 */
  removeQualification(id: string) {
    return http<Record<string, unknown>>(`/provider/qualifications/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    })
  }
}
