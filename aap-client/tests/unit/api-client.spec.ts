/**
 * 页面 1 — 接口客户端单测
 * 依据：18-API设计OpenAPI（前缀 /api/v1、Bearer、ApiError 统一结构、sms/send + sms/login）
 *       17-spec §9 错误码表（E-1001 参数校验）
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { http, ApiError } from '@/api/http'
import { authApi } from '@/api/auth'
import { getCalls, pushResponse, storage, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

describe('http 基础行为', () => {
  beforeEach(() => {
    storage.set('aap_token', 'jwt-token-1')
  })

  it('路径前缀 /api/v1，方法默认 GET', async () => {
    pushResponse(ok({ hello: 1 }))
    await http<{ hello: number }>('/auth/me')
    const [opts] = getCalls('request')[0].args as [Record<string, unknown>]
    expect(opts.url).toBe('/api/v1/auth/me')
    expect((opts.method as string) ?? 'GET').toBe('GET')
  })

  it('自动注入 Authorization: Bearer <token>', async () => {
    pushResponse(ok({}))
    await http('/auth/me')
    const [opts] = getCalls('request')[0].args as [Record<string, any>]
    expect(opts.header.Authorization).toBe('Bearer jwt-token-1')
  })

  it('code=0 时返回 data 本体', async () => {
    pushResponse(ok({ id: 7, phone: '138****8000' }))
    const res = await http<{ id: number }>('/auth/me')
    expect(res.id).toBe(7)
  })

  it('业务错误码抛 ApiError（code 原样透出，如 E-1001）', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1001', message: '参数校验失败', data: {} } })
    await expect(http('/auth/sms/send', { method: 'POST', data: {} })).rejects.toMatchObject({
      code: 'E-1001',
      message: '参数校验失败'
    })
    expect(ApiError).toBeDefined()
  })

  it('HTTP 401 视为未登录：抛 E-1902 并清除本地 token', async () => {
    pushResponse({ statusCode: 401, data: { code: 'E-1902', message: '未认证' } })
    await expect(http('/auth/me')).rejects.toMatchObject({ code: 'E-1902' })
    expect(storage.get('aap_token')).toBeUndefined()
  })

  it('网络失败抛 E-2001，不吞异常', async () => {
    setNextResponse({ statusCode: 0, data: null, fail: true })
    await expect(http('/auth/me')).rejects.toMatchObject({ code: 'E-2001' })
  })
})

describe('authApi（供应商端账号接入）', () => {
  it('sendSms -> POST /api/v1/auth/sms/send {phone, captcha}', async () => {
    pushResponse(ok({ ttl: 300 }))
    await authApi.sendSms({ phone: '13800138000', captcha: 'A7K9' })
    const [opts] = getCalls('request')[0].args as [Record<string, any>]
    expect(opts.url).toBe('/api/v1/auth/sms/send')
    expect(opts.method).toBe('POST')
    expect(opts.data).toEqual({ phone: '13800138000', captcha: 'A7K9' })
  })

  it('login -> POST /api/v1/auth/sms/login {phone, smsCode}，返回 token 与 role', async () => {
    pushResponse(ok({ token: 'jwt-abc', role: 'PROVIDER', providerId: 'AAP-P-000001' }))
    const res = await authApi.login({ phone: '13800138000', smsCode: '123456' })
    const [opts] = getCalls('request')[0].args as [Record<string, any>]
    expect(opts.url).toBe('/api/v1/auth/sms/login')
    expect(opts.data).toEqual({ phone: '13800138000', smsCode: '123456' })
    expect(res.token).toBe('jwt-abc')
    expect(res.role).toBe('PROVIDER')
  })

  it('wechatLogin -> POST /api/v1/auth/wechat/login {code}', async () => {
    pushResponse(ok({ token: 'jwt-wx', role: 'PROVIDER' }))
    await authApi.wechatLogin({ code: 'wx-code-from-stub' })
    const [opts] = getCalls('request')[0].args as [Record<string, any>]
    expect(opts.url).toBe('/api/v1/auth/wechat/login')
    expect(opts.data).toEqual({ code: 'wx-code-from-stub' })
  })

  it('me -> GET /api/v1/auth/me', async () => {
    pushResponse(ok({ phone: '138****8000', status: 'PENDING_CREDENTIAL' }))
    const me = await authApi.me()
    const [opts] = getCalls('request')[0].args as [Record<string, any>]
    expect(opts.url).toBe('/api/v1/auth/me')
    expect(me.status).toBe('PENDING_CREDENTIAL')
  })
})
