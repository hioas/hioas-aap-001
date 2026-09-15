/**
 * 序号 15【合同与通知】合同签署 2（page-15-2）— 合同接口（TDD 切片 2，先红）
 *
 * 接口真源：18-API「Contract」Tag → `/contracts`、`/{id}`、`/contracts/{id}/file`、`/sign`（前缀 /api/v1）。
 * ⚠️ 18-API 卡片只列路径、未列方法与字段级 schema → 方法（GET/POST）与请求体为 REST 语义推断（missing-prd，记台账）。
 */
import { describe, expect, it } from 'vitest'
import { contractApi } from '@/api/contract'
import { pushResponse, getCalls } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

function requests() {
  return getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
}

describe('序号 15 · contractApi', () => {
  it('detail → GET /api/v1/contracts/c1', async () => {
    pushResponse(ok({ contract_no: 'CT-1' }))
    const data = await contractApi.detail('c1')
    expect(requests()).toHaveLength(1)
    expect(requests()[0].url).toBe('/api/v1/contracts/c1')
    expect(requests()[0].method).toBe('GET')
    expect(data).toEqual({ contract_no: 'CT-1' })
  })

  it('file → GET /api/v1/contracts/c1/file', async () => {
    pushResponse(ok({ url: 'https://cdn/x.pdf' }))
    await contractApi.file('c1')
    expect(requests()[0].url).toBe('/api/v1/contracts/c1/file')
    expect(requests()[0].method).toBe('GET')
  })

  it('sign → POST /api/v1/contracts/c1/sign', async () => {
    pushResponse(ok({ status: 'SUPPLIER_SIGNED' }))
    await contractApi.sign('c1')
    expect(requests()[0].url).toBe('/api/v1/contracts/c1/sign')
    expect(requests()[0].method).toBe('POST')
  })

  it('sign 透传请求体（18-API 无请求体 schema → 由调用方决定，缺省不带字段）', async () => {
    pushResponse(ok({}))
    await contractApi.sign('c1', { channel: 'OFFLINE' })
    expect(requests()[0].data).toEqual({ channel: 'OFFLINE' })
  })

  it('业务错误码 → 抛 ApiError（message 用服务端原文，不吞错）', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1601', message: '状态非法流转' } })
    await expect(contractApi.sign('c1')).rejects.toMatchObject({ code: 'E-1601', message: '状态非法流转' })
  })
})
