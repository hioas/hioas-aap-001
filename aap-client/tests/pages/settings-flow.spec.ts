/**
 * 序号 23【工作台与我的】我的设置（page-23-2）— 切片 3：交互
 *
 * 交互真源：.calicat/raw/pages/page-23-2/interaction.json =「不存在图层交互数据」
 *   → 交互退 18-API + 设计稿控件语义（台账序号 23 的逐元素分类）：
 *   返回 = navigation（navigateBack）
 *   手机号 / 微信绑定 / 登录安全三行 = navigation **无落点**（画布 30 页无对应页）→ 不跳转、不提示
 *   短信通知开关 = client-only（本地态；18-API 无 /settings 端点 → 不发请求）
 *   微信订阅消息徽标 = client-only（只读展示，无点击行为）
 *   实名与主体信息 = navigation → /pages/profile/index（序号 10.1 已实现）
 *   服务协议与隐私政策 = navigation **无落点**（画布无页 + PRD 无外链地址）
 *   退出登录 = api → POST /api/v1/auth/logout（先二次确认；无论成败都 reLaunch 登录页）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SettingsPage from '@/pages/settings/index.vue'
import { LOGOUT_CONFIRM_CONTENT, LOGOUT_CONFIRM_TITLE, LOGOUT_FAIL_TEXT } from '@/utils/settings-model'
import { getCalls, pushResponse, setModalAnswer, setNextResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })
const ME = { phone: '13812346621', wechat_bound: true, sms_two_factor: true, wechat_subscribed: true }

async function mountPage() {
  pushResponse(ok(ME))
  const wrapper = mount(SettingsPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

const navUrls = () => getCalls('navigateTo').map((c) => (c.args[0] as Record<string, unknown>).url)
const relaunchUrls = () => getCalls('reLaunch').map((c) => (c.args[0] as Record<string, unknown>).url)
const writeRequests = () =>
  getCalls('request').filter((c) => (c.args[0] as Record<string, unknown>).method !== 'GET')

describe('序号 23 · 返回（navigation）', () => {
  it('点返回 → navigateBack（本页无 TabBar，由「我的」进入）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'settings-back')
    expect(getCalls('navigateBack').length).toBe(1)
  })
})

describe('序号 23 · 功能入口卡（navigation / api）', () => {
  it('点「实名与主体信息」→ navigateTo /pages/profile/index（序号 10.1 已实现）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'row-identity')
    expect(navUrls()).toEqual(['/pages/profile/index'])
  })

  it('点「服务协议与隐私政策」不跳转（画布无该页、PRD 无外链地址 → 无落点，不臆造 URL）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'row-legal')
    expect(getCalls('navigateTo').length).toBe(0)
    expect(getCalls('showToast').length).toBe(0)
  })

  it('账号信息三行也不跳转（画布无手机号 / 微信绑定 / 登录安全页）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'account-row')
    await tap(wrapper, 'account-row')
    expect(getCalls('navigateTo').length).toBe(0)
  })
})

describe('序号 23 · 短信通知开关（client-only：只改本地态，不发请求）', () => {
  it('点开关 → data-on 由 true 变 false，且 0 个写请求（18-API 无 /settings 端点）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="sms-switch"]').attributes('data-on')).toBe('true')
    await tap(wrapper, 'sms-switch')
    expect(wrapper.find('[data-testid="sms-switch"]').attributes('data-on')).toBe('false')
    expect(writeRequests().length).toBe(0)
    expect(getCalls('request').length).toBe(1)
  })

  it('再点一次回到开态（本地开关可逆）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'sms-switch')
    await tap(wrapper, 'sms-switch')
    expect(wrapper.find('[data-testid="sms-switch"]').attributes('data-on')).toBe('true')
  })

  it('点微信订阅消息徽标无任何副作用（只读展示）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'notify-row')
    expect(getCalls('navigateTo').length).toBe(0)
    expect(getCalls('showToast').length).toBe(0)
    expect(writeRequests().length).toBe(0)
  })
})

describe('序号 23 · 退出登录（api：POST /auth/logout）', () => {
  it('点「退出登录」先弹二次确认（未确认前不发请求、不跳转）', async () => {
    const wrapper = await mountPage()
    /* 桩默认 confirm=true；本用例把答案设为 false，才能证明「确认前不发写请求」 */
    setModalAnswer(false)
    await tap(wrapper, 'row-logout')
    const modal = getCalls('showModal')[0].args[0] as Record<string, unknown>
    expect(modal.title).toBe(LOGOUT_CONFIRM_TITLE)
    expect(modal.content).toBe(LOGOUT_CONFIRM_CONTENT)
    expect(writeRequests().length).toBe(0)
    expect(getCalls('reLaunch').length).toBe(0)
  })

  it('确认后 → POST /api/v1/auth/logout → 清本地 token → reLaunch 登录页', async () => {
    storage.set('aap_token', 't-abc')
    const wrapper = await mountPage()
    pushResponse(ok(null))
    setModalAnswer(true)
    await tap(wrapper, 'row-logout')
    const posts = writeRequests()
    expect(posts).toHaveLength(1)
    expect((posts[0].args[0] as Record<string, unknown>).url).toBe('/api/v1/auth/logout')
    expect((posts[0].args[0] as Record<string, unknown>).method).toBe('POST')
    expect(storage.get('aap_token')).toBeUndefined()
    expect(relaunchUrls()).toEqual(['/pages/login/index'])
  })

  it('取消确认 → 不发请求、不跳转、token 不动', async () => {
    storage.set('aap_token', 't-abc')
    const wrapper = await mountPage()
    setModalAnswer(false)
    await tap(wrapper, 'row-logout')
    expect(writeRequests().length).toBe(0)
    expect(getCalls('reLaunch').length).toBe(0)
    expect(storage.get('aap_token')).toBe('t-abc')
  })

  it('退出失败（服务端 500）→ 提示占位文案，但仍清 token 并回登录页（本地会话必清）', async () => {
    storage.set('aap_token', 't-abc')
    const wrapper = await mountPage()
    setNextResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务异常' } })
    setModalAnswer(true)
    await tap(wrapper, 'row-logout')
    const toast = getCalls('showToast').map((c) => (c.args[0] as Record<string, unknown>).title)
    expect(toast).toContain(LOGOUT_FAIL_TEXT)
    expect(storage.get('aap_token')).toBeUndefined()
    expect(relaunchUrls()).toEqual(['/pages/login/index'])
  })

  it('单次点击只触发一次登出（不重复发 POST）', async () => {
    const wrapper = await mountPage()
    pushResponse(ok(null))
    setModalAnswer(true)
    await tap(wrapper, 'row-logout')
    expect(writeRequests().length).toBe(1)
  })
})

describe('序号 23 · 整页不产生意外写请求', () => {
  it('除退出登录外的所有交互全程 0 写请求（页面只读）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'settings-back')
    await tap(wrapper, 'account-row')
    await tap(wrapper, 'sms-switch')
    await tap(wrapper, 'row-identity')
    await tap(wrapper, 'row-legal')
    expect(writeRequests().length).toBe(0)
    expect(getCalls('request').length).toBe(1)
  })
})
