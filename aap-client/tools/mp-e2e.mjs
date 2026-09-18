#!/usr/bin/env node
/**
 * 小程序前后端联调执行器（真实 HTTP，非 mock）
 *
 * 做什么：
 *   把 `dist/build/mp-weixin/api/**` 的**真实编译产物**加载起来，只把 uni 运行时
 *   （`common/vendor.js`）替换成一个忠实实现微信端语义的桩：
 *     - `wx.request` → 真实 HTTP 打到 aap-server（GET 拼 query、其余 JSON body，与 wx.request 一致）
 *     - 相对 URL 一律 fail（微信端真实行为），防止联调脚本自己掩盖基址缺陷
 *     - `getStorageSync/setStorageSync` → token 存储
 *   然后在**小程序代码路径**上跑真实主链路：短信登录 → 拿 token → 工作台取数。
 *
 * 为什么这么做：
 *   微信开发者工具未安装（本机），H5 浏览器验收走的是 dev server 反代，看不到小程序侧的
 *   相对 URL / 域名白名单 / 存储等差异。本执行器直接跑编译产物，能真实覆盖接口契约与登录态。
 *
 * 用法：
 *   npm run build:mp-weixin
 *   node tools/mp-e2e.mjs                 # 默认打 http://127.0.0.1:8084
 *   AAP_API_BASE=... node tools/mp-e2e.mjs
 */
import { mkdirSync, cpSync, writeFileSync, rmSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const distApi = resolve(here, '../dist/build/mp-weixin/api')

const PHONE = process.env.AAP_E2E_PHONE || '13800138000'
const API_BASE = process.env.AAP_API_BASE || 'http://127.0.0.1:8084/api/v1'

const log = (...a) => console.log(...a)
const results = []
function step(name, ok, detail) {
  results.push({ name, ok, detail })
  log(`${ok ? '  ✓' : '  ✗'} ${name}${detail ? ` — ${detail}` : ''}`)
}

// ── 沙箱：真实产物 + uni 运行时替身 ───────────────────────────────────────────
const sandbox = resolve(here, '../.mp-e2e-sandbox')
rmSync(sandbox, { recursive: true, force: true })
mkdirSync(join(sandbox, 'common'), { recursive: true })
cpSync(distApi, join(sandbox, 'api'), { recursive: true })

const storage = new Map()
const traffic = []

/** 把 wx.request 的 options 翻成真实 HTTP 请求 */
async function realRequest(options) {
  const rawUrl = String(options.url ?? '')
  if (!/^https?:\/\//.test(rawUrl)) {
    // 微信端真实行为：相对 URL 直接失败
    const err = { errMsg: `request:fail invalid url "${rawUrl}"` }
    traffic.push({ url: rawUrl, method: options.method, status: 'INVALID_URL' })
    return { fail: err }
  }
  const method = String(options.method ?? 'GET').toUpperCase()
  let url = rawUrl
  const data = options.data
  const init = { method, headers: { ...(options.header || {}) } }

  if (method === 'GET' || method === 'DELETE') {
    if (data && typeof data === 'object') {
      const qs = new URLSearchParams()
      for (const [k, v] of Object.entries(data)) if (v !== undefined && v !== null) qs.append(k, String(v))
      const q = qs.toString()
      if (q) url += (url.includes('?') ? '&' : '?') + q
    }
  } else if (data !== undefined) {
    init.body = JSON.stringify(data)
    init.headers['Content-Type'] = init.headers['Content-Type'] || 'application/json'
  }

  const res = await fetch(url, init)
  const text = await res.text()
  let body
  try {
    body = JSON.parse(text)
  } catch {
    body = text
  }
  traffic.push({ url, method, status: res.status })
  return {
    ok: { statusCode: res.status, data: body, header: Object.fromEntries(res.headers), cookies: [] }
  }
}

const uniStub = {
  getSystemInfoSync: () => ({ uniPlatform: 'mp-weixin', platform: 'devtools' }),
  request(options) {
    realRequest(options)
      .then((r) => {
        if (r.fail) options.fail?.(r.fail)
        else options.success?.(r.ok)
        options.complete?.(r.ok ?? r.fail)
      })
      .catch((e) => options.fail?.({ errMsg: `request:fail ${e.message}` }))
    return { abort() {} }
  },
  getStorageSync: (k) => storage.get(k) ?? '',
  setStorageSync: (k, v) => storage.set(k, v),
  removeStorageSync: (k) => storage.delete(k),
  showToast: () => {},
  hideToast: () => {},
  showLoading: () => {},
  hideLoading: () => {}
}

writeFileSync(join(sandbox, 'common', 'vendor.js'), `module.exports = { index: globalThis.__uniStub__ };\n`)
globalThis.__uniStub__ = uniStub

const require_ = createRequire(pathToFileURL(join(sandbox, 'api', 'http.js')))
const { authApi } = require_(join(sandbox, 'api', 'auth.js'))
const { usageApi } = require_(join(sandbox, 'api', 'usage.js'))
const { providerApi } = require_(join(sandbox, 'api', 'provider.js'))

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// ── 主链路 ──────────────────────────────────────────────────────────────────
log(`\n小程序编译产物 ↔ aap-server 真实联调`)
log(`  产物：dist/build/mp-weixin/api/**`)
log(`  目标：${API_BASE}`)
log(`  平台：uniPlatform=mp-weixin（产物内运行时判定）\n`)

log('[1] 账号接入 · 发送短信验证码')
let devCode = ''
async function sendSmsOnce() {
  return authApi.sendSms({ phone: PHONE, captcha: 'A7K9' })
}
try {
  let send
  try {
    send = await sendSmsOnce()
  } catch (e) {
    // 后端对同手机号有 60s 频控（E-1903）；联调脚本如实等待后重试，不绕过频控
    if (e.code === 'E-1903') {
      log('    · 命中 60s 频控（E-1903），如实等待 62s 后重试…')
      await sleep(62_000)
      send = await sendSmsOnce()
    } else {
      throw e
    }
  }
  devCode = send?.dev_code || ''
  step('POST /auth/sms/send', true, `ttl=${send?.ttl} dev_code=${devCode ? '已下发' : '未下发'}`)
} catch (e) {
  step('POST /auth/sms/send', false, `${e.code || ''} ${e.message}`)
}

log('\n[2] 账号接入 · 短信登录换 Token')
let login = null
try {
  login = await authApi.login({ phone: PHONE, smsCode: devCode })
  step('POST /auth/sms/login', true, `role=${login?.role} providerId=${login?.providerId ?? '-'}`)
} catch (e) {
  step('POST /auth/sms/login', false, `${e.code || ''} ${e.message}`)
}

if (login?.token) {
  // 小程序里登录页也是写 storage；这里等价模拟登录成功后的落盘
  uniStub.setStorageSync('aap_token', login.token)
}

log('\n[3] 登录态 · token 是否落进小程序 storage')
const token = storage.get('aap_token') || ''
step('token 已入 storage', Boolean(token), token ? `${String(token).slice(0, 12)}…` : '空')

log('\n[4] 工作台取数（登录态接口）')
try {
  const summary = await usageApi.summary()
  step('GET /usage/summary', true, `字段数=${summary ? Object.keys(summary).length : 0}`)
} catch (e) {
  step('GET /usage/summary', false, `${e.code || ''} ${e.message}`)
}

try {
  const profile = await providerApi.profile()
  step('GET /provider/profile', true, `company_name=${profile?.company_name ?? profile?.companyName ?? '-'}`)
} catch (e) {
  step('GET /provider/profile', false, `${e.code || ''} ${e.message}`)
}

log('\n[5] 鉴权头真实性（用错 token 应被拒，证明后端真的在校验）')
const realToken = storage.get('aap_token')
storage.set('aap_token', 'invalid.token.value')
let rejected = false
try {
  await usageApi.summary()
} catch (e) {
  rejected = e.code === 'E-1902' || /401|未认证|登录/.test(`${e.code} ${e.message}`)
}
storage.set('aap_token', realToken)
step('伪造 token 被后端拒绝', rejected, rejected ? 'E-1902' : '后端未拒绝（鉴权可疑）')

log('\n[6] 实际发出的 HTTP 流量')
for (const t of traffic) log(`  ${t.method.padEnd(6)} ${t.status}  ${t.url}`)

const invalid = traffic.filter((t) => t.status === 'INVALID_URL')
const failed = results.filter((r) => !r.ok)

log(`\n${'─'.repeat(72)}`)
log(`结果：${results.length - failed.length}/${results.length} 步通过；HTTP 请求 ${traffic.length} 次；相对 URL 失败 ${invalid.length} 次`)

rmSync(sandbox, { recursive: true, force: true })

if (failed.length || invalid.length) {
  log(`\n[FAIL] 联调未通过：${failed.map((f) => f.name).join('、') || '存在相对 URL 请求'}`)
  process.exit(1)
}
log('\n[PASS] 小程序编译产物 ↔ aap-server 主链路联调通过。')
