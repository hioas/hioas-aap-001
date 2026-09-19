/**
 * 用量统计接口 — 依据 18-API设计OpenAPI.md「Usage」Tag
 * GET /usage/hourly、/usage/summary（前缀 /api/v1）
 * 响应字段见 src/utils/workbench-model.ts 顶部说明（字段级 schema 未在 18-API 定义，已记台账 missing-prd）。
 */
import { ApiError, http } from './http'
import type { UsageSummaryRaw } from '@/utils/workbench-model'
import type { UsageOverviewRaw } from '@/utils/usage-model'

export type { UsageModelRaw, UsageSummaryRaw } from '@/utils/workbench-model'
export type { UsageOverviewRaw, UsageDailyRaw, UsageModelShareRaw, UsageCostRaw } from '@/utils/usage-model'

export const usageApi = {
  /** 本月用量汇总（工作台数据台） */
  summary(params?: { startHour?: string; endHour?: string }) {
    return http<UsageSummaryRaw>('/usage/summary', { method: 'GET', data: params })
  },

  /**
   * 用量概览页（序号 22 /pages/usage/index）：同一 /usage/summary 端点 + 月份维度。
   * 逐日趋势 / 模型占比 / 成本构成均从该响应消费（18-API 无独立端点）。
   * ⚠️ month 查询参数为 REST 语义推断（18-API 未列参数）→ 台账 missing-prd。
   */
  overview(params?: { month?: string }) {
    return http<UsageOverviewRaw>('/usage/summary', { method: 'GET', data: params })
  },

  /**
   * 小时用量（「查看逐日 / 逐模型明细」的数据源；画布无明细页 → 本页不调用）。
   *
   * ⚠️ 后端 `from`/`to` **必填**（RFC3339 UTC），实测不传直接 E-1001「from 缺失」。
   *   故这里把两者设为必填并在运行时兜底校验，避免再次出现「类型层可选、调用必失败」的接口。
   */
  hourly(params: { from: string; to: string } & Record<string, unknown>) {
    if (!params?.from) {
      throw new ApiError('E-1001', '缺少查询参数 from（RFC3339 UTC）')
    }
    if (!params?.to) {
      throw new ApiError('E-1001', '缺少查询参数 to（RFC3339 UTC）')
    }
    return http<unknown>('/usage/hourly', { method: 'GET', data: params })
  }
}
