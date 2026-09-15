/**
 * 检测任务接口 — 依据 18-API设计OpenAPI.md「Detection」Tag
 *   GET  /detection-jobs/{jobId}          任务详情（进度页轮询）
 *   GET  /detection-jobs/{jobId}/results  逐项检测结果（分项检测行）
 *   前缀 /api/v1；鉴权 Authorization: Bearer ***
 *   ⚠️ 该卡片只列路径未列方法 → 方法按 REST 语义推断为 GET，台账记「方法为推断」待确认。
 *
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md
 *   aap_detection_job（status QUEUED/RUNNING/PARTIAL/FINISHED/FAILED/CANCELLED、started_at/finished_at、
 *     total_score、result PASS/FAIL/MANUAL_REVIEW、confidence、cost_estimate_usd/cost_actual_usd、
 *     error_code/msg、trigger_type）；aap_detection_result（probe_code/status/score/metrics/evidence/
 *     explanation/weight_used）。字段级 schema 未在 18-API 定义 → missing-prd（见 detecting-model.ts 头部）。
 *
 * 未接线（本页设计稿无对应控件，不臆造）：
 *   GET /detection-jobs/{jobId}/results/{probeCode}（单探测详情）、POST /detection-jobs/{jobId}/cancel（取消）、
 *   POST /detection-jobs/{jobId}/release（人工放行，管理端）
 */
import { http } from './http'
import type { DetectionJobRaw, DetectionResultsRaw } from '@/utils/detecting-model'

export type { DetectionJobRaw, DetectionResultsRaw } from '@/utils/detecting-model'

/** 新建检测任务的响应（序号 7「重新提交检测」）——字段名兼容 job_id/jobId/id，服务端任一为准 */
export interface DetectionCreateRaw {
  job_id?: string | null
  jobId?: string | null
  id?: string | null
  job_no?: string | null
}

const path = (jobId: string) => `/detection-jobs/${encodeURIComponent(jobId)}`

export const detectionApi = {
  /** 检测任务详情（含状态与进度） */
  job(jobId: string) {
    return http<DetectionJobRaw>(path(jobId), { method: 'GET' })
  },

  /** 逐项检测结果（D1–D8 分项行） */
  results(jobId: string) {
    return http<DetectionResultsRaw>(`${path(jobId)}/results`, { method: 'GET' })
  },

  /**
   * 重测（人工点击「重新提交检测」）→ 新建检测任务。
   * 依据：09-PRD §5 触发时机「重测（修改凭证/人工点击）」；15-数据字典 credential 1:N detection_job（可重测）。
   * ⚠️ 18-API 只列路径 /detection-jobs 未列方法 → POST 为 REST 语义推断（台账序号 7 记「方法为推断」）。
   */
  create(payload: { credential_id: string }) {
    return http<DetectionCreateRaw>('/detection-jobs', { method: 'POST', data: payload })
  }
}
