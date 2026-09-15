/**
 * 站内信接口 — 依据 18-API设计OpenAPI.md「Audit/Notification」Tag
 *   路径（18-API 原文）：/admin/audit-logs、/notifications、/notifications/{id}/read（前缀 /api/v1）
 *
 * 本页（序号 20 站内信列表）接线两条：
 *   GET  /notifications              列表（分页 page/pageSize 默认 20 上限 200）
 *   POST /notifications/{id}/read    标记单条已读（设计稿「全部已读」＝按列表逐条调用，见页面注释）
 *
 * ⚠️ 18-API 卡片只列路径、未列方法与查询参数 → 方法（GET/POST）、查询参数名（unread/category）均为
 *    REST 语义推断（missing-prd，已记台账序号 20）。
 * ⚠️ 18-API 无「全部已读」批量接口 → 不臆造 /notifications/read-all；页面逐条调用本接口。
 */
import { http } from './http'
import type { MessageListRaw } from '@/utils/messages-model'

export type { MessageListRaw, MessageRaw } from '@/utils/messages-model'

export interface MessageListParams {
  page?: number
  pageSize?: number
  /** 「未读」chip（read_at 为空的语义；参数名与取值形式为推断） */
  unread?: string
  /** 「订单 / 系统」chip（参数名与取值集合为推断） */
  category?: string
}

const path = (id: string) => `/notifications/${encodeURIComponent(id)}`

export const notificationApi = {
  /** 站内信列表 */
  list(params?: MessageListParams) {
    const data: Record<string, unknown> = { page: params?.page, pageSize: params?.pageSize }
    if (params?.unread) data.unread = params.unread
    if (params?.category) data.category = params.category
    return http<MessageListRaw>('/notifications', { method: 'GET', data })
  },

  /** 标记单条已读 */
  markRead(id: string) {
    return http<unknown>(`${path(id)}/read`, { method: 'POST' })
  }
}
