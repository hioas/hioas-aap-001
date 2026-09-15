/**
 * 序号 8【报价管理】报价单列表（page-8-2）— 接口层单测
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Quote」Tag → /quotes、/{quoteId}（前缀 /api/v1）
 * 通用约定：18-API §通用约定（分页 page/pageSize 默认 20 上限 200；错误结构 ApiError code+message+traceId）
 * ⚠️ 18-API 卡片只列路径未列方法/查询参数 → GET/DELETE 与 status 过滤为 REST 语义推断（记 missing-prd）。
 */
import { describe, expect, it } from 'vitest'
import { quoteApi } from '@/api/quote'
import { ApiError } from '@/api/http'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

describe('序号 8 · quoteApi.list（GET /api/v1/quotes）', () => {
  it('传分页参数，路径为 /api/v1/quotes + GET', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await quoteApi.list({ page: 1, pageSize: 10 })
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/quotes')
    expect(req.method).toBe('GET')
    expect(req.data).toMatchObject({ page: 1, pageSize: 10 })
  })

  it('不带状态时请求体里没有 status（=「全部」chip）', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await quoteApi.list({ page: 1, pageSize: 10 })
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect((req.data as Record<string, unknown>).status).toBeUndefined()
  })

  it('带状态时按逗号拼接（REVIEWING 归入「已提交」）', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await quoteApi.list({ page: 1, pageSize: 10, status: ['SUBMITTED', 'REVIEWING'] })
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect((req.data as Record<string, unknown>).status).toBe('SUBMITTED,REVIEWING')
  })

  it('响应体按 { total, items } 返回', async () => {
    pushResponse(ok({ total: 5, items: [{ id: 'q1', quote_no: 'QT-1' }] }))
    const res = await quoteApi.list({ page: 1, pageSize: 10 })
    expect(res.total).toBe(5)
    expect(res.items).toHaveLength(1)
  })

  it('业务失败（E-xxxx）抛 ApiError，不吞错', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1902', message: '登录已过期' } })
    await expect(quoteApi.list({ page: 1, pageSize: 10 })).rejects.toBeInstanceOf(ApiError)
  })
})

describe('序号 8 · quoteApi.remove（DELETE /api/v1/quotes/{quoteId}）', () => {
  it('路径带 quoteId + 方法 DELETE', async () => {
    pushResponse(ok({}))
    await quoteApi.remove('q1')
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/quotes/q1')
    expect(req.method).toBe('DELETE')
  })

  it('quoteId 会做 URI 编码（防注入）', async () => {
    pushResponse(ok({}))
    await quoteApi.remove('q 1/2')
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/quotes/q%201%2F2')
  })

  it('失败抛 ApiError（页面据此提示并不刷新列表）', async () => {
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    await expect(quoteApi.remove('q1')).rejects.toBeInstanceOf(ApiError)
  })
})
