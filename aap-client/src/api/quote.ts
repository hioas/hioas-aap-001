/**
 * 报价单接口 — 依据 18-API设计OpenAPI.md「Quote」Tag
 *   路径（18-API 原文）：/quotes、/{quoteId}、/{quoteId}/items、/items/{itemId}、
 *   /{quoteId}/submit、/withdraw、/versions、/compile-preview（前缀 /api/v1）
 *
 * 本页（序号 8 报价单列表）只接线两条：
 *   GET    /quotes           列表（分页 page/pageSize 默认 20 上限 200）
 *   DELETE /quotes/{quoteId} 删除（设计稿操作行「删除」；PRD 10 §4.1 的「作废 VOID」口径差异已记台账待拍板）
 *
 * ⚠️ 18-API 卡片只列路径、未列方法与查询参数 → 方法（GET/DELETE）与 status 过滤值为 REST 语义推断（missing-prd）。
 * 未接线（留待对应页面，不臆造）：/{quoteId}/items、/{quoteId}/submit、/withdraw、/versions、/compile-preview。
 */
import { http } from './http'
import type { QuoteListRaw } from '@/utils/quotes-model'

export type { QuoteListRaw, QuoteRowRaw } from '@/utils/quotes-model'

export interface QuoteListParams {
  page?: number
  pageSize?: number
  /** 设计 5 个状态 chip 的过滤值集合；「全部」不传（参数名与取值集合为推断，记 missing-prd） */
  status?: string[]
}

const path = (id: string) => `/quotes/${encodeURIComponent(id)}`

export const quoteApi = {
  /** 报价单列表 */
  list(params?: QuoteListParams) {
    const data: Record<string, unknown> = { page: params?.page, pageSize: params?.pageSize }
    if (params?.status && params.status.length) data.status = params.status.join(',')
    return http<QuoteListRaw>('/quotes', { method: 'GET', data })
  },

  /** 删除报价单（设计稿「删除」；二次确认在页面侧） */
  remove(id: string) {
    return http<unknown>(path(id), { method: 'DELETE' })
  }
}
