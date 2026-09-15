/**
 * 序号 5【检测验真】检测进行中 2（page-5-2）— 接口接线单测（先写，预期红）
 *
 * 接口依据：.calicat/prd/18-API设计OpenAPI.md「Detection」Tag
 *   /detection-jobs、/{jobId}、/{jobId}/cancel、/{jobId}/results、/{jobId}/results/{probeCode}、/{jobId}/release
 *   前缀 /api/v1；鉴权 Authorization: Bearer ***
 *   ⚠️ 该卡片只列路径未列方法（完整 openapi.yaml 不在仓库）→ /{jobId} 与 /{jobId}/results 的方法按 REST
 *      语义推断为 GET，台账记「方法为推断」待确认；不臆造别的路径。
 *   本页只接线 /{jobId} 与 /{jobId}/results；/cancel、/results/{probeCode}、/release 设计稿无对应控件 → 不接线。
 * 错误码：17-spec §9 —— E-1301~E-1305 检测、E-1901/1902/1903 权限/认证/限流、E-2001 内部错误；
 *   统一响应 {code,message,data}；文案一律用服务端 message，前端不自造业务错误文案。
 */
import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/http'
import { detectionApi } from '@/api/detection'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const JOB = {
  id: 'j1',
  job_no: 'DJ-20260916-0001',
  credential_id: 'c1',
  status: 'RUNNING',
  trigger_type: 'FIRST',
  started_at: '2026-09-16T01:00:00Z'
}

describe('detectionApi.job · GET /detection-jobs/{jobId}', () => {
  it('路径带 jobId、方法 GET、带 Bearer token', async () => {
    uni.setStorageSync('aap_token', 'tk-5')
    pushResponse(ok(JOB))

    const res = await detectionApi.job('j1')

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/detection-jobs/j1')
    expect(req.method).toBe('GET')
    expect((req.header as Record<string, string>).Authorization).toBe('Bearer tk-5')
    expect(res).toMatchObject({ status: 'RUNNING' })
  })

  it('jobId 会做 URL 编码（不拼接注入字符）', async () => {
    pushResponse(ok(JOB))
    await detectionApi.job('j 1/2')
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/detection-jobs/j%201%2F2')
  })
})

describe('detectionApi.results · GET /detection-jobs/{jobId}/results', () => {
  it('路径为 /results、方法 GET', async () => {
    pushResponse(ok({ job_id: 'j1', items: [] }))

    await detectionApi.results('j1')

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/detection-jobs/j1/results')
    expect(req.method).toBe('GET')
  })

  it('检测任务不存在（E-1301/E-1304 类）→ ApiError 保留服务端 message', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1301', message: '该凭证已有检测任务进行中' } })
    await expect(detectionApi.results('j1')).rejects.toMatchObject({
      code: 'E-1301',
      message: '该凭证已有检测任务进行中'
    })
  })

  it('网络失败 → E-2001', async () => {
    setNextResponse({ statusCode: 200, data: {}, fail: true })
    await expect(detectionApi.job('j1')).rejects.toBeInstanceOf(ApiError)
  })
})
