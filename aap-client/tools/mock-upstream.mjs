#!/usr/bin/env node
/**
 * 本地 mock 上游（联调用）
 *
 * 用途：aap-server 的凭证预检（UpstreamProbe）会真实 GET `{base_url}/models` 并要求 2xx + `{data:[{id}]}`。
 *   联调时不该打真实厂商，故起一个本地 mock 上游，凭证 base_url 指向它。
 *   配合后端开关 `AAP_ALLOW_LOOPBACK=true`（app.credential.allow-loopback，见 OutboundUrlGuard 注释
 *   「仅用于本地端到端联调与测试」）——否则 127.0.0.1 会被 SSRF 防护按环回地址拒绝。
 *
 * 端点：
 *   GET  /v1/models                → 模型清单（预检用）
 *   POST /v1/chat/completions      → 假 completion（检测探针若打到这里也能拿到 2xx）
 *   GET  /__health                 → 存活探测
 *
 * 用法：node tools/mock-upstream.mjs [port]
 */
import { createServer } from 'node:http'

const PORT = Number(process.argv[2] || process.env.MOCK_UPSTREAM_PORT || 9911)

const MODELS = [
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'claude-3-opus',
  'claude-3-sonnet',
  'claude-3-haiku',
  'gemini-1.5-pro',
  'deepseek-chat',
  'qwen-max',
  'glm-4'
]

const started = Date.now()
let hits = 0

const server = createServer((req, res) => {
  hits++
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`)
  const auth = req.headers.authorization ? '有 Authorization 头' : '无 Authorization 头'
  console.log(`[${new Date().toISOString()}] ${req.method} ${url.pathname}  (${auth})`)

  const json = (code, body) => {
    const payload = JSON.stringify(body)
    res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(payload) })
    res.end(payload)
  }

  if (url.pathname === '/__health') {
    return json(200, { ok: true, uptimeMs: Date.now() - started, hits })
  }

  // 预检：GET {base_url}/models
  if (req.method === 'GET' && url.pathname.endsWith('/models')) {
    return json(200, {
      object: 'list',
      data: MODELS.map((id) => ({ id, object: 'model', created: 1700000000, owned_by: 'mock-upstream' }))
    })
  }

  // 检测探针可能打 completion
  if (req.method === 'POST' && /\/chat\/completions$/.test(url.pathname)) {
    let raw = ''
    req.on('data', (c) => (raw += c))
    req.on('end', () => {
      let model = 'gpt-4o'
      try {
        model = JSON.parse(raw || '{}').model || model
      } catch {
        /* 忽略：mock 不校验请求体 */
      }
      json(200, {
        id: 'chatcmpl-mock',
        object: 'chat.completion',
        created: Math.floor(Date.now() / 1000),
        model,
        choices: [{ index: 0, message: { role: 'assistant', content: 'pong' }, finish_reason: 'stop' }],
        usage: { prompt_tokens: 9, completion_tokens: 2, total_tokens: 11 }
      })
    })
    return
  }

  if (req.method === 'GET' && url.pathname === '/') {
    return json(200, { service: 'aap mock upstream', endpoints: ['/v1/models', '/v1/chat/completions', '/__health'] })
  }

  json(404, { error: { message: `mock upstream 未实现该端点: ${req.method} ${url.pathname}`, type: 'invalid_request_error' } })
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`mock 上游已启动：http://127.0.0.1:${PORT}`)
  console.log(`  预检用：GET http://127.0.0.1:${PORT}/v1/models`)
  console.log(`  凭证 base_url 请填：http://127.0.0.1:${PORT}/v1`)
})
