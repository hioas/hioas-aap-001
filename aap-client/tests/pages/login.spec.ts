/**
 * 页面 1【账号接入】登录注册 — 页面交互单测（序号 1 / page-1-2）
 * 文案与结构取自 .calicat/raw/pages/page-1-2/design.json（430 宽小程序页）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import LoginPage from '@/pages/login/index.vue'
import { getCalls, pushResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

async function mountLogin() {
  const wrapper = mount(LoginPage)
  await flushPromises()
  return wrapper
}

describe('页面 1 · 结构与设计稿一致', () => {
  it('品牌区、表单、协议、第三方登录、免责说明文案齐全', async () => {
    const wrapper = await mountLogin()
    const text = wrapper.text()
    for (const t of [
      '云算接入',
      'SUPPLIER ONBOARDING',
      'API 供应商一站式接入',
      '注册即开通，检测 · 报价 · 结算全流程线上化',
      '手机号登录 / 注册',
      '未注册的手机号将自动创建账号',
      // 三个输入框占位符是 attribute 不是文本，由下一个用例按 placeholder 断言
      '获取验证码',
      '验证码 5 分钟内有效，请注意查收',
      '登录 / 注册',
      '其他登录方式',
      '微信一键登录',
      '我已阅读并同意《服务协议》与《隐私政策》',
      '免责与合规说明',
      '登录即代表您已满 18 周岁',
      '© 2024 云算接入平台 · 保留所有权利'
    ]) {
      expect(text, `缺少文案：${t}`).toContain(t)
    }
  })

  it('输入框占位符与设计稿一致，短信验证码按钮独立存在', async () => {
    const wrapper = await mountLogin()
    const inputs = wrapper.findAll('input')
    const placeholders = inputs.map((i) => i.attributes('placeholder'))
    expect(placeholders).toContain('请输入手机号')
    expect(placeholders).toContain('请输入验证码')
    expect(placeholders).toContain('请输入短信验证码')
  })
})

describe('页面 1 · 交互（未勾协议 / 参数非法一律不发请求）', () => {
  it('手机号非法 -> 点获取验证码只提示，不发 sendSms 请求', async () => {
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="phone"] input').setValue('12345')
    await wrapper.find('[data-test="btn-send-sms"]').trigger('tap')
    await flushPromises()
    expect(getCalls('request')).toHaveLength(0)
    expect(getCalls('showToast').map((c) => (c.args[0] as any).title).join()).toContain('请输入正确的手机号')
  })

  it('图形验证码非法 -> 不发请求', async () => {
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="phone"] input').setValue('13800138000')
    await wrapper.find('[data-test="captcha"] input').setValue('X')
    await wrapper.find('[data-test="btn-send-sms"]').trigger('tap')
    await flushPromises()
    expect(getCalls('request')).toHaveLength(0)
  })

  it('参数合法 -> 发起 POST /auth/sms/send 并进入 60s 冷却', async () => {
    pushResponse(ok({ ttl: 300 }))
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="phone"] input').setValue('13800138000')
    await wrapper.find('[data-test="captcha"] input').setValue('A7K9')
    await wrapper.find('[data-test="btn-send-sms"]').trigger('tap')
    await flushPromises()
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    expect((calls[0].args[0] as any).url).toBe('/api/v1/auth/sms/send')
    expect(wrapper.find('[data-test="btn-send-sms"]').text()).toContain('60s 后重发')
  })

  it('未勾选协议 -> 点登录不发请求，提示先同意协议', async () => {
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="phone"] input').setValue('13800138000')
    await wrapper.find('[data-test="smsCode"] input').setValue('123456')
    await wrapper.find('[data-test="btn-login"]').trigger('tap')
    await flushPromises()
    expect(getCalls('request')).toHaveLength(0)
    expect(getCalls('showToast').map((c) => (c.args[0] as any).title).join()).toContain('请先阅读并同意')
  })

  it('协议已勾选 + 手机号 + 6 位验证码 -> 登录成功：写 token、跳工作台、提示成功', async () => {
    pushResponse(ok({ token: 'jwt-abc', role: 'PROVIDER', providerId: 'AAP-P-000001' }))
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="phone"] input').setValue('13800138000')
    await wrapper.find('[data-test="smsCode"] input').setValue('123456')
    await wrapper.find('[data-test="agree-box"]').trigger('tap')
    await wrapper.find('[data-test="btn-login"]').trigger('tap')
    await flushPromises()
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    expect((calls[0].args[0] as any).url).toBe('/api/v1/auth/sms/login')
    expect(storage.get('aap_token')).toBe('jwt-abc')
    const nav = getCalls('navigateTo')
    expect(nav).toHaveLength(1)
    expect((nav[0].args[0] as any).url).toContain('/pages/workbench/index')
  })

  it('协议勾选框是自绘 view（小程序无 checkbox input）：点一下变选中态', async () => {
    const wrapper = await mountLogin()
    const box = wrapper.find('[data-test="agree-box"]')
    expect(box.exists()).toBe(true)
    expect(box.classes()).not.toContain('agree__box--checked')
    await box.trigger('tap')
    expect(wrapper.find('[data-test="agree-box"]').classes()).toContain('agree__box--checked')
  })

  it('短信验证码位数不足 -> 不发请求', async () => {
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="phone"] input').setValue('13800138000')
    await wrapper.find('[data-test="smsCode"] input').setValue('123')
    await wrapper.find('[data-test="agree-box"]').trigger('tap')
    await wrapper.find('[data-test="btn-login"]').trigger('tap')
    await flushPromises()
    expect(getCalls('request')).toHaveLength(0)
  })

  it('微信一键登录 -> uni.login 拿 code 后调 /auth/wechat/login（协议已勾）', async () => {
    pushResponse(ok({ token: 'jwt-wx', role: 'PROVIDER' }))
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="agree-box"]').trigger('tap')
    await wrapper.find('[data-test="btn-wechat"]').trigger('tap')
    await flushPromises()
    expect(getCalls('login')).toHaveLength(1)
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    expect((calls[0].args[0] as any).url).toBe('/api/v1/auth/wechat/login')
    expect(storage.get('aap_token')).toBe('jwt-wx')
  })

  it('后端返回 E-1001 -> 页面弹错误提示且不写 token', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1001', message: '参数校验失败', data: {} } })
    const wrapper = await mountLogin()
    await wrapper.find('[data-test="phone"] input').setValue('13800138000')
    await wrapper.find('[data-test="smsCode"] input').setValue('123456')
    await wrapper.find('[data-test="agree-box"]').trigger('tap')
    await wrapper.find('[data-test="btn-login"]').trigger('tap')
    await flushPromises()
    expect(getCalls('showToast').map((c) => (c.args[0] as any).title).join()).toContain('参数校验失败')
    expect(storage.get('aap_token')).toBeUndefined()
  })
})

/**
 * 页面 1 · 设计稿结构（page-1-2）
 * 设计：品牌头部 = Logo行[Logo方块 54x54 + spacer 12 + 品牌名块(云算接入 / SUPPLIER ONBOARDING)] + spacer 28 + 定位语块
 *       免责说明 = container(padding 0/16) 里的一张白卡（r16 / padding 16,20 / 描边 #EEF2F7）
 */
describe('页面 1 · 品牌区与免责卡结构按设计稿', () => {
  it('Logo 与品牌名块同处一个 Logo行（不是上下两行）', async () => {
    const wrapper = await mountLogin()
    const row = wrapper.find('.brand__row')
    expect(row.exists(), '缺少 Logo行容器 .brand__row').toBe(true)
    expect(row.find('.brand__logo').exists(), 'Logo方块应在 Logo行内').toBe(true)
    const idBlock = row.find('.brand__id')
    expect(idBlock.exists(), '品牌名块 .brand__id 应在 Logo行内').toBe(true)
    expect(idBlock.find('.brand__name').text()).toBe('云算接入')
    expect(idBlock.find('.brand__en').text()).toBe('SUPPLIER ONBOARDING')
  })

  it('免责说明是 container 内的一张卡片（.disclaimer-wrap > .disclaimer）', async () => {
    const wrapper = await mountLogin()
    const wrap = wrapper.find('.disclaimer-wrap')
    expect(wrap.exists(), '缺少免责说明外层 container .disclaimer-wrap').toBe(true)
    expect(wrap.find('.disclaimer').exists()).toBe(true)
  })
})
