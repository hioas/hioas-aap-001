#!/usr/bin/env node
/**
 * CDP DOM 侦察（调试用，`.claude/skills/dev` 附录 E 的排错辅助）
 * 用法：node tools/cdp-dump.mjs [port] [url] [--no-nav]
 */
const PORT = Number(process.argv[2] || 9333);
const URL_ = process.argv[3] || 'http://localhost:5173';
const NAV = !process.argv.includes('--no-nav');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const page = list.find((t) => t.type === 'page' && t.webSocketDebuggerUrl) || list[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res) => ws.addEventListener('open', res));
  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
  });
  const send = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); return new Promise((r) => pending.set(i, r)); };
  const ev = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.value;

  await send('Page.enable');
  await send('Runtime.enable');
  if (NAV) { await send('Page.navigate', { url: URL_ }); await sleep(6000); }

  console.log('URL:', await ev('location.href'));
  console.log('=== 可点击按钮（class 含 btn/submit/tab/nav/agreement） ===');
  console.log(await ev(`(() => {
    const out = [];
    for (const el of document.querySelectorAll('uni-view,uni-button,uni-text')) {
      const cls = (el.className || '').toString();
      if (!/btn|button|submit|tab|nav|agreement|link/i.test(cls)) continue;
      const t = (el.innerText || '').trim().slice(0, 20);
      const r = el.getBoundingClientRect();
      if (r.width < 40 || r.height < 20) continue;
      out.push({ cls: cls.slice(0, 34), cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2), text: t });
    }
    return JSON.stringify(out.slice(0, 20), null, 1);
  })()`));
  console.log('=== 4 位大写码（图形验证码） ===');
  console.log(await ev(`JSON.stringify([...document.querySelectorAll('*')].filter(e => /^[A-Z0-9]{4}$/.test((e.innerText || '').trim()) && e.children.length === 0).map(e => ({ cls: (e.className||'').toString().slice(0,25), text: e.innerText.trim() })))`));
  console.log('=== input 位置 ===');
  console.log(await ev(`JSON.stringify([...document.querySelectorAll('input')].map(i => ({ ph: i.placeholder, cx: Math.round(i.getBoundingClientRect().x + 20), cy: Math.round(i.getBoundingClientRect().y + 10) })))`));
  ws.close();
})().catch((e) => { console.error('dump 失败:', e.message); process.exit(1); });
