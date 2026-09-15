/**
 * 序号 10 供应商档案接口接线用例
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Provider」→ /provider/profile、/provider/qualifications、
 *   /provider/qualifications/{id}（路径前缀 /api/v1）。
 *   ⚠️ 该卡片只列路径未列方法与字段级 schema → GET / PUT / POST / DELETE 与请求体字段为 REST 语义推断，
 *      与序号 3/4/8/9 同一缺口，记 missing-prd（不臆造新端点）。
 * 通用约定（18-API）：统一响应 {code,message,data}；错误码 E-xxxx 见 17-spec §9。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { ApiError, TOKEN_KEY } from '@/api/http'
import { providerApi } from '@/api/provider'
import { getCalls, pushResponse, resetUniMock, storage } from '../setup'

function lastRequest(): Record<string, unknown> {
  const calls = getCalls('request')
  return calls.at(-1)?.args[0] as Record<string, unknown>
}

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

describe('序号 10 · providerApi.profile（GET /api/v1/provider/profile）', () => {
  beforeEach(() => resetUniMock())

  it('读取档案 → GET /api/v1/provider/profile，返回 data 原样', async () => {
    pushResponse(ok({ company_name: '云智科技有限公司', completeness: 72 }))
    const res = await providerApi.profile()
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/provider/profile')
    expect(options.method ?? 'GET').toBe('GET')
    expect(res).toEqual({ company_name: '云智科技有限公司', completeness: 72 })
  })
})

describe('序号 10 · providerApi.saveProfile（PUT /api/v1/provider/profile）', () => {
  beforeEach(() => resetUniMock())

  it('保存档案 → PUT，请求体为视图模型给出的键', async () => {
    pushResponse(ok({ provider_id: 'p1' }))
    await providerApi.saveProfile({ company_name: '云智科技有限公司', industry_category: 'RESELLER' })
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/provider/profile')
    expect(options.method).toBe('PUT')
    expect(options.data).toEqual({ company_name: '云智科技有限公司', industry_category: 'RESELLER' })
  })

  it('带 token 时附带 Authorization（与既有接口一致）', async () => {
    storage.set(TOKEN_KEY, 'tk-10')
    pushResponse(ok({}))
    await providerApi.saveProfile({ company_name: 'a' })
    const header = lastRequest().header as Record<string, string>
    expect(header.Authorization).toBe('Bearer tk-10')
  })

  it('服务端业务错误 → 抛 ApiError 且保留错误码（不吞错）', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1104', message: '统一社会信用代码已存在', data: null } })
    const pending = providerApi.saveProfile({ unified_social_credit_code: '91330106MA2XXXXX8B' })
    await expect(pending).rejects.toBeInstanceOf(ApiError)
    await expect(pending).rejects.toMatchObject({ code: 'E-1104', message: '统一社会信用代码已存在' })
  })
})

describe('序号 10 · 资质接口（/provider/qualifications）', () => {
  beforeEach(() => resetUniMock())

  it('读取资质列表 → GET /api/v1/provider/qualifications', async () => {
    pushResponse(ok({ items: [{ id: 'q1', category: 'BUSINESS_LICENSE', file_name: '营业执照-云智科技.jpg' }] }))
    const res = await providerApi.qualifications()
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/provider/qualifications')
    expect(options.method ?? 'GET').toBe('GET')
    expect(res).toEqual({
      items: [{ id: 'q1', category: 'BUSINESS_LICENSE', file_name: '营业执照-云智科技.jpg' }]
    })
  })

  it('上传资质 → POST /api/v1/provider/qualifications（只登记分类/文件名/字节数）', async () => {
    pushResponse(ok({ id: 'q9' }))
    await providerApi.uploadQualification({ category: 'OTHER', file_name: '许可.pdf', file_size: 2048 })
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/provider/qualifications')
    expect(options.method).toBe('POST')
    expect(options.data).toEqual({ category: 'OTHER', file_name: '许可.pdf', file_size: 2048 })
  })

  it('删除资质 → DELETE /api/v1/provider/qualifications/{id}（id 需转义）', async () => {
    pushResponse(ok({}))
    await providerApi.removeQualification('q1')
    const options = lastRequest()
    expect(options.url).toBe('/api/v1/provider/qualifications/q1')
    expect(options.method).toBe('DELETE')
  })
})
