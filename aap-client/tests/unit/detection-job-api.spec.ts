/**
 * 序号 7【检测验真】检测未通过报告 2（page-7-2）— 「重新提交检测」接口接线单测（先写，预期红）
 *
 * 接口依据：
 *   1) 18-API设计OpenAPI.md「Detection」Tag 列出路径 /detection-jobs（前缀 /api/v1）；
 *      ⚠️ 该卡片只列路径未列方法 → POST 为 REST 语义推断（创建检测任务），台账记「方法为推断」待确认。
 *   2) 09-PRD §5「触发时机」：首次（提交凭证后自动）、**重测（修改凭证/人工点击）**、定期复测
 *      → 设计稿「重新提交检测」按钮 = 人工点击重测 → 在凭证维度创建新的 DetectionJob。
 *   3) 15-数据字典：credential 1:N detection_job（可重测，同时仅 1 活跃）→ 请求体只带 credential_id。
 *   4) 17-spec：R-08 检测互斥 E-1301、R-09 供应商日配额 5 次；错误文案一律用服务端 message，前端不自造。
 *
 * 未接线（设计稿无对应控件，不臆造）：POST /detection-jobs/{jobId}/cancel、GET /{jobId}/release 等。
 */
import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/http'
import { detectionApi } from '@/api/detection'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

describe('detectionApi.create · POST /detection-jobs（重测）', () => {
  it('路径 /detection-jobs、方法 POST、请求体带 credential_id、带 Bearer token', async () => {
    uni.setStorageSync('aap_token', 'tk-7')
    pushResponse(ok({ job_id: 'j9', job_no: 'DJ-20260916-0009' }))

    const res = await detectionApi.create({ credential_id: 'c1' })

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/detection-jobs')
    expect(req.method).toBe('POST')
    expect(req.data).toEqual({ credential_id: 'c1' })
    expect((req.header as Record<string, string>).Authorization).toBe('Bearer tk-7')
    expect(res).toMatchObject({ job_id: 'j9' })
  })

  it('检测互斥（E-1301）→ ApiError 保留服务端 code 与 message', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1301', message: '该凭证已有检测任务进行中' } })

    await expect(detectionApi.create({ credential_id: 'c1' })).rejects.toMatchObject({
      code: 'E-1301',
      message: '该凭证已有检测任务进行中'
    })
  })

  it('网络失败 → E-2001（ApiError）', async () => {
    setNextResponse({ statusCode: 200, data: {}, fail: true })
    await expect(detectionApi.create({ credential_id: 'c1' })).rejects.toBeInstanceOf(ApiError)
  })
})
