/**
 * 模型目录（M-模型管理）· 真源：AdminCatalogController + CatalogViews
 *
 *   GET  /admin/catalog/vendors              厂商列表（含停用项，供恢复）      ADM-M01
 *   POST /admin/catalog/vendors              新增厂商（Calicat page-3-1）      ADM-M02
 *   GET  /admin/catalog/models?vendorId=     模型列表（可按厂商过滤）           ADM-M03
 *   GET  /admin/catalog/models/grouped       按厂商分组（page-3 是分组列表）   ADM-M04
 *   POST /admin/catalog/models               新增模型（Calicat page-3-2）      ADM-M05
 *   PUT  /admin/catalog/models/{id}          修改模型 / 启用停用               ADM-M06
 *
 * ⚠️ 两个必须知道的约定：
 *   1. **id 是字符串**。后端雪花 ID 18 位（如 459075797691068416），
 *      超过 JS 安全整数 2^53 → 后端已按契约序列化为 string
 *      （docs/backend/json-schema/models/audit-log.schema.json：
 *       「雪花 ID（对外 string，避免 JS 精度丢失）」）。
 *      所以这里的 id 类型一律是 string，**不要 Number() 转换**，否则会打错行。
 *   2. **apiKey 只写不读**。出参只有 apiKeyMask（脱敏）；入参 apiKey 留空表示不改动，
 *      传了值后端按「轮换密钥」处理。
 */
import { request } from '@/api/http';

export interface CatalogVendor {
  id: string;
  name: string;
  vendorKey: string;
  vendorType: string;
  region: string | null;
  website: string | null;
  baseUrl: string;
  apiKeyMask: string | null;
  defaultQps: number | null;
  currency: string | null;
  enabled: boolean;
  description: string | null;
  modelCount: number;
}

export interface CatalogModel {
  id: string;
  vendorId: string;
  vendorName: string | null;
  vendorKey: string | null;
  modelName: string;
  modelUid: string;
  modelType: string;
  contextWindow: number | null;
  maxOutput: number | null;
  inputPrice: number | null;
  outputPrice: number | null;
  /** 单位口径由后端显式带出（设计标 元/1K tokens）—— 不自行换算，见 D-ADM-4 */
  priceUnit: string;
  capabilities: string[];
  baseUrl: string | null;
  enabled: boolean;
  remark: string | null;
}

export interface CatalogVendorGroup {
  vendor: CatalogVendor;
  models: CatalogModel[];
}

export interface VendorPayload {
  name: string;
  vendorKey: string;
  vendorType: string;
  region?: string;
  website?: string;
  baseUrl: string;
  apiKey?: string;
  defaultQps?: number | null;
  currency?: string;
  enabled?: boolean;
  description?: string;
}

export interface ModelPayload {
  vendorId: string;
  modelName: string;
  modelUid: string;
  modelType: string;
  contextWindow?: number | null;
  maxOutput?: number | null;
  inputPrice?: number | null;
  outputPrice?: number | null;
  capabilities?: string[];
  baseUrl?: string;
  apiKey?: string;
  enabled?: boolean;
  remark?: string;
}

/** 设计稿 page-3-1「厂商类型」三个单选（文案逐字取自 design） */
export const VENDOR_TYPES = [
  { value: 'DIRECT', label: '官方直连' },
  { value: 'THIRD_PARTY', label: '第三方代理' },
  { value: 'SELF_GATEWAY', label: '自建网关' }
] as const;

/** 设计稿 page-3-1「所属地区」 */
export const VENDOR_REGIONS = ['中国', '美国', '欧洲', '其他'] as const;

/** 设计稿 page-3-2「模型类型」（对话 / 推理 / 向量 / 图像 / 语音） */
export const MODEL_TYPES = [
  { value: 'CHAT', label: '对话' },
  { value: 'REASONING', label: '推理' },
  { value: 'EMBEDDING', label: '向量' },
  { value: 'IMAGE', label: '图像' },
  { value: 'AUDIO', label: '语音' }
] as const;

/** 设计稿 page-3-2「能力标签」（多选，用于路由与能力筛选） */
export const CAPABILITIES = [
  { value: 'FUNCTION_CALL', label: '函数调用' },
  { value: 'VISION', label: '视觉理解' },
  { value: 'JSON_MODE', label: 'JSON 模式' },
  { value: 'STREAM', label: '流式输出' },
  { value: 'LONG_TEXT', label: '长文本' },
  { value: 'DEEP_REASONING', label: '深度推理' }
] as const;

export const catalogApi = {
  listVendors: () => request<CatalogVendor[]>('/admin/catalog/vendors'),

  createVendor: (payload: VendorPayload) =>
    request<CatalogVendor>('/admin/catalog/vendors', { method: 'POST', body: payload }),

  listModels: (vendorId?: string) =>
    request<CatalogModel[]>(`/admin/catalog/models${vendorId ? `?vendorId=${encodeURIComponent(vendorId)}` : ''}`),

  listGrouped: () => request<CatalogVendorGroup[]>('/admin/catalog/models/grouped'),

  createModel: (payload: ModelPayload) =>
    request<CatalogModel>('/admin/catalog/models', { method: 'POST', body: payload }),

  updateModel: (id: string, payload: Partial<ModelPayload>) =>
    request<CatalogModel>(`/admin/catalog/models/${encodeURIComponent(id)}`, { method: 'PUT', body: payload })
};
