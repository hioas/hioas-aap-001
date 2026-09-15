/**
 * 序号 7【检测验真】检测未通过报告 2（page-7-2）— 页面单测（先写，预期红）
 *
 * 文案与结构真源：.calicat/raw/pages/page-7-2/design.tree.json（430 宽）
 *   顶部导航 5cd2c5ba · 未通过封面卡 07b82bea · 分项评分总览卡 35a1df87 · D2详情卡 09ddc4ca
 *   免责声明卡 1b0391c3 · 底部操作 e60b6a5c
 * 交互分类（台账序号 7 行）：
 *   返回 = navigation(navigateBack 1)
 *   导出 PDF = api（GET /api/v1/reports/{reportId}/export，18-API Report Tag）
 *   重新提交检测 = api（POST /api/v1/detection-jobs，09-PRD §5「重测（人工点击）」；方法为 REST 语义推断）
 *   评分/分项/详情/免责 = client-only（渲染态）
 * 接口：GET /api/v1/reports/{reportId}（18-API Report Tag；方法为推断，台账已记）
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ReportFailedPage from '@/pages/report-failed/index.vue'
import {
  CREDENTIAL_ID_KEY,
  DETECTING_PAGE,
  EXPORT_TEXT,
  MISSING_CREDENTIAL_TOAST,
  MISSING_REPORT_TOAST,
  REPORT_ID_KEY,
  RESUBMIT_TEXT
} from '@/utils/report-failed-model'
import { DESIGN_REPORT_FAILED, DESIGN_RESUBMIT_RESULT } from '../fixtures/report-failed-fixture'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

async function mountPage(payload: unknown = DESIGN_REPORT_FAILED, id = 'DR-1') {
  uni.setStorageSync(REPORT_ID_KEY, id)
  pushResponse(ok(payload))
  const wrapper = mount(ReportFailedPage)
  await flushPromises()
  return wrapper
}

const texts = (
  wrapper: { findAll: (s: string) => { text: () => string }[] },
  sel: string
) => wrapper.findAll(sel).map((n) => n.text())
const toastTitles = () =>
  getCalls('showToast').map((c) => String((c.args[0] as { title?: string }).title ?? ''))

afterEach(() => {
  vi.restoreAllMocks()
})

describe('序号 7 · 页面：页头与结论封面卡文案与设计稿逐条一致', () => {
  it('标题「检测报告」+ 报告编号 + 返回按钮', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="title"]').text()).toBe('检测报告')
    // 设计稿顶部右侧是**单个**文本图层「报告编号 DR-20240614-0312」（含前缀），逐字还原
    expect(w.find('[data-testid="report-no"]').text()).toBe('报告编号 DR-20240614-0312')
    expect(w.find('[data-testid="back-btn"]').exists()).toBe(true)
  })

  it('结论卡：综合评分 54 / 未通过标签 / 通道名 / 一票否决条 / 结论措辞', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="verdict-title"]').text()).toBe('综合检测结论')
    expect(w.find('[data-testid="channel"]').text()).toBe('华南备线路 · 备用通道')
    expect(w.find('[data-testid="score"]').text()).toBe('54')
    expect(w.find('[data-testid="score-label"]').text()).toBe('综合评分')
    expect(w.find('[data-testid="score-max"]').text()).toBe('满分 100')
    expect(w.find('[data-testid="result-chip"]').text()).toBe('未通过')
    expect(w.find('[data-testid="veto-text"]').text()).toBe(DESIGN_REPORT_FAILED.veto_note)
    expect(w.find('[data-testid="verdict-text"]').text()).toBe(DESIGN_REPORT_FAILED.verdict)
  })

  it('未触发一票否决时不渲染否决条', async () => {
    const w = await mountPage({ ...DESIGN_REPORT_FAILED, veto_triggered: false, veto_note: null })
    expect(w.find('[data-testid="veto-text"]').exists()).toBe(false)
  })
})

describe('序号 7 · 页面：分项总览 8 行 + 详情卡 + 免责卡', () => {
  it('分项总览：8 行文案与分值（设计稿逐条）', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="dim-title"]').text()).toBe('分项总览')
    expect(texts(w, '[data-testid="dim-label"]')).toEqual([
      'D1 连通性',
      'D2 鉴权',
      'D3 模型一致性',
      'D4 上下文',
      'D5 稳定性',
      'D6 计费口径',
      'D7 合规安全',
      'D8 并发压测'
    ])
    expect(texts(w, '[data-testid="dim-score"]')).toEqual(['89', '12', '55', '82', '61', '66', '58', '0'])
    expect(w.find('[data-testid="weight-note"]').text()).toBe(
      'D2 鉴权为关键项，未通过将直接判定为“未通过”；其余分项仅作参考。'
    )
  })

  it('D2 详情卡：标题 / 12 分 / 四行解释', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="detail-title"]').text()).toBe('D2 鉴权有效性 · 详情')
    expect(w.find('[data-testid="detail-score"]').text()).toBe('12 分')
    expect(texts(w, '[data-testid="detail-line"]')).toEqual(DESIGN_REPORT_FAILED.detail.lines)
  })

  it('服务端无详情 → 详情卡不渲染', async () => {
    const w = await mountPage({ report_no: 'DR-1', dims: [] })
    expect(w.find('[data-testid="detail-card"]').exists()).toBe(false)
  })

  it('免责声明卡两行文案', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="disclaimer-title"]').text()).toBe('本报告基于抽样检测生成')
    expect(w.find('[data-testid="disclaimer-text"]').text()).toBe(
      '未通过结论仅代表检测时点状态，修正后重新检测即可更新结论。'
    )
  })

  it('无 TabBar（本页为二级页）', async () => {
    const w = await mountPage()
    expect(w.find('[data-testid="tabbar"]').exists()).toBe(false)
  })
})

describe('序号 7 · 页面：交互分类落地', () => {
  it('返回 = navigation(navigateBack 1)', async () => {
    const w = await mountPage()
    await w.find('[data-testid="back-btn"]').trigger('tap')
    expect(getCalls('navigateBack')[0].args[0]).toEqual({ delta: 1 })
  })

  it('导出 PDF = api（GET /reports/{reportId}/export）→ 提示', async () => {
    const w = await mountPage(DESIGN_REPORT_FAILED, 'DR-1')
    pushResponse(ok({ url: 'https://cdn/x.pdf', file_name: 'DR-1.pdf' }))
    await w.find('[data-testid="export-btn"]').trigger('tap')
    await flushPromises()

    const req = getCalls('request')[1].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/reports/DR-1/export')
    expect(req.method).toBe('GET')
    expect(w.find('[data-testid="export-btn"]').text()).toBe(EXPORT_TEXT)
    expect(toastTitles()).toContain('导出链接已生成，请在浏览器中打开')
  })

  it('重新提交检测 = api（POST /detection-jobs，带 credential_id）→ 跳检测进行中页并带 jobId', async () => {
    const w = await mountPage()
    pushResponse(ok(DESIGN_RESUBMIT_RESULT))
    await w.find('[data-testid="resubmit-btn"]').trigger('tap')
    await flushPromises()

    expect(w.find('[data-testid="resubmit-btn"]').text()).toBe(RESUBMIT_TEXT)
    const req = getCalls('request')[1].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/detection-jobs')
    expect(req.method).toBe('POST')
    expect(req.data).toEqual({ credential_id: 'c1' })
    expect(getCalls('navigateTo')[0].args[0]).toEqual({
      url: `${DETECTING_PAGE}?jobId=j9`
    })
  })

  it('缺凭证标识 → 不发请求，只提示', async () => {
    const w = await mountPage({ report_no: 'DR-1', credential_id: null })
    await w.find('[data-testid="resubmit-btn"]').trigger('tap')
    await flushPromises()

    expect(getCalls('request').length).toBe(1)
    expect(toastTitles()).toContain(MISSING_CREDENTIAL_TOAST)
    expect(getCalls('navigateTo').length).toBe(0)
  })

  it('无 query/storage 凭证时回退 storage 键 aap_credential_id', async () => {
    uni.setStorageSync(CREDENTIAL_ID_KEY, 'c9')
    const w = await mountPage({ report_no: 'DR-1', credential_id: null })
    pushResponse(ok({ id: 'j5' }))
    await w.find('[data-testid="resubmit-btn"]').trigger('tap')
    await flushPromises()

    const req = getCalls('request')[1].args[0] as Record<string, unknown>
    expect(req.data).toEqual({ credential_id: 'c9' })
    expect(getCalls('navigateTo')[0].args[0]).toEqual({ url: `${DETECTING_PAGE}?jobId=j5` })
  })

  it('检测互斥 E-1301 → 提示服务端文案，不跳转', async () => {
    const w = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-1301', message: '该凭证已有检测任务进行中' } })
    await w.find('[data-testid="resubmit-btn"]').trigger('tap')
    await flushPromises()

    expect(toastTitles()).toContain('该凭证已有检测任务进行中')
    expect(getCalls('navigateTo').length).toBe(0)
  })

  it('缺 reportId → 提示且不发请求', async () => {
    uni.setStorageSync(REPORT_ID_KEY, '')
    const w = mount(ReportFailedPage)
    await flushPromises()
    expect(toastTitles()).toContain(MISSING_REPORT_TOAST)
    expect(getCalls('request').length).toBe(0)
  })

  it('报告详情加载失败 → 提示服务端文案（不吞错）', async () => {
    uni.setStorageSync(REPORT_ID_KEY, 'DR-1')
    setNextResponse({ statusCode: 200, data: { code: 'E-1304', message: '报告不存在' } })
    const w = mount(ReportFailedPage)
    await flushPromises()
    expect(toastTitles()).toContain('报告不存在')
    expect(w.find('[data-testid="score"]').text()).toBe('—')
  })
})
