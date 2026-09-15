/**
 * 序号 20【合同与通知】站内信列表（page-20-2）— 接口层单测（切片 2）
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Audit/Notification」Tag
 *   → /notifications（列表）、/notifications/{id}/read（标记已读）（前缀 /api/v1）
 * 通用约定：分页 page/pageSize（默认 20 上限 200）；错误结构 ApiError（code+message+traceId）
 * ⚠️ 18-API 只列路径未列方法/参数 → GET/POST 与 unread/category 过滤为 REST 语义推断（missing-prd）。
 */
import { describe, expect, it } from 'vitest'
import { notificationApi } from '@/api/notification'
import { ApiError } from '@/api/http'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

describe('序号 20 · notificationApi.list（GET /api/v1/notifications）', () => {
  it('路径 /api/v1/notifications + 方法 GET + 分页参数', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await notificationApi.list({ page: 1, pageSize: 20 })
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/notifications')
    expect(req.method).toBe('GET')
    expect(req.data).toMatchObject({ page: 1, pageSize: 20 })
  })

  it('「全部」chip 不带筛选参数', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await notificationApi.list({ page: 1, pageSize: 20 })
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    const data = req.data as Record<string, unknown>
    expect(data.unread).toBeUndefined()
    expect(data.category).toBeUndefined()
  })

  it('「未读」chip → unread=true', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await notificationApi.list({ page: 1, pageSize: 20, unread: 'true' })
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect((req.data as Record<string, unknown>).unread).toBe('true')
  })

  it('「订单」chip → category=ORDER', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await notificationApi.list({ page: 1, pageSize: 20, category: 'ORDER' })
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect((req.data as Record<string, unknown>).category).toBe('ORDER')
  })

  it('响应体按 { total, items } 返回', async () => {
    pushResponse(ok({ total: 3, items: [{ id: 'n1', title: 'T' }] }))
    const res = await notificationApi.list({ page: 1, pageSize: 20 })
    expect(res.total).toBe(3)
    expect(res.items).toHaveLength(1)
  })

  it('业务失败（E-xxxx）抛 ApiError，不吞错', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1902', message: '登录已过期' } })
    await expect(notificationApi.list({ page: 1, pageSize: 20 })).rejects.toBeInstanceOf(ApiError)
  })
})

describe('序号 20 · notificationApi.markRead（POST /api/v1/notifications/{id}/read）', () => {
  it('路径带 id + 方法 POST', async () => {
    pushResponse(ok({}))
    await notificationApi.markRead('n1')
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/notifications/n1/read')
    expect(req.method).toBe('POST')
  })

  it('id 会做 URI 编码（防注入）', async () => {
    pushResponse(ok({}))
    await notificationApi.markRead('n 1/2')
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/notifications/n%201%2F2/read')
  })

  it('失败抛 ApiError（页面据此提示且不误标已读）', async () => {
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    await expect(notificationApi.markRead('n1')).rejects.toBeInstanceOf(ApiError)
  })
})
