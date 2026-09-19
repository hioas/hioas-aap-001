/**
 * HTTP 客户端 — 依据 18-API设计OpenAPI「通用约定」+ 17-spec §9 错误码表
 * - 路径前缀 /api/v1
 * - 统一响应 {"code":"0|E-xxxx","message":"...","data":{}}
 * - 401 → 先用 refresh token **自动续期一次**再重试；续期不可用/失败 → 清本地 token + E-1902
 * - 网络层失败 → E-2001
 *
 * ⚠️ refresh 是**轮换式**（后端会撤销旧 token 记录，见 AuthService.refresh 注释）：
 *   续期成功后**必须把新的 access + refresh 双 token 一起落盘**，否则旧 token 立刻失效。
 *   实测教训：把 refresh 放在链路中间而不落盘新 token，会让后续请求全部 E-1902。
 */

import { currentUniPlatform, resolveApiBase } from './base-url'

/**
 * 接口基址。
 * ⚠️ 必须按平台解析：H5 可相对（dev server 反代），小程序**必须绝对 URL**
 *   —— `wx.request` 不接受相对路径，会直接 request:fail invalid url。
 *   构建门禁 `tools/check-mp-api-base.mjs` 会在产物上复核这一点。
 */
export const API_BASE = resolveApiBase(import.meta.env.VITE_API_BASE, currentUniPlatform())
export const TOKEN_KEY = 'aap_token'
export const REFRESH_TOKEN_KEY = 'aap_refresh_token'

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
  /**
   * 仅使用 18-API「通用约定」里的四种方法。
   * uni.request 的类型定义为 'GET'|'POST'|'PUT'|'DELETE'|'OPTIONS'|'HEAD'|'TRACE'|'CONNECT'，
   * 不含 PATCH —— 这里与之对齐，避免出现类型层可用、运行时不被支持的写法。
   */
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
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

export function getRefreshToken(): string {
  try {
    return (uni.getStorageSync(REFRESH_TOKEN_KEY) as string) || ''
  } catch {
    return ''
  }
}

export function setRefreshToken(token: string): void {
  uni.setStorageSync(REFRESH_TOKEN_KEY, token)
}

export function clearRefreshToken(): void {
  try {
    uni.removeStorageSync(REFRESH_TOKEN_KEY)
  } catch {
    /* 忽略 */
  }
}

/** 登录响应的 token 载荷（refresh_token/refreshToken 两种写法后端都返回，容错读取） */
export interface TokenPair {
  token: string
  refresh_token?: string
  refreshToken?: string
}

/**
 * 登录/续期成功后统一落盘。
 * 后端同时返回 snake_case 与 camelCase，两者取其一即可（缺失时保留原 refresh token）。
 */
export function persistTokenPair(pair: TokenPair): void {
  setToken(pair.token)
  const rt = pair.refresh_token || pair.refreshToken
  if (rt) setRefreshToken(rt)
}

/** 底层单次请求（不含续期逻辑） */
function requestOnce<T>(path: string, options: RequestOptions): Promise<T> {
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
        // uni.request 的 data 类型为 string|AnyObject|ArrayBuffer，运行时由服务端契约决定；
        // 这里只做形状校验（下方 typeof body.code 判断），不做类型断言可信化。
        const body = res.data as unknown as ApiEnvelope<T> | undefined

        if (status === 401) {
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

/** 续期中的并发去重：多个请求同时 401 时只发一次 /auth/refresh */
let renewing: Promise<string> | null = null

/** 用 refresh token 换发新 token；成功返回新 access token，失败返回空串 */
function renewToken(): Promise<string> {
  if (renewing) return renewing
  const rt = getRefreshToken()
  if (!rt) return Promise.resolve('')

  renewing = requestOnce<TokenPair>('/auth/refresh', {
    method: 'POST',
    data: { refreshToken: rt },
    auth: false
  })
    .then((pair) => {
      if (!pair?.token) return ''
      persistTokenPair(pair)
      return pair.token
    })
    .catch(() => '')
    .finally(() => {
      renewing = null
    })

  return renewing
}

/**
 * 发起请求。401 时（且该请求带鉴权）自动续期一次并重试；再失败则清 token 抛 E-1902。
 * 只重试一次（`retried` 标志），避免死循环。
 */
export async function http<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  try {
    return await requestOnce<T>(path, options)
  } catch (e) {
    const isUnauth = e instanceof ApiError && e.code === 'E-1902'
    if (!isUnauth || options.auth === false) throw e

    const fresh = await renewToken()
    if (!fresh) {
      clearToken()
      clearRefreshToken()
      throw e
    }
    try {
      return await requestOnce<T>(path, options)
    } catch (e2) {
      if (e2 instanceof ApiError && e2.code === 'E-1902') {
        clearToken()
        clearRefreshToken()
      }
      throw e2
    }
  }
}
