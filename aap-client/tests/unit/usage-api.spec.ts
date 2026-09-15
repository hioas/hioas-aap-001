/**
 * 工作台数据台（序号 2 / page-2-b）— 数据层与视图模型单测
 *
 * 接口依据：.calicat/prd/18-API设计OpenAPI.md「Usage」Tag → GET /usage/summary（前缀 /api/v1）
 * 字段依据：.calicat/prd/15-数据模型ER与数据字典.md aap_usage_hourly
 *           + 11-同步与用量统计PRD §4「对账视图指标」（请求数/输入输出 token/缓存读/命中率/quota/cost）
 * 文案依据：.calicat/raw/pages/page-2-b/design.tree.json（数值与标签逐条对齐设计稿）
 */
import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/http'
import { usageApi } from '@/api/usage'
import { buildWorkbenchModel, mergeModelRows } from '@/utils/workbench-model'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 与设计稿 page-2-b 数字一致的一份 /usage/summary 响应（字段名取自数据字典用量域） */
const RAW = {
  stat_hour: '2024-06-14T00:00:00Z',
  request_count: 1_240_000,
  total_tokens: 3_860_000_000,
  prompt_tokens: 1_740_000_000,
  completion_tokens: 1_160_000_000,
  cache_read_tokens: 580_000_000,
  image_input_tokens: 150_000_000,
  audio_input_tokens: 230_000_000,
  video_input_tokens: 230_000_000,
  cache_hit_rate: 0.15,
  mom_rate: 0.125,
  cost_usd: 17_920,
  models: [
    { model_name: 'gpt-4o-mini', request_count: 1_240_000, total_tokens: 1_740_000_000, amount: 54_200 },
    { model_name: 'claude-3-5-sonnet', request_count: 860_000, total_tokens: 1_160_000_000, amount: 39_800 },
    { model_name: 'gpt-4o', request_count: 420_000, total_tokens: 580_000_000, amount: 26_400 },
    { model_name: 'qwen-max', request_count: 40_000, total_tokens: 60_000_000, amount: 4_240 },
    { model_name: 'glm-4', request_count: 40_000, total_tokens: 40_000_000, amount: 4_000 }
  ]
}

describe('usageApi.summary · 接口接线', () => {
  it('GET /api/v1/usage/summary，带 Bearer token', async () => {
    uni.setStorageSync('aap_token', 'tk-1')
    pushResponse(ok(RAW))

    await usageApi.summary()

    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    const req = calls[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/usage/summary')
    expect(req.method).toBe('GET')
    expect((req.header as Record<string, string>).Authorization).toBe('Bearer tk-1')
  })

  it('后端返回业务错误码 → 抛出 ApiError', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-3001', message: '用量聚合未完成' } })
    await expect(usageApi.summary()).rejects.toBeInstanceOf(ApiError)
  })

  it('网络失败 → E-2001', async () => {
    setNextResponse({ statusCode: 200, data: {}, fail: true })
    await expect(usageApi.summary()).rejects.toMatchObject({ code: 'E-2001' })
  })
})

describe('buildWorkbenchModel · 视图模型对齐设计稿', () => {
  const model = buildWorkbenchModel(RAW)

  it('顶部栏：环比 12.5% 与总词元 3.86B', () => {
    expect(model.momText).toBe('12.5%')
    expect(model.totalText).toBe('3.86B')
    expect(model.centerLabel).toBe('总词元')
  })

  it('构成图例顺序与文案（设计稿 6 行，标签 + 占比·数值）', () => {
    expect(model.categories.map((c) => c.label)).toEqual([
      '输入词元',
      '输出词元',
      '缓存命中',
      '图片',
      '音频',
      '视频'
    ])
    expect(model.categories.map((c) => c.text)).toEqual([
      '45% · 1.74B',
      '30% · 1.16B',
      '15% · 0.58B',
      '4% · 0.15B',
      '6% · 0.23B',
      '6% · 0.23B'
    ])
  })

  it('构成图例点色值取自设计稿', () => {
    expect(model.categories.map((c) => c.color)).toEqual([
      '#1d4ed8',
      '#3b82f6',
      '#16a34a',
      '#5856d6',
      '#f59e0b',
      '#af52de'
    ])
  })

  it('底行三指标：调用请求 1.24M / Token 3.86B / 缓存命中率 15%', () => {
    expect(model.metrics.map((m) => [m.label, m.value])).toEqual([
      ['调用请求', '1.24M'],
      ['Token', '3.86B'],
      ['缓存命中率', '15%']
    ])
  })

  it('模型行按收入倒序、序号从 1 开始、金额与「调用量 · 占比」', () => {
    expect(model.models.map((m) => m.rank)).toEqual([1, 2, 3, 4])
    expect(model.models[0]).toMatchObject({
      name: 'gpt-4o-mini',
      amountText: '¥54,200',
      callsText: '1.24M · 42%'
    })
    expect(model.models[1]).toMatchObject({ name: 'claude-3-5-sonnet', amountText: '¥39,800', callsText: '0.86M · 31%' })
    expect(model.models[2]).toMatchObject({ name: 'gpt-4o', amountText: '¥26,400', callsText: '0.42M · 21%' })
    expect(model.models[3]).toMatchObject({ name: '其他模型', amountText: '¥8,240', callsText: '0.08M · 6%' })
  })

  it('模型卡底行：合计 ¥128,640 · 4 个模型（4 = 展示行数）', () => {
    expect(model.footerText).toBe('合计 ¥128,640 · 4 个模型')
  })

  it('占比条宽度 = 金额占比（42/31/21/6）', () => {
    expect(model.models.map((m) => m.barPercent)).toEqual([42, 31, 21, 6])
  })
})

describe('mergeModelRows · 超过 3 个模型时尾部合并为「其他模型」', () => {
  it('<=3 个模型原样展示', () => {
    const rows = mergeModelRows([
      { model_name: 'a', request_count: 10, total_tokens: 100, amount: 300 },
      { model_name: 'b', request_count: 5, total_tokens: 50, amount: 100 }
    ])
    expect(rows.map((r) => r.model_name)).toEqual(['a', 'b'])
  })

  it('>3 个模型 → 前 3 + 其他模型（金额/调用量求和）', () => {
    const rows = mergeModelRows(RAW.models)
    expect(rows.map((r) => r.model_name)).toEqual([
      'gpt-4o-mini',
      'claude-3-5-sonnet',
      'gpt-4o',
      '其他模型'
    ])
    expect(rows[3]).toMatchObject({ amount: 8_240, request_count: 80_000 })
  })

  it('无模型数据 → 空数组（页面走空态）', () => {
    expect(mergeModelRows(undefined)).toEqual([])
    expect(mergeModelRows([])).toEqual([])
  })
})

describe('buildWorkbenchModel · 缺失/空数据不崩且不编造', () => {
  it('空响应 → 数值一律占位符「—」，不出现 NaN', () => {
    const m = buildWorkbenchModel({})
    expect(m.totalText).toBe('—')
    expect(m.momText).toBe('—')
    expect(m.categories.every((c) => !c.text.includes('NaN'))).toBe(true)
    expect(m.metrics.map((x) => x.value)).toEqual(['—', '—', '—'])
    expect(m.models).toEqual([])
    expect(m.footerText).toBe('合计 —')
  })
})
