#!/usr/bin/env node
/**
 * IDEA MCP 单次调用器（配合 idea-mcp-bridge.mjs 的 SSE 逻辑，但一次性执行后退出）
 *
 * 用法：
 *   node scripts/idea-mcp-call.mjs tools/list
 *   node scripts/idea-mcp-call.mjs execute_run_configuration '{"configurationName":"dev"}'
 *   node scripts/idea-mcp-call.mjs <tool> '<json>' [超时秒数]
 *
 * 说明：IDE 必须在 IDEA 里已启用 MCP Server（Settings | Tools | MCP Server），默认端口 64342。
 */

const BASE = process.env.IDE_URL || `http://${process.env.HOST || '127.0.0.1'}:${process.env.IDE_PORT || '64342'}`;
const tool = process.argv[2];
const argsRaw = process.argv[3] || '{}';
const timeoutS = Number(process.argv[4] || 120);

if (!tool) { console.error('用法: node idea-mcp-call.mjs <tool|tools/list> [json-args] [timeoutS]'); process.exit(2); }

const deadline = Date.now() + timeoutS * 1000;
const pending = new Map();
let postUrl = null;
const queue = [];

function send(msg) {
  return fetch(postUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(msg) })
    .catch((e) => { throw new Error(`POST 失败: ${e.message}`); });
}
const call = (method, params) => new Promise((resolve) => {
  const id = Math.floor(Math.random() * 1e9);
  pending.set(id, resolve);
  const msg = { jsonrpc: '2.0', id, method, ...(params ? { params } : {}) };
  postUrl ? send(msg) : queue.push(msg);
});

async function main() {
  const res = await fetch(`${BASE}/sse`, { headers: { Accept: 'text/event-stream' } });
  if (!res.ok) throw new Error(`SSE 连接失败 HTTP ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  (async () => {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true }).replace(/\r\n/g, '\n');
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const raw = buf.slice(0, i); buf = buf.slice(i + 2);
        let event = '', data = '';
        for (const line of raw.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim();
          else if (line.startsWith('data:')) data += line.slice(5).trim();
        }
        if (event === 'endpoint') { postUrl = data.startsWith('http') ? data : BASE + data; queue.splice(0).forEach(send); }
        else if (data) { try { const m = JSON.parse(data); if (m.id !== undefined && pending.has(m.id)) { const f = pending.get(m.id); pending.delete(m.id); f(m); } } catch { /* 忽略 */ } }
      }
    }
  })().catch(() => {});

  const init = await call('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'hermes-idea-call', version: '1.0' } });
  if (init.error) throw new Error('initialize 失败: ' + JSON.stringify(init.error));
  await send({ jsonrpc: '2.0', method: 'notifications/initialized' });

  if (tool === 'tools/list' || tool === 'tools.list') {
    const r = await call('tools/list');
    const names = (r.result?.tools || []).map((t) => t.name);
    console.log(JSON.stringify({ count: names.length, tools: names }, null, 2));
  } else {
    const args = JSON.parse(argsRaw);
    const r = await call('tools/call', { name: tool, arguments: args });
    console.log(JSON.stringify(r.result ?? r, null, 2));
  }
  process.exit(0);
}

setTimeout(() => { console.error(`超时 ${timeoutS}s`); process.exit(124); }, Math.max(0, deadline - Date.now()));
main().catch((e) => { console.error('ERROR: ' + e.message); process.exit(1); });
