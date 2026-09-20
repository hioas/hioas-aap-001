#!/usr/bin/env node
/**
 * 诊断：万兴脑图的 token 到底签给谁 —— 解出 App 请求头里的 JWT payload，
 * 与 `/api/mm_web/token` 接口返回的 token 对比。
 *
 * 用法：node tools/edrawmind-token-diag.mjs <脑图URL>
 *
 * 为什么要做：`coop2exprot` 用它判「signature is invalid」→ 需要确认
 * 这枚 token 的 iss/aud/scope 是不是这个端点要的，而不是继续盲试入参。
 */
import { chromium } from 'playwright'

const url = process.argv.slice(2).find((a) => !a.startsWith('--'))
if (!url) {
  console.error('用法: node tools/edrawmind-token-diag.mjs <脑图URL>')
  process.exit(1)
}

const JWT_RE = /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}/g

/** 解 JWT 的 payload（不验签，只看内容） */
function payloadOf(jwt) {
  try {
    const p = jwt.split('.')[1]
    const b = Buffer.from(p.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8')
    return JSON.parse(b)
  } catch (e) {
    return { _error: e.message }
  }
}

const main = async () => {
  const appId = (url.match(/\/editor\/([A-Za-z0-9]+)/) || [])[1]
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' })
  const page = await ctx.newPage()

  // 收集 mindapi 请求的 Authorization（区分「有 JWT」和「只有 Bearer 占位」）
  const perReq = []
  page.on('request', (r) => {
    if (!r.url().includes('mindapi.edrawsoft.cn')) return
    const a = r.headers().authorization || ''
    perReq.push({
      path: r.url().replace('https://mindapi.edrawsoft.cn/api/mm_web', '').split('?')[0],
      auth: a,
      jwt: (a.match(JWT_RE) || [])[0] || null
    })
  })

  console.log('① 打开脑图…')
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(15000)

  console.log('\n② App 发出的 mindapi 请求及其 Authorization：')
  const seen = new Set()
  for (const r of perReq) {
    const k = `${r.path}|${(r.jwt || r.auth).slice(0, 20)}`
    if (seen.has(k)) continue
    seen.add(k)
    console.log(`   ${r.path}`)
    console.log(`     jwt: ${r.jwt ? r.jwt.slice(0, 30) + '…' : `(无 JWT，原始值="${r.auth}")`}`)
  }

  const appJwts = [...new Set(perReq.map((r) => r.jwt).filter(Boolean))]
  console.log(`\n③ App 用到的 JWT 共 ${appJwts.length} 枚：`)
  appJwts.forEach((j) => console.log('   payload =', JSON.stringify(payloadOf(j))))

  // ④ 与 /token 接口返回的对比
  const apiJwt = await page.evaluate(async (id) => {
    const r = await fetch(`https://mindapi.edrawsoft.cn/api/mm_web/token?file_key=${id}`, {
      headers: { Origin: 'https://mm.edrawsoft.cn', Referer: location.href }
    })
    const j = await r.json()
    return j?.data?.token || null
  }, appId)

  console.log('\n④ /api/mm_web/token 返回的 token：')
  if (!apiJwt) {
    console.log('   (未取到)')
  } else {
    console.log('   payload =', JSON.stringify(payloadOf(apiJwt)))
    const sameAsApp = appJwts.includes(apiJwt)
    console.log(`   是否与 App 实际使用的一致：${sameAsApp ? '是 ✓' : '**否** ← 这就是 signature invalid 的原因'}`)
  }

  await browser.close()
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(1)
})
