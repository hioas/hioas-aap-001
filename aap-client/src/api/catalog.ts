/**
 * 可用模型目录（供应商侧）· 真源：CatalogQueryController
 *
 *   GET /catalog/models   只返回「厂商启用 **且** 模型启用」的项（ADM 侧维护）
 *
 * ⚠️ 为什么需要这个模块：凭证页的模型清单此前只从**凭证详情**里取
 * （`raw.model_catalog` / `raw.model_list`），而凭证刚建时两者都为空 →
 * 供应商看不到任何可选模型 → 无法勾选 → 报价时带不出模型。
 * 管理端维护的模型目录（aap_model/aap_vendor）必须由**这个接口**提供给 H5 端，
 * 这正是当初补模型目录能力的目的（用户 2026-09-20 指令）。
 *
 * ⚠️ id 按字符串处理：后端雪花 ID 已按契约序列化为 string（超 JS 安全整数）。
 */
import { http } from '@/api/http'

export interface CatalogModel {
  id: string
  vendorId: string
  vendorName: string | null
  vendorKey: string | null
  modelName: string
  /** 模型标识 —— **进 model_list 的就是它** */
  modelUid: string
  modelType: string
  contextWindow: number | null
  maxOutput: number | null
  inputPrice: number | null
  outputPrice: number | null
  priceUnit: string
  capabilities: string[]
  baseUrl: string | null
  enabled: boolean
  remark: string | null
}

export const catalogApi = {
  /** 可用模型清单（仅启用项）。失败时返回空数组，由调用方决定是否提示。 */
  async availableModels(): Promise<CatalogModel[]> {
    // ⚠️ `http` 是**函数**（`http<T>(path, options)`），不是带 .get/.post 的对象 ——
    //    初版写成 http.get(...) 报 TS2339。
    const r = await http<CatalogModel[]>('/catalog/models')
    return Array.isArray(r) ? r : []
  }
}
