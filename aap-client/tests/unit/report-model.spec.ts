/**
 * 序号 6【检测验真】大模型检测报告 · 多维度专业版（page-6）— 视图模型单测（先写，预期红）
 *
 * 设计真源：.calicat/raw/pages/page-6/design.tree.json（430 宽）
 * 文案/数值真源：tests/fixtures/report-fixture.ts（逐字抄自设计稿）
 * 规则真源：09-PRD §3（总分与通过判定、结果三态）/ §4（报告生成）；21-验收 AC-18/AC-37/AC-38
 */
import { describe, expect, it } from 'vitest'
import {
  DETAIL_SCORE_HINT,
  DISCLAIMER_TITLE,
  EXPORT_TEXT,
  GROUP_COLORS,
  LEGEND_ITEMS,
  PAGE_TITLE,
  QUOTE_TEXT,
  RADAR_SHORT_LABELS,
  STATUS_CELL_LABELS,
  buildReportModel,
  radarDataUri,
  radarGeometry
} from '@/utils/report-model'
import { DESIGN_ITEM_LABELS, DESIGN_REPORT } from '../fixtures/report-fixture'

const model = buildReportModel(DESIGN_REPORT as never)

/** 测试侧最小 base64 解码（只处理 ASCII，用于校验 SVG 文本内容） */
function decodeBase64Ascii(b64: string): string {
  const table = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  const clean = b64.replace(/=+$/, '')
  let bits = ''
  for (const ch of clean) bits += table.indexOf(ch).toString(2).padStart(6, '0')
  let out = ''
  for (let i = 0; i + 8 <= bits.length; i += 8) out += String.fromCharCode(parseInt(bits.slice(i, i + 8), 2))
  return out
}

describe('序号 6 · 模型：标题与页头文案与 page-6 设计稿一致', () => {
  it('页面标题为「检测报告」，报告编号取服务端 report_no', () => {
    expect(PAGE_TITLE).toBe('检测报告')
    expect(model.reportNo).toBe('DR-20240613-0758')
  })

  it('底部两个按钮文案与设计稿一致（导出 PDF / 填写报价）', () => {
    expect(EXPORT_TEXT).toBe('导出 PDF')
    expect(QUOTE_TEXT).toBe('填写报价')
  })
})

describe('序号 6 · 模型：综合检测结论卡', () => {
  it('区块标题与通道名取自设计稿', () => {
    expect(model.verdictTitle).toBe('综合检测结论')
    expect(model.channelText).toBe('华东主线路 · GPT 通道')
  })

  it('综合评分数字与结论标签（PASS → 通过，绿色）', () => {
    expect(model.scoreText).toBe('92')
    expect(model.resultLabel).toBe('通过')
    expect(model.resultTone).toBe('success')
    expect(model.scoreSectionLabel).toBe('综合评分')
    expect(model.scoreMaxLabel).toBe('满分 100')
  })

  it('结果三态按 09-PRD §3 映射：FAIL → 未通过，MANUAL_REVIEW → 人工复核', () => {
    expect(buildReportModel({ result: 'FAIL' }).resultLabel).toBe('未通过')
    expect(buildReportModel({ result: 'MANUAL_REVIEW' }).resultLabel).toBe('人工复核')
    expect(buildReportModel({ result: 'FAIL' }).resultTone).toBe('danger')
  })

  it('状态四格：标签取设计稿，值来自服务端计数/置信度/否决开关', () => {
    expect(STATUS_CELL_LABELS).toEqual(['通过项', '不可测', '置信度', '一票否决'])
    expect(model.statusCells.map((c) => c.value)).toEqual(['7/8', '1 项', '较高', '未触发'])
    expect(model.statusCells.map((c) => c.label)).toEqual(['通过项', '不可测', '置信度', '一票否决'])
    // 「未触发」在设计稿里是绿色（design id=950cbd49 状态4）
    expect(model.statusCells[3].tone).toBe('success')
  })

  it('一票否决已触发时文案不臆造颜色（danger）', () => {
    const m = buildReportModel({ veto_triggered: true })
    expect(m.statusCells[3].value).toBe('已触发')
    expect(m.statusCells[3].tone).toBe('danger')
  })

  it('服务端给了 confidence_label 时优先直显，不覆盖', () => {
    expect(buildReportModel({ confidence: 'HIGH', confidence_label: '可靠子项一致' }).statusCells[2].value).toBe(
      '可靠子项一致'
    )
  })

  it('置信度无服务端标签时按 09-PRD「高/中/低」口径展示为设计稿措辞', () => {
    expect(buildReportModel({ confidence: 'HIGH' }).statusCells[2].value).toBe('较高')
    expect(buildReportModel({ confidence: 'MEDIUM' }).statusCells[2].value).toBe('中')
    expect(buildReportModel({ confidence: 'LOW' }).statusCells[2].value).toBe('低')
  })

  it('结论措辞与信息清单 5 行逐条与设计稿一致', () => {
    expect(model.verdict).toBe(DESIGN_REPORT.verdict)
    expect(model.infoRows.map((r) => r.label)).toEqual(['供应商', '凭证', '模型清单', '检测时间', '耗时 / 成本'])
    expect(model.infoRows[0].value).toBe('星辰云科技（Provider #P-2041）')
    expect(model.infoRows[1].value).toBe('sk-••••••••••••••••4f2a')
    expect(model.infoRows[2].value).toBe('gpt-4o · gpt-4o-mini · gpt-3.5-turbo')
    expect(model.infoRows[3].value).toBe('2026-07-10 15:32 · 触发方式：提交凭证自动')
    expect(model.infoRows[4].value).toBe('12 分 46 秒 · 预估 $1.86（实际 $1.72）')
  })
})

describe('序号 6 · 模型：关键指标卡（核心 6 项）', () => {
  it('6 项指标的标签/数值/单位/副行与设计稿逐条一致', () => {
    expect(model.metrics).toHaveLength(6)
    expect(model.metrics.map((m) => m.label)).toEqual([
      '模型指纹相似度',
      'TTFT 首 token（P50）',
      'RPM 实测 / 申报',
      'TPM 实测',
      'Prompt 缓存',
      '服务可用性'
    ])
    expect(model.metrics.map((m) => `${m.value}${m.unit}`)).toEqual([
      '0.93余弦',
      '268ms',
      '52/ 60',
      '1.24M/min',
      '命中78%',
      '99.9%'
    ])
    expect(model.metrics.map((m) => m.sub)).toEqual([
      '高于告警线 0.70',
      'P90 620 ms',
      '达成 87%',
      '窗口内主动降速',
      'cached_tokens 字段可用',
      '30 分钟观测窗口'
    ])
    expect(model.metrics[0].subTone).toBe('success')
    expect(model.metrics[1].subTone).toBe('muted')
  })

  it('缺失指标不伪造：无 key_metrics 时列表为空', () => {
    expect(buildReportModel({}).metrics).toEqual([])
  })
})

describe('序号 6 · 模型：维度总览卡（六维均分 + 雷达 + 图例）', () => {
  it('六行均分行的名称/分值/条形宽度与设计稿一致', () => {
    expect(model.dims.map((d) => d.name)).toEqual([
      '时延与性能',
      '吞吐与限速',
      '一致与可靠',
      '模型指纹',
      '计量与计费',
      '安全与合规'
    ])
    expect(model.dims.map((d) => d.scoreText)).toEqual(['86', '84', '92', '90', '94', '92'])
    // 设计稿条底宽 200，96→185/200=92.5% → 取整 93
    expect(model.dims.map((d) => d.barPercent)).toEqual([86, 84, 92, 90, 94, 92])
  })

  it('六行色点取设计稿原色（性能 #2563EB / 吞吐 #0891B2 / 一致 #16A34A / 指纹 #7C3AED / 计费 #D97706 / 安全 #E11D48）', () => {
    expect(model.dims.map((d) => d.color)).toEqual(['#2563EB', '#0891B2', '#16A34A', '#7C3AED', '#D97706', '#E11D48'])
    expect(GROUP_COLORS.A).toBe('#2563EB')
    expect(GROUP_COLORS.G).toBe('#64748B')
  })

  it('雷达轴 = 前六个计分组，轴名与设计稿短名一致', () => {
    expect(RADAR_SHORT_LABELS.A).toBe('性能')
    expect(model.radar.labels).toEqual(['性能', '吞吐', '一致性', '指纹', '计费', '安全'])
    expect(model.radar.values).toEqual([86, 84, 92, 90, 94, 92])
  })

  it('图例三项文案与色点与设计稿一致', () => {
    expect(LEGEND_ITEMS.map((l) => l.text)).toEqual(['计入总分', '仅证据', '不可测 / 未申报'])
    expect(LEGEND_ITEMS.map((l) => l.color)).toEqual(['#16A34A', '#64748B', '#D97706'])
  })

  it('雷达几何：6 个顶点成闭合多边形，首点在上方且半径与分值成比例', () => {
    const geo = radarGeometry([100, 50, 50, 50, 50, 50], { size: 176, radius: 78 })
    expect(geo.dots).toHaveLength(6)
    const [first, second] = geo.dots
    expect(Math.round(first.x)).toBe(88)
    expect(Math.round(first.y)).toBe(10) // 88 - 78*1
    expect(Math.round(second.x)).toBe(122) // 88 + 78*0.5*sin60 ≈ 121.8
    expect(geo.rings).toHaveLength(4)
    expect(geo.points.split(' ')).toHaveLength(6)
  })

  it('分值缺失/越界的维度在雷达上按 0 处理，不臆造数值', () => {
    const geo = radarGeometry([null, 84, 92, 90, 94, 92], { size: 176, radius: 78 })
    expect(geo.dots[0].x).toBe(88)
    expect(geo.dots[0].y).toBe(88)
  })

  it('雷达以 SVG data-URI 交给 <image>（mp-weixin 不支持内联 svg 标签，矢量图只能走 image）', () => {
    const uri = radarDataUri(radarGeometry([86, 84, 92, 90, 94, 92], { size: 176, radius: 78 }))
    expect(uri.startsWith('data:image/svg+xml;base64,')).toBe(true)
    const svg = decodeBase64Ascii(uri.split(',')[1])
    // 4 圈网格 + 6 条轴线（3 条交叉线）+ 6 个顶点圆点 + 1 个数据多边形
    expect((svg.match(/<polygon/g) || []).length).toBe(5)
    expect((svg.match(/<line/g) || []).length).toBe(6)
    expect((svg.match(/<circle/g) || []).length).toBe(6)
    expect(svg).toContain('fill="rgba(37,99,235,0.16)"')
    expect(svg).toContain('viewBox="0 0 176 176"')
  })
})

describe('序号 6 · 模型：全维度明细卡（55 项 / 7 分组）', () => {
  it('分组标题为「A · 时延与性能」…「G · 真实源证据（不计分）」，与设计稿逐条一致', () => {
    expect(model.sections.map((s) => s.title)).toEqual([
      'A · 时延与性能',
      'B · 吞吐与限速',
      'C · 一致性与可靠性',
      'D · 模型指纹（核心项）',
      'E · 计量与缓存计费',
      'F · 安全与合规',
      'G · 真实源证据（不计分）'
    ])
  })

  it('分组副标题「均分 86 · 9 项」，证据组不带均分', () => {
    expect(model.sections[0].meta).toBe('均分 86 · 9 项')
    expect(model.sections[1].meta).toBe('均分 84 · 8 项')
    expect(model.sections[6].meta).toBe('仅证据 · 6 项')
  })

  it('每项显示名「A1 TTFT 首 token 延迟」与度量摘要，逐条与设计稿一致（共 55 条）', () => {
    const labels = model.sections.flatMap((s) => s.items.map((i) => i.label))
    expect(labels).toEqual(DESIGN_ITEM_LABELS)
    expect(labels).toHaveLength(55)
    expect(model.sections[0].items[0].metric).toBe('P50 268 ms')
    expect(model.sections[0].items[3].metric).toBe('P50 3.1 s（500 / 256）')
    expect(model.sections[3].items[6].metric).toBe('多语文本集偏移 +1.2%')
  })

  it('计分项显示分值，条形宽度按分值（0–100）比例', () => {
    const a1 = model.sections[0].items[0]
    expect(a1.statusKey).toBe('scored')
    expect(a1.scoreText).toBe('92')
    expect(a1.barPercent).toBe(92)
    expect(a1.color).toBe('#2563EB')
  })

  it('未申报 / 仅证据 / 不可测 三类不显示分值，显示设计稿状态词', () => {
    const b8 = model.sections[1].items[7]
    expect(b8.statusKey).toBe('not_declared')
    expect(b8.scoreText).toBe('未申报')
    const f2 = model.sections[5].items[1]
    expect(f2.statusKey).toBe('evidence')
    expect(f2.scoreText).toBe('仅证据')
    const f7 = model.sections[5].items[6]
    expect(f7.statusKey).toBe('not_measurable')
    expect(f7.scoreText).toBe('不可测')
  })

  it('证据组（G，不计分）各项显示服务端证据值，不显示分值', () => {
    expect(model.sections[6].items.map((i) => i.statusKey)).toEqual([
      'evidence',
      'evidence',
      'evidence',
      'evidence',
      'evidence',
      'evidence'
    ])
    expect(model.sections[6].items[0].scoreText).toBe('20.42.xx.xx · AS8075 Azure')
    expect(model.sections[6].items[5].scoreText).toBe('未检出 cf-ray')
  })

  it('区分「值 pill」与「状态标签 pill」：G 组各项的值是数据，F 组的仅证据/不可测是标签', () => {
    // 设计依据：G 组各项的值图层（如 ef69fd0e「20.42.xx.xx · AS8075 Azure」）声明 fs=11 / Regular，
    // 而 F 组标签 pill 的图层（1b3c9a9f「仅证据」/ 66800e15「不可测」）声明 fs=10 / SemiBold(600)
    // → 两者必须能在视图模型里被区分（否则实现只能二选一，必然错一半）
    expect(model.sections[6].items.every((i) => i.statusIsValue)).toBe(true)
    const f2 = model.sections[5].items[1]
    expect(f2.scoreText).toBe('仅证据')
    expect(f2.statusIsValue).toBe(false)
    const f7 = model.sections[5].items[6]
    expect(f7.scoreText).toBe('不可测')
    expect(f7.statusIsValue).toBe(false)
    // 计分行的分值不是 pill，也不许被标成值 pill
    expect(model.sections[0].items[0].statusIsValue).toBe(false)
  })

  it('明细说明行由真实条数派生（46 计入总分 · 7 仅证据 · 1 项未申报 · 1 项不可测 · 打分 0–100）', () => {
    expect(model.detailSummary).toBe('46 项计入总分 · 7 项仅证据 · 1 项未申报 · 1 项不可测 · ' + DETAIL_SCORE_HINT)
    expect(DETAIL_SCORE_HINT).toBe('打分 0–100')
    expect(model.itemCountText).toBe('共 55 项')
  })

  it('未知状态原样直显，不臆造中文', () => {
    const m = buildReportModel({
      sections: [{ code: 'A', name: '时延与性能', avg: null, scored: true, items: [{ code: 'A1', name: 'x', status: 'WEIRD' }] }]
    })
    expect(m.sections[0].items[0].scoreText).toBe('WEIRD')
    expect(m.sections[0].items[0].statusKey).toBe('other')
  })
})

describe('序号 6 · 模型：风险 / 证据 / 免责 / 说明', () => {
  it('关键发现 4 条（标题 + 正文 + 色调）与设计稿一致', () => {
    expect(model.findings).toHaveLength(4)
    expect(model.findings.map((f) => f.title)).toEqual([
      '模型指纹与宣称一致',
      '长上下文时延偏高（A7 78）',
      '高并发能力受限（A8 74 / B3 82）',
      '数据留存声明缺失（不可测）'
    ])
    expect(model.findings.map((f) => f.tone)).toEqual(['success', 'warning', 'warning', 'info'])
    expect(model.findings[1].body).toBe('128K 输入下 P50 9.4 s，低于同类中位；建议对超长上下文场景设置超时与降级策略。')
  })

  it('原始证据 6 行键值对与设计稿一致', () => {
    expect(model.evidenceRows.map((r) => r.key)).toEqual([
      'DNS / ASN',
      'TLS 证书',
      '响应头',
      'Tokenizer',
      '缓存字段',
      '错误样本'
    ])
    expect(model.evidenceRows[4].value).toBe('usage.prompt_tokens_details.cached_tokens = 1560')
  })

  it('免责声明标题 + 正文（含「不是"真 / 假"判决」措辞）与设计稿一致', () => {
    expect(DISCLAIMER_TITLE).toBe('本报告基于抽样检测生成')
    expect(model.disclaimer).toBe(DESIGN_REPORT.disclaimer)
    expect(model.disclaimer).toContain('不是"真 / 假"判决')
    expect(model.disclaimer).toContain('报告有效期 30 天')
  })

  it('一票否决说明与权重说明为设计稿原文（本次不按 PRD 改写，冲突已记台账）', () => {
    expect(model.vetoNote).toBe(DESIGN_REPORT.veto_note)
    expect(model.weightNote).toBe(DESIGN_REPORT.weight_note)
  })

  it('服务端未给说明文案时回退设计稿原文，不显示空白', () => {
    const m = buildReportModel({})
    expect(m.vetoNote).toBe(DESIGN_REPORT.veto_note)
    expect(m.weightNote).toBe(DESIGN_REPORT.weight_note)
    expect(m.disclaimer).toContain('报告有效期 30 天')
  })
})

describe('序号 6 · 模型：空数据不崩', () => {
  it('null / undefined 入参返回空壳模型', () => {
    const m = buildReportModel(null)
    expect(m.sections).toEqual([])
    expect(m.itemCountText).toBe('共 0 项')
    expect(m.scoreText).toBe('—')
    expect(m.statusCells[0].value).toBe('—/—')
  })
})
