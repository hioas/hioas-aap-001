#!/usr/bin/env node
/**
 * 微信开发者工具内联调冒烟（真微信小程序 runtime）
 *
 * 与 tools/mp-e2e-full.mjs 的分工：
 *   - mp-e2e-full.mjs：加载**编译产物**在 Node 里跑接口链路（验接口契约/鉴权/字段）
 *   - 本脚本：在**真微信 runtime**（开发者工具模拟器）里跑页面（验 wx.request 真行为、
 *     storage、TabBar、wxss 渲染、页面跳转——这些在 H5/Node 里都验不到）
 *
 * 前置：
 *   1. 开发者工具已登录（cli islogin 返回 true）
 *   2. 已 `cli auto --project <dist/build/mp-weixin> --auto-port 9420`（开自动化端口）
 *   3. aap-server 在 8084，且产物基址指向它（见 src/api/base-url.ts）
 *
 * 用法：node tools/mp-ide-smoke.mjs
 */
import { createRequire } from 'node:module'
import { writeFileSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const require_ = createRequire(import.meta.url)
const automator = require_('miniprogram-automator')

const here = dirname(fileURLToPath(import.meta.url))
const SHOTS = resolve(here, '../evidence/ide')
mkdirSync(SHOTS, { recursive: true })

const WS = process.env.MP_AUTO_WS || 'ws://127.0.0.1:9420'
const API = process.env.AAP_API_BASE || 'http://127.0.0.1:8084/api/v1'
const PHONE = process.env.AAP_E2E_PHONE || '13800138000'

const rows = []
const mark = (name, ok, detail) => {
  rows.push({ name, ok, detail })
  console.log(`  ${ok ? '✓' : '✗'} ${name}${detail ? ` — ${detail}` : ''}`)
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

console.log(`微信开发者工具内冒烟`)
console.log(`  ws=${WS}  后端=${API}  账号=${PHONE}\n`)

// ── 0. 连接 ────────────────────────────────────────────────────────────────
let mp
try {
  mp = await automator.connect({ wsEndpoint: WS })
  mark('连接自动化端口', true, WS)
} catch (e) {
  mark('连接自动化端口', false, e.message)
  console.log('\n[FAIL] 连不上自动化端口。先跑：')
  console.log('  cli.bat auto --project "<dist/build/mp-weixin 绝对路径>" --auto-port 9420')
  process.exit(1)
}

// ── 1. 证明这是真微信 runtime ──────────────────────────────────────────────
try {
  const si = await mp.systemInfo()
  const plat = si?.platform ?? si?.uniPlatform ?? '-'
  const model = si?.model ?? '-'
  mark('系统信息（真 runtime）', true, `platform=${plat} model=${model} SDK=${si?.SDKVersion ?? '-'}`)
} catch (e) {
  mark('系统信息（真 runtime）', false, e.message)
}

// ── 2. Node 侧取短信码（小程序侧只做登录，避免与页面「获取验证码」互相顶掉）──
let devCode = ''
try {
  const send = await fetch(`${API}/auth/sms/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: PHONE, captcha: '1234' })
  }).then((r) => r.json())
  if (send?.code !== '0') throw new Error(`${send?.code} ${send?.message}`)
  devCode = send.data?.dev_code || ''
  mark('取短信验证码（真实接口）', Boolean(devCode), devCode ? `ttl=${send.data.ttl}` : '后端未回显 dev_code')
} catch (e) {
  mark('取短信验证码（真实接口）', false, e.message)
}

// ── 3. 登录页：真机交互 → 真实后端 → token 落 storage ─────────────────────
let loginOk = false
try {
  const page = await mp.reLaunch('/pages/login/index')
  await page.waitFor(800)

  const typeInto = async (testId, text) => {
    const el = await page.$(`[data-test="${testId}"] input`)
    if (!el) throw new Error(`找不到输入框 [data-test="${testId}"]`)
    await el.input(text)
  }

  await typeInto('phone', PHONE)
  await typeInto('captcha', '1234')
  await typeInto('smsCode', devCode)
  const box = await page.$('[data-test="agree-box"]')
  await box.tap()
  await sleep(300)
  const btn = await page.$('[data-test="btn-login"]')
  await btn.tap()
  await sleep(2500)

  const cur = await mp.currentPage()
  const path = cur?.path ?? ''
  loginOk = /workbench/.test(path)
  await mp.screenshot({ path: resolve(SHOTS, '01-after-login.png') })
  mark('登录（真机点击 → 真后端 → 跳工作台）', loginOk, `当前页=${path}`)

  // token 是否真的落进小程序 storage（H5/Node 里验不到）
  const tok = await mp.callWxMethod('getStorageSync', 'aap_token').catch(() => null)
  mark('token 落进小程序 storage', Boolean(tok && String(tok).length > 10), tok ? `${String(tok).slice(0, 14)}…` : '空')
} catch (e) {
  mark('登录（真机点击 → 真后端 → 跳工作台）', false, e.message)
}

// ── 4. 全页面冒烟：逐页 reLaunch，看是否渲染出内容且无报错 ──────────────────
const appJson = require_(resolve(here, '../dist/build/mp-weixin/app.json'))
const pages = appJson.pages || []
console.log(`\n全页面冒烟（${pages.length} 页）`)

const pageResults = []
for (const p of pages) {
  const url = `/${p}`
  try {
    const page = await mp.reLaunch(url)
    await page.waitFor(1200)
    const cur = await mp.currentPage()
    const actual = cur?.path ?? ''
    // 取页面可见文本长度作为「渲染出内容」的判据（空壳页面文本≈0）
    const textLen = await page
      .$$('view,text')
      .then(async (els) => {
        let n = 0
        for (const el of els.slice(0, 400)) {
          const t = await el.text().catch(() => '')
          n += (t || '').length
        }
        return n
      })
      .catch(() => -1)
    const landed = actual === p
    // ⚠️ 判据说明：`page.$$('view,text')` 与 wx.createSelectorQuery() **都不跨自定义组件边界**，
    //    内容全在子组件里的页面（如 quote-form/index 是 QuoteFormView 的薄壳）文本恒为 0，
    //    但页面其实是正常渲染的（已用截图核对）。故**通过与否只由「落点是否正确」决定**，
    //    文本长度只作信号；低文本页面自动截图留证，避免把渲染正常的组件型页面误报成缺陷。
    const thin = textLen <= 20
    pageResults.push({ page: p, ok: landed, textLen, componentOnly: thin })
    mark(
      p,
      landed,
      `落点=${actual} 可见文本≈${textLen}` + (thin ? '（内容在自定义组件内 → 已截图留证）' : '')
    )
    if (thin) await mp.screenshot({ path: resolve(SHOTS, `thin-${p.replace(/[/]/g, '_')}.png`) })
  } catch (e) {
    pageResults.push({ page: p, ok: false, err: e.message })
    mark(p, false, e.message)
  }
}

await mp.screenshot({ path: resolve(SHOTS, '02-last-page.png') })

// ── 5. 汇总 ────────────────────────────────────────────────────────────────
const bad = rows.filter((r) => !r.ok)
const pageBad = pageResults.filter((r) => !r.ok)
console.log(`\n${'─'.repeat(76)}`)
console.log(
  `步骤 ${rows.length}：通过 ${rows.length - bad.length}，失败 ${bad.length}；` +
    `页面 ${pages.length}：通过 ${pages.length - pageBad.length}，失败 ${pageBad.length}`
)
if (bad.length) {
  console.log('\n失败明细：')
  for (const b of bad) console.log(`  ✗ ${b.name} — ${b.detail}`)
}
writeFileSync(
  resolve(here, '../../.agents/state/evidence/mp-ide-smoke.json'),
  JSON.stringify({ ws: WS, api: API, phone: PHONE, rows, pages: pageResults }, null, 2)
)
console.log(`\n明细已写入 .agents/state/evidence/mp-ide-smoke.json`)

try {
  await mp.disconnect()
} catch {
  /* 断开失败不影响结论 */
}
process.exit(bad.length || pageBad.length ? 1 : 0)
