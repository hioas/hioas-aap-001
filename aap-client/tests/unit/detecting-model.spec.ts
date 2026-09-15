/**
 * 序号 5【检测验真】检测进行中 2（page-5-2）— 视图模型单测（先写，预期红）
 *
 * 设计真源：.calicat/raw/pages/page-5-2/design.tree.json（430 宽）
 *   顶部导航 c2a2498d（返回 24px #334155 · 标题「检测进行中」17px #0F172A · chip「进行中」#EFF6FF/#2563EB）
 *   总进度卡片 88f1ee17（「总进度」15px / 「58%」20px #2563EB；进度条 61993aa5 高 10 轨道 #E2E8F0 填充 #2563EB 209/358）
 *   进度元信息行 dac2c177（「已完成 7 / 12 个检测项」12px #64748B / 「预计剩余 42 分钟」12px #94A3B8）
 *   成本保护行 257b52bf（#ECFDF5 r12 · 图标 #16A34A · 「检测期间已启用成本保护」12px #15803D ·
 *     「本次检测由平台承担费用，不会计入你的账单」11px #16A34A）
 *   分项进度卡片 2138c3d3（「分项检测」15px #0F172A · 8 行 D1–D8 · 行内 32×32 图标块 r10 + 名称 13px + 详情 11px + 状态 chip h22 r11）
 *   提示卡片 c960eff4（图标 #D97706 · 「检测期间你可以先完善供应商档案，检测完成后会自动通知你，无需停留本页。」12px #64748B）
 *   底部操作条 ed66b6f1（按钮 73a98024 #F1F5F9 r12 h48 · 「查看历史检测报告」14px #475569）
 * 交互真源：page-5-2 interaction.json =「不存在图层交互数据」→ 退 PRD 09/17-spec/18-API + 画布 30 页清单
 *
 * ⚠️ 缺口（均记台账，不臆造）：
 *   1) 设计 8 行名称（网络连通性/鉴权有效性/模型清单一致性/上下文长度/稳定性与错误率/计费口径核验/合规与内容安全/峰值并发压测）
 *      在 22 份 PRD 中零命中；09-PRD §2 的 D1–D8 是 TTFT/P50/一致性/RPM/TPM/缓存命中/模型指纹/真实源 → 设计示例名 ≠ 规范项名，
 *      行名以服务端 probe_name 为准，缺失时回退 09-PRD §2 名称，再缺失回退 probe_code（不得臆造第三种名字）。
 *   2) 设计「已完成 7 / 12 个检测项」是 12 项，而画布该卡片只有 8 行（设计内部不自洽）→ 进度优先取服务端 progress
 *      （percent/finished/total/eta_minutes，18-API 无字段级 schema → missing-prd），缺失时按返回的检测项条数派生。
 *   3) ProbeStatus（17-spec：SUCCESS/FAILED/SKIPPED/NOT_MEASURABLE）无 RUNNING/QUEUED，而设计有「进行中/排队中」两态
 *      → 三态映射为「服务端给的 status 到设计三态」的字典，未知状态原样直显（不臆造中文）。
 *   4) 设计无失败/完成态（无对应徽章文案与后续动作）→ 未覆盖状态原样直显 + 记台账待拍板。
 */
import { describe, expect, it } from 'vitest'
import {
  COST_SUB,
  COST_TITLE,
  HISTORY_TEXT,
  PAGE_TITLE,
  POLL_INTERVAL_MS,
  SECTION_LABEL,
  TIP_TEXT,
  TOTAL_LABEL,
  buildDetectingModel,
  shouldPoll
} from '@/utils/detecting-model'

/** 与设计稿 page-5-2 逐条一致的响应（示例态） */
const JOB = {
  id: 'j1',
  status: 'RUNNING',
  progress: { percent: 58, finished: 7, total: 12, eta_minutes: 42 }
}

const RESULTS = {
  job_id: 'j1',
  items: [
    { probe_code: 'D1', probe_name: '网络连通性', status: 'SUCCESS', detail: '236ms' },
    { probe_code: 'D2', probe_name: '鉴权有效性', status: 'SUCCESS', detail: '密钥有效' },
    { probe_code: 'D3', probe_name: '模型清单一致性', status: 'RUNNING', detail: '2/2 模型已核验' },
    { probe_code: 'D4', probe_name: '上下文长度', status: 'RUNNING', detail: '长文本压测中' },
    { probe_code: 'D5', probe_name: '稳定性与错误率', status: 'RUNNING', detail: '采样 30 / 100' },
    { probe_code: 'D6', probe_name: '计费口径核验', status: 'QUEUED' },
    { probe_code: 'D7', probe_name: '合规与内容安全', status: 'QUEUED' },
    { probe_code: 'D8', probe_name: '峰值并发压测', status: 'QUEUED' }
  ]
}

describe('detecting-model · 设计稿文案常量（page-5-2 原文，不得改写）', () => {
  it('标题/区块/成本保护/提示/按钮文案与设计稿一致', () => {
    expect(PAGE_TITLE).toBe('检测进行中')
    expect(TOTAL_LABEL).toBe('总进度')
    expect(SECTION_LABEL).toBe('分项检测')
    expect(COST_TITLE).toBe('检测期间已启用成本保护')
    expect(COST_SUB).toBe('本次检测由平台承担费用，不会计入你的账单')
    expect(TIP_TEXT).toBe('检测期间你可以先完善供应商档案，检测完成后会自动通知你，无需停留本页。')
    expect(HISTORY_TEXT).toBe('查看历史检测报告')
  })
})

describe('detecting-model · 服务端 progress 优先', () => {
  it('进度/计数/预计剩余取自服务端 progress（复现设计稿 58% · 7/12 · 42 分钟）', () => {
    const m = buildDetectingModel(JOB, RESULTS)
    expect(m.chipLabel).toBe('进行中')
    expect(m.percentText).toBe('58%')
    expect(m.percent).toBe(58)
    expect(m.finishedText).toBe('已完成 7 / 12 个检测项')
    expect(m.etaText).toBe('预计剩余 42 分钟')
  })

  it('progress 缺失 → 按返回的检测项条数派生（5 完成 / 8 条 = 63%），预计剩余不渲染', () => {
    const items = RESULTS.items.map((r, i) => (i < 5 ? { ...r, status: 'SUCCESS' } : r))
    const m = buildDetectingModel({ id: 'j1', status: 'RUNNING' }, { items })
    expect(m.percent).toBe(63)
    expect(m.percentText).toBe('63%')
    expect(m.finishedText).toBe('已完成 5 / 8 个检测项')
    expect(m.etaText).toBeUndefined()
  })

  it('progress 值非法（越界/非数字）→ 忽略该字段并派生，不把脏值渲染出去', () => {
    const items = [{ probe_code: 'D1', status: 'SUCCESS' }, { probe_code: 'D2', status: 'QUEUED' }]
    const m = buildDetectingModel({ status: 'RUNNING', progress: { percent: 180, finished: -1, total: 0 } }, { items })
    expect(m.percent).toBe(50)
    expect(m.finishedText).toBe('已完成 1 / 2 个检测项')
  })

  it('结果为空 → 0% · 0/0，不抛异常', () => {
    const m = buildDetectingModel({ status: 'QUEUED' }, { items: [] })
    expect(m.percent).toBe(0)
    expect(m.rows).toEqual([])
    expect(m.finishedText).toBe('已完成 0 / 0 个检测项')
  })
})

describe('detecting-model · 分项检测行（三态映射 + 行名回退）', () => {
  it('8 行逐条：名称「D<code> <name>」、详情「态 · 度量」、chip 文案与设计稿一致', () => {
    const m = buildDetectingModel(JOB, RESULTS)
    expect(m.rows).toHaveLength(8)
    expect(m.rows[0]).toMatchObject({
      code: 'D1',
      label: 'D1 网络连通性',
      detailText: '已通过 · 236ms',
      chipText: '完成',
      stateKey: 'done'
    })
    expect(m.rows[2]).toMatchObject({ label: 'D3 模型清单一致性', detailText: '进行中 · 2/2 模型已核验', chipText: '进行中', stateKey: 'running' })
    expect(m.rows[5]).toMatchObject({ label: 'D6 计费口径核验', detailText: '排队中', chipText: '排队中', stateKey: 'queued' })
  })

  it('无 probe_name → 回退 09-PRD §2 的名称；未知 probe_code → 用 code 本身', () => {
    const m = buildDetectingModel(JOB, {
      items: [
        { probe_code: 'D1', status: 'QUEUED' },
        { probe_code: 'D9', status: 'QUEUED' }
      ]
    })
    expect(m.rows[0].label).toBe('D1 TTFT')
    expect(m.rows[1].label).toBe('D9')
  })

  it('未知状态（FAILED/SKIPPED/NOT_MEASURABLE）→ 原样直显，不臆造中文', () => {
    const m = buildDetectingModel(JOB, { items: [{ probe_code: 'D1', status: 'FAILED', detail: '上游 401' }] })
    expect(m.rows[0].chipText).toBe('FAILED')
    expect(m.rows[0].stateKey).toBe('other')
    expect(m.rows[0].detailText).toBe('上游 401')
  })

  it('状态缺失 → 视为排队中（任务已入队但该项无结果）', () => {
    const m = buildDetectingModel(JOB, { items: [{ probe_code: 'D1' }] })
    expect(m.rows[0].stateKey).toBe('queued')
    expect(m.rows[0].detailText).toBe('排队中')
  })
})

describe('detecting-model · 顶部状态 chip 与轮询判定', () => {
  it('任务状态 RUNNING/QUEUED 映射设计徽章文案；未覆盖状态原样直显', () => {
    expect(buildDetectingModel({ status: 'RUNNING' }, RESULTS).chipLabel).toBe('进行中')
    expect(buildDetectingModel({ status: 'QUEUED' }, RESULTS).chipLabel).toBe('排队中')
    expect(buildDetectingModel({ status: 'FINISHED' }, RESULTS).chipLabel).toBe('FINISHED')
    expect(buildDetectingModel({}, RESULTS).chipLabel).toBe('')
  })

  it('shouldPoll：QUEUED/RUNNING/PARTIAL 继续轮询，终态/未知状态停止', () => {
    expect(shouldPoll('QUEUED')).toBe(true)
    expect(shouldPoll('RUNNING')).toBe(true)
    expect(shouldPoll('PARTIAL')).toBe(true)
    expect(shouldPoll('PARTIAL_DONE')).toBe(true)
    expect(shouldPoll('FINISHED')).toBe(false)
    expect(shouldPoll('COMPLETED')).toBe(false)
    expect(shouldPoll('REPORT_GENERATED')).toBe(false)
    expect(shouldPoll('FAILED')).toBe(false)
    expect(shouldPoll('CANCELLED')).toBe(false)
    expect(shouldPoll(undefined)).toBe(false)
    expect(shouldPoll('MAYBE')).toBe(false)
  })

  it('轮询间隔为常量（页面与测试共用，避免魔法数字）', () => {
    expect(POLL_INTERVAL_MS).toBe(5000)
  })
})
