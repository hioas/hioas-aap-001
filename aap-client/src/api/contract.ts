/**
 * 合同接口 — 依据 18-API设计OpenAPI「Contract」Tag
 *   /contracts、/{id}、/contracts/{id}/file、/sign（前缀 /api/v1 · 见 src/api/http.ts）
 *
 * ⚠️ 18-API 卡片只列路径、未列方法与请求体 schema（missing-prd，已记台账序号 15）：
 *   - detail/file 取 GET、sign 取 POST（REST 语义推断）；
 *   - sign 的请求体由调用方决定（缺省不带字段，同序号 12 提交报价的口径）；
 *   - /sign 在卡片里是独立条目，按 REST 语义挂到 `/contracts/{id}/sign`（推断）。
 */
import { http } from './http'
import type { ContractRaw } from '@/utils/contract-model'

export interface ContractFileResult {
  url?: string
  file_url?: string
  file_name?: string
}

export const contractApi = {
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
