#!/usr/bin/env node
/**
 * 在**已登录**的持久化 profile 下，抓万兴脑图「导出」的真实请求。
 *
 * 目的：`coop2exprot` 需要 Authorization: Bearer <JWT>。
 *   已排除的候选（实测）：
 *     · /api/mm_web/token?file_key=  → user_id=0 的访客票 → `signature is invalid`
 *     · storage 的 qdwpa_saas_d2_*   → 非 JWT → `invalid number of segments`
 *   所以必须看 App 自己导出时发的是什么。本脚本记录**所有** mindapi 请求的
 *   Authorization 头（含 JWT 形态判定），并尝试点击「导出」菜单。
 *
 * 用法：node tools/edrawmind-probe-export.mjs <脑图URL> [--headed]
 */
import path from 'node:path'
import os from 'node:os'
import { chromium } from 'playwright'

const args = process.argv.slice(2)
const url = args.find((a) => !a.startsWith('--'))
const headed = args.includes('--headed')
if (!url) {
  console.error('用法: node tools/edrawmind-probe-export.mjs <脑图URL> [--headed]')
  process.exit(1)
}

const PROFILE_DIR = path.join(os.homedir(), '.edrawmind-profile')
const JWT_RE = /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}/

const main = async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE_DIR, {
    channel: 'chrome',
    headless: !headed,
    viewport: { width: 1600, height: 900 },
    locale: 'zh-CN'
  })
  const page = ctx.pages()[0] || (await ctx.newPage())

  const reqs = []
  page.on('request', (r) => {
    if (!r.url().includes('mindapi.edrawsoft.cn')) return
    reqs.push({
      m: r.method(),
      p: r.url().replace('https://mindapi.edrawsoft.cn/api/mm_web', '').split('?')[0],
      auth: r.headers().authorization || '',
      ct: r.headers()['content-type'] || '',
      body: r.postData() || ''
    })
  })

  console.log('① 打开脑图（已登录 profile）…')
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(15000)

  console.log('\n② App 发出的 mindapi 请求：')
  const seen = new Set()
  for (const r of reqs) {
    const k = `${r.m}${r.p}|${r.auth.slice(0, 12)}`
    if (seen.has(k)) continue
    seen.add(k)
    const isJwt = JWT_RE.test(r.auth)
    console.log(`   ${r.m} ${r.p}`)
    console.log(`     Authorization: ${r.auth ? r.auth.slice(0, 40) + '…' : '(无)'}${isJwt ? '  ★ 内含 JWT' : ''}`)
    if (isJwt) {
      const j = r.auth.match(JWT_RE)[0]
      try {
        const pl = JSON.parse(Buffer.from(j.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'),'base64').toString('utf8'))
        console.log(`     ★★ JWT payload = ${JSON.stringify(pl)}`)
      } catch {}
      console.log(`     ★★ 完整 Authorization（可直接用于 --token）：`)
      console.log(r.auth)
    }
    if (r.body) console.log(`     body: ${r.body.slice(0, 160)}`)
  }

  // ③ 尝试驱动「导出」：先找主菜单触发器（导出项本体是 hidden）
  console.log('\n③ 尝试打开主菜单并点「导出」…')
  const menuTrig = await page.evaluate(() => {
    const cands = []
    document.querySelectorAll('[class*=mainmenu], [class*=menu-trigger], [class*=editor-menu], button').forEach((el) => {
      const r = el.getBoundingClientRect()
      if (r.width > 10 && r.height > 10 && r.y < 90) cands.push({ cls: String(el.className).slice(0, 50), x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) })
    })
    return cands.slice(0, 12)
  })
  menuTrig.forEach((m) => console.log(`   <${m.cls}> @(${m.x},${m.y})`))

  // 直接把「导出」祖先链的可点元素 clicking（不依赖可见性，用 JS 派发）
  const did = await page.evaluate(() => {
    const sp = [...document.querySelectorAll('[title="导出"]')][0]
    if (!sp) return 'no-导出-span'
    let el = sp
    for (let i = 0; i < 6 && el; i++) {
      if (el.tagName === 'LI' || el.getAttribute?.('role') === 'menuitem') {
        el.dispatchEvent(new MouseEvent('click', { bubbles: true }))
        el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }))
        return `clicked <${el.tagName}> .${String(el.className).slice(0, 40)}`
      }
      el = el.parentElement
    }
    return 'no-clickable-ancestor'
  })
  console.log(`   ${did}`)
  await page.waitForTimeout(3000)

  const after = await page.evaluate(() => {
    const out = []
    document.querySelectorAll('*').forEach((el) => {
      const t = (el.textContent || '').trim()
      const r = el.getBoundingClientRect()
      if (!el.children.length && t && t.length < 20 && r.width > 0 && r.height > 0 && /Markdown|XMind|PDF|Word|大纲|文本/i.test(t)) {
        out.push(`${t} @(${Math.round(r.x + r.width / 2)},${Math.round(r.y + r.height / 2)})`)
      }
    })
    return [...new Set(out)].slice(0, 15)
  })
  console.log('   可见的导出格式项：', after.length ? after.join(' | ') : '(无)')

  console.log('\n④ 新增的 mindapi 请求：')
  const before = seen
  const seen2 = new Set()
  for (const r of reqs) {
    const k = `${r.m}${r.p}|${r.auth.slice(0, 12)}`
    if (seen2.has(k)) continue
    seen2.add(k)
    if (before.has(k)) continue
    console.log(`   ★ ${r.m} ${r.p}  auth=${r.auth.slice(0, 30)}…  body=${r.body.slice(0, 200)}`)
  }

  if (headed) await page.waitForTimeout(60000)
  await ctx.close()
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(1)
})
