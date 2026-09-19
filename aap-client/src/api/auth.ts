/**
 * 账号接入接口 — 依据 18-API设计OpenAPI「Auth」Tag
 * POST /auth/sms/send、/auth/sms/login、/auth/wechat/login、/auth/refresh、/auth/logout、GET /auth/me
 */
import { clearRefreshToken, clearToken, http, persistTokenPair } from './http'

export interface SmsSendReq {
  phone: string
  captcha: string
}

export interface SmsLoginReq {
  phone: string
  smsCode: string
}

export interface WechatLoginReq {
  code: string
}

/** 17-spec §4 Role / §3 ProviderAccount */
export type Role = 'SUPPLIER' | 'PROVIDER' | 'BIZ_OPERATOR' | 'TECH_OPS' | 'SUPER_ADMIN'

export interface LoginResult {
  token: string
  /**
   * 续期令牌。实测后端**同时**返回 snake_case 与 camelCase 两种写法
   * （`refresh_token` / `refreshToken`），两者都声明，读取时容错。
   */
  refresh_token?: string
  refreshToken?: string
  /** access token 有效期（秒），实测响应含该字段 */
  expires_in?: number
  role: Role
  providerId?: string
  /** 供应商生命周期状态（01-PRD总览 §4） */
  status?: string
}

export interface MeResult {
  phone: string
  role: Role
  providerId?: string
  status?: string
  providerCode?: string
}

export const authApi = {
  sendSms(payload: SmsSendReq) {
    return http<{ ttl: number }>('/auth/sms/send', { method: 'POST', data: payload, auth: false })
  },

  async login(payload: SmsLoginReq) {
    const res = await http<LoginResult>('/auth/sms/login', {
      method: 'POST',
      data: payload,
      auth: false
    })
    // 双 token 一起落盘：refresh 是轮换式的，只存 access 会让续期失效
    persistTokenPair(res)
    return res
  },

  async wechatLogin(payload: WechatLoginReq) {
    const res = await http<LoginResult>('/auth/wechat/login', {
      method: 'POST',
      data: payload,
      auth: false
    })
    persistTokenPair(res)
    return res
  },

  async refresh(refreshToken: string) {
    const res = await http<LoginResult>('/auth/refresh', {
      method: 'POST',
      data: { refreshToken },
      auth: false
    })
    persistTokenPair(res)
    return res
  },

  async logout() {
    try {
      await http<null>('/auth/logout', { method: 'POST' })
    } finally {
      clearToken()
      clearRefreshToken()
    }
  },

  me() {
    return http<MeResult>('/auth/me')
  }
}
