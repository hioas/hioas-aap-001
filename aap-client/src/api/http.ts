/**
 * HTTP 客户端 — 依据 18-API设计OpenAPI「通用约定」+ 17-spec §9 错误码表
 * - 路径前缀 /api/v1
 * - 统一响应 {"code":"0|E-xxxx","message":"...","data":{}}
 * - 401 → E-1902（未认证），清除本地 token
 * - 网络层失败 → E-2001
 */

export const API_BASE = '/api/v1'
export const TOKEN_KEY = 'aap_token'

export class ApiError extends Error {
  code: string
  traceId?: string
  details?: unknown

  constructor(code: string, message: string, traceId?: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.traceId = traceId
    this.details = details
  }
}

export interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  traceId?: string
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  data?: Record<string, unknown> | unknown
  header?: Record<string, string>
  /** 是否附带 Authorization（默认附带） */
  auth?: boolean
}

export function getToken(): string {
  try {
    return (uni.getStorageSync(TOKEN_KEY) as string) || ''
  } catch {
    return ''
  }
}

export function setToken(token: string): void {
  uni.setStorageSync(TOKEN_KEY, token)
}

export function clearToken(): void {
  try {
    uni.removeStorageSync(TOKEN_KEY)
  } catch {
    /* 忽略：清理失败不影响主流程 */
  }
}

export function http<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', data, header = {}, auth = true } = options
  const token = auth ? getToken() : ''
  const finalHeader: Record<string, string> = {
    'Content-Type': 'application/json',
    ...header
  }
  if (token) finalHeader.Authorization = `Bearer ${token}`

  return new Promise<T>((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
      method,
      data: data as Record<string, unknown>,
      header: finalHeader,
      success: (res) => {
        const status = (res as { statusCode?: number }).statusCode ?? 0
        const body = (res as { data?: ApiEnvelope<T> }).data

        if (status === 401) {
          clearToken()
          reject(new ApiError('E-1902', body?.message || '登录已过期，请重新登录'))
          return
        }
        if (status >= 400) {
          reject(new ApiError(body?.code || 'E-2001', body?.message || `请求失败(${status})`))
          return
        }
        if (!body || typeof body.code !== 'string') {
          reject(new ApiError('E-2001', '响应格式非法'))
          return
        }
        if (body.code !== '0') {
          reject(new ApiError(body.code, body.message || '请求失败', body.traceId, undefined))
          return
        }
        resolve(body.data)
      },
      fail: () => {
        reject(new ApiError('E-2001', '网络异常，请稍后重试'))
      }
    })
  })
}
