/**
 * 接入申请（准入表单变体）接口 — 序号 4-v1 / page-24
 *
 * 接口依据：.calicat/prd/18-API设计OpenAPI.md
 *   Provider  Tag → /provider/qualifications、/provider/qualifications/{id}
 *   Detection Tag → /detection-jobs、/{jobId}、/{jobId}/cancel、/{jobId}/results …
 *   通用约定：前缀 /api/v1；鉴权 Authorization: Bearer ***；错误体 ApiError(code+message+traceId+details)；
 *            非幂等写支持 Idempotency-Key（24h）。
 *
 * 「提交接入」= 一次资质/接入申请提交（POST /provider/qualifications）。
 * 设计脚注「提交后系统将自动发起检测，预计 5 分钟内完成」是**服务端副作用**
 * （09-PRD §5 与其一致），前端不额外调 /detection-jobs，避免重复建任务（DetectionJob 互斥不变式）。
 *
 * ⚠️ missing-prd（台账序号 4-v1 行已登记，不臆造别的路径）：
 *   1) 18-API 卡片只列路径未列方法（该卡为 153KB openapi.yaml 的摘要，完整文件不在仓库）
 *      → POST 为 REST 语义推断；
 *   2) 企业信息（company_name / unified_social_credit_code / contact_name / contact_phone）在
 *      15-数据字典 aap_provider 有列，但 18-API **没有** provider 主体写接口（仅 /provider/profile
 *      与 /provider/qualifications）→ 本页把企业信息随该申请体一起提交，接口归属待人类拍板；
 *   3) 响应字段级 schema 未定义 → 只按主键命名取可选字段（id / detection_job_id），不编造业务字段。
 */

import { http } from './http'
import type { AccessApplicationPayload } from '@/utils/access-application-model'

export type { AccessApplicationPayload } from '@/utils/access-application-model'

/**
 * 提交结果：字段级 schema 未在 18-API 定义 → 全部可选，缺失时不编造。
 * 检测任务号用于跳转「检测进行中」页；服务端未返回时不带 query（页面自行拉取最新任务）。
 */
export interface AccessApplicationResultRaw {
  id?: string
  qualification_id?: string
  detection_job_id?: string
  job_id?: string
}

export const accessApplicationApi = {
  /** 提交接入申请（企业信息 + 凭证资料登记） */
  submit(payload: AccessApplicationPayload) {
    return http<AccessApplicationResultRaw>('/provider/qualifications', {
      method: 'POST',
      data: payload as unknown as Record<string, unknown>
    })
  }
}
