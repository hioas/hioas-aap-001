/**
 * 凭证接口 — 依据 18-API设计OpenAPI.md「Credential」Tag
 *   GET  /credentials            列表（前缀 /api/v1；分页 page/pageSize 默认 20 上限 200）
 *   GET  /credentials/{id}       详情（18-API 只列路径未列方法 → 方法按 REST 语义推断，台账记「方法为推断」）
 *   PUT  /credentials/{id}       保存（同上，保存草稿/提交前的落库）
 *   POST /credentials/{id}/precheck  提交检测（路径与语义见 18-API；09-PRD §5「提交凭证后创建 DetectionJob 入队」）
 *
 * 响应字段见 src/utils/credential-form-model.ts / credentials-model.ts 顶部说明
 * （字段级 schema 未在 18-API 定义，字段名一律取 15-数据字典，已记台账 missing-prd）。
 *
 * 未接线（本页不调用，留待对应页面，不臆造）：
 *   POST /credentials、GET /credentials/{id}/precheck/latest、
 *   POST /credentials/{id}/reveal（超管二次验证）
 */
import { http } from './http'
import type { CredentialListRaw } from '@/utils/credentials-model'
import type { CredentialDetailRaw, CredentialSavePayload } from '@/utils/credential-form-model'

export type { CredentialListRaw, CredentialRowRaw } from '@/utils/credentials-model'
export type { CredentialDetailRaw, CredentialSavePayload } from '@/utils/credential-form-model'

/** 预检（提交检测）响应：字段级 schema 未在 18-API 定义 → 只取已声明的 job 标识，缺省不编造 */
export interface PrecheckResultRaw {
  job_id?: string
  jobId?: string
  detection_job_id?: string
  status?: string
  /**
   * 预检探到的**上游模型清单**（后端真打 `{base_url}/models`，见 `CredentialViews.PrecheckResult.models`）。
   *
   * ⚠️ 缺陷 10（2026-09-19 H5 联调发现）：此前**没有声明这个字段**，页面也从不消费它 →
   *   凭证 `model_list` 永远为空 → 报价单创建时「按凭证实时带出」带不出任何模型
   *   → **供应商无法报价**（H5 链路实测卡死在这一步）。
   *   模型清单由后台接口提供，前端必须写回凭证。
   */
  models?: string[]
}

const path = (id: string) => `/credentials/${encodeURIComponent(id)}`

export const credentialApi = {
  /**
   * 新建凭证（CRED-02）。契约见 `docs/backend/json-schema/requests/credential-create.schema.json`
   * （required = `api_key` + `base_url`）。
   *
   * ⚠️ 联调发现（2026-09-19）：此前前端**只声明了 list/detail/PUT/precheck，漏了 create**，
   *   凭证 id 只能靠页面 query/storage 传入 → **小程序/H5 内用户根本无法新建凭证**，
   *   凭证列表恒空，检测/报告/报价/合同/打款全链路不可达。
   */
  create(payload: CredentialSavePayload) {
    return http<CredentialDetailRaw>('/credentials', {
      method: 'POST',
      data: payload as unknown as Record<string, unknown>
    })
  },

  /** 凭证列表（最近接入优先） */
  list(params?: { page?: number; pageSize?: number }) {
    return http<CredentialListRaw>('/credentials', { method: 'GET', data: params })
  },

  /** 凭证详情（页面 4 表单回填） */
  detail(id: string) {
    return http<CredentialDetailRaw>(path(id), { method: 'GET' })
  },

  /** 保存凭证（草稿） */
  save(id: string, payload: CredentialSavePayload) {
    return http<CredentialDetailRaw>(path(id), { method: 'PUT', data: payload as unknown as Record<string, unknown> })
  },

  /** 提交检测（预检 → 服务端按 09-PRD §5 创建 DetectionJob 入队） */
  precheck(id: string) {
    return http<PrecheckResultRaw>(`${path(id)}/precheck`, { method: 'POST' })
  }
}
