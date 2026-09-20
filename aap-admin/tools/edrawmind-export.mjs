#!/usr/bin/env node
/**
 * 万兴脑图（mm.edrawsoft.cn）脑图 → Markdown 导出。
 *
 * 用法：
 *   # 1) 登录取会话（弹有头浏览器，手动登录一次；用持久化 profile，之后不用再登）
 *   node tools/edrawmind-export.mjs --login
 *
 *   # 2) 导出
 *   node tools/edrawmind-export.mjs <脑图URL> [--out 输出.md] [--headed]
 *
 *   # 或直接给登录用户的 token
 *   node tools/edrawmind-export.mjs <脑图URL> --token <JWT>
 *
 * ── 已实测确认（非推测） ────────────────────────────────────────────
 *   导出接口：POST /api/mm_web/convert/coop2exprot
 *             （接口名拼作 coop2exprot —— 对方把 export 拼错了，照抄别「纠正」）
 *   鉴权位置：Authorization: Bearer <JWT>
 *             · 裸 token（无 Bearer）    → 401 `invalid token`
 *             · token / X-Token / Cookie → 401 `unauthorized`
 *   匿名不行：GET /api/mm_web/token?file_key=<id> 公开可用，但签出的是
 *             {"user_id":"0","permission":1,...} 的**访客票**，
 *             导出接口对它判 401 `signature is invalid`。
 *
 * ── 本版修的两处（上一版登录检测失败的原因） ─────────────────────────
 *   1. **检测太窄**：只认 localStorage 里的三段式 JWT。登录后凭据可能是
 *      **Cookie 会话**或不透明字符串 → 漏检。本版同时看 Cookie 与 storage。
 *   2. **鉴权载体**：登录后 App 走 Cookie，而上一版用 Node 侧 fetch 直发、
 *      **不带 Cookie** → 必然 signature invalid。本版把导出请求**放进页面上下文**
 *      发（page.evaluate + credentials:'include'），Cookie 自动生效，
 *      与 App 行为一致。
 *   3. 用**持久化 profile**（上一版用内存 context，关掉就丢登录态）。
 *
 * ── 定位过程（踩坑记录）────────────────────────────────────────────
 *   · 编辑页是 SPA 空壳（14KB），curl 拿不到内嵌 token、也不下发 Cookie
 *   · 真跑浏览器抓请求，App 启动只调两个接口：
 *       GET /api/mm_web/file/s/{ivt}?device_id=…（公开分享取文件元数据）
 *       GET /api/mm_web/token?file_key={appId}  （token 来源）
 *     且 App 自身请求**不带 JWT**（只发字面量 "Bearer" 占位）
 *   · 抓「第一个带 authorization 的请求头」当 token 是**错的**：
 *     实测首个是字面量 "Bearer"（长度 6 的占位空值），照抄会一路 401
 */
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { chromium } from 'playwright'

const API = 'https://mindapi.edrawsoft.cn/api/mm_web'
const PROFILE_DIR = path.join(os.homedir(), '.edrawmind-profile')
const JWT_RE = /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}/

const args = process.argv.slice(2)
const outIdx = args.indexOf('--out')
const outPath = outIdx >= 0 ? args[outIdx + 1] : null
const tokIdx = args.indexOf('--token')
const explicitToken = tokIdx >= 0 ? args[tokIdx + 1] : null
const headed = args.includes('--headed')
const inputUrl = args.find(
  (a, i) => !a.startsWith('--') && !(i > 0 && ['--out', '--token'].includes(args[i - 1]))
)

function parseMindUrl(u) {
  const p = new URL(u)
  return {
    appId: (p.pathname.match(/\/editor\/([A-Za-z0-9]+)/) || [])[1] || '',
    pageId: p.searchParams.get('page') || ''
  }
}

function payloadOf(jwt) {
  try {
    return JSON.parse(
      Buffer.from(jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8')
    )
  } catch {
    return {}
  }
}

const openProfile = (headless) =>
  chromium.launchPersistentContext(PROFILE_DIR, {
    channel: 'chrome',
    headless,
    viewport: { width: 1600, height: 900 },
    locale: 'zh-CN'
  })

/** 全面取凭据：storage 里的 JWT + 所有 cookie（登录后凭据可能在 Cookie 里） */
async function grabCredentials(ctx, page) {
  // ⚠️ 在 about:blank 上读 localStorage 会抛 SecurityError（同源限制）→ 必须包 try，
  //    并在调用前先导航到真实页面。本函数对「还没导航」的情况退化为只读 Cookie。
  const storage = await page
    .evaluate(() => {
      const o = {}
      try {
        for (const s of [localStorage, sessionStorage]) {
          for (let i = 0; i < s.length; i++) o[s.key(i)] = String(s.getItem(s.key(i)) || '')
        }
      } catch {
        return { __unavailable: '1' }
      }
      return o
    })
    .catch(() => ({}))
  const cookies = await ctx.cookies()
  let jwt = null
  let jwtKey = null
  for (const [k, v] of Object.entries(storage)) {
    const m = String(v).match(JWT_RE)
    if (m) {
      jwt = m[0]
      jwtKey = `storage["${k}"]`
      break
    }
  }
  if (!jwt) {
    for (const c of cookies) {
      const m = String(c.value).match(JWT_RE)
      if (m) {
        jwt = m[0]
        jwtKey = `cookie["${c.name}"]`
        break
      }
    }
  }
  return { storage, cookies, jwt, jwtKey }
}

/** --login：弹出有头浏览器，等人登录；用持久化 profile 保存 */
async function doLogin() {
  console.log(`打开浏览器（profile: ${PROFILE_DIR}）`)
  console.log('请在窗口里登录万兴脑图。登录后本脚本会自动识别并保存，之后不用再登。\n')
  const ctx = await openProfile(false)
  const page = ctx.pages()[0] || (await ctx.newPage())
  await page.goto('https://mm.edrawsoft.cn/', { waitUntil: 'domcontentloaded' })

  const deadline = Date.now() + 8 * 60 * 1000
  let done = false
  while (Date.now() < deadline) {
    await page.waitForTimeout(4000)
    const { storage, cookies, jwt, jwtKey } = await grabCredentials(ctx, page)
    const authish = [
      ...Object.keys(storage).filter((k) => /token|auth|user|session|login/i.test(k)),
      ...cookies.filter((c) => /token|auth|session|user/i.test(c.name)).map((c) => `cookie:${c.name}`)
    ]
    if (jwt || authish.length) {
      console.log('检测到登录态凭据：')
      if (jwt) {
        console.log(`  JWT 来源：${jwtKey}`)
        console.log(`  payload = ${JSON.stringify(payloadOf(jwt))}`)
      }
      if (authish.length) console.log(`  其它：${authish.slice(0, 10).join(', ')}`)
      done = true
      break
    }
  }
  console.log(
    done
      ? `✅ 会话已存入持久化 profile：${PROFILE_DIR}`
      : '⚠️ 8 分钟内未检测到登录态。profile 已保留，下次 --login 会带上已登状态。'
  )
  await ctx.close()
}

const main = async () => {
  if (args.includes('--login')) return doLogin()
  if (!inputUrl) {
    console.error('用法: node tools/edrawmind-export.mjs <脑图URL> [--out x.md] [--token JWT] | --login')
    process.exit(1)
  }

  const { appId, pageId } = parseMindUrl(inputUrl)
  if (!appId) throw new Error('未能从 URL 解析出脑图 id')
  console.log(`脑图 id=${appId}${pageId ? ` page=${pageId}` : ''}`)

  const ctx = await openProfile(!headed)
  const page = ctx.pages()[0] || (await ctx.newPage())

  // ★ 顺序很重要：**先导航到脑图页**，再读凭据。
  //   在 about:blank 上读 localStorage 会被同源策略拒绝（SecurityError）。
  await page.goto(inputUrl, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(8000)

  const cred = await grabCredentials(ctx, page)
  console.log(`凭据：cookie ${cred.cookies.length} 个；JWT ${cred.jwt ? '有' : '无'}`)
  if (cred.jwt) console.log(`  payload = ${JSON.stringify(payloadOf(cred.jwt))}`)

  const token = explicitToken || cred.jwt
  if (token && String(payloadOf(token).user_id ?? '') === '0') {
    console.log('⚠️ 这是**匿名** token（user_id=0），导出接口不认。请先 --login 用登录账号。')
    await ctx.close()
    process.exit(3)
  }

  // ★ 关键：在页面里发请求 → 自动带 Cookie，与 App 行为一致
  const shapes = [
    { file_key: appId, page: pageId, type: 'md' },
    { file_key: appId, page: pageId, format: 'md' },
    { file_key: appId, page: pageId },
    { file_key: appId, type: 'md' },
    { file_key: appId }
  ]
  const hdrs = { 'Content-Type': 'application/json' }
  if (token) hdrs.Authorization = `Bearer ${token}`

  let downloadUrl = null
  let hit = null
  for (const body of shapes) {
    const r = await page.evaluate(
      async ([api, h, b]) => {
        const res = await fetch(api, {
          method: 'POST',
          headers: h,
          body: JSON.stringify(b),
          credentials: 'include'
        })
        let j = null
        try {
          j = await res.json()
        } catch {
          /* 非 JSON */
        }
        return { status: res.status, j }
      },
      [`${API}/convert/coop2exprot`, hdrs, body]
    )
    const j = r.j
    if (j?.data?.download_url) {
      downloadUrl = j.data.download_url
      hit = JSON.stringify(body)
      break
    }
    console.log(`   · ${JSON.stringify(body)} → ${j ? `code=${j.code} ${j.msg}` : `http=${r.status}`}`)
  }

  if (!downloadUrl) {
    console.log('\n未取到 download_url。若错误是 unauthorized/signature invalid → 当前 profile 未登录。')
    console.log('请先执行：node tools/edrawmind-export.mjs --login')
    await ctx.close()
    process.exit(4)
  }
  console.log(`② 导出成功，入参形状：${hit}`)

  const dl = await fetch(downloadUrl)
  if (!dl.ok) throw new Error(`下载失败 http=${dl.status}`)
  const text = await dl.text()
  const target = path.resolve(outPath || `mindmap-${appId.slice(0, 8)}.md`)
  fs.writeFileSync(target, text, 'utf8')
  console.log(`③ 已保存：${target}（${text.length} 字符 / ${text.split('\n').length} 行）`)
  console.log(text.split('\n').slice(0, 10).map((l) => '   ' + l).join('\n'))
  console.log('✅ 流程走通')
  await ctx.close()
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(1)
})
