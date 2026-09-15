/**
 * 打款/结算接口 — 依据 18-API设计OpenAPI.md「Payment」Tag
 *   /payments、/admin/payments、/admin/payments/{id}/confirm、/admin/settlements（前缀 /api/v1）
 *
 * 本页（序号 21 我的页）只用 GET /payments 作为「我的钱包」卡的数据源：
 *   可提现余额 / 待结算 / 累计结算 —— 三项金额在 22 份 PRD 零命中，18-API 也**没有钱包汇总端点**
 *   → 字段名与归属为 REST 语义推断（missing-prd，已记台账序号 21）：
 *     · 优先读响应顶层的汇总字段（available_balance / pending_settlement / total_settled 及别名）；
 *     · 缺字段时页面渲染占位「—」，**不编造 0、不在前端造汇总口径**。
 *
 * ⚠️ 「提现」按钮：18-API 无提现端点，且 02-需求澄清 One-Pager 明写「供应商侧资金结算/提现（走线下）」
 *   → 设计稿与 PRD 冲突（已记台账待拍板）；本文件**不臆造** /withdraw 之类端点，页面点击只做占位提示。
 *
 * 未接线（本页不调用，留待管理端页面，不臆造）：
 *   /admin/payments、/admin/payments/{id}/confirm、/admin/settlements。
 */
import { http } from './http'
import type { MineWalletSource } from '@/utils/mine-model'

/** 打款记录列表响应（含可选的钱包汇总字段，字段级 schema 未在 18-API 定义 → 容错读取） */
export interface PaymentListRaw extends MineWalletSource {
  total?: number
  items?: unknown[]
  list?: unknown[]
  records?: unknown[]
}

export interface PaymentListParams {
  page?: number
  pageSize?: number
}

export const paymentApi = {
  /** 打款记录列表（同时用作钱包汇总数据源） */
  list(params?: PaymentListParams) {
    return http<PaymentListRaw>('/payments', {
      method: 'GET',
      data: { page: params?.page, pageSize: params?.pageSize }
    })
  }
}
