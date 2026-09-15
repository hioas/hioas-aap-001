/**
 * 序号 7【检测验真】检测未通过报告 2（page-7-2）— 视图模型单测（先写，预期红）
 *
 * 设计真源：.calicat/raw/pages/page-7-2/design.tree.json（430 宽）
 *   顶部导航 5cd2c5ba · 未通过封面卡 07b82bea · 分项评分总览卡 35a1df87 · D2详情卡 09ddc4ca
 *   免责声明卡 1b0391c3 · 底部操作 e60b6a5c（导出 PDF 193×44 + 重新提交检测 fill×44 #2563EB）
 * 交互真源：page-7-2 interaction.json =「不存在图层交互数据」→ 退 PRD 09/17-spec/18-API/21-验收
 *
 * ⚠️ 已知缺口（全部记台账序号 7 备注，不臆造）：
 *   1) 设计 D1–D8 名（连通性/鉴权/模型一致性/上下文/稳定性/计费口径/合规安全/并发压测）
 *      与 09-PRD §2 的 D1 TTFT / D2 P50-TPS / D3 一致性 / D4 RPM / D5 TPM / D6 缓存命中 /
 *      D7 模型指纹 / D8 真实源 **不是同一套口径**（设计「D2 鉴权」在 PRD D 列表中不存在）
 *      → 分项名与分值与一票否决项一律以服务端返回为准，设计示例值仅作夹具。
 *   2) 一票否决维度冲突：设计「D2 鉴权为关键项」vs 17-spec R-20 / 13-管理端PRD「D7<40 否决」
 *      → 文案按设计稿原文直显（不静默改写），冲突记台账待人类拍板。
 *   3) 配色阈值：设计样本 82/89 绿、55/58/61/66 琥珀、12/0 红 —— 与 09-PRD §3 pass_score=70、
 *      17-spec R-20 否决线 40 自洽，故取 70/40（非 80/40）。
 */
import { describe, expect, it } from 'vitest'
import {
  DEFAULT_DISCLAIMER,
  DEFAULT_VERDICT,
  DETAIL_TITLE,
  DIM_TITLE,
  DISCLAIMER_TITLE,
  EXPORT_TEXT,
  PAGE_TITLE,
  PASS_SCORE,
  REPORT_NO_PREFIX,
  RESUBMIT_TEXT,
  RESULT_LABELS,
  SCORE_LABEL,
  SCORE_MAX_LABEL,
  VETO_SCORE,
  VERDICT_TITLE,
  WEIGHT_NOTE,
  buildReportFailedModel,
  scoreColor
} from '@/utils/report-failed-model'
import { PLACEHOLDER } from '@/utils/format'
import { DESIGN_REPORT_FAILED } from '../fixtures/report-failed-fixture'

describe('序号 7 · 模型：设计稿原文常量逐条一致（不得改写）', () => {
  it('页头与结论卡文案', () => {
    expect(PAGE_TITLE).toBe('检测报告')
    expect(REPORT_NO_PREFIX).toBe('报告编号 ')
    expect(VERDICT_TITLE).toBe('综合检测结论')
    expect(SCORE_LABEL).toBe('综合评分')
    expect(SCORE_MAX_LABEL).toBe('满分 100')
  })

  it('分项总览卡文案与权重说明（design 18dda7b2 逐字）', () => {
    expect(DIM_TITLE).toBe('分项总览')
    expect(WEIGHT_NOTE).toBe('D2 鉴权为关键项，未通过将直接判定为“未通过”；其余分项仅作参考。')
  })

  it('详情卡标题 / 免责卡 / 底部按钮文案', () => {
    expect(DETAIL_TITLE).toBe('D2 鉴权有效性 · 详情')
    expect(DISCLAIMER_TITLE).toBe('本报告基于抽样检测生成')
    expect(DEFAULT_DISCLAIMER).toBe('未通过结论仅代表检测时点状态，修正后重新检测即可更新结论。')
    expect(EXPORT_TEXT).toBe('导出 PDF')
    expect(RESUBMIT_TEXT).toBe('重新提交检测')
  })

  it('结果三态映射取自 09-PRD §3（通过 / 未通过 / 人工复核）', () => {
    expect(RESULT_LABELS.PASS).toBe('通过')
    expect(RESULT_LABELS.FAIL).toBe('未通过')
    expect(RESULT_LABELS.MANUAL_REVIEW).toBe('人工复核')
  })

  it('配色阈值取自 09-PRD pass_score 与 17-spec R-20 否决线', () => {
    expect(PASS_SCORE).toBe(70)
    expect(VETO_SCORE).toBe(40)
  })
})

describe('序号 7 · 模型：页头与结论封面卡', () => {
  it('报告编号 / 通道名 / 综合分 / 结论标签 与设计稿一致', () => {
    const m = buildReportFailedModel(DESIGN_REPORT_FAILED)
    expect(m.reportNo).toBe('DR-20240614-0312')
    expect(m.channel).toBe('华南备线路 · 备用通道')
    expect(m.scoreText).toBe('54')
    expect(m.resultLabel).toBe('未通过')
  })

  it('一票否决条与结论措辞按服务端文案渲染（设计示例同文）', () => {
    const m = buildReportFailedModel(DESIGN_REPORT_FAILED)
    expect(m.vetoVisible).toBe(true)
    expect(m.vetoText).toBe('命中一票否决项：D2 鉴权在检测期间返回 401，模型清单存在 1 项无法调用。')
    expect(m.verdictText).toBe('请核对 APIKey 有效期与模型开放范围后重新提交检测；已通过项无需重复准备。')
  })

  it('未触发一票否决时该条不渲染', () => {
    const m = buildReportFailedModel({ ...DESIGN_REPORT_FAILED, veto_triggered: false, veto_note: null })
    expect(m.vetoVisible).toBe(false)
  })

  it('触发否决但服务端未给措辞 → 回退设计稿原文（不回退成空白）', () => {
    const m = buildReportFailedModel({ veto_triggered: true })
    expect(m.vetoVisible).toBe(true)
    expect(m.vetoText).toBe('命中一票否决项：D2 鉴权在检测期间返回 401，模型清单存在 1 项无法调用。')
  })

  it('结果值未知时原样直显，缺失时按本页语义默认「未通过」', () => {
    expect(buildReportFailedModel({ result: 'PASS' }).resultLabel).toBe('通过')
    expect(buildReportFailedModel({ result: 'MANUAL_REVIEW' }).resultLabel).toBe('人工复核')
    expect(buildReportFailedModel({ result: 'WEIRD' }).resultLabel).toBe('WEIRD')
    expect(buildReportFailedModel({}).resultLabel).toBe('未通过')
  })

  it('综合分缺失 → 占位符（不臆造数字）', () => {
    expect(buildReportFailedModel({}).scoreText).toBe(PLACEHOLDER)
  })
})

describe('序号 7 · 模型：分项总览 8 行（设计稿逐条）', () => {
  it('行文案 = 「code 名称」，分值与设计稿一致', () => {
    const m = buildReportFailedModel(DESIGN_REPORT_FAILED)
    expect(m.dims.map((d) => d.label)).toEqual([
      'D1 连通性',
      'D2 鉴权',
      'D3 模型一致性',
      'D4 上下文',
      'D5 稳定性',
      'D6 计费口径',
      'D7 合规安全',
      'D8 并发压测'
    ])
    expect(m.dims.map((d) => d.scoreText)).toEqual(['89', '12', '55', '82', '61', '66', '58', '0'])
    expect(m.dims.map((d) => d.score)).toEqual([89, 12, 55, 82, 61, 66, 58, 0])
  })

  it('条长 = 分值百分比（clamp 0–100），与设计 8 行中的 6 行自洽口径一致', () => {
    const m = buildReportFailedModel(DESIGN_REPORT_FAILED)
    expect(m.dims.map((d) => d.barPercent)).toEqual([89, 12, 55, 82, 61, 66, 58, 0])
    expect(buildReportFailedModel({ dims: [{ code: 'D1', name: 'x', score: 120 }] }).dims[0].barPercent).toBe(100)
    expect(buildReportFailedModel({ dims: [{ code: 'D1', name: 'x', score: -5 }] }).dims[0].barPercent).toBe(0)
  })

  it('配色：≥70 绿 #16A34A · 40–69 琥珀 #F59E0B · <40 红 #DC2626（与设计取色一一对上）', () => {
    const m = buildReportFailedModel(DESIGN_REPORT_FAILED)
    expect(m.dims.map((d) => d.color)).toEqual([
      '#16A34A',
      '#DC2626',
      '#F59E0B',
      '#16A34A',
      '#F59E0B',
      '#F59E0B',
      '#F59E0B',
      '#DC2626'
    ])
    expect(scoreColor(70)).toBe('#16A34A')
    expect(scoreColor(69)).toBe('#F59E0B')
    expect(scoreColor(40)).toBe('#F59E0B')
    expect(scoreColor(39)).toBe('#DC2626')
    expect(scoreColor(null)).toBe('#E2E8F0')
  })

  it('分值缺失的行不臆造分数（scoreText 占位、条长 0）', () => {
    const m = buildReportFailedModel({ dims: [{ code: 'D1', name: '连通性' }] })
    expect(m.dims[0].scoreText).toBe(PLACEHOLDER)
    expect(m.dims[0].score).toBeNull()
    expect(m.dims[0].barPercent).toBe(0)
  })
})

describe('序号 7 · 模型：D2 详情卡与免责卡', () => {
  it('详情卡标题 / 分数 / 四行解释（现象·依据·影响·建议）逐条一致', () => {
    const m = buildReportFailedModel(DESIGN_REPORT_FAILED)
    expect(m.detail.visible).toBe(true)
    expect(m.detail.title).toBe('D2 鉴权有效性 · 详情')
    expect(m.detail.scoreText).toBe('12 分')
    expect(m.detail.lines).toEqual([
      '· 现象：第 3 次探测返回 401 Unauthorized。',
      '· 依据：APIKey 与 BaseURL 不匹配，或密钥已轮换失效。',
      '· 影响：无法建立稳定转发链路，暂不可承接业务。',
      '· 建议：更新 APIKey 后重新提交检测。'
    ])
  })

  it('服务端未返回详情 → 不渲染该卡（不臆造内容）', () => {
    const m = buildReportFailedModel({ report_no: 'DR-1' })
    expect(m.detail.visible).toBe(false)
    expect(m.detail.lines).toEqual([])
  })

  it('免责卡：标题为设计原文，正文服务端优先、缺失回退设计原文', () => {
    expect(buildReportFailedModel(DESIGN_REPORT_FAILED).disclaimerText).toBe(DEFAULT_DISCLAIMER)
    expect(buildReportFailedModel({}).disclaimerTitle).toBe('本报告基于抽样检测生成')
    expect(buildReportFailedModel({ disclaimer: '服务端文案' }).disclaimerText).toBe('服务端文案')
  })

  it('凭证 id 透传（重新提交检测的请求体依据）', () => {
    expect(buildReportFailedModel(DESIGN_REPORT_FAILED).credentialId).toBe('c1')
    expect(buildReportFailedModel({}).credentialId).toBe('')
  })
})

describe('序号 7 · 模型：空壳入参', () => {
  it('null / undefined / {} 返回空壳模型且文案仍为设计原文', () => {
    for (const raw of [null, undefined, {}]) {
      const m = buildReportFailedModel(raw)
      expect(m.dims).toEqual([])
      expect(m.reportNo).toBe('')
      expect(m.channel).toBe('')
      expect(m.scoreText).toBe(PLACEHOLDER)
      expect(m.resultLabel).toBe('未通过')
      expect(m.vetoVisible).toBe(false)
      expect(m.verdictText).toBe(DEFAULT_VERDICT)
      expect(m.weightNote).toBe(WEIGHT_NOTE)
      expect(m.detail.visible).toBe(false)
    }
  })
})
