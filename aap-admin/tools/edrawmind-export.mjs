#!/usr/bin/env node
/**
 * 万兴脑图（mm.edrawsoft.cn）脑图 → Markdown 导出。**已实测走通。**
 *
 * 用法：
 *   # 1) 登录一次（弹有头浏览器，手动登录；用持久化 profile，之后免登）
 *   node tools/edrawmind-export.mjs --login
 *
 *   # 2) 导出
 *   node tools/edrawmind-export.mjs <脑图URL> [--out 输出.md] [--headed]
 *
 *   # 或直接给登录 token（从浏览器 DevTools 的 Authorization 头里复制 Bearer 后面那串）
 *   node tools/edrawmind-export.mjs <脑图URL> --token <JWT>
 *
 * ══════════════════════════════════════════════════════════════════════════
 * 正确的请求形态（**来自用户 DevTools 的真实 curl，不是我猜的**）
 * ══════════════════════════════════════════════════════════════════════════
 *   POST https://mindapi.edrawsoft.cn/api/mm_web/convert/coop2exprot
 *     （接口名拼作 coop2exprot —— 对方的 export 拼错了，照抄别「纠正」）
 *
 *   Headers（**实测必需项**，逐条验证过）：
 *     authorization: Bearer <账号登录 JWT>   ← 唯一真正必需的
 *     content-type: application/json;charset=UTF-8
 *     origin: https://mm.edrawsoft.cn
 *     referer: https://mm.edrawsoft.cn/
 *     x-device-id: <设备指纹>   ← ⚠️ **非必需**：实测「不带」与「用随机值」都返回 code=200。
 *                                此处保留（随机值）只为与浏览器请求更一致，不是硬要求。
 *
 *   Body：
 *     {"file_key":"<脑图id>","export_type":"markdown","export_params":{"pageIndex":0}}
 *                  ↑ export_type 是 "markdown"（**不是 "md"**），且多了嵌套 export_params
 *
 *   响应：{"code":200,"msg":"success","data":{"download_url":"https://…oss…md?Expires=…"}}
 *   再 GET download_url 即得 .md（OSS 签名直链，无需再带鉴权头）
 *
 * ══════════════════════════════════════════════════════════════════════════
 * 两套 token，别搞混（这是之前一直 401 的根因）
 * ══════════════════════════════════════════════════════════════════════════
 *   · GET /api/mm_web/token?file_key=<id>  →  **访客票**
 *        payload: {"file_key":…,"user_id":"0","permission":1,"expires_at":…}
 *        公开可调、无需登录，但导出接口对它判 401 `signature is invalid`
 *   · 账号登录 JWT（导出真正要的）→  payload:
 *        {"iss":"EdrawSoft","aud":"<userId>","src":"password",
 *         "sub":"{…union_key:\"<uid>-xxxx\", platform:\"web\"}"}
 *        aud 即用户 id，src 表示登录方式。**它不在 localStorage/Cookie 里**
 *        （实测登录后 storage 只有 qdwpa_saas_d2_<uid> 等非 JWT 值），
 *        需要用 --token 传入，或由浏览器运行时取。
 *
 * ══════════════════════════════════════════════════════════════════════════
 * 踩坑记录（每条都真实踩过，避免重走）
 * ══════════════════════════════════════════════════════════════════════════
 *   · 编辑页是 SPA 空壳（14KB）：curl 拿不到内嵌 token、也不下发任何 Cookie
 *   · 抓「第一个带 authorization 的请求头」当 token 是错的 ——
 *     实测首个是字面量 "Bearer"（长度 6 的占位空值），照抄会一路 401
 *   · 在 about:blank 上读 localStorage 会抛 SecurityError（同源限制）
 *     → 必须先导航到真实页面再取凭据
 *   · 登录后 App 走 Cookie，Node 侧 fetch 不带 Cookie → 必然 signature invalid
 *     → 请求放进页面上下文发（page.evaluate + credentials:'include'）
 *   · 登录检测不能只认「三段式 JWT」：凭据可能是 Cookie 会话或不透明串 → 会漏检
 *   · 导出菜单在公开访客视角下是 hidden（getBoundingClientRect 全 0），
 *     点不动 —— 别在这上面耗，直接用接口
 *   · **别把「看起来该必需」的头当成必需**：x-device-id 是 DevTools 里显示的头，
 *     我据此写成「缺一不可」，实测去掉照样 200 —— 断言必须验证过再写进文档
 */
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { chromium } from 'playwright'

const API = 'https://mindapi.edrawsoft.cn/api/mm_web/convert/coop2exprot'
const PROFILE_DIR = path.join(os.homedir(), '.edrawmind-profile')
// 设备指纹：**实测非必需**（不带也是 code=200），且随机值即可 →
// 用随机值，不把使用者的真实设备指纹写进仓库；需要固定时用 EDRAWMIND_DEVICE_ID 覆盖。
const DEVICE_ID = process.env.EDRAWMIND_DEVICE_ID || randomHex(16)

function randomHex(n) {
  return Array.from({ length: n * 2 }, () => '0123456789abcdef'[Math.floor(Math.random() * 16)]).join('')
}

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

/** --login：弹有头浏览器等人登录，会话存持久化 profile */
async function doLogin() {
  console.log(`打开浏览器（profile: ${PROFILE_DIR}）`)
  console.log('请在窗口里登录万兴脑图。登录后关掉窗口即可，会话会保留。\n')
  const ctx = await openProfile(false)
  const page = ctx.pages()[0] || (await ctx.newPage())
  await page.goto('https://mm.edrawsoft.cn/', { waitUntil: 'domcontentloaded' })

  const deadline = Date.now() + 8 * 60 * 1000
  while (Date.now() < deadline) {
    await page.waitForTimeout(4000)
    const st = await page
      .evaluate(() => {
        const o = {}
        try {
          for (const s of [localStorage, sessionStorage]) {
            for (let i = 0; i < s.length; i++) o[s.key(i)] = String(s.getItem(s.key(i)) || '')
          }
        } catch {
          /* 同源限制 */
        }
        return o
      })
      .catch(() => ({}))
    const authish = Object.keys(st).filter((k) => /user_id|token|auth|uuid|_d2_/i.test(k))
    if (authish.length) {
      console.log(`检测到登录态（${authish.length} 个相关键）：${authish.slice(0, 6).join(', ')}`)
      console.log(`✅ 会话已存入：${PROFILE_DIR}`)
      await ctx.close()
      return
    }
  }
  console.log('⚠️ 8 分钟内未检测到登录态。profile 已保留，下次 --login 会带上已登状态。')
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
  await page.goto(inputUrl, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(8000)

  let token = explicitToken
  if (!token) {
    // 兜底：扫 storage / cookie 找 iss=EdrawSoft 的账号 JWT（实测通常没有，故推荐 --token）
    const found = await page.evaluate(() => {
      const out = []
      try {
        for (const s of [localStorage, sessionStorage]) {
          for (let i = 0; i < s.length; i++) out.push(String(s.getItem(s.key(i)) || ''))
        }
      } catch {
        /* 同源限制 */
      }
      return out
    })
    for (const v of found) {
      const m = String(v).match(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/)
      if (m && payloadOf(m[0]).iss === 'EdrawSoft') {
        token = m[0]
        console.log('token 来源：storage 里的 EdrawSoft JWT')
        break
      }
    }
  }

  if (!token) {
    console.log('⚠️ 未取得账号登录 token（导出必需）。')
    console.log('   请先 --login，或用 --token 传入 DevTools 里 authorization 头的 Bearer 值。')
    await ctx.close()
    process.exit(3)
  }
  console.log(`token payload = ${JSON.stringify(payloadOf(token))}`)

  // ★ 正确的请求形态（来自真实 curl）
  const body = {
    file_key: appId,
    export_type: 'markdown',
    export_params: { pageIndex: 0 }
  }
  const headers = {
    authorization: `Bearer ${token}`,
    'content-type': 'application/json;charset=UTF-8',
    accept: 'application/json, text/plain, */*',
    origin: 'https://mm.edrawsoft.cn',
    referer: 'https://mm.edrawsoft.cn/',
    'x-device-id': DEVICE_ID
  }

  // 放在页面上下文里发：Cookie / 同源策略 / UA 与真实浏览器一致
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
      return { status: res.status, j, text: JSON.stringify(j) }
    },
    [API, headers, body]
  )

  const downloadUrl = r.j?.data?.download_url
  if (!downloadUrl) {
    console.log(`② 导出失败：http=${r.status} ${r.text?.slice(0, 200)}`)
    await ctx.close()
    process.exit(4)
  }
  console.log(`② 导出成功 code=${r.j.code}（body: file_key + export_type=markdown + export_params.pageIndex）`)

  const dl = await fetch(downloadUrl)
  if (!dl.ok) throw new Error(`下载失败 http=${dl.status}`)
  const text = await dl.text()
  const target = path.resolve(outPath || `mindmap-${appId.slice(0, 8)}.md`)
  fs.writeFileSync(target, text, 'utf8')

  const lines = text.split('\n')
  console.log(`③ 已保存：${target}（${text.length} 字符 / ${lines.length} 行）`)
  console.log('   开头预览：')
  console.log(lines.slice(0, 10).map((l) => '     ' + l).join('\n'))
  console.log('✅ 流程走通')
  await ctx.close()
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(1)
})
