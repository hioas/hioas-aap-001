/**
 * 序号 23【工作台与我的】我的设置（page-23-2）— 切片 2：页面结构与文案
 *
 * 设计真源：.calicat/raw/pages/page-23-2/design.tree.json（430 宽 · 设计总高 797 · 无 TabBar）
 *   导航「账号与设置」· 账号信息卡（手机号 138 **** 6621 / 微信绑定 已绑定绿胶囊 / 登录安全 已开启短信二次校验）
 *   通知设置卡（短信通知 + 说明 + 开态开关 / 微信订阅消息 + 说明 + 已授权绿胶囊）
 *   功能入口卡（实名与主体信息 / 服务协议与隐私政策 / 退出登录）· 底部两行说明
 * 接口真源：GET /api/v1/auth/me（18-API「Auth」Tag）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SettingsPage from '@/pages/settings/index.vue'
import { LOAD_FAIL_TEXT } from '@/utils/settings-model'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 与设计帧逐值对齐的一份 /auth/me 响应 */
const ME = { phone: '13812346621', wechat_bound: true, sms_two_factor: true, wechat_subscribed: true }

async function mountPage(raw: unknown = ME) {
  pushResponse(ok(raw))
  const wrapper = mount(SettingsPage)
  await flushPromises()
  return wrapper
}

const texts = (wrapper: ReturnType<typeof mount>, selector: string) => wrapper.findAll(selector).map((el) => el.text())

/** 逐行取值：有胶囊取胶囊文本，否则取 .row__value（值节点二选一，同序号 21 口径） */
const rowValue = (wrapper: ReturnType<typeof mount>, index: number) => {
  const row = wrapper.findAll('[data-testid="account-row"]')[index]
  const pill = row.find('[data-testid="account-pill"]')
  return pill.exists() ? pill.text() : row.find('[data-testid="account-value"]').text()
}

const req = (index = 0) => getCalls('request')[index].args[0] as Record<string, unknown>

describe('序号 23 · 取数与顶部导航', () => {
  it('首屏只发一个只读 GET /api/v1/auth/me', async () => {
    await mountPage()
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    expect(req().url).toBe('/api/v1/auth/me')
    expect(req().method).toBe('GET')
  })

  it('导航标题「账号与设置」+ 返回按钮存在', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('.settings').exists()).toBe(true)
    expect(wrapper.find('[data-testid="settings-title"]').text()).toBe('账号与设置')
    expect(wrapper.find('[data-testid="settings-back"]').exists()).toBe(true)
  })
})

describe('序号 23 · 账号信息卡', () => {
  it('标题行 + 三行标签逐字对齐设计帧', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="account-title"]').text()).toBe('账号信息')
    expect(texts(wrapper, '[data-testid="account-label"]')).toEqual(['手机号', '微信绑定', '登录安全'])
    expect(wrapper.findAll('[data-testid="account-row"]').map((el) => el.attributes('data-key'))).toEqual([
      'phone',
      'wechat',
      'security'
    ])
  })

  it('三行取值：脱敏手机号 / 已绑定胶囊 / 二次校验文案', async () => {
    const wrapper = await mountPage()
    /* 逐行取值：胶囊行渲染胶囊（值在胶囊内），其余行渲染 .row__value（同序号 21「逐行 valueOf」口径） */
    expect([0, 1, 2].map((i) => rowValue(wrapper, i))).toEqual(['138 **** 6621', '已绑定', '已开启短信二次校验'])
    const pills = wrapper.findAll('[data-testid="account-pill"]')
    expect(pills).toHaveLength(1)
    expect(pills[0].text()).toBe('已绑定')
  })

  it('每行右侧有 chevron（无落点，也不臆造路由）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('[data-testid="account-chevron"]')).toHaveLength(3)
    expect(wrapper.findAll('[data-testid="account-row"]').map((el) => el.attributes('data-target'))).toEqual([
      '',
      '',
      ''
    ])
  })

  it('字段缺失 → 三行均为占位「—」且无胶囊（不冒充已绑定）', async () => {
    const wrapper = await mountPage({})
    expect(texts(wrapper, '[data-testid="account-value"]')).toEqual(['—', '—', '—'])
    expect(wrapper.findAll('[data-testid="account-pill"]')).toHaveLength(0)
  })
})

describe('序号 23 · 通知设置卡', () => {
  it('标题 + 两行标题与副文案逐字对齐设计帧', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="notify-title"]').text()).toBe('通知设置')
    expect(texts(wrapper, '[data-testid="notify-row-title"]')).toEqual(['短信通知', '微信订阅消息'])
    expect(texts(wrapper, '[data-testid="notify-row-desc"]')).toEqual([
      '审核结果、账单与合同提醒',
      '检测进度与用量周报'
    ])
    expect(wrapper.findAll('[data-testid="notify-row"]').map((el) => el.attributes('data-key'))).toEqual([
      'sms',
      'subscribe'
    ])
  })

  it('短信行为开态开关（设计帧为开）；微信订阅行为「已授权」绿胶囊', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="sms-switch"]').attributes('data-on')).toBe('true')
    const badge = wrapper.find('[data-testid="subscribe-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('已授权')
  })
})

describe('序号 23 · 功能入口卡', () => {
  it('三行文案逐字对齐设计帧，行可点且有 data-tone', async () => {
    const wrapper = await mountPage()
    expect(texts(wrapper, '[data-testid="entry-label"]')).toEqual([
      '实名与主体信息',
      '服务协议与隐私政策',
      '退出登录'
    ])
    /* 行级 hook 沿用序号 21 约定：data-testid=`row-<key>` */
    expect(wrapper.findAll('[data-testid^="row-"]').map((el) => el.attributes('data-tone'))).toEqual([
      'primary',
      'neutral',
      'danger'
    ])
    expect(wrapper.find('[data-testid="row-identity"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="row-legal"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="row-logout"]').exists()).toBe(true)
  })

  it('卡片无标题行（设计帧功能入口卡 kids 只有 3 行 + 2 条分隔）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="entry-card"]').findAll('[data-testid="entry-title"]')).toHaveLength(0)
    expect(wrapper.findAll('[data-testid="entry-sep"]')).toHaveLength(2)
  })
})

describe('序号 23 · 底部说明与页面形态', () => {
  it('底部两行说明逐字对齐设计帧', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="footer-version"]').text()).toBe('云算接入平台 v1.4.2')
    expect(wrapper.find('[data-testid="footer-copyright"]').text()).toBe('© 2024 保留所有权利')
  })

  it('无 TabBar（设计帧无底部导航）、无原生输入控件', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="tab-工作台"]').exists()).toBe(false)
    expect(wrapper.findAll('input')).toHaveLength(0)
  })
})

describe('序号 23 · 取数失败', () => {
  it('接口失败 → 账号三行占位「—」+ 提示，不编造状态', async () => {
    setNextResponse({ statusCode: 200, data: { code: 'E-1902', message: '登录已过期' } })
    const wrapper = mount(SettingsPage)
    await flushPromises()
    expect(texts(wrapper, '[data-testid="account-value"]')).toEqual(['—', '—', '—'])
    const toast = getCalls('showToast')[0].args[0] as Record<string, unknown>
    expect(toast.title).toBe(LOAD_FAIL_TEXT)
  })

  it('取数失败后仍渲染完整结构（通知设置卡与功能入口卡不受影响）', async () => {
    setNextResponse({ statusCode: 200, data: { code: 'E-2001', message: '网络异常' } })
    const wrapper = mount(SettingsPage)
    await flushPromises()
    expect(wrapper.findAll('[data-testid="notify-row"]')).toHaveLength(2)
    expect(wrapper.findAll('[data-testid^="row-"]')).toHaveLength(3)
  })
})
