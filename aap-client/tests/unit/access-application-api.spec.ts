/**
 * 序号 4-v1「接入凭证-表单」（page-24）— 接口接线单测
 *
 * 接口依据：.calicat/prd/18-API设计OpenAPI.md
 *   Provider  Tag → POST /provider/qualifications（「凭证资料」的资质登记）
 *   Detection Tag → POST /detection-jobs（设计脚注「提交后系统将自动发起检测」= 服务端副作用）
 *   前缀 /api/v1；鉴权 Authorization: Bearer ***
 * ⚠️ missing-prd（已在台账登记，不臆造别的路径）：
 *   1) 18-API 卡片只列路径未列方法 → POST 按 REST 语义推断（该卡为摘要，完整 openapi.yaml 不在仓库）；
 *   2) 企业信息（company_name / unified_social_credit_code / contact_name / contact_phone）在
 *      15-数据字典 aap_provider 有字段，但 18-API **没有** provider 主体写接口（只有 /provider/profile
 *      与 /provider/qualifications）→ 本页把企业信息随资质申请体一起提交，接口归属待人拍板（阻塞项）；
 *   3) 响应字段级 schema 未定义 → 只按 15-数据字典 主键命名取可选字段，不编造业务字段。
 * 错误码：17-spec §9；统一响应 {code,message,data}；文案一律用服务端 message，前端不自造业务文案。
 */
import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/http'
import { accessApplicationApi } from '@/api/access-application'
import type { AccessApplicationPayload } from '@/utils/access-application-model'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const PAYLOAD: AccessApplicationPayload = {
  company_name: '深圳市恒信科技有限公司',
  unified_social_credit_code: '91440300MA5DAJQH6X',
  contact_name: '张伟',
  contact_phone: '13800138000',
  qualification_files: [{ file_name: '营业执照扫描件.pdf', file_size: 2516582 }]
}

describe('accessApplicationApi.submit · POST /provider/qualifications', () => {
  it('路径 /api/v1/provider/qualifications、方法 POST、带 Bearer token', async () => {
    uni.setStorageSync('aap_token', 'tk-4v1')
    pushResponse(ok({ id: 'q1' }))

    const res = await accessApplicationApi.submit(PAYLOAD)

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/provider/qualifications')
    expect(req.method).toBe('POST')
    expect((req.header as Record<string, string>).Authorization).toBe('Bearer tk-4v1')
    expect(req.data).toEqual(PAYLOAD)
    expect(res).toMatchObject({ id: 'q1' })
  })

  it('响应里的检测任务号原样透传（用于跳转检测进行中页）', async () => {
    pushResponse(ok({ id: 'q1', detection_job_id: 'J-20260916-001' }))
    const res = await accessApplicationApi.submit(PAYLOAD)
    expect(res.detection_job_id).toBe('J-20260916-001')
  })

  it('服务端业务错误（E-1104 重复申请）→ 抛 ApiError 且保留服务端 message', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1104', message: '该企业已提交过接入申请' } })

    await expect(accessApplicationApi.submit(PAYLOAD)).rejects.toMatchObject({
      name: 'ApiError',
      code: 'E-1104',
      message: '该企业已提交过接入申请'
    })
  })

  it('网络层失败 → ApiError E-2001', async () => {
    pushResponse({ statusCode: 0, data: {}, fail: true })

    const err = await accessApplicationApi.submit(PAYLOAD).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('E-2001')
  })

  it('401 → 清 token 并按 E-1902 处理', async () => {
    uni.setStorageSync('aap_token', 'expired')
    pushResponse({ statusCode: 401, data: { code: 'E-1902', message: '登录已过期' } })

    const err = await accessApplicationApi.submit(PAYLOAD).catch((e: unknown) => e)
    expect((err as ApiError).code).toBe('E-1902')
    expect(uni.getStorageSync('aap_token')).toBe('')
  })
})
