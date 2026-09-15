/**
 * 序号 5【检测验真】检测进行中 2（序号 5 / page-5-2）— 页面单测（先写，预期红）
 *
 * 文案与结构真源：.calicat/raw/pages/page-5-2/design.tree.json（430 宽，129 图层）
 *   顶部导航 c2a2498d · 总进度卡片 88f1ee17 · 分项进度卡片 2138c3d3（8 行）· 提示卡片 c960eff4 · 底部操作条 ed66b6f1
 * 交互分类（台账序号 5 行）：
 *   返回 = navigation(navigateBack 1)
 *   「查看历史检测报告」= client-only（画布 30 页无「历史检测报告」页；18-API 的 GET /reports 无对应页面设计 → 不臆造路由）
 *   页面轮询 = client-only（GET /detection-jobs/{jobId} + /results，进行中每 5s 一次，终态停止）
 * 接口：18-API Detection Tag → GET /api/v1/detection-jobs/{jobId}、GET /api/v1/detection-jobs/{jobId}/results
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DetectingPage from '@/pages/detecting/index.vue'
import { MISSING_JOB_TOAST, POLL_INTERVAL_MS } from '@/utils/detecting-model'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const JOB_KEY = 'aap_detection_job_id'

/** 与设计稿 page-5-2 逐条一致的示例态响应 */
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

async function mountPage(job: unknown = JOB, results: unknown = RESULTS, id = 'j1') {
  uni.setStorageSync(JOB_KEY, id)
  pushResponse(ok(job))
  pushResponse(ok(results))
  const wrapper = mount(DetectingPage)
  await flushPromises()
  return wrapper
}

const toastTitles = () => getCalls('showToast').map((c) => String((c.args[0] as { title?: string }).title ?? ''))
const texts = (wrapper: { findAll: (s: string) => { text: () => string }[] }, sel: string) =>
  wrapper.findAll(sel).map((n) => n.text())

afterEach(() => {
  vi.restoreAllMocks()
})

describe('页面 5 · 渲染：文案与 page-5-2 设计稿逐条一致', () => {
  it('顶部导航：返回按钮 + 标题「检测进行中」+ 状态 chip「进行中」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="back-btn"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('检测进行中')
    expect(wrapper.find('[data-testid="status-chip"]').text()).toBe('进行中')
  })

  it('总进度卡片：总进度 / 58% / 进度条 58% / 已完成 7 / 12 个检测项 / 预计剩余 42 分钟', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="total-label"]').text()).toBe('总进度')
    expect(wrapper.find('[data-testid="total-percent"]').text()).toBe('58%')
    expect((wrapper.find('[data-testid="progress-fill"]').element as HTMLElement).style.width).toBe('58%')
    expect(wrapper.find('[data-testid="progress-finished"]').text()).toBe('已完成 7 / 12 个检测项')
    expect(wrapper.find('[data-testid="eta-text"]').text()).toBe('预计剩余 42 分钟')
  })

  it('成本保护行：两行文案（design id=257b52bf）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="cost-block"]').text()).toContain('检测期间已启用成本保护')
    expect(wrapper.find('[data-testid="cost-block"]').text()).toContain('本次检测由平台承担费用，不会计入你的账单')
  })

  it('分项检测卡片：标题 + 8 行，每行名称/详情/状态 chip 与设计稿一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="section-label"]').text()).toBe('分项检测')
    expect(texts(wrapper, '[data-testid="probe-name"]')).toEqual([
      'D1 网络连通性',
      'D2 鉴权有效性',
      'D3 模型清单一致性',
      'D4 上下文长度',
      'D5 稳定性与错误率',
      'D6 计费口径核验',
      'D7 合规与内容安全',
      'D8 峰值并发压测'
    ])
    expect(texts(wrapper, '[data-testid="probe-detail"]')).toEqual([
      '已通过 · 236ms',
      '已通过 · 密钥有效',
      '进行中 · 2/2 模型已核验',
      '进行中 · 长文本压测中',
      '进行中 · 采样 30 / 100',
      '排队中',
      '排队中',
      '排队中'
    ])
    expect(texts(wrapper, '[data-testid="probe-chip"]')).toEqual([
      '完成',
      '完成',
      '进行中',
      '进行中',
      '进行中',
      '排队中',
      '排队中',
      '排队中'
    ])
  })

  it('提示卡片 + 底部按钮文案（design id=c960eff4 / 73a98024）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="tip-card"]').text()).toBe(
      '检测期间你可以先完善供应商档案，检测完成后会自动通知你，无需停留本页。'
    )
    expect(wrapper.find('[data-testid="history-btn"]').text()).toBe('查看历史检测报告')
  })

  it('三态行带上各自的状态类（供样式区分，done/running/queued）', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="probe-row"]')
    expect(rows[0].classes()).toContain('probe-row--done')
    expect(rows[2].classes()).toContain('probe-row--running')
    expect(rows[5].classes()).toContain('probe-row--queued')
  })
})

describe('页面 5 · 交互', () => {
  it('返回 → navigateBack(delta 1)，不发起导航到别的路由', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="back-btn"]').trigger('tap')
    expect(getCalls('navigateBack')[0].args[0]).toEqual({ delta: 1 })
    expect(getCalls('navigateTo')).toHaveLength(0)
  })

  it('「查看历史检测报告」→ client-only（画布无该页）：只 toast，不 navigateTo', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="history-btn"]').trigger('tap')
    expect(getCalls('navigateTo')).toHaveLength(0)
    expect(toastTitles()).toContain('历史检测报告可在凭证列表中查看')
  })

  it('页面入参：query 里的 jobId 优先，并写入 storage 兜底；两个接口路径正确', async () => {
    // @ts-expect-error 测试注入页面栈
    globalThis.getCurrentPages = () => [{ options: { jobId: 'j9' } }]
    pushResponse(ok(JOB))
    pushResponse(ok(RESULTS))
    const wrapper = mount(DetectingPage)
    await flushPromises()
    const urls = getCalls('request').map((c) => String((c.args[0] as { url?: string }).url))
    expect(urls).toContain('/api/v1/detection-jobs/j9')
    expect(urls).toContain('/api/v1/detection-jobs/j9/results')
    // @ts-expect-error 清理注入
    delete globalThis.getCurrentPages
    wrapper.unmount()
  })

  it('无 jobId → 不发请求，只提示', async () => {
    const wrapper = mount(DetectingPage)
    await flushPromises()
    expect(getCalls('request')).toHaveLength(0)
    expect(toastTitles()).toContain(MISSING_JOB_TOAST)
    wrapper.unmount()
  })

  it('加载失败（服务端 message）→ toast 服务端文案，页面不崩', async () => {
    uni.setStorageSync(JOB_KEY, 'j1')
    setNextResponse({ statusCode: 200, data: { code: 'E-1301', message: '该凭证已有检测任务进行中' } })
    const wrapper = mount(DetectingPage)
    await flushPromises()
    expect(toastTitles()).toContain('该凭证已有检测任务进行中')
    // 无任务数据 → 不臆造顶部徽章（chipLabel 为空即不渲染），但页面骨架仍在
    expect(wrapper.find('[data-testid="back-btn"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="status-chip"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="probe-row"]')).toHaveLength(0)
    wrapper.unmount()
  })
})

describe('页面 5 · 轮询（client-only，进行中每 5s，终态停止）', () => {
  it('进行中每 5s 再拉一轮；收到终态后停止轮询（clearInterval 被调用且不再发请求）', async () => {
    const setSpy = vi.spyOn(globalThis, 'setInterval')
    const clearSpy = vi.spyOn(globalThis, 'clearInterval')
    const wrapper = await mountPage()
    expect(getCalls('request')).toHaveLength(2)
    expect(setSpy.mock.calls[0][1]).toBe(POLL_INTERVAL_MS)
    const tick = setSpy.mock.calls[0][0] as () => void

    // 第二轮：仍在进行中
    pushResponse(ok(JOB))
    pushResponse(ok(RESULTS))
    tick()
    await flushPromises()
    expect(getCalls('request')).toHaveLength(4)

    // 第三轮：任务终态 → 停止
    pushResponse(ok({ ...JOB, status: 'FINISHED' }))
    pushResponse(ok(RESULTS))
    tick()
    await flushPromises()
    expect(clearSpy).toHaveBeenCalled()
    expect(wrapper.find('[data-testid="status-chip"]').text()).toBe('FINISHED')

    const settled = getCalls('request').length
    tick()
    await flushPromises()
    expect(getCalls('request')).toHaveLength(settled)

    wrapper.unmount()
  })

  it('组件卸载时清理定时器', async () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval')
    const wrapper = await mountPage()
    wrapper.unmount()
    expect(clearSpy).toHaveBeenCalled()
  })
})
