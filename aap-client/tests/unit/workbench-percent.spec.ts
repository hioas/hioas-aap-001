/**
 * 工作台视图模型 · 图例百分比统一口径（决策 D3，`.agents/state/aap-decisions.md`）
 *
 * 真源：`GET /api/v1/usage/summary` 的数值（设计稿 page-2-b「构成图例」的 45/30/15/4/6/6
 * 合计 106%，是逐项取整的产物，只作视觉参考）。
 * 口径：分母 = max(total_tokens, Σ六类)；整数百分比用最大余数法；环形图与图例共用同一份整数。
 */
import { describe, expect, it } from 'vitest'
import { buildWorkbenchModel } from '@/utils/workbench-model'

/** 与 `.agents/state/h5-measure/api/v1/usage/summary` 同源的设计稿场景数据（六类合计 4.09B > 总量 3.86B） */
const DESIGN_LIKE = {
  request_count: 1_240_000,
  total_tokens: 3_860_000_000,
  prompt_tokens: 1_740_000_000,
  completion_tokens: 1_160_000_000,
  cache_read_tokens: 580_000_000,
  image_input_tokens: 150_000_000,
  audio_input_tokens: 230_000_000,
  video_input_tokens: 230_000_000,
  models: [
    { model_name: 'gpt-4o-mini', request_count: 1_240_000, amount: 54_200 },
    { model_name: 'claude-3-5-sonnet', request_count: 860_000, amount: 39_800 },
    { model_name: 'gpt-4o', request_count: 420_000, amount: 26_400 },
    { model_name: 'qwen-max', request_count: 40_000, amount: 4_240 },
    { model_name: 'glm-4', request_count: 40_000, amount: 4_000 }
  ]
}

const texts = (raw: Parameters<typeof buildWorkbenchModel>[0]) =>
  buildWorkbenchModel(raw).categories.map((c) => c.text)

describe('D3 · 图例百分比由真实数值计算（不再照抄设计稿 45/30/15）', () => {
  it('设计稿场景 → 42% · 1.74B / 28% · 1.16B / 14% · 0.58B / 4% · 0.15B / 6% · 0.23B / 6% · 0.23B', () => {
    expect(texts(DESIGN_LIKE)).toEqual([
      '42% · 1.74B',
      '28% · 1.16B',
      '14% · 0.58B',
      '4% · 0.15B',
      '6% · 0.23B',
      '6% · 0.23B'
    ])
  })

  it('分母 = max(total_tokens, Σ六类)（本场景 4.09B，不是总量 3.86B）', () => {
    const model = buildWorkbenchModel(DESIGN_LIKE)
    expect(model.ring.denominator).toBe(4_090_000_000)
    expect(model.categories[0].percent).toBe(42)
    expect(model.categories[0].percent).not.toBe(45)
  })

  it('音频/视频 随数值变化，不再是固定的 6%/6%', () => {
    const model = buildWorkbenchModel({
      total_tokens: 1_000_000_000,
      audio_input_tokens: 100_000_000,
      video_input_tokens: 50_000_000
    })
    expect(model.categories[4].text.startsWith('10% · ')).toBe(true)
    expect(model.categories[5].text.startsWith('5% · ')).toBe(true)
  })

  it('六类整数百分比之和恒 ≤ 100（容差 0），且等于环形图分段之和', () => {
    for (const raw of [DESIGN_LIKE, { total_tokens: 1_000_000_000, audio_input_tokens: 1, video_input_tokens: 1 }, { total_tokens: 3, prompt_tokens: 1, completion_tokens: 1, cache_read_tokens: 1 }]) {
      const model = buildWorkbenchModel(raw)
      const legendSum = model.categories.reduce((s, c) => s + (c.percent ?? 0), 0)
      const ringSum = model.ring.segments.reduce((s, seg) => s + seg.percent, 0)
      expect(legendSum).toBeLessThanOrEqual(100)
      expect(ringSum).toBe(legendSum)
      expect(model.ring.percentSum).toBe(legendSum)
    }
  })
})

describe('D3 · 环形图与图例同分母、同一份计算结果', () => {
  it('分段与图例逐项同 key / 同色 / 同整数百分比', () => {
    const model = buildWorkbenchModel(DESIGN_LIKE)
    expect(model.ring.segments.map((s) => s.key)).toEqual(model.categories.map((c) => c.key))
    expect(model.ring.segments.map((s) => s.color)).toEqual(model.categories.map((c) => c.color))
    expect(model.ring.segments.map((s) => s.percent)).toEqual(model.categories.map((c) => c.percent))
  })

  it('余量（轨道色段） = 100 − 分段之和', () => {
    const model = buildWorkbenchModel({ total_tokens: 1000, prompt_tokens: 100, completion_tokens: 50 })
    expect(model.ring.percentSum).toBe(15)
    expect(model.ring.remainderPercent).toBe(85)
    expect(model.ring.hasData).toBe(true)
  })
})

describe('D3 · 缺字段与空数据一律占位符（不显示 0%）', () => {
  it('音频/视频 字段缺失 → 图例显示 — 且不参与环形图分段', () => {
    const model = buildWorkbenchModel({
      total_tokens: 1_000_000_000,
      prompt_tokens: 400_000_000,
      completion_tokens: 200_000_000,
      cache_read_tokens: 100_000_000,
      image_input_tokens: 50_000_000
    })
    expect(model.categories[4].text).toBe('—')
    expect(model.categories[4].percent).toBeNull()
    expect(model.categories[5].text).toBe('—')
    expect(model.categories[5].percent).toBeNull()
    expect(model.ring.segments.map((s) => s.key)).toEqual(['prompt', 'completion', 'cache', 'image'])
    /* 分母 = max(10亿, 7.5亿) = 10亿 → 40/20/10/5，合计 75 ≤ 100 */
    expect(model.categories.slice(0, 4).map((c) => c.percent)).toEqual([40, 20, 10, 5])
    expect(model.ring.remainderPercent).toBe(25)
  })

  it('整个 summary 为空 → 六类全占位、环形图无数据（退轨道色）', () => {
    const model = buildWorkbenchModel({})
    expect(model.categories.map((c) => c.text)).toEqual(['—', '—', '—', '—', '—', '—'])
    expect(model.categories.map((c) => c.percent)).toEqual([null, null, null, null, null, null])
    expect(model.ring.hasData).toBe(false)
    expect(model.ring.segments).toEqual([])
    expect(model.ring.percentSum).toBe(0)
    expect(model.totalText).toBe('—')
  })

  it('字段存在但为 0 是「真 0」而不是缺失 → 显示 0% · 0（区别于占位符）', () => {
    const model = buildWorkbenchModel({ total_tokens: 1000, prompt_tokens: 0, completion_tokens: 500 })
    expect(model.categories[0].text).toBe('0% · 0')
    expect(model.categories[0].percent).toBe(0)
    expect(model.categories[2].text).toBe('—')
  })
})

describe('D3 · 模型行占比用同一口径（合计 100，与原留证数值一致）', () => {
  it('四行占比 42/31/21/6（合计 100），条宽用同一整数', () => {
    const model = buildWorkbenchModel(DESIGN_LIKE)
    expect(model.models.map((m) => m.barPercent)).toEqual([42, 31, 21, 6])
    expect(model.models.map((m) => m.callsText)).toEqual([
      '1.24M · 42%',
      '0.86M · 31%',
      '0.42M · 21%',
      '0.08M · 6%'
    ])
  })
})
