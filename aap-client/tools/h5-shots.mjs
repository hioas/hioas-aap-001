#!/usr/bin/env node
/**
 * H5 侧同宽截图（用于与小程序模拟器做同页对照）
 *
 * 走 dev server（5173，自带 /api → 8084 反代，取数与小程序的真实后端一致），
 * 视口固定 390x844（= 微信模拟器 iPhone 12/13 的逻辑分辨率），保证是同宽对比。
 *
 * 用法：node tools/h5-shots.mjs [page1,page2,...]
 * 产物：evidence/ide/h5-<page>.png
 */
import { spawn } from 'node:child_process'
import { mkdirSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const OUT = resolve(here, process.env.H5_OUT || '../evidence/ide')
mkdirSync(OUT, { recursive: true })

const PORT = process.env.H5_PORT || 5173
// ⚠️ 用 localhost 而不是 127.0.0.1：vite dev server 可能只监听 [::1]（IPv6），
//    写死 127.0.0.1 会 ERR_CONNECTION_REFUSED（本轮实测踩过）。
const HOST = process.env.H5_HOST || 'localhost'
const W = Number(process.env.H5_W || 390)
const H = Number(process.env.H5_H || 844)
const TOKEN = process.env.AAP_TOKEN || ''

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
if (!existsSync(CHROME)) {
  console.error(`找不到 Chrome：${CHROME}（用 CHROME_PATH 指定）`)
  process.exit(1)
}

const pages = (process.argv[2] || 'pages/login/index,pages/workbench/index')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// 用 CDP 起一个有头/无头 Chrome，设置视口后逐页导航并截图
const userDataDir = resolve(process.env.LOCALAPPDATA || '.', `Temp/h5-shot-${Date.now()}`)
const port = 9500 + Math.floor(Math.random() * 300)

const chrome = spawn(
  CHROME,
  [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--hide-scrollbars',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    `--window-size=${W},${H}`,
    'about:blank'
  ],
  { stdio: 'ignore' }
)

async function cdpTargets() {
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/list`)
      if (r.ok) return await r.json()
    } catch {
      /* 等 Chrome 起来 */
    }
    await sleep(500)
  }
  throw new Error('Chrome 调试端口未就绪')
}

const list = await cdpTargets()
const page = list.find((t) => t.type === 'page')
if (!page) throw new Error('没有可用的 page target')

const WebSocketImpl = globalThis.WebSocket
if (!WebSocketImpl) throw new Error('需要 Node 22+ 的全局 WebSocket')
const ws = new WebSocketImpl(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data)
  if (msg.id && pending.has(msg.id)) {
    const { resolve: res, reject } = pending.get(msg.id)
    pending.delete(msg.id)
    msg.error ? reject(new Error(JSON.stringify(msg.error))) : res(msg.result)
  }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params = {}) =>
  new Promise((res, rej) => {
    const mid = ++id
    pending.set(mid, { resolve: res, reject: rej })
    ws.send(JSON.stringify({ id: mid, method, params }))
  })

await send('Page.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: W,
  height: H,
  deviceScaleFactor: 2,
  mobile: true
})

// 先加载一次 app 并写入 token，然后**强制重载**让应用带 token 启动。
// ⚠️ 坑：直接 Page.navigate 到「同一个带 hash 的 URL」不会重载（只改 hash），
//    页面会停在无 token 那次请求 401 之后的空态，永远不会重新取数（本轮实测踩过）。
await send('Page.navigate', { url: `http://${HOST}:${PORT}/` })
await sleep(3000)
if (TOKEN) {
  await send('Runtime.evaluate', {
    expression: `localStorage.setItem('aap_token', ${JSON.stringify(TOKEN)})`
  })
  await send('Page.reload', { ignoreCache: false })
  await sleep(4000)
}

for (const p of pages) {
  const url = `http://${HOST}:${PORT}/#/${p}`
  await send('Page.navigate', { url })
  await sleep(1500)
  // dev 模式 H5 首屏 + 取数都慢，固定 sleep 会拍到「还没取到数据」的中间态（实测踩过：
  // 拍到空态「暂无报价单」）。改为**轮询直到可见文本稳定**（连续两次相同且非空）。
  const textLen = async () => {
    const r = await send('Runtime.evaluate', {
      expression: `(document.body.innerText||'').length`,
      returnByValue: true
    })
    return r.result.value
  }
  let prev = -1
  let stable = 0
  for (let i = 0; i < 50; i++) {
    await sleep(500)
    const cur = await textLen()
    if (cur > 20 && cur === prev) {
      stable++
      if (stable >= 2) break
    } else {
      stable = 0
    }
    prev = cur
  }
  const len = await textLen()
  const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
  const file = resolve(OUT, `h5-${p.replace(/[/]/g, '_')}.png`)
  const { writeFileSync } = await import('node:fs')
  writeFileSync(file, Buffer.from(data, 'base64'))
  console.log(`saved ${file}  (${W}x${H}, 可见文本 ${len} 字${len < 20 ? ' ⚠️ 疑似未渲染' : ''})`)
}

ws.close()
chrome.kill()
