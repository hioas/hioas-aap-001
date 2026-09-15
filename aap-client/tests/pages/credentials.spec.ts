/**
 * 页面 3【工作台与我的】凭证列表-有数据（序号 3 / page-3）— 页面单测
 *
 * 文案与结构真源：.calicat/raw/pages/page-3/design.tree.json（430 宽；顶部栏/接入凭证按钮/
 *   列表标题行/状态统计行/凭证列表卡(表头+10 行)/列表底部说明/底部 TabBar）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 17-spec / 18-API + 画布页面清单
 * 接口：GET /api/v1/credentials（18-API Credential Tag）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CredentialsPage from '@/pages/credentials/index.vue'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const models = (n: number) => Array.from({ length: n }, (_, i) => ({ model_name: `m${i}` }))

const LIST = {
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

async function mountPage() {
  pushResponse(ok(LIST))
  const wrapper = mount(CredentialsPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

describe('页面 3 · 结构与设计稿一致', () => {
  it('顶部栏文案：凭证列表 / 统一管理客户检测凭证', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('凭证列表')
    expect(wrapper.text()).toContain('统一管理客户检测凭证')
  })

  it('「接入凭证」按钮文案与设计稿一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="submit-btn"]').text()).toContain('接入凭证')
  })

  it('列表标题行「凭证列表 / 共 10 条」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('共 10 条')
  })

  it('状态统计行 4 个：待检测 3 / 检测中 2 / 不通过 1 / 通过 4', async () => {
    const wrapper = await mountPage()
    const chips = wrapper.findAll('.chip')
    expect(chips).toHaveLength(4)
    expect(chips.map((c) => c.text())).toEqual(['待检测3', '检测中2', '不通过1', '通过4'])
  })

  it('表头 4 列文案：凭证名称 / 模型数 / 状态 / 查看', async () => {
    const wrapper = await mountPage()
    const head = wrapper.find('.cred-card__head')
    expect(head.text()).toContain('凭证名称')
    expect(head.text()).toContain('模型数')
    expect(head.text()).toContain('状态')
    expect(head.text()).toContain('查看')
  })

  it('列表 10 行，逐行名称/时间/模型数与设计稿一致', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="cred-row"]')
    expect(rows).toHaveLength(10)
    expect(rows[0].text()).toContain('华东主线路 · GPT 通道')
    expect(rows[0].text()).toContain('2026-07-10 14:08:21')
    expect(rows[0].find('.cred-row__models').text()).toBe('2')
    expect(rows[1].text()).toContain('华北备用 · Claude 通道')
    expect(rows[9].text()).toContain('港澳线路 · GPT 通道')
    expect(rows.map((r) => r.find('.cred-row__models').text())).toEqual(['2', '5', '3', '1', '4', '6', '2', '3', '5', '4'])
  })

  it('「报告」链接只出现在 通过/不通过 行（设计稿 5 条）', async () => {
    const wrapper = await mountPage()
    const reports = wrapper.findAll('[data-testid^="row-report-"]')
    expect(reports).toHaveLength(5)
    expect(reports.every((r) => r.text() === '报告')).toBe(true)
  })

  it('行状态点颜色取自设计稿（绿=通过 蓝=检测中 灰=待检测 红=不通过）', async () => {
    const wrapper = await mountPage()
    const dots = wrapper.findAll('.cred-row__dot')
    expect(dots).toHaveLength(10)
    // jsdom 会把 style 里的 hex 归一成 rgb(...)，故按设计稿色值的等价写法断言
    expect(dots[0].attributes('style')).toContain('rgb(22, 163, 74)') // #16a34a 通过
    expect(dots[1].attributes('style')).toContain('rgb(37, 99, 235)') // #2563eb 检测中
    expect(dots[2].attributes('style')).toContain('rgb(148, 163, 184)') // #94a3b8 待检测
    expect(dots[3].attributes('style')).toContain('rgb(239, 68, 68)') // #ef4444 不通过
  })

  it('列表底部说明与设计稿一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('仅展示最近接入的 10 条凭证记录')
  })

  it('底部 TabBar 4 项，当前高亮「工作台」', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('.tabbar__item')).toHaveLength(4)
    expect(wrapper.find('.tabbar__label--active').text()).toBe('工作台')
  })
})

describe('页面 3 · 数据来自接口', () => {
  it('挂载即请求 GET /api/v1/credentials（page=1 pageSize=10）', async () => {
    await mountPage()
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    const req = calls[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/credentials')
    expect(req.method).toBe('GET')
    expect(req.data).toMatchObject({ page: 1, pageSize: 10 })
  })

  it('列表内容全部来自接口响应（不硬编码设计稿数据）', async () => {
    pushResponse(
      ok({
        total: 2,
        items: [
          { id: 'x1', alias: 'unit-线路 A', model_list: models(7), created_at: '2026-01-02T03:04:05Z', detection_status: 'PASS', latest_report_id: 'rx1' },
          { id: 'x2', alias: 'unit-线路 B', model_list: models(9), created_at: '2026-01-02T03:04:05Z', detection_status: 'RUNNING' }
        ]
      })
    )
    const wrapper = mount(CredentialsPage)
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('共 2 条')
    expect(text).toContain('unit-线路 A')
    expect(text).toContain('7')
    expect(text).not.toContain('华东主线路 · GPT 通道')
    expect(wrapper.findAll('[data-testid="cred-row"]')).toHaveLength(2)
  })
})

describe('页面 3 · 交互（分类见台账）', () => {
  it('返回按钮 → navigateBack', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'back-btn')
    expect(getCalls('navigateBack')).toHaveLength(1)
  })

  it('帮助按钮：设计画布无帮助页 → 不臆造路由，只提示（client-only）', async () => {
    const wrapper = await mountPage()
    const before = getCalls('navigateTo').length
    await tap(wrapper, 'help-btn')
    expect(getCalls('navigateTo').length).toBe(before)
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({ title: '帮助功能开发中' })
  })

  it('「接入凭证」→ 提交接入凭证页：/pages/credential-submit/index', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'submit-btn')
    const nav = getCalls('navigateTo').at(-1)
    expect((nav?.args[0] as Record<string, unknown>).url).toBe('/pages/credential-submit/index')
  })

  it('通过行的「报告」→ /pages/report/index?reportId=…（序号 6 页面）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'row-report-0')
    const nav = getCalls('navigateTo').at(-1)
    expect((nav?.args[0] as Record<string, unknown>).url).toBe('/pages/report/index?reportId=rp1')
  })

  it('不通过行的「报告」→ /pages/report-failed/index?reportId=…（序号 7 页面）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'row-report-3')
    const nav = getCalls('navigateTo').at(-1)
    expect((nav?.args[0] as Record<string, unknown>).url).toBe('/pages/report-failed/index?reportId=rp4')
  })

  it('底部 TabBar：报告→报告页、报价→报价单列表、我的→我的；工作台不跳转', async () => {
    const wrapper = await mountPage()
    const cases: Array<[string, string]> = [
      ['tab-报告', '/pages/report/index'],
      ['tab-报价', '/pages/quotes/index'],
      ['tab-我的', '/pages/mine/index']
    ]
    for (const [testid, url] of cases) {
      await tap(wrapper, testid)
      const nav = getCalls('navigateTo').at(-1)
      expect((nav?.args[0] as Record<string, unknown>).url, `${testid} 应跳转 ${url}`).toBe(url)
    }
    const before = getCalls('navigateTo').length
    await tap(wrapper, 'tab-工作台')
    expect(getCalls('navigateTo').length).toBe(before)
  })
})

describe('页面 3 · 失败与非 happy-path', () => {
  it('接口失败 → 提示 + 骨架保留 + 不显示假数据', async () => {
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务器开小差' } })
    const wrapper = mount(CredentialsPage)
    await flushPromises()
    const text = wrapper.text()
    expect(getCalls('showToast').length).toBeGreaterThan(0)
    expect(text).toContain('统一管理客户检测凭证')
    expect(text).toContain('共 0 条')
    expect(text).not.toContain('华东主线路 · GPT 通道')
  })

  it('空列表 → 空态文案，仍保留表头与底部说明', async () => {
    pushResponse(ok({ total: 0, items: [] }))
    const wrapper = mount(CredentialsPage)
    await flushPromises()
    const text = wrapper.text()
    expect(wrapper.find('[data-testid="cred-empty"]').text()).toBe('暂无接入凭证')
    expect(text).toContain('凭证名称')
    expect(text).toContain('仅展示最近接入的 10 条凭证记录')
    expect(wrapper.findAll('[data-testid="cred-row"]')).toHaveLength(0)
  })
})
