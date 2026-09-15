/**
 * 凭证接口 — 依据 18-API设计OpenAPI.md「Credential」Tag
 * GET /credentials（前缀 /api/v1）：分页 page/pageSize（默认 20 上限 200）
 * 响应字段见 src/utils/credentials-model.ts 顶部说明（字段级 schema 未在 18-API 定义，已记台账 missing-prd）。
 *
 * 未接线（本页不调用，留待对应页面，不臆造）：
 *   POST /credentials、GET /credentials/{id}、POST /credentials/{id}/precheck、
 *   GET /credentials/{id}/precheck/latest、POST /credentials/{id}/reveal（超管二次验证）
 */
import { http } from './http'
import type { CredentialListRaw } from '@/utils/credentials-model'

export type { CredentialListRaw, CredentialRowRaw } from '@/utils/credentials-model'

export const credentialApi = {
  /** 凭证列表（最近接入优先） */
  list(params?: { page?: number; pageSize?: number }) {
    return http<CredentialListRaw>('/credentials', { method: 'GET', data: params })
  }
}
