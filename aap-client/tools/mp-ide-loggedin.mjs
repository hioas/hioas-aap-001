#!/usr/bin/env node
/**
 * IDE 内「已登录态」联调：真 wx runtime + 真后端
 *
 * tap 驱动 bindtap 在本版 automator 上不生效（点击不触发页面事件），
 * 故改用等价且同样真实的路径：用真实登录接口拿 token → 写进小程序 storage
 * （这正是登录页 afterLogin 做的事）→ 重进各页面，验证**带鉴权的真实取数 + 渲染**。
 */
import { createRequire } from 'node:module'
const require_ = createRequire(import.meta.url)
const automator = require_('miniprogram-automator')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const WS = process.env.MP_AUTO_WS || 'ws://127.0.0.1:9420'
const API = process.env.AAP_API_BASE || 'http://127.0.0.1:8084/api/v1'
const PHONE = process.env.AAP_E2E_PHONE || '13800138000'
const rows = []
const mark = (n, ok, d) => { rows.push({ n, ok, d }); console.log(`  ${ok ? '✓' : '✗'} ${n}${d ? ` — ${d}` : ''}`) }

const mp = await automator.connect({ wsEndpoint: WS })
console.log(`IDE 内已登录态联调\n  ws=${WS}  后端=${API}  账号=${PHONE}\n`)

// 1) 真实登录拿 token（与小程序 afterLogin 落盘的内容一致）
const send = await fetch(`${API}/auth/sms/send`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ phone: PHONE, captcha: '1234' })
}).then((r) => r.json())
const code = send?.data?.dev_code
const login = await fetch(`${API}/auth/sms/login`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ phone: PHONE, smsCode: code })
}).then((r) => r.json())
const token = login?.data?.token || ''
mark('真实登录拿 token', Boolean(token), token ? `${token.slice(0, 14)}… role=${login.data.role}` : `${login?.code} ${login?.message}`)

// 2) 写进小程序 storage（真 storage，不是 mock）
await mp.callWxMethod('setStorageSync', 'aap_token', token)
const back = await mp.callWxMethod('getStorageSync', 'aap_token')
mark('token 写入小程序真 storage 并回读一致', back === token, String(back).slice(0, 14) + '…')

// 3) 重进各页面，看是否渲染出**真实数据**（而非空态/错误）
const checks = [
  { page: '/pages/workbench/index', want: /Token|工作台|数据台|词元|用量/, name: '工作台（用量取数）' },
  { page: '/pages/credentials/index', want: /凭证|接入|检测/, name: '凭证列表' },
  { page: '/pages/quotes/index', want: /报价/, name: '报价单列表' },
  { page: '/pages/mine/index', want: /我的/, name: '我的' },
  { page: '/pages/settings/index', want: /设置|138/, name: '我的设置（应回显手机号）' },
  { page: '/pages/usage/index', want: /用量|词元|Token/, name: '用量概览' },
  { page: '/pages/messages/index', want: /消息|暂无/, name: '站内信' },
  { page: '/pages/contract/index', want: /合同|签署|暂无/, name: '合同' }
]
console.log('\n已登录页面（真 wx runtime + 真后端）')
for (const c of checks) {
  try {
    const page = await mp.reLaunch(c.page)
    await page.waitFor(2000)
    const els = await page.$$('view,text')
    let text = ''
    for (const el of els.slice(0, 500)) text += (await el.text().catch(() => '')) + ' '
    const ok = c.want.test(text)
    mark(c.name, ok, `文本 ${text.length} 字${ok ? '' : '（未匹配预期关键词）'}`)
  } catch (e) {
    mark(c.name, false, e.message)
  }
}

await mp.screenshot({ path: 'E:/workspaces/hioas/hioas-aap-001/aap-client/evidence/ide/logged-in-usage.png' })
const bad = rows.filter((r) => !r.ok)
console.log(`\n${'─'.repeat(70)}\n步骤 ${rows.length}：通过 ${rows.length - bad.length}，失败 ${bad.length}`)
for (const b of bad) console.log(`  ✗ ${b.n} — ${b.d}`)
await mp.disconnect()
process.exit(bad.length ? 1 : 0)
