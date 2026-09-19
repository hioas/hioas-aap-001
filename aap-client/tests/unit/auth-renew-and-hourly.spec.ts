/**
 * 联调发现的两个前端缺陷 —— 先红后绿
 *
 * 缺陷 5：`usageApi.hourly()` 允许不传参，但后端 `from`/`to` 必填（RFC3339 UTC）
 *         → 按现状调用**必然 E-1001**（实测）。
 * 缺陷 6：`authApi.refresh()` 声明了却无任何页面调用，401 分支只 `clearToken` 不续期；
 *         且 refresh 是**轮换式**（后端会撤销旧 token 记录），调用方必须落盘新 token，
 *         否则续期后旧 token 立刻失效。实测：把 refresh 放在链路中间会导致后续全部 E-1902。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import {
  ApiError,
  clearToken,
  getRefreshToken,
  getToken,
  http,
  setRefreshToken,
  setToken
} from '@/api/http'
import { usageApi } from '@/api/usage'
import { getCalls, pushResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })
const unauth = () => ({ statusCode: 401, data: { code: 'E-1902', message: '未认证或登录已过期' } })

describe('缺陷5 · usageApi.hourly 必须带 from/to', () => {
  beforeEach(() => setToken('t1'))

  it('传 from/to 时按 query 参数发出', async () => {
    pushResponse(ok({ items: [] }))
    await usageApi.hourly({ from: '2026-08-01T00:00:00Z', to: '2026-09-01T00:00:00Z' })
    const [opts] = getCalls('request')[0].args as [Record<string, any>]
    expect(opts.url).toBe('/api/v1/usage/hourly')
    expect(opts.data).toEqual({ from: '2026-08-01T00:00:00Z', to: '2026-09-01T00:00:00Z' })
  })

  it('不传 from/to 时**客户端就拦下**（不再打到后端拿 E-1001）', () => {
    // 用 as never 绕过 TS 必填约束，模拟「有人按旧签名调用」的运行时后果
    expect(() => usageApi.hourly({} as never)).toThrowError(/from/)
  })

  it('只传 from 也拦下（两个都要）', () => {
    expect(() => usageApi.hourly({ from: '2026-08-01T00:00:00Z' } as never)).toThrowError(/to/)
  })
})

describe('缺陷6 · 401 时用 refresh token 自动续期一次', () => {
  beforeEach(() => {
    clearToken()
    storage.clear()
  })

  it('登录后 refresh_token 应能落盘/回读', () => {
    setRefreshToken('rt-abc')
    expect(getRefreshToken()).toBe('rt-abc')
  })

  it('401 → 续期成功 → 落盘新 token → 重试原请求并返回结果', async () => {
    setToken('old-token')
    setRefreshToken('rt-1')
    pushResponse(unauth()) // 原请求 401
    pushResponse(ok({ token: 'new-token', refresh_token: 'rt-2' })) // /auth/refresh
    pushResponse(ok({ id: 7 })) // 重试原请求

    const res = await http<{ id: number }>('/auth/me')
    expect(res.id).toBe(7)

    const calls = getCalls('request').map((c) => (c.args[0] as Record<string, any>).url)
    expect(calls[0]).toBe('/api/v1/auth/me')
    expect(calls[1]).toBe('/api/v1/auth/refresh')
    expect(calls[2]).toBe('/api/v1/auth/me')

    // 关键：新 token 与**轮换后的新 refresh token** 都必须落盘
    expect(getToken()).toBe('new-token')
    expect(getRefreshToken()).toBe('rt-2')
    expect(storage.get('aap_token')).toBe('new-token')
  })

  it('无 refresh_token 时维持旧行为：清 token + E-1902', async () => {
    setToken('old-token')
    pushResponse(unauth())
    await expect(http('/auth/me')).rejects.toMatchObject({ code: 'E-1902' })
    expect(getToken()).toBe('')
  })

  it('续期失败（refresh 也 401）→ 清 token + E-1902，不无限重试', async () => {
    setToken('old-token')
    setRefreshToken('rt-bad')
    pushResponse(unauth()) // 原请求
    pushResponse(unauth()) // refresh 也失败
    await expect(http('/auth/me')).rejects.toMatchObject({ code: 'E-1902' })
    expect(getToken()).toBe('')
    // 只应有 2 次请求（原请求 + refresh），不得出现重试环
    expect(getCalls('request').length).toBe(2)
  })

  it('续期后重试仍 401 → 直接抛，不再续期（防死循环）', async () => {
    setToken('old-token')
    setRefreshToken('rt-1')
    pushResponse(unauth()) // 原请求
    pushResponse(ok({ token: 'new-token', refresh_token: 'rt-2' })) // refresh 成功
    pushResponse(unauth()) // 重试仍 401
    await expect(http('/auth/me')).rejects.toMatchObject({ code: 'E-1902' })
    expect(getCalls('request').length).toBe(3)
  })

  it('登录类请求（auth:false）401 不触发续期', async () => {
    setToken('old-token')
    setRefreshToken('rt-1')
    pushResponse(unauth())
    await expect(http('/auth/sms/login', { method: 'POST', auth: false })).rejects.toMatchObject({
      code: 'E-1902'
    })
    expect(getCalls('request').length).toBe(1)
  })

  it('业务错误码（如 E-1001）不触发续期', async () => {
    setToken('t')
    setRefreshToken('rt-1')
    pushResponse({ statusCode: 200, data: { code: 'E-1001', message: '参数校验失败', data: {} } })
    await expect(http('/auth/me')).rejects.toMatchObject({ code: 'E-1001' })
    expect(getCalls('request').length).toBe(1)
  })

  it('ApiError 仍是可识别类型', () => {
    expect(new ApiError('E-1902', 'x')).toBeInstanceOf(ApiError)
  })
})
