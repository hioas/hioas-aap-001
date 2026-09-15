/**
 * 账号接入接口 — 依据 18-API设计OpenAPI「Auth」Tag
 * POST /auth/sms/send、/auth/sms/login、/auth/wechat/login、/auth/refresh、/auth/logout、GET /auth/me
 */
import { clearToken, http } from './http'

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

  login(payload: SmsLoginReq) {
    return http<LoginResult>('/auth/sms/login', { method: 'POST', data: payload, auth: false })
  },

  wechatLogin(payload: WechatLoginReq) {
    return http<LoginResult>('/auth/wechat/login', { method: 'POST', data: payload, auth: false })
  },

  refresh(refreshToken: string) {
    return http<LoginResult>('/auth/refresh', {
      method: 'POST',
      data: { refreshToken },
      auth: false
    })
  },

  async logout() {
    try {
      await http<null>('/auth/logout', { method: 'POST' })
    } finally {
      clearToken()
    }
  },

  me() {
    return http<MeResult>('/auth/me')
  }
}
