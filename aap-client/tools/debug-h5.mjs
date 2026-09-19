#!/usr/bin/env node
/** 诊断 H5 页面为何空白：抓 console/异常 + DOM 文本长度 + 最终 URL */
import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const HOST = process.env.H5_HOST || 'localhost'
const PORT = process.env.H5_PORT || 5173
const TARGET = process.argv[2] || 'pages/quotes/index'
const TOKEN = process.env.AAP_TOKEN || ''
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const dbgPort = 9700 + Math.floor(Math.random() * 200)
const userDataDir = resolve(process.env.LOCALAPPDATA || '.', `Temp/h5-dbg-${Date.now()}`)
const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--no-sandbox',
  `--remote-debugging-port=${dbgPort}`, `--user-data-dir=${userDataDir}`,
  '--window-size=390,844', 'about:blank'
], { stdio: 'ignore' })

async function targets() {
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(`http://127.0.0.1:${dbgPort}/json/list`); if (r.ok) return await r.json() } catch {}
    await sleep(500)
  }
  throw new Error('CDP 未就绪')
}
const list = await targets()
const t = list.find((x) => x.type === 'page')
const ws = new WebSocket(t.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const logs = []
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (m.method === 'Runtime.consoleAPICalled') logs.push(`[console.${m.params.type}] ` + (m.params.args || []).map(a => a.value ?? a.description ?? '').join(' ').slice(0, 200))
  if (m.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + JSON.stringify(m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails).slice(0, 300))
  if (m.method === 'Network.requestWillBeSent' && /\/api\//.test(m.params.request.url)) {
    logs.push(`[net→] ${m.params.request.method} ${m.params.request.url}  auth=${m.params.request.headers.Authorization ? '有' : '无'}`)
  }
  if (m.method === 'Network.responseReceived' && /\/api\//.test(m.params.response.url)) {
    logs.push(`[net←] ${m.params.response.status} ${m.params.response.url}`)
  }
  if (m.method === 'Network.loadingFailed') logs.push(`[net✗] ${m.params.errorText} ${m.params.requestId}`)
  if (m.id && pending.has(m.id)) { const { resolve: res, reject } = pending.get(m.id); pending.delete(m.id); m.error ? reject(new Error(JSON.stringify(m.error))) : res(m.result) }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params = {}) => new Promise((res, rej) => { const mid = ++id; pending.set(mid, { resolve: res, reject: rej }); ws.send(JSON.stringify({ id: mid, method, params })) })

await send('Page.enable')
await send('Runtime.enable')
await send('Network.enable')
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })

await send('Page.navigate', { url: `http://${HOST}:${PORT}/` })
await sleep(2500)
if (TOKEN) {
  await send('Runtime.evaluate', { expression: `localStorage.setItem('aap_token', ${JSON.stringify(TOKEN)})` })
}
await send('Page.navigate', { url: `http://${HOST}:${PORT}/#/${TARGET}` })
await sleep(8000)

const r = await send('Runtime.evaluate', {
  expression: `JSON.stringify({url: location.href, title: document.title, bodyLen: (document.body.innerText||'').length, htmlLen: document.body.innerHTML.length, head: (document.body.innerText||'').slice(0,200), appEl: !!document.querySelector('#app'), appChildren: document.querySelector('#app')?.children.length ?? -1})`,
  returnByValue: true
})
console.log('DOM 状态:', r.result.value)
console.log('\n控制台/异常:')
for (const l of logs.slice(-25)) console.log('  ' + l)

ws.close(); chrome.kill()
