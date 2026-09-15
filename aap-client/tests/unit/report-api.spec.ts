/**
 * 序号 6【检测验真】大模型检测报告 · 多维度专业版（page-6）— 接口单测（先写，预期红）
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Report」Tag
 *   /reports、/{reportId}、/{reportId}/html、/{reportId}/export；路径前缀 /api/v1；鉴权 Bearer。
 *   ⚠️ 该卡片只列路径未列方法 → 方法按 REST 语义推断为 GET，台账记「方法为推断」待人类确认。
 */
import { describe, expect, it } from 'vitest'
import { ApiError, TOKEN_KEY } from '@/api/http'
import { reportApi } from '@/api/report'
import { DESIGN_REPORT } from '../fixtures/report-fixture'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })
const fail = (code: string, message: string) => ({ statusCode: 200, data: { code, message, data: null } })

describe('序号 6 · 接口：GET /api/v1/reports/{reportId}', () => {
  it('路径与鉴权头符合 18-API 通用约定', async () => {
    uni.setStorageSync(TOKEN_KEY, 'T-1')
    pushResponse(ok(DESIGN_REPORT))
    const data = await reportApi.detail('DR-1')
    const req = getCalls('request')[0].args[0] as { url: string; method: string; header: Record<string, string> }
    expect(req.url).toBe('/api/v1/reports/DR-1')
    expect(req.method).toBe('GET')
    expect(req.header.Authorization).toBe('Bearer T-1')
    expect(data.report_no).toBe('DR-20240613-0758')
  })

  it('reportId 做 URL 编码，避免路径注入', async () => {
    pushResponse(ok(DESIGN_REPORT))
    await reportApi.detail('r/1 2')
    const req = getCalls('request')[0].args[0] as { url: string }
    expect(req.url).toBe('/api/v1/reports/r%2F1%202')
  })

  it('服务端业务错误码原样抛 ApiError（不吞错）', async () => {
    setNextResponse(fail('E-1404', '报告不存在'))
    await expect(reportApi.detail('DR-404')).rejects.toBeInstanceOf(ApiError)
    await expect(reportApi.detail('DR-404')).rejects.toMatchObject({ code: 'E-1404', message: '报告不存在' })
  })
})

describe('序号 6 · 接口：GET /api/v1/reports/{reportId}/export', () => {
  it('导出 PDF 走 /export 子资源', async () => {
    pushResponse(ok({ url: 'https://cdn.example.com/dr-1.pdf', file_name: 'DR-1.pdf' }))
    const data = await reportApi.exportFile('DR-1')
    const req = getCalls('request')[0].args[0] as { url: string; method: string }
    expect(req.url).toBe('/api/v1/reports/DR-1/export')
    expect(req.method).toBe('GET')
    expect(data.url).toBe('https://cdn.example.com/dr-1.pdf')
  })

  it('未登录（401）清 token 并报 E-1902', async () => {
    uni.setStorageSync(TOKEN_KEY, 'T-2')
    setNextResponse({ statusCode: 401, data: { code: 'E-1902', message: '未认证' } })
    await expect(reportApi.exportFile('DR-1')).rejects.toMatchObject({ code: 'E-1902' })
    expect(uni.getStorageSync(TOKEN_KEY)).toBe('')
  })
})
