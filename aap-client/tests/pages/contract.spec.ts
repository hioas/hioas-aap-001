/**
 * 序号 15【合同与通知】合同签署 2（page-15-2）— 页面取数与渲染（TDD 切片 3，先红）
 *
 * 页面入参：contractId 优先页面栈 query（H5/mini 的 ?contractId=），其次 storage 键 aap_contract_id（单测/刷新兜底）。
 * 接口真源：18-API「Contract」/contracts/{id}（前缀 /api/v1；方法为 REST 推断）。
 * 设计基线：430 宽 · 设计帧 430x1231（顶栏 96 + 7 卡 + 底栏 84，
 *   见 .agents/state/h5-measure/__measure-contract.html 与 .agents/state/col-bands.py 量得的卡片边界）。
 *
 * ⚠️ 本页无输入控件、无 TabBar（设计帧实测 inputCount 0 / 无 TabBar）——只读展示 + 两个出口按钮。
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ContractPage from '@/pages/contract/index.vue'
import { getCalls, pushResponse, storage } from '../setup'
import { CONTRACT_DESIGN } from '../fixtures/contract-fixture'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

function requests() {
  return getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
}

function urls() {
  return requests().map((r) => String(r.url))
}

function toasts() {
  return getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
}

function text(wrapper: ReturnType<typeof mount>, testid: string) {
  const el = wrapper.find(`[data-testid="${testid}"]`)
  return el.exists() ? el.text() : ''
}

function rowTexts(wrapper: ReturnType<typeof mount>, sel: string) {
  return wrapper.findAll(sel).map((r) => r.text())
}

async function mountLoaded() {
  storage.set('aap_contract_id', 'c1')
  pushResponse(ok(CONTRACT_DESIGN))
  const wrapper = mount(ContractPage)
  await flushPromises()
  return wrapper
}

describe('序号 15 · 取数（api）', () => {
  it('有 contractId → GET /api/v1/contracts/c1（只发这一个请求）', async () => {
    await mountLoaded()
    expect(urls()).toEqual(['/api/v1/contracts/c1'])
    expect(requests()[0].method).toBe('GET')
  })

  it('无 contractId → 不发请求，四张信息卡全部占位「—」，无条款/无记录', async () => {
    const wrapper = mount(ContractPage)
    await flushPromises()
    expect(urls()).toEqual([])
    expect(text(wrapper, 'nav-no')).toBe('')
    expect(text(wrapper, 'status-title')).toBe('')
    expect(wrapper.find('[data-testid="status-chip"]').exists()).toBe(false)
    expect(text(wrapper, 'deadline')).toBe('')
    expect(rowTexts(wrapper, '.card--basic .crow')).toEqual(['供应商—', '合作模式—', '生效期—', '结算账期—'])
    expect(rowTexts(wrapper, '.card--fee .crow')).toEqual(['平台服务费率—', '结算币种—', '最低结算额—'])
    expect(rowTexts(wrapper, '.card--sign .crow')).toEqual(['签署人—', '手机号—', '签署方式—'])
    expect(wrapper.findAll('.clause')).toHaveLength(0)
    expect(wrapper.findAll('.record')).toHaveLength(0)
  })

  it('详情失败 → toast 服务端 message，页面回到占位（不编造合同内容）', async () => {
    storage.set('aap_contract_id', 'c1')
    pushResponse({ statusCode: 200, data: { code: 'E-1404', message: '合同不存在' } })
    const wrapper = mount(ContractPage)
    await flushPromises()
    expect(toasts()).toEqual(['合同不存在'])
    expect(text(wrapper, 'status-title')).toBe('')
    expect(rowTexts(wrapper, '.card--basic .crow')).toEqual(['供应商—', '合作模式—', '生效期—', '结算账期—'])
  })
})

describe('序号 15 · 渲染（设计稿结构与文案）', () => {
  it('顶栏：返回 + 标题「合同签署」+ 单图层编号（含「编号 」前缀）', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'nav-title')).toBe('合同签署')
    expect(text(wrapper, 'nav-no')).toBe('编号 CT-2024-0613-008')
  })

  it('合同状态卡：合同名 + 状态胶囊「待签署」+ 签署期限句式', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'status-title')).toBe('API 接入服务合同')
    expect(text(wrapper, 'status-chip')).toBe('待签署')
    expect(text(wrapper, 'deadline')).toBe('请在 2024-06-20 前完成签署，逾期将自动作废')
  })

  it('电子签提示卡：设计原文逐字', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'tip')).toBe('本合同采用电子签章，签署后即时生效并具备法律效力。')
  })

  it('合同基本信息 4 行 / 费用与分成 3 行 / 签署信息 3 行，标签与值逐字一致', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'card-basic-title')).toBe('合同基本信息')
    expect(rowTexts(wrapper, '.card--basic .crow')).toEqual([
      '供应商云智科技有限公司',
      '合作模式API 转售（非独家）',
      '生效期2024-07-01 至 2025-06-30',
      '结算账期月结 · 次月 15 日'
    ])
    expect(text(wrapper, 'card-fee-title')).toBe('费用与分成')
    expect(rowTexts(wrapper, '.card--fee .crow')).toEqual([
      '平台服务费率8%',
      '结算币种CNY',
      '最低结算额¥1,000.00'
    ])
    expect(text(wrapper, 'card-sign-title')).toBe('签署信息')
    expect(rowTexts(wrapper, '.card--sign .crow')).toEqual([
      '签署人李明（商务负责人）',
      '手机号138 **** 6621',
      '签署方式短信验证码签署'
    ])
  })

  it('关键条款 4 条（按设计原文 + 序号）', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'card-terms-title')).toBe('关键条款')
    expect(rowTexts(wrapper, '.clause')).toEqual([
      '1. 供应商须保证上游接口的合法来源与稳定可用。',
      '2. 平台按实际用量结算，价格以审核通过的报价单为准。',
      '3. 若月度可用率低于 99%，平台有权下调报价或终止合作。',
      '4. 合同期内价格调整需双方确认后生效。'
    ])
  })

  it('签署记录卡：2 条记录（标题 + 时间/副文案 + 圆点色）', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'card-records-title')).toBe('签署记录')
    expect(rowTexts(wrapper, '.record')).toEqual([
      '平台方已盖章2024-06-13 09:12',
      '等待供应商签署请尽快完成，逾期作废'
    ])
    const dots = wrapper.findAll('.record__dot')
    expect(dots.map((d) => d.attributes('data-tone'))).toEqual(['success', 'pending'])
  })

  it('底部操作条两个按钮（PDF / 去签署）', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'btn-pdf')).toBe('PDF')
    expect(text(wrapper, 'btn-sign')).toBe('去签署')
  })

  it('结构：7 张卡片、无输入控件、无 TabBar（只读展示页）', async () => {
    const wrapper = await mountLoaded()
    expect(wrapper.findAll('.card')).toHaveLength(7)
    expect(wrapper.findAll('input,textarea')).toHaveLength(0)
    expect(wrapper.find('.tabbar').exists()).toBe(false)
  })
})
