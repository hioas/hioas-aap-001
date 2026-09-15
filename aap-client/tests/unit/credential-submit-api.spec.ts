/**
 * 序号 4【检测验真】提交接入凭证 2（page-4-2）— 接口接线单测
 *
 * 接口依据：.calicat/prd/18-API设计OpenAPI.md「Credential」Tag
 *   /credentials、/credentials/{id}、/{id}/precheck、/{id}/precheck/latest、/{id}/reveal
 *   前缀 /api/v1；鉴权 Authorization: Bearer ***
 *   ⚠️ 该卡片只列路径未列方法（完整 openapi.yaml 不在仓库）→ /credentials/{id} 的方法按 REST
 *      语义推断为 GET(详情)/PUT(保存)，台账记「方法为推断」待确认，不臆造别的路径。
 * 错误码：17-spec §9 —— E-1101~E-1104 预检/重复、E-1201 SSRF、E-1301 检测互斥、E-1903 限流；
 *   统一响应 {code,message,data}；文案一律用服务端 message，前端不自造业务错误文案。
 */
import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/http'
import { credentialApi } from '@/api/credential'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const DETAIL = {
  id: 'c1',
  alias: '华东主线路 · GPT 通道',
  base_url: 'https://api.example-llm.com/v1',
  api_key_mask: 'sk-••••••••••••••••4f2a',
  primary_flag: true,
  model_list: [{ model_name: 'gpt-4o' }]
}

describe('credentialApi.detail · GET /credentials/{id}', () => {
  it('路径带 id、方法 GET、带 Bearer token', async () => {
    uni.setStorageSync('aap_token', 'tk-4')
    pushResponse(ok(DETAIL))

    const res = await credentialApi.detail('c1')

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/credentials/c1')
    expect(req.method).toBe('GET')
    expect((req.header as Record<string, string>).Authorization).toBe('Bearer tk-4')
    expect(res).toMatchObject({ alias: '华东主线路 · GPT 通道' })
  })

  it('id 会做 URL 编码（不拼接注入字符）', async () => {
    pushResponse(ok(DETAIL))
    await credentialApi.detail('c 1/2')
    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/credentials/c%201%2F2')
  })
})

describe('credentialApi.save · PUT /credentials/{id}', () => {
  it('方法 PUT，请求体原样透传（含 base_url 与 model_list）', async () => {
    pushResponse(ok({ id: 'c1' }))

    await credentialApi.save('c1', {
      alias: '华东主线路 · GPT 通道',
      base_url: 'https://api.example-llm.com/v1',
      model_list: ['gpt-4o', 'claude-3-5-sonnet']
    })

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/credentials/c1')
    expect(req.method).toBe('PUT')
    expect(req.data).toEqual({
      alias: '华东主线路 · GPT 通道',
      base_url: 'https://api.example-llm.com/v1',
      model_list: ['gpt-4o', 'claude-3-5-sonnet']
    })
  })

  it('重复凭证（E-1104）→ 抛 ApiError 且保留服务端 message', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1104', message: '该凭证已存在' } })
    await expect(credentialApi.save('c1', { alias: 'A', base_url: 'https://a.com', model_list: [] })).rejects.toMatchObject({
      code: 'E-1104',
      message: '该凭证已存在'
    })
  })
})

describe('credentialApi.precheck · POST /credentials/{id}/precheck', () => {
  it('方法 POST，路径为 /precheck', async () => {
    pushResponse(ok({ job_id: 'j1' }))

    await credentialApi.precheck('c1')

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/credentials/c1/precheck')
    expect(req.method).toBe('POST')
  })

  it('SSRF 拒绝（E-1201）/ 检测互斥（E-1301）→ ApiError 携带服务端文案', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1201', message: 'BaseURL 指向内网地址，已拒绝' } })
    await expect(credentialApi.precheck('c1')).rejects.toMatchObject({
      code: 'E-1201',
      message: 'BaseURL 指向内网地址，已拒绝'
    })

    pushResponse({ statusCode: 200, data: { code: 'E-1301', message: '该凭证已有检测任务进行中' } })
    await expect(credentialApi.precheck('c1')).rejects.toMatchObject({
      code: 'E-1301',
      message: '该凭证已有检测任务进行中'
    })
  })

  it('网络失败 → E-2001', async () => {
    setNextResponse({ statusCode: 200, data: {}, fail: true })
    await expect(credentialApi.precheck('c1')).rejects.toBeInstanceOf(ApiError)
  })
})
