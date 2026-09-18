// 临时探针：读当前页面文本 + 再次点击提交并监听网络，定位「登录点了但没反应」
const PORT = 9333;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const page = list.find(t => t.type === 'page' && t.webSocketDebuggerUrl) || list[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));
  let id = 0; const pending = new Map(); const reqs = [];
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
    if (m.method === 'Network.requestWillBeSent') reqs.push(`${m.params.request.method} ${m.params.request.url}`);
  });
  const send = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); return new Promise(r => pending.set(i, r)); };
  const ev = async e => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.value;
  await send('Runtime.enable'); await send('Network.enable');
  console.log('=== 当前页面文本 ===');
  console.log((await ev('document.body.innerText')).split('\n').filter(Boolean).slice(0, 14).join('\n'));
  console.log('=== 当前 input 值（是否还在） ===');
  console.log(await ev('JSON.stringify([...document.querySelectorAll("input")].map(i=>i.value))'));
  console.log('=== 点击 .submit 并观察网络 ===');
  const box = await ev(`(() => { const el = document.querySelector('.submit'); const r = el.getBoundingClientRect(); return JSON.stringify({x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)}); })()`);
  const { x, y } = JSON.parse(box);
  for (const t of ['mousePressed','mouseReleased']) await send('Input.dispatchMouseEvent', { type: t, x, y, button: 'left', clickCount: 1 });
  await sleep(4000);
  console.log('   期间网络请求:'); reqs.slice(-8).forEach(r => console.log('     ' + r));
  console.log('=== 点击后页面文本 ===');
  console.log((await ev('document.body.innerText')).split('\n').filter(Boolean).slice(0, 14).join('\n'));
  ws.close();
})();
