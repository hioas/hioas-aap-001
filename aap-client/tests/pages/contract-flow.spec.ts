/**
 * 序号 15【合同与通知】合同签署 2（page-15-2）— 页面交互（TDD 切片 4，先红）
 *
 * 交互真源：`.calicat/raw/pages/page-15-2/interaction.json` = 「不存在图层交互数据」
 *   → 交互按设计稿控件语义 + 18-API「Contract」路径推断（记 missing-prd）：
 *     返回 = navigateBack（无栈时不变）；PDF = GET /contracts/{id}/file；去签署 = POST /contracts/{id}/sign。
 * 设计帧与 PRD 冲突（电子签 vs R-41 线下签署）已在 contract-model.ts / 台账序号 15 登记；**已拍板 = 决策 D7「保留 a 电子签入口」**，
 * 故本文件保留「去签署」4 例作为回归锁定（入口存在 + 二次确认 + POST /contracts/c1/sign + 失败保持状态），不再按线下签署口径下架该入口。
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ContractPage from '@/pages/contract/index.vue'
import { getCalls, pushResponse, setModalAnswer, storage } from '../setup'
import { CONTRACT_DESIGN } from '../fixtures/contract-fixture'
import { CONFIRM_SIGN_CONTENT, CONFIRM_SIGN_TITLE, TOAST_NO_CONTRACT, TOAST_NO_FILE, TOAST_SIGNED } from '@/utils/contract-model'

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

function modals() {
  return getCalls('showModal').map((c) => c.args[0] as Record<string, unknown>)
}

async function mountLoaded() {
  storage.set('aap_contract_id', 'c1')
  pushResponse(ok(CONTRACT_DESIGN))
  const wrapper = mount(ContractPage)
  await flushPromises()
  return wrapper
}

describe('序号 15 · 返回', () => {
  it('点返回 → navigateBack（delta 1）', async () => {
    const wrapper = await mountLoaded()
    await wrapper.find('[data-testid="back"]').trigger('tap')
    expect(getCalls('navigateBack').map((c) => c.args[0])).toEqual([{ delta: 1 }])
    expect(urls()).toEqual(['/api/v1/contracts/c1'])
  })
})

describe('序号 15 · 下载 PDF', () => {
  it('有合同 id → 先 GET /contracts/c1/file，拿到 url 再 uni.downloadFile + openDocument', async () => {
    storage.set('aap_contract_id', 'c1')
    pushResponse(ok(CONTRACT_DESIGN))
    pushResponse(ok({ url: 'https://cdn.hioas.com/CT-2024-0613-008.pdf' }))
    const wrapper = mount(ContractPage)
    await flushPromises()
    await wrapper.find('[data-testid="btn-pdf"]').trigger('tap')
    await flushPromises()
    expect(urls()).toEqual(['/api/v1/contracts/c1', '/api/v1/contracts/c1/file'])
    const dl = getCalls('downloadFile').map((c) => c.args[0] as Record<string, unknown>)
    expect(dl).toHaveLength(1)
    expect(dl[0].url).toBe('https://cdn.hioas.com/CT-2024-0613-008.pdf')
    expect(getCalls('openDocument').map((c) => (c.args[0] as Record<string, unknown>).filePath)).toEqual(['/tmp/x.pdf'])
    expect(toasts()).toEqual([])
  })

  it('服务端未给 url → toast「合同文件尚未生成」，不调 downloadFile（不编造地址）', async () => {
    storage.set('aap_contract_id', 'c1')
    pushResponse(ok(CONTRACT_DESIGN))
    pushResponse(ok({}))
    const wrapper = mount(ContractPage)
    await flushPromises()
    await wrapper.find('[data-testid="btn-pdf"]').trigger('tap')
    await flushPromises()
    expect(toasts()).toEqual([TOAST_NO_FILE])
    expect(getCalls('downloadFile')).toHaveLength(0)
  })

  it('文件接口失败 → toast 服务端 message', async () => {
    storage.set('aap_contract_id', 'c1')
    pushResponse(ok(CONTRACT_DESIGN))
    pushResponse({ statusCode: 200, data: { code: 'E-2001', message: '文件服务不可用' } })
    const wrapper = mount(ContractPage)
    await flushPromises()
    await wrapper.find('[data-testid="btn-pdf"]').trigger('tap')
    await flushPromises()
    expect(toasts()).toEqual(['文件服务不可用'])
  })

  it('无合同 id → 点 PDF 只 toast，不发请求', async () => {
    const wrapper = mount(ContractPage)
    await flushPromises()
    await wrapper.find('[data-testid="btn-pdf"]').trigger('tap')
    await flushPromises()
    expect(toasts()).toEqual([TOAST_NO_FILE])
    expect(urls()).toEqual([])
  })
})

describe('序号 15 · 去签署', () => {
  it('确认弹窗通过 → POST /contracts/c1/sign → toast + 重新拉详情', async () => {
    storage.set('aap_contract_id', 'c1')
    pushResponse(ok(CONTRACT_DESIGN))
    const wrapper = await mountLoaded()
    pushResponse(ok({ status: 'SUPPLIER_SIGNED' }))
    pushResponse(ok({ ...CONTRACT_DESIGN, status: 'SUPPLIER_SIGNED' }))
    await wrapper.find('[data-testid="btn-sign"]').trigger('tap')
    await flushPromises()
    const m = modals()[0]
    expect(m.title).toBe(CONFIRM_SIGN_TITLE)
    expect(m.content).toBe(CONFIRM_SIGN_CONTENT)
    const signReq = requests().find((r) => String(r.url).endsWith('/sign'))
    expect(signReq?.url).toBe('/api/v1/contracts/c1/sign')
    expect(signReq?.method).toBe('POST')
    expect(toasts()).toEqual([TOAST_SIGNED])
    expect(urls()).toEqual(['/api/v1/contracts/c1', '/api/v1/contracts/c1/sign', '/api/v1/contracts/c1'])
    expect(wrapper.find('[data-testid="status-chip"]').text()).toBe('待确认')
  })

  it('弹窗取消 → 不发 POST，状态不变', async () => {
    const wrapper = await mountLoaded()
    setModalAnswer(false)
    await wrapper.find('[data-testid="btn-sign"]').trigger('tap')
    await flushPromises()
    expect(urls()).toEqual(['/api/v1/contracts/c1'])
    expect(toasts()).toEqual([])
    expect(wrapper.find('[data-testid="status-chip"]').text()).toBe('待签署')
  })

  it('签署被拒（E-1601 状态非法流转）→ toast 服务端 message，状态保持', async () => {
    const wrapper = await mountLoaded()
    pushResponse({ statusCode: 200, data: { code: 'E-1601', message: '状态非法流转' } })
    await wrapper.find('[data-testid="btn-sign"]').trigger('tap')
    await flushPromises()
    expect(toasts()).toEqual(['状态非法流转'])
    expect(wrapper.find('[data-testid="status-chip"]').text()).toBe('待签署')
  })

  it('无合同 id → 点去签署只 toast，不弹窗、不发请求', async () => {
    const wrapper = mount(ContractPage)
    await flushPromises()
    await wrapper.find('[data-testid="btn-sign"]').trigger('tap')
    await flushPromises()
    expect(toasts()).toEqual([TOAST_NO_CONTRACT])
    expect(modals()).toHaveLength(0)
    expect(urls()).toEqual([])
  })
})
