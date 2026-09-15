/**
 * 序号 9 报价单创建/明细行接口接线用例
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Quote」→ /quotes、/{quoteId}/items（前缀 /api/v1）
 *   ⚠️ 该卡片只列路径未列方法 → POST 为 REST 语义推断（与序号 8 的 GET/DELETE 同一缺口，记 missing-prd）。
 * 通用约定（18-API）：统一响应 {code,message,data}；错误码见 17-spec §错误码表
 *   E-1602 未通过检测报报价 → 服务端拒绝，前端只透传 message（不自行判定）。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { quoteApi } from '@/api/quote'
import { ApiError } from '@/api/http'
import { getCalls, pushResponse, resetUniMock, storage } from '../setup'
import { TOKEN_KEY } from '@/api/http'

function lastRequest() {
  const calls = getCalls('request')
  const options = calls.at(-1)?.args[0] as Record<string, unknown>
  return options
}

describe('quoteApi.create（POST /api/v1/quotes）', () => {
  beforeEach(() => resetUniMock())

  it('创建一个报价单 → POST /api/v1/quotes，请求体为视图模型给出的键', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: { quote_id: 'q9' } } })
    const res = await quoteApi.create({ name: '2024Q3 主线路报价', provider_id: 'p1', credential_id: 'c1' })
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/quotes')
    expect(options.method).toBe('POST')
    expect(options.data).toEqual({ name: '2024Q3 主线路报价', provider_id: 'p1', credential_id: 'c1' })
    expect(res).toEqual({ quote_id: 'q9' })
  })

  it('带 token 时附带 Authorization（与既有接口一致）', async () => {
    storage.set(TOKEN_KEY, 'tk-9')
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: {} } })
    await quoteApi.create({ name: 'a' })
    const header = lastRequest().header as Record<string, string>
    expect(header.Authorization).toBe('Bearer tk-9')
  })

  it('服务端 E-1602（未通过检测报报价）→ 抛 ApiError 且保留错误码', async () => {
    pushResponse({
      statusCode: 200,
      data: { code: 'E-1602', message: '未通过检测的凭证不可报价', data: null }
    })
    const pending = quoteApi.create({ name: 'a' })
    await expect(pending).rejects.toBeInstanceOf(ApiError)
    await expect(pending).rejects.toMatchObject({ code: 'E-1602' })
  })
})

describe('quoteApi.setItems（POST /api/v1/quotes/{quoteId}/items）', () => {
  beforeEach(() => resetUniMock())

  it('写入勾选的模型明细行 → POST /api/v1/quotes/q9/items', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: {} } })
    await quoteApi.setItems('q9', { items: [{ model_name: 'gpt-4o' }] })
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/quotes/q9/items')
    expect(options.method).toBe('POST')
    expect(options.data).toEqual({ items: [{ model_name: 'gpt-4o' }] })
  })

  it('quoteId 做 URL 编码（防注入到路径）', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: {} } })
    await quoteApi.setItems('q/9', { items: [] })
    expect(lastRequest().url).toBe('/api/v1/quotes/q%2F9/items')
  })
})
