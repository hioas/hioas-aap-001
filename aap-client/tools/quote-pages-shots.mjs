#!/usr/bin/env node
/**
 * 报价相关页面的双端截图对照（小程序侧）
 * 用法：node tools/quote-pages-shots.mjs [mp|h5]
 */
import { createRequire } from 'node:module'
import { mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const require_ = createRequire(import.meta.url)
const here = dirname(fileURLToPath(import.meta.url))
const OUT = resolve(here, '../evidence/quote-compare')
mkdirSync(OUT, { recursive: true })

const QUOTE_PAGES = [
  'pages/quotes/index',
  'pages/quote-models/index',
  'pages/quote-form/index',
  'pages/quote-form/apikey',
  'pages/quote-form/success',
  'pages/quote-preview/index',
  'pages/model-pricing/index'
]

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const mode = process.argv[2] || 'mp'

if (mode === 'mp') {
  const automator = require_('miniprogram-automator')
  const mp = await automator.connect({ wsEndpoint: process.env.MP_AUTO_WS || 'ws://127.0.0.1:9420' })
  // 保证已登录态：拿真 token 写进小程序 storage（与登录页 afterLogin 行为一致）
  const API = process.env.AAP_API_BASE || 'http://127.0.0.1:8084/api/v1'
  const PHONE = process.env.AAP_E2E_PHONE || '13800138000'
  const send = await fetch(`${API}/auth/sms/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: PHONE, captcha: '1234' })
  }).then((r) => r.json())
  const code = send?.data?.dev_code
  const login = await fetch(`${API}/auth/sms/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: PHONE, smsCode: code })
  }).then((r) => r.json())
  if (login?.data?.token) {
    await mp.callWxMethod('setStorageSync', 'aap_token', login.data.token)
    await mp.callWxMethod('setStorageSync', 'aap_refresh_token', login.data.refresh_token || login.data.refreshToken || '')
  }
  for (const p of QUOTE_PAGES) {
    const page = await mp.reLaunch(`/${p}`)
    await page.waitFor(2200)
    await mp.screenshot({ path: resolve(OUT, `mp-${p.replace(/[/]/g, '_')}.png`) })
    console.log('mp  ', p)
  }
  await mp.disconnect()
} else {
  console.error('H5 侧请用 tools/h5-shots.mjs')
  process.exit(1)
}
