/**
 * 序号 11「模型定价-详情」明细行读写接口接线用例（TDD 切片 2）
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Quote」→ /quotes、/{quoteId}/items、/items/{itemId}（前缀 /api/v1）
 *   ⚠️ 该卡片只列路径未列方法 → GET/PUT 为 REST 语义推断（与序号 8/9 同一缺口，记 missing-prd）。
 * 业务真源：06-报价模型与计费编译规则 §1.2（八大单价，单位为 $/1M tokens 真实单价）
 *   15-数据模型「aap_quote_item：quote_id、model_name、input/output_price（≥0）、cache_read/write/write_1h_price…」
 * 通用约定（18-API）：统一响应 {code,message,data}；错误码见 17-spec（E-1401 时段重叠 / E-1403 倍率非法 → 服务端拒绝，前端透传 message）
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { quoteApi } from '@/api/quote'
import { ApiError } from '@/api/http'
import { getCalls, pushResponse, resetUniMock } from '../setup'

function lastRequest() {
  return getCalls('request').at(-1)?.args[0] as Record<string, unknown>
}

const PAYLOAD = {
  input_price: 2.5,
  output_price: 10,
  tier: 'base',
  billing_mode: '按 token',
  request_rules: [{ field: '时间', granularity: '小时', tz: 'Asia/Shanghai', op: '大于等于', value: '', multiplier: '1.0' }]
}

describe('quoteApi.getItem（GET /api/v1/quotes/items/{itemId}）', () => {
  beforeEach(() => resetUniMock())

  it('按明细行 id 取详情 → GET /api/v1/quotes/items/qi1', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: { item_id: 'qi1', model_name: 'gpt-4o' } } })
    const res = await quoteApi.getItem('qi1')
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/quotes/items/qi1')
    expect(options.method).toBe('GET')
    expect(res).toEqual({ item_id: 'qi1', model_name: 'gpt-4o' })
  })

  it('itemId 做 URL 编码', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: {} } })
    await quoteApi.getItem('qi/1')
    expect(lastRequest().url).toBe('/api/v1/quotes/items/qi%2F1')
  })
})

describe('quoteApi.listItems（GET /api/v1/quotes/{quoteId}/items）', () => {
  beforeEach(() => resetUniMock())

  it('取报价单下的明细行（无 itemId 时的回落入口）→ GET /api/v1/quotes/q9/items', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: { items: [{ item_id: 'qi1' }] } } })
    const res = await quoteApi.listItems('q9')
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/quotes/q9/items')
    expect(options.method).toBe('GET')
    expect(res).toEqual({ items: [{ item_id: 'qi1' }] })
  })
})

describe('quoteApi.saveItem（PUT /api/v1/quotes/items/{itemId}）', () => {
  beforeEach(() => resetUniMock())

  it('保存定价 → PUT /api/v1/quotes/items/qi1，请求体为模型给出的键', async () => {
    pushResponse({ statusCode: 200, data: { code: '0', message: 'ok', data: { item_id: 'qi1' } } })
    await quoteApi.saveItem('qi1', PAYLOAD)
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/quotes/items/qi1')
    expect(options.method).toBe('PUT')
    expect(options.data).toEqual(PAYLOAD)
  })

  it('服务端 E-1403（倍率非法）→ 抛 ApiError 且保留错误码（前端不自行判定）', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1403', message: '倍率非法', data: null } })
    const pending = quoteApi.saveItem('qi1', PAYLOAD)
    await expect(pending).rejects.toBeInstanceOf(ApiError)
    await expect(pending).rejects.toMatchObject({ code: 'E-1403' })
  })
})
