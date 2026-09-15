/**
 * 检测报告接口 — 依据 18-API设计OpenAPI.md「Report」Tag
 *   GET /reports                     报告列表（**序号 21 我的页新增**：「检测报告 N 份」计数）
 *   GET /reports/{reportId}          报告详情（本页数据源：结论 / 关键指标 / 维度 / 明细 / 风险 / 证据 / 免责）
 *   GET /reports/{reportId}/export   导出（设计稿「导出 PDF」按钮）
 *   前缀 /api/v1；鉴权 Authorization: Bearer ***
 *   ⚠️ 该卡片只列路径未列方法 → 方法按 REST 语义推断为 GET，台账记「方法为推断」待人类确认。
 *
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md（aap_report / aap_report_section / aap_report_template）；
 *   17-spec §2 Report / ReportTemplate 领域对象（report 1:1 detection_job）。
 *   字段级 schema 未在 18-API 定义 → missing-prd（见 src/utils/report-model.ts 头部缺口清单）。
 *
 * 未接线（本页不调用，不臆造）：
 *   GET /reports/{reportId}/html（在线 HTML 版，设计仅「导出 PDF」）。
 *   ★ 序号 21 已接线 GET /reports：画布无「报告列表页」，只用于计数（落点记台账阻塞）。
 */
import { http } from './http'
import type { ReportExportRaw, ReportRaw } from '@/utils/report-model'

export type { ReportExportRaw, ReportRaw } from '@/utils/report-model'

/** 报告列表响应（字段级 schema 未在 18-API 定义 → 只取计数与标识） */
export interface ReportListRaw {
  total?: number
  items?: { id?: string; report_id?: string; status?: string }[]
  list?: { id?: string; report_id?: string }[]
}

export interface ReportListParams {
  page?: number
  pageSize?: number
}

const path = (reportId: string) => `/reports/${encodeURIComponent(reportId)}`

export const reportApi = {
  /** 报告列表（序号 21 「检测报告」入口计数；无列表页设计 → 不渲染列表） */
  list(params?: ReportListParams) {
    return http<ReportListRaw>('/reports', {
      method: 'GET',
      data: { page: params?.page, pageSize: params?.pageSize }
    })
  },

  /**
   * 报告详情。
   * 泛型参数用于「同一端点、不同报告模板」的场景：序号 7 未通过报告（/pages/report-failed/index）
   * 复用同一 GET /reports/{reportId}，但视图字段不同 → 以 ReportFailedRaw 消费。
   */
  detail<T = ReportRaw>(reportId: string) {
    return http<T>(path(reportId), { method: 'GET' })
  },

  /** 导出（PDF/文件链接由服务端生成） */
  exportFile(reportId: string) {
    return http<ReportExportRaw>(`${path(reportId)}/export`, { method: 'GET' })
  }
}
