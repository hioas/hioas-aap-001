/**
 * 供应商档案接口 — 依据 18-API设计OpenAPI.md「Provider」Tag
 * /provider/profile、/provider/qualifications（前缀 /api/v1）
 *
 * ⚠️ companyName 字段名未在 18-API 明确 → 工作台顶部栏公司名用它渲染；
 *    已记入台账 missing-prd（字段级），缺字段时顶部栏显示占位符 «—»，不编造公司名。
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
}

export const providerApi = {
  profile() {
    return http<ProviderProfile>('/provider/profile')
  }
}
