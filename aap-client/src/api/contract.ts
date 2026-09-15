/**
 * 合同接口 — 依据 18-API设计OpenAPI「Contract」Tag
 *   /contracts、/{id}、/contracts/{id}/file、/sign（前缀 /api/v1 · 见 src/api/http.ts）
 *
 * ⚠️ 18-API 卡片只列路径、未列方法与请求体 schema（missing-prd，已记台账序号 15）：
 *   - detail/file 取 GET、sign 取 POST（REST 语义推断）；
 *   - sign 的请求体由调用方决定（缺省不带字段，同序号 12 提交报价的口径）；
 *   - /sign 在卡片里是独立条目，按 REST 语义挂到 `/contracts/{id}/sign`（推断）。
 *
 * 序号 21（我的页）新增 list：
 *   GET /contracts?status=PENDING_SIGN —— 「我的合同 待签署 N」计数（10-PRD §4.2 状态机 PENDING_SIGN）。
 *   ⚠️ 合同页把 CREATED 与 PENDING_SIGN 都显示为「待签署」（src/utils/contract-model.ts STATUS_LABELS），
 *      是否合并计数待拍板 → 已记台账序号 21。
 */
import { http } from './http'
import type { ContractRaw } from '@/utils/contract-model'

export interface ContractListItemRaw {
  id?: string
  contract_id?: string
  status?: string
  [key: string]: unknown
}

/** 合同列表响应（字段级 schema 未在 18-API 定义 → 只取计数与标识） */
export interface ContractListRaw {
  total?: number
  items?: ContractListItemRaw[]
  list?: ContractListItemRaw[]
  records?: ContractListItemRaw[]
}

export interface ContractListParams {
  page?: number
  pageSize?: number
  status?: string
}

export interface ContractFileResult {
  url?: string
  file_url?: string
  file_name?: string
}

export const contractApi = {
  /** 合同列表（序号 21 待签署计数；画布无合同列表页 → 不渲染列表） */
  list(params?: ContractListParams): Promise<ContractListRaw> {
    const data: Record<string, unknown> = { page: params?.page, pageSize: params?.pageSize }
    if (params?.status) data.status = params.status
    return http<ContractListRaw>('/contracts', { method: 'GET', data })
  },

  /** 合同详情（本页取数主接口） */
  detail(contractId: string): Promise<ContractRaw> {
    return http<ContractRaw>(`/contracts/${contractId}`)
  },

  /** 合同文件（PDF 下载按钮） */
  file(contractId: string): Promise<ContractFileResult> {
    return http<ContractFileResult>(`/contracts/${contractId}/file`)
  },

  /** 发起签署 */
  sign(contractId: string, data?: Record<string, unknown>): Promise<unknown> {
    return http<unknown>(`/contracts/${contractId}/sign`, { method: 'POST', data })
  }
}
