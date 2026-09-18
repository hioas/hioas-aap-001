#!/usr/bin/env node
/**
 * 登录链路探针：完整走一遍登录表单，打印 toast 文本 + 三个输入框的真实值 + 网络请求，
 * 用来定位「点了提交但没发请求」到底卡在哪一个前端守卫（`.agents/skills/dev` 排错用）。
 * 用法：node tools/cdp-login-probe.mjs <phone> [port]
 */
const phone = process.argv[2] || '13809180001';
const PORT = Number(process.argv[3] || 9333);
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PROFILE = `${process.env.LOCALAPPDATA}\\Temp\\aap-cdp-probe-profile`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const { spawn } = await import('node:child_process');
  const alive = await fetch(`http://127.0.0.1:${PORT}/json/version`).then((r) => r.ok).catch(() => false);
  if (!alive) {
    spawn(CHROME, [`--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, '--no-first-run',
      '--window-size=1440,900', 'http://localhost:5173'], { detached: true, stdio: 'ignore' }).unref();
    await sleep(4000);
  }
  let wsUrl = null;
  for (let i = 0; i < 30 && !wsUrl; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      wsUrl = list.find((t) => t.type === 'page' && t.webSocketDebuggerUrl)?.webSocketDebuggerUrl;
    } catch { /* 未就绪 */ }
    if (!wsUrl) await sleep(500);
  }
  const ws = new WebSocket(wsUrl);
  await new Promise((r) => ws.addEventListener('open', r));
  let id = 0; const pending = new Map(); const reqs = [];
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
    if (m.method === 'Network.requestWillBeSent') reqs.push(`${m.params.request.method} ${m.params.request.url.replace('http://localhost:5173', '')}`);
  });
  const send = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); return new Promise((r) => pending.set(i, r)); };
  const ev = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.value;
  await send('Runtime.enable'); await send('Network.enable'); await send('Page.enable');

  // 用带 detail 的 CustomEvent 填值（上轮已验证这种写法能让框架收到）
  const fill = async (idx, text) => {
    const box = JSON.parse(await ev(`(() => { const i = document.querySelectorAll('input')[${idx}]; if (!i) return 'null'; const r = i.getBoundingClientRect(); return JSON.stringify({x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)}); })()`) || 'null');
    if (!box) return 'input-missing';
    for (const t of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type: t, x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await sleep(150);
    return ev(`(() => {
      const el = document.querySelectorAll('input')[${idx}];
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      el.focus(); setter.call(el, ${JSON.stringify(text)});
      const f = (t) => el.dispatchEvent(new CustomEvent(t, { bubbles: true, cancelable: true, detail: { value: ${JSON.stringify(text)} } }));
      f('input'); f('change'); f('blur');
      return el.value;
    })()`);
  };
  const click = async (sel) => {
    const box = JSON.parse(await ev(`(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return 'null'; const r = el.getBoundingClientRect(); return JSON.stringify({x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)}); })()`) || 'null');
    if (!box) return false;
    for (const t of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type: t, x: box.x, y: box.y, button: 'left', clickCount: 1 });
    return true;
  };
  const toast = () => ev(`(() => { const t = [...document.querySelectorAll('*')].filter(e => (e.innerText||'').trim() && (e.className||'').toString().match(/toast|uni-toast/i)); return t.map(e => e.innerText.trim()).join(' | ') || '(无 toast)'; })()`);

  await send('Page.navigate', { url: 'http://localhost:5173' }); await sleep(6000);
  const captcha = await ev(`(() => { const el = [...document.querySelectorAll('*')].find(e => /^[A-Z0-9]{4}$/.test((e.innerText||'').trim()) && e.children.length === 0); return el ? el.innerText.trim() : null; })()`);
  console.log('图形验证码(页面):', captcha);
  console.log('填手机号 ->', await fill(0, phone));
  console.log('填图形码 ->', await fill(1, captcha));
  await click('.sms-btn'); await sleep(3000);
  console.log('toast:', await toast());
  const code = String(Math.floor(100000 + Math.random() * 900000)); // 探针不依赖 dev_code，直接构造 6 位
  console.log('填短信码(构造) ->', await fill(2, code));
  console.log('三个输入框的值:', await ev(`JSON.stringify([...document.querySelectorAll('input')].map(i => i.value))`));
  // 同意协议：uni-app H5 的 @tap 对纯鼠标事件不可靠 → 依次尝试 鼠标 → 触摸 → JS click，并校验勾选结果
  const agreedSel = `(() => { const t = document.querySelector('.agree__tick'); return t ? 'checked' : 'unchecked'; })()`;
  console.log('勾选前:', await ev(agreedSel));
  await click('.agree__box'); await sleep(300);
  console.log('  鼠标点击后:', await ev(agreedSel));
  if ((await ev(agreedSel)) === 'unchecked') {
    const box = JSON.parse(await ev(`(() => { const el = document.querySelector('.agree__box'); const r = el.getBoundingClientRect(); return JSON.stringify({x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)}); })()`));
    await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: box.x, y: box.y }] });
    await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await sleep(300);
    console.log('  触摸事件后:', await ev(agreedSel));
  }
  if ((await ev(agreedSel)) === 'unchecked') {
    await ev(`(() => { const el = document.querySelector('.agree__box'); el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); return true; })()`);
    await sleep(300);
    console.log('  JS click 后:', await ev(agreedSel));
  }
  reqs.length = 0;
  const clicked = await click('.submit');
  console.log('点击提交:', clicked);
  await sleep(4000);
  console.log('提交后 toast:', await toast());
  console.log('提交后请求:', reqs.length ? reqs.join(' , ') : '(无请求 ✗ ← 被前端守卫拦住)');
  console.log('URL:', await ev('location.href'));
  ws.close();
  process.exit(0);
})().catch((e) => { console.error('探针失败:', e.message); process.exit(1); });
