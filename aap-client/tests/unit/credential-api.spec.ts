/**
 * 序号 3【工作台与我的】凭证列表-有数据（page-3）— 数据层与视图模型单测
 *
 * 接口依据：.calicat/prd/18-API设计OpenAPI.md「Credential」Tag → POST/GET /credentials（前缀 /api/v1）
 * 字段依据：.calicat/prd/15-数据模型ER与数据字典.md
 *           aap_credential（alias / model_list / created_at）+ aap_detection_job（status / result）
 * 文案依据：.calicat/raw/pages/page-3/design.tree.json（表头/统计/行/底部说明逐条对齐设计稿）
 * ⚠️ 字段级 schema 未在 18-API 定义（该卡为摘要，完整 yaml 不在本仓库）→ 已记台账 missing-prd。
 */
import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/http'
import { credentialApi } from '@/api/credential'
import {
  CREDENTIAL_STATUS_META,
  STATUS_ORDER,
  buildCredentialsModel,
  formatDateTime,
  statusKeyOf,
  type CredentialListRaw
} from '@/utils/credentials-model'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 造 n 个模型项（model_list 为 jsonb 数组，设计稿「模型数」= 数组长度） */
const models = (n: number) => Array.from({ length: n }, (_, i) => ({ model_name: `m${i}` }))

/**
 * 与设计稿 page-3 表格逐行一致的 /credentials 响应（10 行：名称/模型数/状态/报告）
 * 设计稿状态点：绿=通过、蓝=检测中、灰=待检测、红=不通过；右列「报告」只出现在 通过/不通过 行。
 */
const RAW: CredentialListRaw = {
  total: 10,
  items: [
    { id: 'c1', alias: '华东主线路 · GPT 通道', model_list: models(2), created_at: '2026-07-10T14:08:21Z', detection_status: 'PASS', latest_report_id: 'rp1' },
    { id: 'c2', alias: '华北备用 · Claude 通道', model_list: models(5), created_at: '2026-07-10T14:08:21Z', detection_status: 'RUNNING' },
    { id: 'c3', alias: '华南专线 · Gemini 通道', model_list: models(3), created_at: '2026-07-10T14:08:21Z', detection_status: 'PENDING' },
    { id: 'c4', alias: '华东测试 · GPT 通道', model_list: models(1), created_at: '2026-07-10T14:08:21Z', detection_status: 'FAIL', latest_report_id: 'rp4' },
    { id: 'c5', alias: '华中主线路 · Claude 通道', model_list: models(4), created_at: '2026-07-10T14:08:21Z', detection_status: 'PASS', latest_report_id: 'rp5' },
    { id: 'c6', alias: '华南备用 · GPT 通道', model_list: models(6), created_at: '2026-07-10T14:08:21Z', detection_status: 'RUNNING' },
    { id: 'c7', alias: '西南专线 · 通义通道', model_list: models(2), created_at: '2026-07-10T14:08:21Z', detection_status: 'PASS', latest_report_id: 'rp7' },
    { id: 'c8', alias: '华北主线路 · Gemini 通道', model_list: models(3), created_at: '2026-07-10T14:08:21Z', detection_status: 'PENDING' },
    { id: 'c9', alias: '华东灰度 · DeepSeek 通道', model_list: models(5), created_at: '2026-07-10T14:08:21Z', detection_status: 'PASS', latest_report_id: 'rp9' },
    { id: 'c10', alias: '港澳线路 · GPT 通道', model_list: models(4), created_at: '2026-07-10T14:08:21Z', detection_status: 'PENDING' }
  ]
}

describe('credentialApi.list · 接口接线（18-API Credential Tag）', () => {
  it('GET /api/v1/credentials，带 page/pageSize 与 Bearer token', async () => {
    uni.setStorageSync('aap_token', 'tk-3')
    pushResponse(ok(RAW))

    await credentialApi.list({ page: 1, pageSize: 10 })

    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    const req = calls[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/credentials')
    expect(req.method).toBe('GET')
    expect(req.data).toMatchObject({ page: 1, pageSize: 10 })
    expect((req.header as Record<string, string>).Authorization).toBe('Bearer tk-3')
  })

  it('业务错误码 → 抛 ApiError', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1104', message: '凭证重复' } })
    await expect(credentialApi.list()).rejects.toBeInstanceOf(ApiError)
  })

  it('网络失败 → E-2001', async () => {
    setNextResponse({ statusCode: 200, data: {}, fail: true })
    await expect(credentialApi.list()).rejects.toMatchObject({ code: 'E-2001' })
  })
})

describe('statusKeyOf · 检测态映射到设计稿 4 态', () => {
  it('PENDING→pending / RUNNING→detecting / PASS→passed / FAIL→rejected', () => {
    expect(statusKeyOf('PENDING')).toBe('pending')
    expect(statusKeyOf('RUNNING')).toBe('detecting')
    expect(statusKeyOf('PASS')).toBe('passed')
    expect(statusKeyOf('FAIL')).toBe('rejected')
  })

  it('缺失或未知状态不臆造：一律落 pending（待检测）', () => {
    expect(statusKeyOf(undefined)).toBe('pending')
    expect(statusKeyOf('')).toBe('pending')
    expect(statusKeyOf('WEIRD')).toBe('pending')
  })
})

describe('CREDENTIAL_STATUS_META · 文案与色值取自设计稿', () => {
  it('4 态顺序为 待检测/检测中/不通过/通过（design 状态统计行左→右）', () => {
    expect(STATUS_ORDER).toEqual(['pending', 'detecting', 'rejected', 'passed'])
  })

  it('标签与色值逐条对齐 design 状态点', () => {
    expect(CREDENTIAL_STATUS_META.pending).toMatchObject({ label: '待检测', color: '#94a3b8' })
    expect(CREDENTIAL_STATUS_META.detecting).toMatchObject({ label: '检测中', color: '#2563eb' })
    expect(CREDENTIAL_STATUS_META.rejected).toMatchObject({ label: '不通过', color: '#ef4444' })
    expect(CREDENTIAL_STATUS_META.passed).toMatchObject({ label: '通过', color: '#16a34a' })
  })
})

describe('formatDateTime · 「YYYY-MM-DD HH:mm:ss」', () => {
  it('RFC3339（UTC）→ 设计稿形态，不做时区换算', () => {
    expect(formatDateTime('2026-07-10T14:08:21Z')).toBe('2026-07-10 14:08:21')
    expect(formatDateTime('2026-07-10 14:08:21')).toBe('2026-07-10 14:08:21')
    expect(formatDateTime('2026-07-10T14:08:21.123+08:00')).toBe('2026-07-10 14:08:21')
  })

  it('缺失/非法 → 占位符「—」（不显示 NaN/Invalid Date）', () => {
    expect(formatDateTime(undefined)).toBe('—')
    expect(formatDateTime('')).toBe('—')
    expect(formatDateTime('not-a-date')).toBe('—')
  })
})

describe('buildCredentialsModel · 视图模型对齐设计稿', () => {
  const model = buildCredentialsModel(RAW)

  it('列表标题行：共 10 条（total 来自接口）', () => {
    expect(model.totalText).toBe('共 10 条')
  })

  it('状态统计行 4 个：待检测 3 / 检测中 2 / 不通过 1 / 通过 4（= 设计稿计数）', () => {
    expect(model.chips.map((c) => [c.label, c.count])).toEqual([
      ['待检测', 3],
      ['检测中', 2],
      ['不通过', 1],
      ['通过', 4]
    ])
    expect(model.chips.map((c) => c.color)).toEqual(['#94a3b8', '#2563eb', '#ef4444', '#16a34a'])
  })

  it('10 行：名称/时间/模型数逐条一致', () => {
    expect(model.rows).toHaveLength(10)
    expect(model.rows[0]).toMatchObject({
      alias: '华东主线路 · GPT 通道',
      timeText: '2026-07-10 14:08:21',
      modelCountText: '2',
      statusKey: 'passed'
    })
    expect(model.rows.map((r) => r.alias)).toEqual([
      '华东主线路 · GPT 通道',
      '华北备用 · Claude 通道',
      '华南专线 · Gemini 通道',
      '华东测试 · GPT 通道',
      '华中主线路 · Claude 通道',
      '华南备用 · GPT 通道',
      '西南专线 · 通义通道',
      '华北主线路 · Gemini 通道',
      '华东灰度 · DeepSeek 通道',
      '港澳线路 · GPT 通道'
    ])
    expect(model.rows.map((r) => r.modelCountText)).toEqual(['2', '5', '3', '1', '4', '6', '2', '3', '5', '4'])
  })

  it('「报告」列只出现在 通过/不通过 行（设计稿 1/4/5/7/9 行）', () => {
    expect(model.rows.map((r) => r.reportText)).toEqual([
      '报告',
      undefined,
      undefined,
      '报告',
      '报告',
      undefined,
      '报告',
      undefined,
      '报告',
      undefined
    ])
  })

  it('行状态色值取自设计稿状态点', () => {
    expect(model.rows.map((r) => r.statusColor)).toEqual([
      '#16a34a',
      '#2563eb',
      '#94a3b8',
      '#ef4444',
      '#16a34a',
      '#2563eb',
      '#16a34a',
      '#94a3b8',
      '#16a34a',
      '#94a3b8'
    ])
  })

  it('底部说明文案与设计稿一致', () => {
    expect(model.footerText).toBe('仅展示最近接入的 10 条凭证记录')
  })
})

describe('buildCredentialsModel · 空/缺失数据不崩且不编造', () => {
  it('空响应 → 共 0 条、4 个统计全 0、0 行、不出现 NaN', () => {
    const m = buildCredentialsModel({})
    expect(m.totalText).toBe('共 0 条')
    expect(m.chips.map((c) => c.count)).toEqual([0, 0, 0, 0])
    expect(m.rows).toEqual([])
    expect(JSON.stringify(m)).not.toContain('NaN')
  })

  it('null/undefined 入参同样安全', () => {
    expect(buildCredentialsModel(undefined).rows).toEqual([])
    expect(buildCredentialsModel(null).totalText).toBe('共 0 条')
  })

  it('total 缺省时退化为已返回行数（不编造更大的数）', () => {
    const m = buildCredentialsModel({ items: [{ id: 'x', alias: 'A', detection_status: 'PASS' }] })
    expect(m.totalText).toBe('共 1 条')
  })
})
