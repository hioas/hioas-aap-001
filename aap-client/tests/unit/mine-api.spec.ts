/**
 * 序号 21【工作台与我的】我的页（page-21-2）— 接口层单测（切片 2）
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md（前缀 /api/v1）
 *   Payment   /payments                     ← 钱包三金额的数据源（**无汇总 schema → missing-prd**）
 *   Report    /reports                      ← 「检测报告 N 份」计数（本页新增 list）
 *   Contract  /contracts                    ← 「我的合同 待签署 N」计数（本页新增 list）
 *   其余计数与头部复用既有接口：/provider/profile、/quotes、/credentials、/notifications
 *
 * ⚠️ 18-API 只列路径未列方法/查询参数 → GET 与 status/unread/page/pageSize 为 REST 语义推断（missing-prd）。
 */
import { describe, expect, it } from 'vitest'
import { contractApi } from '@/api/contract'
import { paymentApi } from '@/api/payment'
import { reportApi } from '@/api/report'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const req = (index = 0) => getCalls('request')[index].args[0] as Record<string, unknown>

describe('序号 21 · paymentApi.list（GET /api/v1/payments，钱包数据源）', () => {
  it('路径 /api/v1/payments + 方法 GET + 分页参数', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    await paymentApi.list({ page: 1, pageSize: 20 })
    expect(req().url).toBe('/api/v1/payments')
    expect(req().method).toBe('GET')
    expect(req().data).toMatchObject({ page: 1, pageSize: 20 })
  })

  it('响应体原样返回（含可选钱包汇总字段）', async () => {
    pushResponse(ok({ available_balance: 12860, pending_settlement: 3240, total_settled: 86420, items: [] }))
    const res = await paymentApi.list()
    expect(res.available_balance).toBe(12860)
    expect(res.pending_settlement).toBe(3240)
    expect(res.total_settled).toBe(86420)
  })

  it('未传参数时不带多余查询键', async () => {
    pushResponse(ok({ items: [] }))
    await paymentApi.list()
    const data = req().data as Record<string, unknown>
    expect(Object.values(data).every((v) => v === undefined)).toBe(true)
  })
})

describe('序号 21 · reportApi.list（GET /api/v1/reports）', () => {
  it('路径 /api/v1/reports + 方法 GET + 分页参数', async () => {
    pushResponse(ok({ total: 2, items: [] }))
    await reportApi.list({ page: 1, pageSize: 1 })
    expect(req().url).toBe('/api/v1/reports')
    expect(req().method).toBe('GET')
    expect(req().data).toMatchObject({ page: 1, pageSize: 1 })
  })

  it('响应体按 { total, items } 返回', async () => {
    pushResponse(ok({ total: 2, items: [{ id: 'r1' }, { id: 'r2' }] }))
    const res = await reportApi.list({ page: 1, pageSize: 1 })
    expect(res.total).toBe(2)
    expect(res.items?.length).toBe(2)
  })

  it('详情接口不受影响（同一 api 对象）', async () => {
    pushResponse(ok({ id: 'r1' }))
    await reportApi.detail('r1')
    expect(req().url).toBe('/api/v1/reports/r1')
  })
})

describe('序号 21 · contractApi.list（GET /api/v1/contracts）', () => {
  it('路径 /api/v1/contracts + 方法 GET + status 过滤（待签署计数口径）', async () => {
    pushResponse(ok({ total: 1, items: [] }))
    await contractApi.list({ page: 1, pageSize: 1, status: 'PENDING_SIGN' })
    expect(req().url).toBe('/api/v1/contracts')
    expect(req().method).toBe('GET')
    expect(req().data).toMatchObject({ page: 1, pageSize: 1, status: 'PENDING_SIGN' })
  })

  it('不带 status 时查询体里不出现该键', async () => {
    pushResponse(ok({ items: [] }))
    await contractApi.list()
    expect((req().data as Record<string, unknown>).status).toBeUndefined()
  })

  it('响应体按 { total, items } 返回', async () => {
    pushResponse(ok({ total: 1, items: [{ id: 'c1', status: 'PENDING_SIGN' }] }))
    const res = await contractApi.list({ status: 'PENDING_SIGN' })
    expect(res.total).toBe(1)
    expect(res.items?.[0].id).toBe('c1')
  })

  it('详情接口不受影响（同一 api 对象）', async () => {
    pushResponse(ok({ id: 'c1', status: 'PENDING_SIGN' }))
    await contractApi.detail('c1')
    expect(req().url).toBe('/api/v1/contracts/c1')
  })
})
