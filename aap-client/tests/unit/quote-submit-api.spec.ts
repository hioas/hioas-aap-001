/**
 * 序号 12「报价预览与提交 2」报价单详情 + 提交接口接线用例（TDD 切片 2，先红）
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Quote」
 *   路径（原文）：/quotes、/{quoteId}、/{quoteId}/items、/items/{itemId}、/{quoteId}/submit、/withdraw、/versions、/compile-preview
 *   ⚠️ 该卡片只列路径未列方法与请求体 → GET 详情 / POST 提交为 REST 语义推断（missing-prd，与序号 8/9/11 同一缺口）。
 *   `/quotes/{quoteId}/submit` **无请求体 schema** → 本实现不发请求体（确认勾选只当前端门禁）。
 * 业务真源：10-PRD §4.1 状态机 DRAFT→SUBMITTED；17-spec E-1601 状态非法流转（服务端拒绝，前端透传 message）
 * 通用约定（18-API）：统一响应 {code,message,data}；金额单位 USD/1M tokens
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { quoteApi } from '@/api/quote'
import { ApiError } from '@/api/http'
import { getCalls, pushResponse, resetUniMock } from '../setup'

function lastRequest() {
  return getCalls('request').at(-1)?.args[0] as Record<string, unknown>
}

describe('quoteApi.detail（GET /api/v1/quotes/{quoteId}）', () => {
  beforeEach(() => resetUniMock())

  it('取报价单详情（含明细行）→ GET /api/v1/quotes/q7', async () => {
    pushResponse({
      statusCode: 200,
      data: { code: '0', message: 'ok', data: { quote_id: 'q7', status: 'DRAFT', items: [] } }
    })
    const res = await quoteApi.detail('q7')
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/quotes/q7')
    expect(options.method).toBe('GET')
    expect(res).toEqual({ quote_id: 'q7', status: 'DRAFT', items: [] })
  })

  it('quoteId 做 URL 编码', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: {} } })
    await quoteApi.detail('q/7')
    expect(lastRequest().url).toBe('/api/v1/quotes/q%2F7')
  })
})

describe('quoteApi.submit（POST /api/v1/quotes/{quoteId}/submit）', () => {
  beforeEach(() => resetUniMock())

  it('提交报价单 → POST /api/v1/quotes/q7/submit，且**不带请求体**（无 schema 依据）', async () => {
    pushResponse({
      statusCode: 200,
      data: { code: '0', message: 'ok', data: { quote_id: 'q7', status: 'SUBMITTED' } }
    })
    const res = await quoteApi.submit('q7')
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/quotes/q7/submit')
    expect(options.method).toBe('POST')
    expect(options.data).toBeUndefined()
    expect(res).toEqual({ quote_id: 'q7', status: 'SUBMITTED' })
  })

  it('quoteId 做 URL 编码', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: {} } })
    await quoteApi.submit('q/7')
    expect(lastRequest().url).toBe('/api/v1/quotes/q%2F7/submit')
  })

  it('服务端 E-1601（状态非法流转）→ 抛 ApiError 且保留错误码（前端不自行判定状态）', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1601', message: '状态非法流转', data: null } })
    const pending = quoteApi.submit('q7')
    await expect(pending).rejects.toBeInstanceOf(ApiError)
    await expect(pending).rejects.toMatchObject({ code: 'E-1601' })
  })
})
