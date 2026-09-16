/**
 * 工作台视图模型 — 模型行「序号」文字配色（序号 2 / page-2-b）
 *
 * 真源：.calicat/raw/pages/page-2-b/design.tree.json 的 模型1~4序号 子图层 fontFill：
 *   1 → rgba(37,99,235,1)   2 → rgba(22,163,74,1)   3 → rgba(217,119,6,1)   4 → rgba(100,116,139,1)
 * 序号底色（fills）与占比条色（fills）本文件一并固定，防止后续只改一个。
 */
import { describe, expect, it } from 'vitest'
import { buildWorkbenchModel } from '@/utils/workbench-model'

const MODELS = [
  { model_name: 'gpt-4o-mini', request_count: 1_240_000, amount: 54_200 },
  { model_name: 'claude-3-5-sonnet', request_count: 860_000, amount: 39_800 },
  { model_name: 'gpt-4o', request_count: 420_000, amount: 26_400 },
  { model_name: 'qwen-max', request_count: 40_000, amount: 4_240 },
  { model_name: 'glm-4', request_count: 40_000, amount: 4_000 }
]

describe('工作台视图模型 · 模型行配色（设计稿逐行给色）', () => {
  it('四行序号文字色 = #2563eb / #16a34a / #d97706 / #64748b（设计 模型1~4序号 fontFill）', () => {
    const model = buildWorkbenchModel({ total_tokens: 3_860_000_000, models: MODELS })
    expect(model.models).toHaveLength(4)
    expect(model.models.map((m) => m.rankColor)).toEqual(['#2563eb', '#16a34a', '#d97706', '#64748b'])
  })

  it('序号底色与占比条色与设计稿一致（模型1~4序号 fills / 条填 fills）', () => {
    const model = buildWorkbenchModel({ total_tokens: 3_860_000_000, models: MODELS })
    expect(model.models.map((m) => m.badgeBg)).toEqual(['#eff6ff', '#ecfdf5', '#fff7ed', '#f1f5f9'])
    expect(model.models.map((m) => m.barColor)).toEqual(['#2563eb', '#60a5fa', '#f59e0b', '#94a3b8'])
  })
})
