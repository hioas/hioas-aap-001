/**
 * 序号 23【工作台与我的】我的设置（page-23-2 / /pages/settings/index）— 视图模型
 *
 * 真源：
 *  - 设计：.calicat/raw/pages/page-23-2/design.tree.json
 *      （430 宽 · 设计总高 797 = 导航 96 + 12 + 账号信息卡 223 + 12 + 通知设置卡 176 + 12 + 功能入口卡 186 + 底部说明 80）
 *      文案逐字：账号与设置 / 账号信息 / 手机号 / 138 **** 6621 / 微信绑定 / 已绑定 / 登录安全 /
 *      已开启短信二次校验 / 通知设置 / 短信通知 / 审核结果、账单与合同提醒 / 微信订阅消息 /
 *      检测进度与用量周报 / 已授权 / 实名与主体信息 / 服务协议与隐私政策 / 退出登录 /
 *      云算接入平台 v1.4.2 / © 2024 保留所有权利
 *  - 接口：18-API设计OpenAPI.md（前缀 /api/v1）
 *      Auth → GET /auth/me（手机号 / 微信绑定 / 登录安全）· POST /auth/logout（退出登录）
 *
 * ⚠️ 缺口（一律记台账序号 23，不臆造）：
 *  1. `/auth/me` 字段级 schema 未定义（18-API 只列路径）→ phone / wechat_bound / sms_two_factor
 *     等字段名与微信绑定、二次校验取值均为**容错读取**（含别名），缺字段渲染占位「—」，不冒充状态；
 *  2. 手机号脱敏格式两处口径不同：18-API 通用约定写 `138****8888`，设计帧写 `138 **** 6621`
 *     → 服务端已带 `*` 时**原样直出**（服务端口径优先），客户端派生时**按设计帧格式**（带空格）；
 *  3. 通知设置（短信通知开关 / 微信订阅消息）在 22 份 PRD 零命中，18-API 亦无 `/settings/**`
 *     → 开关只做**本地状态**（不发请求，`missing-prd`）；初始值取设计帧常量（开）；「已授权」徽标为只读展示；
 *  4. 「手机号 / 微信绑定 / 登录安全」三行在设计帧有 chevron，但画布 30 页**无**对应页
 *     → 无落点（target 空串），点击不跳转、不弹占位提示（同序号 22「明细入口」口径）；
 *  5. 「服务协议与隐私政策」同样无画布页、PRD 无外链地址 → 无落点（不臆造 URL）；
 *  6. 退出登录成功后的落点（reLaunch 登录页）PRD 无定义 → REST/交互推断，记台账；
 *  7. 短信开关关闭态配色设计帧未给（本帧只有开态蓝）→ 关态用中性 #CBD5E1（占位，记台账）。
 */
import { PROFILE_PAGE } from './routes'

export { PROFILE_PAGE }

/* ============================== 设计文案（逐字，不得改写） ============================== */

export const NAV_TITLE = '账号与设置'
export const ACCOUNT_TITLE = '账号信息'
export const NOTIFY_TITLE = '通知设置'
export const PHONE_LABEL = '手机号'
export const WECHAT_LABEL = '微信绑定'
export const SECURITY_LABEL = '登录安全'
export const SMS_NOTIFY_TITLE = '短信通知'
export const SMS_NOTIFY_DESC = '审核结果、账单与合同提醒'
export const SUBSCRIBE_TITLE = '微信订阅消息'
export const SUBSCRIBE_DESC = '检测进度与用量周报'
export const BOUND_TEXT = '已绑定'
export const AUTHORIZED_TEXT = '已授权'
export const ENTRY_IDENTITY_TEXT = '实名与主体信息'
export const ENTRY_LEGAL_TEXT = '服务协议与隐私政策'
export const ENTRY_LOGOUT_TEXT = '退出登录'
export const FOOTER_VERSION_TEXT = '云算接入平台 v1.4.2'
export const FOOTER_COPYRIGHT_TEXT = '© 2024 保留所有权利'

/* ============================== 派生文案（设计帧无对照 → 常量集中，缺口记台账） ============================== */

export const UNBOUND_TEXT = '未绑定'
export const UNAUTHORIZED_TEXT = '未授权'
export const SECURITY_ON_TEXT = '已开启短信二次校验'
export const SECURITY_OFF_TEXT = '未开启短信二次校验'
/** 字段缺失占位（设计帧无空态稿 → 占位符，不编造状态） */
export const EMPTY_VALUE = '—'
/** 取数失败提示（设计稿无 toast 稿 → 占位，与序号 20/21/22 同口径） */
export const LOAD_FAIL_TEXT = '数据加载失败，请稍后重试'
/** 退出登录二次确认文案（设计帧无弹窗稿 → 占位，同序号 8「删除」口径） */
export const LOGOUT_CONFIRM_TITLE = '退出登录'
export const LOGOUT_CONFIRM_CONTENT = '确认退出当前账号？退出后需重新登录。'
/** 退出登录失败提示（占位）；本地 token 由 authApi.logout 的 finally 清除，仍回登录页 */
export const LOGOUT_FAIL_TEXT = '退出登录失败，请稍后重试'

/** 短信通知开关默认值：设计帧为开态（无接口可读 → 常量，记台账缺口 3） */
export const SMS_NOTIFY_DEFAULT = true

/** 三个无落点的 target 空串（画布无对应页 → 不臆造路由，缺口 4/5） */
export const PHONE_TARGET = ''
export const WECHAT_TARGET = ''
export const SECURITY_TARGET = ''
export const LEGAL_TARGET = ''
/** 退出登录 = api 类动作（POST /auth/logout），非导航落点 */
export const LOGOUT_ACTION = 'logout'

export const ENTRY_TONES = ['primary', 'neutral', 'danger'] as const
export type EntryTone = (typeof ENTRY_TONES)[number]

/* ============================== 中性工具 ============================== */

const str = (value: unknown): string => {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return ''
}

const firstStr = (...values: unknown[]): string => {
  for (const v of values) {
    const s = str(v)
    if (s) return s
  }
  return ''
}

/** 布尔容错：true/false、'true'/'false'、1/0、'1'/'0'、'yes'/'no'；其余 → undefined（不猜测） */
const boolOf = (...values: unknown[]): boolean | undefined => {
  for (const v of values) {
    if (typeof v === 'boolean') return v
    if (typeof v === 'number' && (v === 1 || v === 0)) return v === 1
    const s = str(v).toLowerCase()
    if (s === 'true' || s === '1' || s === 'yes') return true
    if (s === 'false' || s === '0' || s === 'no') return false
  }
  return undefined
}

/**
 * 手机号脱敏（设计帧「138 **** 6621」）：
 *  - 服务端已带 `*` → 原样直出（服务端口径优先，18-API 写 `138****8888`，与设计帧不一致，缺口 2）；
 *  - 11 位（或任意 ≥7 位纯数字）→ `前3 **** 后4`；
 *  - 其余（空 / 非数字 / 过短）→ 占位「—」（不编造号码）。
 */
export function maskPhone(value: unknown): string {
  const s = str(value)
  if (!s) return EMPTY_VALUE
  if (s.includes('*')) return s
  const digits = s.replace(/\D/g, '')
  if (digits.length === 11) return `${digits.slice(0, 3)} **** ${digits.slice(7)}`
  if (digits.length >= 7) return `${digits.slice(0, 3)} **** ${digits.slice(-4)}`
  return EMPTY_VALUE
}

/* ============================== 类型 ============================== */

/** GET /auth/me 响应（18-API 无字段级 schema → 全部可选 + 别名容错） */
export interface SettingsRaw {
  phone?: unknown
  mobile?: unknown
  phone_number?: unknown
  wechat_bound?: unknown
  wechatBound?: unknown
  wx_bound?: unknown
  wechat_authorized?: unknown
  login_security?: unknown
  security_text?: unknown
  sms_2fa?: unknown
  sms_two_factor?: unknown
  smsTwoFactor?: unknown
  wechat_subscribed?: unknown
  subscribe_authorized?: unknown
  [key: string]: unknown
}

export interface AccountRow {
  key: 'phone' | 'wechat' | 'security'
  label: string
  value: string
  /** 绿胶囊（设计帧「已绑定」）—— 仅服务端明确为真时使用 */
  pill: boolean
  /** 落点：画布无对应页 → 空串（不跳转） */
  target: string
}

export interface NotifyRow {
  key: 'sms' | 'subscribe'
  title: string
  desc: string
  control: 'switch' | 'badge'
  /** control=switch 时的本地开关态 */
  on?: boolean
  /** control=badge 时的展示值 */
  value?: string
  pill?: boolean
}

export interface EntryRow {
  key: 'identity' | 'legal' | 'logout'
  label: string
  tone: EntryTone
  /** 导航落点（空串 = 无落点） */
  target: string
  /** api 类动作 id（仅「退出登录」） */
  action?: string
}

export interface SettingsOverview {
  navTitle: string
  accountTitle: string
  accountRows: AccountRow[]
  notifyTitle: string
  notifyRows: NotifyRow[]
  entryRows: EntryRow[]
  footer: { version: string; copyright: string }
}

/* ============================== 视图模型构造 ============================== */

/**
 * 账号信息卡三行。
 * ⚠️ 微信绑定 / 登录安全 / 微信订阅的取值来源在 18-API 无字段级 schema（缺口 1）：
 *    服务端明确值时用服务端口径；缺字段一律「—」，绝不冒充「已绑定 / 已开启」。
 */
function buildAccountRows(raw: SettingsRaw): AccountRow[] {
  const phone = firstStr(raw.phone, raw.mobile, raw.phone_number)
  const bound = boolOf(raw.wechat_bound, raw.wechatBound, raw.wx_bound, raw.wechat_authorized)
  const securityText = firstStr(raw.login_security, raw.security_text)
  const twoFactor = boolOf(raw.sms_2fa, raw.sms_two_factor, raw.smsTwoFactor)

  const wechatValue = bound === true ? BOUND_TEXT : bound === false ? UNBOUND_TEXT : EMPTY_VALUE
  const securityValue = securityText || (twoFactor === true ? SECURITY_ON_TEXT : twoFactor === false ? SECURITY_OFF_TEXT : EMPTY_VALUE)

  return [
    { key: 'phone', label: PHONE_LABEL, value: maskPhone(phone), pill: false, target: PHONE_TARGET },
    { key: 'wechat', label: WECHAT_LABEL, value: wechatValue, pill: bound === true, target: WECHAT_TARGET },
    { key: 'security', label: SECURITY_LABEL, value: securityValue, pill: false, target: SECURITY_TARGET }
  ]
}

/** 通知设置卡两行：短信开关（本地态，入参）+ 微信订阅徽标（只读展示） */
function buildNotifyRows(raw: SettingsRaw, smsOn: boolean): NotifyRow[] {
  const subscribed = boolOf(raw.wechat_subscribed, raw.subscribe_authorized)
  const subscribeValue = subscribed === true ? AUTHORIZED_TEXT : subscribed === false ? UNAUTHORIZED_TEXT : EMPTY_VALUE
  return [
    { key: 'sms', title: SMS_NOTIFY_TITLE, desc: SMS_NOTIFY_DESC, control: 'switch', on: smsOn },
    {
      key: 'subscribe',
      title: SUBSCRIBE_TITLE,
      desc: SUBSCRIBE_DESC,
      control: 'badge',
      value: subscribeValue,
      pill: subscribed === true
    }
  ]
}

function buildEntryRows(): EntryRow[] {
  return [
    { key: 'identity', label: ENTRY_IDENTITY_TEXT, tone: 'primary', target: PROFILE_PAGE },
    { key: 'legal', label: ENTRY_LEGAL_TEXT, tone: 'neutral', target: LEGAL_TARGET },
    { key: 'logout', label: ENTRY_LOGOUT_TEXT, tone: 'danger', target: '', action: LOGOUT_ACTION }
  ]
}

export function buildSettingsOverview(
  raw: SettingsRaw | null | undefined,
  smsOn: boolean = SMS_NOTIFY_DEFAULT
): SettingsOverview {
  const source: SettingsRaw = raw ?? {}
  return {
    navTitle: NAV_TITLE,
    accountTitle: ACCOUNT_TITLE,
    accountRows: buildAccountRows(source),
    notifyTitle: NOTIFY_TITLE,
    notifyRows: buildNotifyRows(source, smsOn),
    entryRows: buildEntryRows(),
    footer: { version: FOOTER_VERSION_TEXT, copyright: FOOTER_COPYRIGHT_TEXT }
  }
}
