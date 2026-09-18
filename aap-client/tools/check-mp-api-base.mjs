#!/usr/bin/env node
/**
 * 构建门禁 · 小程序产物内接口基址必须是绝对 URL
 *
 * 为什么需要这个门禁（真实缺陷，2026-09-19 联调发现）：
 *   H5 里 `uni.request` 走浏览器 XHR，相对路径 `/api/v1/...` 由 dev server 的 `server.proxy` 反代到后端，能跑通；
 *   但小程序里 `uni.request` 直接落到 `wx.request`，**相对 URL 一律失败**（request:fail invalid url），
 *   小程序运行时也不存在 proxy。
 *   → 这个缺陷在 H5 浏览器验收里 100% 看不见，只有在小程序产物/运行时才暴露。
 *
 * 判据是**执行态**而非 grep：把真实编译产物 `dist/build/mp-weixin/api/http.js` 加载起来，
 * 用一个最小 `common/vendor.js` 替身（即 uni 运行时）拦截它发出的请求，检查 URL。
 *   好处：产物里基址是字面量还是运行时算出来的，都拦得住；grep 会漏。
 *
 * 用法：npm run build:mp-weixin && node tools/check-mp-api-base.mjs
 * 退出码：0 = 通过；1 = 存在相对基址；2 = 没拦到请求（空转，防假绿）
 */
import { mkdirSync, cpSync, writeFileSync, existsSync, rmSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const distApi = resolve(here, '../dist/build/mp-weixin/api')
const httpJs = join(distApi, 'http.js')

if (!existsSync(httpJs)) {
  console.error(`[FAIL] 找不到编译产物：${httpJs}`)
  console.error('       先跑 `npm run build:mp-weixin`')
  process.exit(1)
}

/** 沙箱：复制真实产物（整个 api/ 目录），只把 common/vendor.js 换成替身（= uni 运行时桩） */
const sandbox = resolve(here, '../.mp-gate-sandbox')
rmSync(sandbox, { recursive: true, force: true })
mkdirSync(join(sandbox, 'common'), { recursive: true })
cpSync(distApi, join(sandbox, 'api'), { recursive: true })

const captured = []
const storage = new Map()

// 替身必须如实实现微信端的约束：**相对 URL 直接 fail**（wx.request 的真实行为）
const uniStub = {
  getSystemInfoSync: () => ({ uniPlatform: 'mp-weixin', platform: 'devtools' }),
  request(options) {
    captured.push(options)
    const url = String(options.url ?? '')
    const fail = options.fail
    const success = options.success
    if (!/^https?:\/\//.test(url)) {
      // 微信端真实报错：request:fail invalid url "/api/v1/auth/me"
      Promise.resolve().then(() =>
        fail?.({ errMsg: `request:fail invalid url "${url}"` })
      )
      return { abort() {} }
    }
    Promise.resolve().then(() =>
      success?.({ statusCode: 200, data: { code: '0', message: 'ok', data: {} }, header: {}, cookies: [] })
    )
    return { abort() {} }
  },
  getStorageSync: (k) => storage.get(k) ?? '',
  setStorageSync: (k, v) => storage.set(k, v),
  removeStorageSync: (k) => storage.delete(k)
}

writeFileSync(
  join(sandbox, 'common', 'vendor.js'),
  `module.exports = { index: globalThis.__uniStub__ };\n`
)
globalThis.__uniStub__ = uniStub

const require_ = createRequire(pathToFileURL(join(sandbox, 'api', 'http.js')))
const artifact = require_(join(sandbox, 'api', 'http.js'))

if (typeof artifact.http !== 'function') {
  console.error('[FAIL] 产物未导出 http()，门禁判据失效（编译产物形态变了？）')
  process.exit(2)
}

// 真的发一次请求，看它到底把什么 URL 交给 wx.request
await artifact.http('/auth/me').catch(() => {})

if (captured.length === 0) {
  console.error('[FAIL] 空转：没有拦到任何 wx.request 调用。门禁判据失效，不得判绿。')
  process.exit(2)
}

const bad = []
const good = []
for (const c of captured) {
  const url = String(c.url ?? '')
  ;(/^https?:\/\//.test(url) ? good : bad).push(url)
}

console.log(`[INFO] 执行态加载真实产物 dist/build/mp-weixin/api/http.js，拦截到 ${captured.length} 次请求`)
for (const u of good) console.log(`  [OK]   ${u}`)

if (bad.length > 0) {
  console.error(`\n[FAIL] ${bad.length} 处交给 wx.request 的是相对 URL —— 微信端会 request:fail invalid url：`)
  for (const u of bad) console.error(`  [BAD]  ${u}`)
  console.error('\n修法：非 H5 平台基址必须由 src/api/base-url.ts 的 resolveApiBase() 解析为绝对 URL。')
  process.exit(1)
}

console.log('\n[PASS] 小程序产物交给 wx.request 的基址是绝对 URL。')
rmSync(sandbox, { recursive: true, force: true })
