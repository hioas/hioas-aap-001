/**
 * 接口基址解析 —— 小程序前后端联调的关键分歧点
 *
 * 背景（真实缺陷，2026-09-19 联调发现）：
 *   `src/api/http.ts` 原先把基址硬编码为 `'/api/v1'`（相对路径）。
 *   H5 能跑通，是因为 dev server 的 `server.proxy` 把 `/api` 反代到 aap-server:8084；
 *   小程序里 `uni.request` 直接落到 `wx.request`，**相对 URL 一律失败**（request:fail invalid url），
 *   且小程序运行时不存在 proxy。
 *   → 必须按平台解析：H5 用相对路径（同源/反代），小程序用绝对 URL。
 *
 * 平台判据：`uni.getSystemInfoSync().uniPlatform`
 *   实测产物：H5 = "web"，mp-weixin = "mp-weixin"（见 dist/build/mp-weixin/common/vendor.js）
 */
import { describe, expect, it } from 'vitest'
import { MP_DEV_API_BASE, resolveApiBase } from '@/api/base-url'

describe('接口基址解析（小程序联调）', () => {
  it('H5（uniPlatform=web）用相对路径，交由 dev server 反代', () => {
    expect(resolveApiBase(undefined, 'web')).toBe('/api/v1')
  })

  it('小程序（uniPlatform=mp-weixin）必须解析为绝对 URL', () => {
    const base = resolveApiBase(undefined, 'mp-weixin')
    expect(base).toBe(MP_DEV_API_BASE)
    expect(/^https?:\/\//.test(base)).toBe(true)
  })

  it('构建期 VITE_API_BASE 优先于平台默认（生产小程序指向 https 域名）', () => {
    expect(resolveApiBase('https://api.example.com/api/v1', 'mp-weixin')).toBe(
      'https://api.example.com/api/v1'
    )
    expect(resolveApiBase('https://api.example.com/api/v1', 'web')).toBe(
      'https://api.example.com/api/v1'
    )
  })

  it('小程序拿到相对 base 直接抛错 —— 防止再次把 H5 的写法带进小程序', () => {
    expect(() => resolveApiBase('/api/v1', 'mp-weixin')).toThrow(/绝对/)
  })

  it('H5 允许相对 base（同源部署 / dev 反代）', () => {
    expect(resolveApiBase('/api/v1', 'web')).toBe('/api/v1')
  })

  it('去掉尾部斜杠，避免拼出 //auth/me', () => {
    expect(resolveApiBase('https://api.example.com/api/v1/', 'mp-weixin')).toBe(
      'https://api.example.com/api/v1'
    )
    expect(resolveApiBase('/api/v1/', 'web')).toBe('/api/v1')
  })

  it('平台未知时按 H5 处理（vitest / 未来新平台不误伤）', () => {
    expect(resolveApiBase(undefined, undefined)).toBe('/api/v1')
    expect(resolveApiBase(undefined, '')).toBe('/api/v1')
  })
})
