#!/usr/bin/env node
/**
 * 登录态下取 token：带会话 Cookie 调 `/api/mm_web/token`，看它签出的 payload。
 *
 * 假设：匿名时该接口签出 user_id=0 的访客票（导出接口不认）；
 *       带登录 Cookie 后应签出**带真实 user_id** 的 token。
 *
 * 用法：node tools/edrawmind-get-token.mjs <脑图URL>
 */
import path from 'node:path'
import os from 'node:os'
import { chromium } from 'playwright'

const url = process.argv.slice(2).find((a) => !a.startsWith('--'))
if (!url) {
  console.error('用法: node tools/edrawmind-get-token.mjs <脑图URL>')
  process.exit(1)
}
const PROFILE_DIR = path.join(os.homedir(), '.edrawmind-profile')
const appId = (url.match(/\/editor\/([A-Za-z0-9]+)/) || [])[1]

function payloadOf(jwt) {
  try {
    return JSON.parse(
      Buffer.from(jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8')
    )
  } catch {
    return { _err: 'unparsable' }
  }
}

const main = async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE_DIR, {
    channel: 'chrome',
    headless: true,
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN'
  })
  const page = ctx.pages()[0] || (await ctx.newPage())
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(9000)

  // 带 Cookie 调 token 接口（页面内 fetch → credentials 自动带上）
  const res = await page.evaluate(async (id) => {
    const r = await fetch(`https://mindapi.edrawsoft.cn/api/mm_web/token?file_key=${id}`, {
      credentials: 'include'
    })
    return { status: r.status, body: await r.text() }
  }, appId)

  console.log(`token 接口 http=${res.status}`)
  let token = null
  try {
    const j = JSON.parse(res.body)
    token = j?.data?.token || null
    if (!token) console.log('  响应（无 token 字段）：', res.body.slice(0, 300))
  } catch {
    console.log('  响应非 JSON：', res.body.slice(0, 200))
  }

  if (token) {
    const pl = payloadOf(token)
    console.log(`  token 长度 ${token.length}`)
    console.log(`  payload = ${JSON.stringify(pl)}`)
    const uid = String(pl.user_id ?? '0')
    console.log(`  user_id = ${uid} → ${uid === '0' ? '**仍是访客票**' : '✅ 登录用户票！可用于导出'}`)
    if (uid !== '0') {
      console.log('\n[可复制用于 --token]')
      console.log(token)
    }
  }

  // 顺带看看登录后 localStorage 里有没有非 JWT 形态的凭据
  const st = await page.evaluate(() => {
    const o = {}
    try {
      for (const s of [localStorage, sessionStorage]) {
        for (let i = 0; i < s.length; i++) o[s.key(i)] = String(s.getItem(s.key(i)) || '').slice(0, 80)
      }
    } catch {
      /* 同源限制 */
    }
    return o
  })
  console.log('\nstorage 键（截断 80 字符）：')
  Object.entries(st).forEach(([k, v]) => console.log(`  ${k} = ${v}`))

  await ctx.close()
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(1)
})
