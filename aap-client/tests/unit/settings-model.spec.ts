/**
 * 序号 23【工作台与我的】我的设置（page-23-2）— 切片 1：视图模型
 *
 * 设计真源：.calicat/raw/pages/page-23-2/design.tree.json（430 宽 · 设计总高 797 · **无 TabBar**）
 *   顶部导航「账号与设置」17px Bold（padding 48/16/12/16 · 内容行 36 = 24px 图标 × 1.5）
 *   账号信息卡 108..331(223) padding 20 r18：标题行 27（图标 18+6+「账号信息」14px SemiBold）
 *     + 手机号行（padding-top 16 · 行高 30 · 标签列 87）「手机号 138 **** 6621 ›」
 *     + 分隔（12 + 1px + 12）· 微信绑定行「微信绑定〔绿胶囊 已绑定〕›」· 分隔 · 登录安全行「登录安全 已开启短信二次校验 ›」
 *   通知设置卡 343..519(176) padding 20 r18 描边 #EEF2F7：标题行 27 + 短信开关行（说明 132×34 + 开关 46×26）
 *     + 分隔 + 微信订阅消息行（说明 99×34 + 绿胶囊 已授权）
 *   功能入口卡 531..717(186) padding 8/20 r18 描边 #EEF2F7：3 行 × (12 + 32 + 12) + 两条 1px 分隔
 *     实名与主体信息（蓝图标底）· 服务协议与隐私政策（灰图标底）· 退出登录（红图标底 + 红字）
 *   底部说明 718..797(80) padding 24/0：两行 11px 居中「云算接入平台 v1.4.2」「© 2024 保留所有权利」
 * 接口真源：18-API设计OpenAPI.md「Auth」Tag → GET /api/v1/auth/me（账号信息）· POST /api/v1/auth/logout（退出登录）
 */
import { describe, expect, it } from 'vitest'
import {
  ACCOUNT_TITLE,
  AUTHORIZED_TEXT,
  BOUND_TEXT,
  EMPTY_VALUE,
  ENTRY_IDENTITY_TEXT,
  ENTRY_LEGAL_TEXT,
  ENTRY_LOGOUT_TEXT,
  FOOTER_COPYRIGHT_TEXT,
  FOOTER_VERSION_TEXT,
  LEGAL_TARGET,
  LOGOUT_ACTION,
  LOGOUT_CONFIRM_CONTENT,
  LOGOUT_CONFIRM_TITLE,
  LOGOUT_FAIL_TEXT,
  LOAD_FAIL_TEXT,
  NAV_TITLE,
  NOTIFY_TITLE,
  PHONE_LABEL,
  SECURITY_LABEL,
  SECURITY_OFF_TEXT,
  SECURITY_ON_TEXT,
  SMS_NOTIFY_DEFAULT,
  SMS_NOTIFY_DESC,
  SMS_NOTIFY_TITLE,
  SUBSCRIBE_DESC,
  SUBSCRIBE_TITLE,
  UNAUTHORIZED_TEXT,
  UNBOUND_TEXT,
  WECHAT_LABEL,
  buildSettingsOverview,
  maskPhone
} from '@/utils/settings-model'
import { PROFILE_PAGE } from '@/utils/routes'

describe('序号 23 · 设计文案（逐字，不得改写）', () => {
  it('导航 / 卡片标题 / 行标签 / 底部说明与设计帧逐字一致', () => {
    expect([
      NAV_TITLE,
      ACCOUNT_TITLE,
      NOTIFY_TITLE,
      PHONE_LABEL,
      WECHAT_LABEL,
      SECURITY_LABEL,
      SMS_NOTIFY_TITLE,
      SMS_NOTIFY_DESC,
      SUBSCRIBE_TITLE,
      SUBSCRIBE_DESC,
      BOUND_TEXT,
      AUTHORIZED_TEXT,
      ENTRY_IDENTITY_TEXT,
      ENTRY_LEGAL_TEXT,
      ENTRY_LOGOUT_TEXT,
      FOOTER_VERSION_TEXT,
      FOOTER_COPYRIGHT_TEXT
    ]).toEqual([
      '账号与设置',
      '账号信息',
      '通知设置',
      '手机号',
      '微信绑定',
      '登录安全',
      '短信通知',
      '审核结果、账单与合同提醒',
      '微信订阅消息',
      '检测进度与用量周报',
      '已绑定',
      '已授权',
      '实名与主体信息',
      '服务协议与隐私政策',
      '退出登录',
      '云算接入平台 v1.4.2',
      '© 2024 保留所有权利'
    ])
  })

  it('派生文案（未绑定 / 未授权 / 登录安全两态 / 占位 / 提示）为常量', () => {
    expect([UNBOUND_TEXT, UNAUTHORIZED_TEXT, SECURITY_ON_TEXT, SECURITY_OFF_TEXT, EMPTY_VALUE]).toEqual([
      '未绑定',
      '未授权',
      '已开启短信二次校验',
      '未开启短信二次校验',
      '—'
    ])
    expect([LOAD_FAIL_TEXT, LOGOUT_FAIL_TEXT]).toEqual(['数据加载失败，请稍后重试', '退出登录失败，请稍后重试'])
    expect([LOGOUT_CONFIRM_TITLE, LOGOUT_CONFIRM_CONTENT]).toEqual([
      '退出登录',
      '确认退出当前账号？退出后需重新登录。'
    ])
  })
})

describe('序号 23 · 手机号脱敏（设计帧「138 **** 6621」）', () => {
  it('11 位手机号 → 前 3 + 空格 + **** + 空格 + 后 4（设计帧格式）', () => {
    expect(maskPhone('13812346621')).toBe('138 **** 6621')
    expect(maskPhone(13812346621)).toBe('138 **** 6621')
  })

  it('服务端已脱敏（含 *）→ 原样直出，不二次改写', () => {
    expect(maskPhone('138****6621')).toBe('138****6621')
    expect(maskPhone('sk-****abcd')).toBe('sk-****abcd')
  })

  it('缺失 / 非法 → 占位「—」（不编造号码）', () => {
    expect(maskPhone('')).toBe(EMPTY_VALUE)
    expect(maskPhone(undefined)).toBe(EMPTY_VALUE)
    expect(maskPhone(null)).toBe(EMPTY_VALUE)
    expect(maskPhone('待补充')).toBe(EMPTY_VALUE)
  })
})

describe('序号 23 · 账号信息卡（3 行 · 标签列 87 · 值与胶囊）', () => {
  const raw = { phone: '13812346621', wechat_bound: true, sms_two_factor: true }

  it('三行标签逐字对齐设计帧', () => {
    const model = buildSettingsOverview(raw, true)
    expect(model.accountTitle).toBe(ACCOUNT_TITLE)
    expect(model.accountRows.map((r) => r.label)).toEqual(['手机号', '微信绑定', '登录安全'])
  })

  it('手机号取值经脱敏；微信绑定为绿胶囊；登录安全取派生两态', () => {
    const model = buildSettingsOverview(raw, true)
    expect(model.accountRows[0].value).toBe('138 **** 6621')
    expect(model.accountRows[0].pill).toBe(false)
    expect(model.accountRows[1].value).toBe(BOUND_TEXT)
    expect(model.accountRows[1].pill).toBe(true)
    expect(model.accountRows[2].value).toBe(SECURITY_ON_TEXT)
  })

  it('微信未绑定 / 二次校验未开 → 对应文案且不再用胶囊', () => {
    const model = buildSettingsOverview({ phone: '13812346621', wechat_bound: false, sms_two_factor: false }, true)
    expect(model.accountRows[1].value).toBe(UNBOUND_TEXT)
    expect(model.accountRows[1].pill).toBe(false)
    expect(model.accountRows[2].value).toBe(SECURITY_OFF_TEXT)
  })

  it('字段缺失 → 占位「—」（不冒充已绑定 / 已开启）', () => {
    const model = buildSettingsOverview({}, true)
    expect(model.accountRows.map((r) => r.value)).toEqual([EMPTY_VALUE, EMPTY_VALUE, EMPTY_VALUE])
    expect(model.accountRows.every((r) => r.pill === false)).toBe(true)
  })

  it('字段别名容错（18-API 无字段级 schema）：mobile / wechatBound / smsTwoFactor 均可读', () => {
    const model = buildSettingsOverview(
      { mobile: '13812346621', wechatBound: true, smsTwoFactor: true },
      true
    )
    expect(model.accountRows.map((r) => r.value)).toEqual(['138 **** 6621', BOUND_TEXT, SECURITY_ON_TEXT])
  })

  it('服务端给出登录安全文本时优先（服务端口径 > 前端派生）', () => {
    const model = buildSettingsOverview({ login_security: '已开启指纹校验' }, true)
    expect(model.accountRows[2].value).toBe('已开启指纹校验')
  })
})

describe('序号 23 · 通知设置卡（短信开关 + 微信订阅消息）', () => {
  it('两行标题与副文案逐字对齐设计帧', () => {
    const model = buildSettingsOverview({}, SMS_NOTIFY_DEFAULT)
    expect(model.notifyTitle).toBe(NOTIFY_TITLE)
    expect(model.notifyRows.map((r) => r.title)).toEqual([SMS_NOTIFY_TITLE, SUBSCRIBE_TITLE])
    expect(model.notifyRows.map((r) => r.desc)).toEqual([SMS_NOTIFY_DESC, SUBSCRIBE_DESC])
  })

  it('短信行为开关控件（本地态，取值来自入参）；微信订阅为胶囊控件', () => {
    const on = buildSettingsOverview({ wechat_subscribed: true }, true)
    expect(on.notifyRows[0].control).toBe('switch')
    expect(on.notifyRows[0].on).toBe(true)
    expect(on.notifyRows[1].control).toBe('badge')
    expect(on.notifyRows[1].value).toBe(AUTHORIZED_TEXT)
    expect(on.notifyRows[1].pill).toBe(true)

    const off = buildSettingsOverview({ wechat_subscribed: true }, false)
    expect(off.notifyRows[0].on).toBe(false)
  })

  it('订阅未授权 → 「未授权」且不用胶囊；字段缺失 → 占位「—」', () => {
    const denied = buildSettingsOverview({ wechat_subscribed: false }, true)
    expect(denied.notifyRows[1].value).toBe(UNAUTHORIZED_TEXT)
    expect(denied.notifyRows[1].pill).toBe(false)
    const unknown = buildSettingsOverview({}, true)
    expect(unknown.notifyRows[1].value).toBe(EMPTY_VALUE)
    expect(unknown.notifyRows[1].pill).toBe(false)
  })

  it('开关默认值取设计帧常量（本帧为开）', () => {
    expect(SMS_NOTIFY_DEFAULT).toBe(true)
  })
})

describe('序号 23 · 功能入口卡（3 行 · 图标底色三色 · 落点）', () => {
  it('三行文案与图标色调逐条对齐设计帧', () => {
    const model = buildSettingsOverview({}, true)
    expect(model.entryRows.map((r) => r.label)).toEqual([ENTRY_IDENTITY_TEXT, ENTRY_LEGAL_TEXT, ENTRY_LOGOUT_TEXT])
    expect(model.entryRows.map((r) => r.tone)).toEqual(['primary', 'neutral', 'danger'])
  })

  it('实名与主体信息 → 主体档案页；服务协议与隐私政策 → 画布无该页（无落点）', () => {
    const model = buildSettingsOverview({}, true)
    expect(model.entryRows[0].target).toBe(PROFILE_PAGE)
    expect(LEGAL_TARGET).toBe('')
    expect(model.entryRows[1].target).toBe(LEGAL_TARGET)
  })

  it('退出登录是 api 类动作（POST /auth/logout），不是导航落点', () => {
    const model = buildSettingsOverview({}, true)
    expect(model.entryRows[2].target).toBe('')
    expect(model.entryRows[2].action).toBe(LOGOUT_ACTION)
    expect(LOGOUT_ACTION).toBe('logout')
  })
})

describe('序号 23 · 账号信息卡三行的落点（画布无对应页 → 无落点）', () => {
  it('手机号 / 微信绑定 / 登录安全三行 target 均为空串（不臆造路由）', () => {
    const model = buildSettingsOverview({}, true)
    expect(model.accountRows.map((r) => r.target)).toEqual(['', '', ''])
  })
})

describe('序号 23 · 整页视图模型', () => {
  it('结构：导航标题 + 3 卡 + 底部两行；行数 3/2/3', () => {
    const model = buildSettingsOverview({ phone: '13812346621', wechat_bound: true }, true)
    expect(model.navTitle).toBe(NAV_TITLE)
    expect(model.accountRows).toHaveLength(3)
    expect(model.notifyRows).toHaveLength(2)
    expect(model.entryRows).toHaveLength(3)
    expect(model.footer).toEqual({ version: FOOTER_VERSION_TEXT, copyright: FOOTER_COPYRIGHT_TEXT })
  })

  it('raw 为 null / undefined 时仍能得到完整结构（全部走占位）', () => {
    const model = buildSettingsOverview(null, SMS_NOTIFY_DEFAULT)
    expect(model.accountRows).toHaveLength(3)
    expect(model.accountRows[0].value).toBe(EMPTY_VALUE)
    expect(model.notifyRows[1].value).toBe(EMPTY_VALUE)
    expect(model.entryRows).toHaveLength(3)
  })
})
