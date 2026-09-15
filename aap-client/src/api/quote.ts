/**
 * 报价单接口 — 依据 18-API设计OpenAPI.md「Quote」Tag
 *   路径（18-API 原文）：/quotes、/{quoteId}、/{quoteId}/items、/items/{itemId}、
 *   /{quoteId}/submit、/withdraw、/versions、/compile-preview（前缀 /api/v1）
 *
 * 本页（序号 8 报价单列表）只接线两条：
 *   GET    /quotes           列表（分页 page/pageSize 默认 20 上限 200）
 *   DELETE /quotes/{quoteId} 删除（设计稿操作行「删除」；PRD 10 §4.1 的「作废 VOID」口径差异已记台账待拍板）
 *
 * 序号 9（模型报价设置）新增两条：
 *   POST /quotes                创建报价单（主体信息；请求体键见 buildQuotePayload）
 *   POST /quotes/{quoteId}/items 写入勾选的模型明细行（只带 model_name，单价在下一步设置）
 *
 * 序号 11（模型定价-详情）新增三条：
 *   GET /quotes/items/{itemId}          取单个明细行的定价详情（页面入参 itemId）
 *   GET /quotes/{quoteId}/items         取明细行列表（无 itemId 时的回落入口，取首行）
 *   PUT /quotes/items/{itemId}          保存定价（设计稿「保存」「保存价格」两处同一动作）
 *
 * 序号 12（报价预览与提交）新增两条：
 *   GET  /quotes/{quoteId}               报价预览取数（报价单 + 明细行）
 *   POST /quotes/{quoteId}/submit        提交报价进入运营审核（10-PRD §4.1 DRAFT→SUBMITTED；**无请求体 schema** → 不发字段）
 *
 * ⚠️ 18-API 卡片只列路径、未列方法与查询参数/请求体 → 方法（GET/DELETE/POST/PUT）、查询参数与请求体均为
 *    REST 语义推断（missing-prd）。未接线（留待对应页面，不臆造）：/withdraw、/versions、/compile-preview。
 */
import { http } from './http'
import type { QuoteListRaw } from '@/utils/quotes-model'
import type { QuoteItemRaw } from '@/utils/model-pricing-model'
import type { QuoteDetailLike } from '@/utils/quote-preview-model'

export type { QuoteListRaw, QuoteRowRaw } from '@/utils/quotes-model'

/** 创建报价单响应：字段级 schema 未在 18-API 定义 → 容错读取已声明的标识（missing-prd） */
export interface QuoteCreateRaw {
  quote_id?: string
  quoteId?: string
  id?: string
  quote_no?: string
  status?: string
}

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
  },

  /**
   * 创建报价单（序号 9 保存/存为草稿）
   * 请求体键：name（推断，missing-prd）/ provider_id / credential_id（见 buildQuotePayload）
   */
  create(payload: Record<string, unknown>) {
    return http<QuoteCreateRaw>('/quotes', { method: 'POST', data: payload })
  },

  /**
   * 写入报价单明细行（序号 9 勾选的模型）
   * 本页只带 model_name —— 单价属「下一步设置单价」（设计原文），V3 输入/输出价必填在**提交**时校验。
   */
  setItems(quoteId: string, payload: { items: Array<{ model_name: string }> }) {
    return http<unknown>(`${path(quoteId)}/items`, {
      method: 'POST',
      data: payload as unknown as Record<string, unknown>
    })
  },

  /** 明细行详情（序号 11 入参 itemId；字段级 schema 未定义 → 容错读取，missing-prd） */
  getItem(itemId: string) {
    return http<QuoteItemRaw>(`/quotes/items/${encodeURIComponent(itemId)}`, { method: 'GET' })
  },

  /** 报价单下的明细行列表（序号 11 无 itemId 时的回落入口） */
  listItems(quoteId: string) {
    return http<{ items?: QuoteItemRaw[]; total?: number }>(`${path(quoteId)}/items`, { method: 'GET' })
  },

  /** 保存单个明细行的定价（设计稿「保存」与「保存价格」同一动作） */
  saveItem(itemId: string, payload: Record<string, unknown>) {
    return http<QuoteItemRaw>(`/quotes/items/${encodeURIComponent(itemId)}`, {
      method: 'PUT',
      data: payload
    })
  },

  /** 报价单详情（序号 12 报价预览取数：报价单 + 明细行；字段级 schema 未定义 → 容错读取，missing-prd） */
  detail(quoteId: string) {
    return http<QuoteDetailLike>(path(quoteId), { method: 'GET' })
  },

  /**
   * 提交报价进入运营审核（序号 12 设计稿「提交报价」）
   * 10-PRD §4.1：DRAFT→SUBMITTED（服务端做 V1–V17 全量校验，前端只做「有明细 + 已确认」门禁）；
   * 18-API 未定义请求体 → 不发送任何字段。
   */
  submit(quoteId: string) {
    return http<QuoteDetailLike>(`${path(quoteId)}/submit`, { method: 'POST' })
  }
}
