/**
 * 检测报告接口 — 依据 18-API设计OpenAPI.md「Report」Tag
 *   GET /reports/{reportId}          报告详情（本页数据源：结论 / 关键指标 / 维度 / 明细 / 风险 / 证据 / 免责）
 *   GET /reports/{reportId}/export   导出（设计稿「导出 PDF」按钮）
 *   前缀 /api/v1；鉴权 Authorization: Bearer ***
 *   ⚠️ 该卡片只列路径未列方法 → 方法按 REST 语义推断为 GET，台账记「方法为推断」待人类确认。
 *
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md（aap_report / aap_report_section / aap_report_template）；
 *   17-spec §2 Report / ReportTemplate 领域对象（report 1:1 detection_job）。
 *   字段级 schema 未在 18-API 定义 → missing-prd（见 src/utils/report-model.ts 头部缺口清单）。
 *
 * 未接线（本页设计稿无对应控件，不臆造）：
 *   GET /reports（报告列表，画布无列表页设计）、GET /reports/{reportId}/html（在线 HTML 版，设计仅「导出 PDF」）。
 */
import { http } from './http'
import type { ReportExportRaw, ReportRaw } from '@/utils/report-model'

export type { ReportExportRaw, ReportRaw } from '@/utils/report-model'

const path = (reportId: string) => `/reports/${encodeURIComponent(reportId)}`

export const reportApi = {
  /** 报告详情 */
  detail(reportId: string) {
    return http<ReportRaw>(path(reportId), { method: 'GET' })
  },

  /** 导出（PDF/文件链接由服务端生成） */
  exportFile(reportId: string) {
    return http<ReportExportRaw>(`${path(reportId)}/export`, { method: 'GET' })
  }
}
