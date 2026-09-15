/**
 * 序号 6【检测验真】大模型检测报告 · 多维度专业版（page-6）— 页面单测（先写，预期红）
 *
 * 文案与结构真源：.calicat/raw/pages/page-6/design.tree.json（430 宽）
 *   顶部 b362b5a2 · 结论封面卡 4e855266 · 关键指标卡 c13761bd · 维度总览卡 7530b31a
 *   明细卡 7806d174 · 风险发现卡 658a45d1 · 原始证据卡 9844215a · 免责声明卡 30918987 · 底部操作条 e096bd63
 * 交互分类（台账序号 6 行）：
 *   返回 = navigation(navigateBack 1)
 *   导出 PDF = api（GET /api/v1/reports/{reportId}/export，18-API Report Tag）
 *   填写报价 = navigation(navigateTo /pages/quote-form/index，画布序号 12-v1「新增报价单-初始态」）
 *   其余（评分/维度/明细/风险/证据）均为渲染态 → client-only
 * 接口：GET /api/v1/reports/{reportId}（18-API Report Tag；方法为 REST 语义推断，台账已记）
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ReportPage from '@/pages/report/index.vue'
import { EXPORT_TEXT, MISSING_REPORT_TOAST, QUOTE_TEXT, REPORT_ID_KEY } from '@/utils/report-model'
import { DESIGN_REPORT } from '../fixtures/report-fixture'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

async function mountPage(payload: unknown = DESIGN_REPORT, id = 'DR-1') {
  uni.setStorageSync(REPORT_ID_KEY, id)
  pushResponse(ok(payload))
  const wrapper = mount(ReportPage)
  await flushPromises()
  return wrapper
}

const texts = (wrapper: { findAll: (s: string) => { text: () => string }[] }, sel: string) =>
  wrapper.findAll(sel).map((n) => n.text())
const toastTitles = () => getCalls('showToast').map((c) => String((c.args[0] as { title?: string }).title ?? ''))

afterEach(() => {
  vi.restoreAllMocks()
})

describe('序号 6 · 页面：页头与结论卡文案与设计稿逐条一致', () => {
  it('标题「检测报告」+ 报告编号 + 返回按钮', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="title"]').text()).toBe('检测报告')
    expect(w.find('[data-testid="report-no"]').text()).toBe('DR-20240613-0758')
    expect(w.find('[data-testid="back-btn"]').exists()).toBe(true)
  })

  it('结论卡：综合评分 92 / 通过标签 / 通道名 / 结论措辞 / 信息清单 5 行', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="verdict-title"]').text()).toBe('综合检测结论')
    expect(w.find('[data-testid="channel"]').text()).toBe('华东主线路 · GPT 通道')
    expect(w.find('[data-testid="score"]').text()).toBe('92')
    expect(w.find('[data-testid="result-chip"]').text()).toBe('通过')
    expect(w.find('[data-testid="verdict-text"]').text()).toBe(DESIGN_REPORT.verdict)
    expect(texts(w, '[data-testid="info-label"]')).toEqual(['供应商', '凭证', '模型清单', '检测时间', '耗时 / 成本'])
    expect(texts(w, '[data-testid="info-value"]')).toEqual([
      '星辰云科技（Provider #P-2041）',
      'sk-••••••••••••••••4f2a',
      'gpt-4o · gpt-4o-mini · gpt-3.5-turbo',
      '2026-07-10 15:32 · 触发方式：提交凭证自动',
      '12 分 46 秒 · 预估 $1.86（实际 $1.72）'
    ])
  })

  it('状态四格：7/8 通过项 · 1 项不可测 · 较高置信度 · 未触发一票否决', async () => {
    const w = await mountPage()
    expect(texts(w, '[data-testid="status-value"]')).toEqual(['7/8', '1 项', '较高', '未触发'])
    expect(texts(w, '[data-testid="status-label"]')).toEqual(['通过项', '不可测', '置信度', '一票否决'])
  })
})

describe('序号 6 · 页面：关键指标 / 维度总览 / 明细三卡', () => {
  it('关键指标 6 项（标签 + 数值 + 单位 + 副行）', async () => {
    const w = await mountPage()
    expect(texts(w, '[data-testid="metric-label"]')).toEqual([
      '模型指纹相似度',
      'TTFT 首 token（P50）',
      'RPM 实测 / 申报',
      'TPM 实测',
      'Prompt 缓存',
      '服务可用性'
    ])
    expect(texts(w, '[data-testid="metric-value"]')).toEqual(['0.93', '268', '52', '1.24', '命中', '99.9'])
    expect(texts(w, '[data-testid="metric-sub"]')).toEqual([
      '高于告警线 0.70',
      'P90 620 ms',
      '达成 87%',
      '窗口内主动降速',
      'cached_tokens 字段可用',
      '30 分钟观测窗口'
    ])
  })

  it('维度总览 6 行均分 + 3 项图例', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="radar"]').exists()).toBe(true)
    expect(texts(w, '[data-testid="radar-label"]')).toEqual(['性能', '吞吐', '一致性', '指纹', '计费', '安全'])
    expect(texts(w, '[data-testid="dim-name"]')).toEqual([
      '时延与性能',
      '吞吐与限速',
      '一致与可靠',
      '模型指纹',
      '计量与计费',
      '安全与合规'
    ])
    expect(texts(w, '[data-testid="dim-score"]')).toEqual(['86', '84', '92', '90', '94', '92'])
    expect(texts(w, '[data-testid="legend-text"]')).toEqual(['计入总分', '仅证据', '不可测 / 未申报'])
  })

  it('全维度明细：7 个分组 + 55 项 + 说明行 + 共 55 项', async () => {
    const w = await mountPage()
    expect(texts(w, '[data-testid="section-title"]')).toHaveLength(7)
    expect(w.findAll('[data-testid="section-item"]')).toHaveLength(55)
    expect(w.find('[data-testid="detail-summary"]').text()).toBe(
      '46 项计入总分 · 7 项仅证据 · 1 项未申报 · 1 项不可测 · 打分 0–100'
    )
    expect(w.find('[data-testid="item-count"]').text()).toBe('共 55 项')
    expect(w.find('[data-testid="section-title"]').text()).toBe('A · 时延与性能')
    expect(texts(w, '[data-testid="item-label"]')[0]).toBe('A1 TTFT 首 token 延迟')
    expect(texts(w, '[data-testid="item-metric"]')[0]).toBe('P50 268 ms')
  })

  it('未申报 / 仅证据 / 不可测 三类状态词出现在明细里', async () => {
    const w = await mountPage()
    const all = w.findAll('[data-testid="section-item"]').map((n) => n.text())
    expect(all.some((t) => t.includes('每日配额') && t.includes('未申报'))).toBe(true)
    expect(all.some((t) => t.includes('证书签发机构') && t.includes('仅证据'))).toBe(true)
    expect(all.some((t) => t.includes('数据留存声明') && t.includes('不可测'))).toBe(true)
  })
})

describe('序号 6 · 页面：风险 / 证据 / 免责', () => {
  it('关键发现与风险 4 条（标题 + 正文）', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="risk-title"]').text()).toBe('关键发现与风险')
    expect(texts(w, '[data-testid="finding-title"]')).toEqual([
      '模型指纹与宣称一致',
      '长上下文时延偏高（A7 78）',
      '高并发能力受限（A8 74 / B3 82）',
      '数据留存声明缺失（不可测）'
    ])
    expect(texts(w, '[data-testid="finding-body"]')).toHaveLength(4)
  })

  it('原始证据（节选）6 行键值', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="evidence-title"]').text()).toBe('原始证据（节选）')
    expect(w.find('[data-testid="evidence-sub"]').text()).toBe('可导出')
    expect(texts(w, '[data-testid="evidence-key"]')).toEqual([
      'DNS / ASN',
      'TLS 证书',
      '响应头',
      'Tokenizer',
      '缓存字段',
      '错误样本'
    ])
  })

  it('免责声明：标题 + 正文含「不是"真 / 假"判决」', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="disclaimer-title"]').text()).toBe('本报告基于抽样检测生成')
    expect(w.find('[data-testid="disclaimer-text"]').text()).toBe(DESIGN_REPORT.disclaimer)
  })
})

describe('序号 6 · 页面：接口与交互分类', () => {
  it('首屏按 reportId 调 GET /api/v1/reports/{id}', async () => {
    await mountPage(DESIGN_REPORT, 'DR-9')
    const req = getCalls('request')[0].args[0] as { url: string; method: string }
    expect(req.url).toBe('/api/v1/reports/DR-9')
    expect(req.method).toBe('GET')
  })

  it('返回 = navigation(navigateBack 1)', async () => {
    const w = await mountPage()
    await w.find('[data-testid="back-btn"]').trigger('tap')
    expect(getCalls('navigateBack')[0].args[0]).toMatchObject({ delta: 1 })
  })

  it('导出 PDF = api(GET /export) + 提示（H5/小程序内不直接下载文件）', async () => {
    const w = await mountPage()
    pushResponse(ok({ url: 'https://cdn.example.com/dr-1.pdf', file_name: 'DR-1.pdf' }))
    await w.find('[data-testid="export-btn"]').trigger('tap')
    await flushPromises()
    const urls = getCalls('request').map((c) => (c.args[0] as { url: string }).url)
    expect(urls).toContain('/api/v1/reports/DR-1/export')
    expect(toastTitles().length).toBeGreaterThan(0)
    expect(w.find('[data-testid="export-btn"]').text()).toBe(EXPORT_TEXT)
  })

  it('填写报价 = navigation(navigateTo /pages/quote-form/index)', async () => {
    const w = await mountPage()
    await w.find('[data-testid="quote-btn"]').trigger('tap')
    expect(getCalls('navigateTo')[0].args[0]).toMatchObject({ url: '/pages/quote-form/index' })
    expect(w.find('[data-testid="quote-btn"]').text()).toBe(QUOTE_TEXT)
  })

  it('缺少报告标识时不发请求，只提示', async () => {
    await mountPage(DESIGN_REPORT, '')
    expect(getCalls('request')).toHaveLength(0)
    expect(toastTitles()).toContain(MISSING_REPORT_TOAST)
  })

  it('加载失败提示服务端消息且页面不崩（标题仍在）', async () => {
    uni.setStorageSync(REPORT_ID_KEY, 'DR-1')
    setNextResponse({ statusCode: 200, data: { code: 'E-1404', message: '报告不存在', data: null } })
    const w = mount(ReportPage)
    await flushPromises()
    expect(toastTitles()).toContain('报告不存在')
    expect(w.find('[data-testid="title"]').text()).toBe('检测报告')
  })
})
