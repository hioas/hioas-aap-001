#!/usr/bin/env node
/**
 * 有头浏览器验收驱动（CDP，零依赖；`.claude/skills/dev` 附录 E 优先级 3）
 *
 * 用途：按 SOP §3 步骤 6 做「页面能开、能点、能登录」的可视化验收并留证：
 *   - 每步截图 → <outDir>/<时间戳>-<step>.png
 *   - 浏览器控制台错误 / 失败请求（4xx/5xx）→ 输出；任一异常即判定未通过（退出码 1）
 *
 * 实现要点（踩过的坑）：
 *   1. uni-app H5 的点击绑定在 `<uni-view>` 上，靠 `innerText` 找文本节点点不动 →
 *      统一用 **Input.dispatchMouseEvent 真实鼠标事件**点击 DOM 元素中心。
 *   2. 输入框用 **Input.insertText**（先点聚焦），比 JS 直接改 value 更接近真人，能触发框架的 input 事件。
 *   3. 图形验证码由页面自己生成并显示，必须**读页面上的码**再填，不能硬编码。
 *   4. 用独立 user-data-dir 起 Chrome，不动用户正在用的浏览器与登录态。
 *
 * 用法：node tools/cdp-acceptance.mjs <baseUrl> <outDir> <phone> [port]
 */

import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const [baseUrl = 'http://localhost:5173', outDir = 'logs/screenshots', phone = '13800000066', portArg] = process.argv.slice(2);
// 端口策略：默认按进程随机（9400-9899），**不用固定端口**——本机其他项目（如 hioas-aim 的 aim-tdd）
// 固定占用 9223 跑自己的 CDP 套件，固定端口很容易撞车并互相打断。
const PORT = Number(portArg || process.env.AAP_CDP_PORT || (9400 + (process.pid % 500)));
const PROFILE_NAME = 'aap-cdp-profile';
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PROFILE = join(tmpdir(), PROFILE_NAME + '-' + process.pid);
mkdirSync(outDir, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const stamp = () => new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15);

function launchChrome() {
  const child = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    '--no-first-run', '--no-default-browser-check', '--enable-automation', '--window-size=1440,900', '--window-position=40,40', baseUrl,
  ], { detached: true, stdio: 'ignore' });
  child.unref();
}

async function portAlive() {
  try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); return r.ok; } catch { return false; }
}

async function targetWs() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* 未就绪 */ }
    await sleep(500);
  }
  throw new Error('CDP 未就绪');
}

class Cdp {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    this.consoleErrors = []; this.failedRequests = []; this.devCode = null;
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
        return;
      }
      if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
        this.consoleErrors.push(`${m.params.type}: ${(m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 160)}`);
      }
      if (m.method === 'Runtime.exceptionThrown') {
        this.consoleErrors.push(`exception: ${m.params.exceptionDetails?.exception?.description ?? m.params.exceptionDetails?.text}`);
      }
      if (m.method === 'Network.responseReceived' && m.params.response.status >= 400 && !m.params.response.url.includes('favicon')) {
        this.failedRequests.push(`${m.params.response.status} ${m.params.type} ${m.params.response.url}`);
      }
      if (m.method === 'Network.responseReceived' && m.params.response.url.includes('/auth/sms/send')) {
        this.smsRequestId = m.params.requestId;
      }
      if (m.method === 'Network.loadingFinished' && this.smsRequestId && m.params.requestId === this.smsRequestId) {
        this.send('Network.getResponseBody', { requestId: this.smsRequestId }).then((r) => {
          try { this.devCode = JSON.parse(r.body)?.data?.dev_code ?? null; } catch { /* 忽略 */ }
        }).catch(() => {});
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id; this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  async eval(expression) {
    const r = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
    return r.result?.value;
  }
  /** 真实鼠标左键点击（元素中心）：先滚入视口再取坐标，避免点到视口外落空 */
  async clickSelector(selector) {
    await this.eval(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (el) el.scrollIntoView({ block: 'center', inline: 'center' });
      return true;
    })()`);
    await sleep(300);
    const box = await this.eval(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el) return null;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) return null;
      const x = Math.round(r.x + r.width / 2);
      const y = Math.round(r.y + r.height / 2);
      const inView = x >= 0 && y >= 0 && x <= innerWidth && y <= innerHeight;
      return { x, y, inView };
    })()`);
    if (!box) return false;
    if (!box.inView) console.log(`   [警告] ${selector} 的中心仍在视口外 (${box.x},${box.y})，点击可能落空`);
    for (const type of ['mousePressed', 'mouseReleased']) {
      await this.send('Input.dispatchMouseEvent', { type, x: box.x, y: box.y, button: 'left', clickCount: 1 });
    }
    return true;
  }
  async typeInto(selector, text) {
    await this.clickSelector(selector);
    await sleep(200);
    await this.send('Input.insertText', { text });
    await sleep(200);
  }
  async text() { return this.eval('document.body ? document.body.innerText : ""'); }
  async shot(step) {
    const r = await this.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    const file = join(outDir, `${stamp()}-${step}.png`);
    writeFileSync(file, Buffer.from(r.data, 'base64'));
    console.log(`  [截图] ${file}`);
    return file;
  }
}

async function main() {
  if (!existsSync(CHROME)) throw new Error(`未找到 Chrome：${CHROME}`);
  // 已有调试实例就直接复用（同 user-data-dir 二次启动只会把 URL 交给旧实例，导致连到旧 target 卡死）
  if (await portAlive()) {
    console.error(`端口 ${PORT} 已有调试实例在监听：**拒绝复用**（可能是其他项目正在用的浏览器，`
      + `本机 aim-tdd 固定使用 9223 + aim-cdp-profile）。请用 AAP_CDP_PORT=<空闲端口> 重跑。`);
    process.exit(4);
  }
  console.log(`启动独立 Chrome（有头，独立 user-data-dir，端口 ${PORT}）→ ${baseUrl}`);
  launchChrome();
  // === 安全边界（2026-09-18 事故后加） ===
  // 绝不按镜像名杀进程、绝不关别人的浏览器：只有确认该调试实例的 user-data-dir 是本脚本自己的 profile，
  // 才允许对它做 Browser.close。归属不明 → 直接放弃，宁可不清理也不误伤别的项目（本机 aim 用 9223）。
  // 路径分隔符用 fromCharCode 构造，源码里不出现裸反斜杠（避免转义地狱）
  // 路径分隔符用 fromCharCode 构造，源码里不出现裸反斜杠（避免转义地狱）
  const BS = String.fromCharCode(92);
  const ownProfileWin = join(tmpdir(), PROFILE_NAME).toLowerCase();
  const ownProfilePosix = ownProfileWin.split(BS).join('/');

  async function assertOwnBrowserOrRefuse() {
    try {
      const info = await cdp.send('Browser.getBrowserCommandLine');
      const args = (info.arguments || []).join(' ').toLowerCase();
      if (!args.includes(ownProfilePosix) && !args.includes(ownProfileWin)) {
        console.error('拒绝操作：该调试实例不属于本脚本（profile 不匹配），可能是其他项目的工作浏览器');
        return false;
      }
      return true;
    } catch {
      return false;
    }
  }

  // 看门狗：任何一步卡住都不让脚本无限等待（SOP：证据要能收敛）
  const watchdog = setTimeout(() => { console.error('看门狗超时：验收未在 150s 内完成'); process.exit(3); }, 150000);
  watchdog.unref?.();
  const ws = new WebSocket(await targetWs());
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  const cdp = new Cdp(ws);
  for (const d of ['Page', 'Runtime', 'Network']) await cdp.send(`${d}.enable`);
  await cdp.send('Page.navigate', { url: baseUrl });
  await sleep(6000);

  console.log(`① 入口页 title="${await cdp.eval('document.title')}"  截图留证`);
  await cdp.shot('01-login');

  // ② 手机号 + 页面生成的图形验证码
  const captcha = await cdp.eval(`(() => {
    const el = [...document.querySelectorAll('*')].find(e => /^[A-Z0-9]{4}$/.test((e.innerText||'').trim()) && e.children.length === 0);
    return el ? el.innerText.trim() : null;
  })()`);
  console.log(`② 图形验证码（读页面）: ${captcha}`);
  const inputs = ['uni-input[class*=field__input] input', 'input'];
  const firstInput = await cdp.eval('document.querySelectorAll("input").length');
  console.log(`   表单 input 数量: ${firstInput}`);
  // 依次聚焦第 1、2 个 input 并键入（real events）
  /**
   * 填值：先真实点击聚焦，再用**原生 setter + input/change/blur 事件**写入。
   * 坑：uni-app H5 下 `Input.insertText` 不会更新框架内部状态（值看着进不去、提交被客户端校验挡住），
   * 原生 setter + 事件才能让 v-model 生效。
   */
  const typeAt = async (idx, text) => {
    const box = await cdp.eval(`(() => { const i = document.querySelectorAll('input')[${idx}]; if (!i) return null; const r = i.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()`);
    if (!box) return false;
    for (const t of ['mousePressed', 'mouseReleased']) await cdp.send('Input.dispatchMouseEvent', { type: t, x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await sleep(150);
    const ok = await cdp.eval(`(() => {
      const el = document.querySelectorAll('input')[${idx}];
      if (!el) return false;
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      el.focus();
      setter.call(el, ${JSON.stringify(text)});
      // 关键：uni-app H5 的 v-model 从 e.detail.value 取值，普通 Event 没有 detail → 框架内部状态仍是空
      const fire = (type) => el.dispatchEvent(new CustomEvent(type, {
        bubbles: true, cancelable: true, detail: { value: ${JSON.stringify(text)} },
      }));
      fire('input'); fire('change'); fire('blur');
      return el.value === ${JSON.stringify(text)};
    })()`);
    await sleep(300);
    return ok;
  };
  console.log('   手机号:', await typeAt(0, phone) ? '已填写' : '失败');
  console.log('   图形验证码:', captcha && await typeAt(1, captcha) ? '已填写' : '失败');
  await cdp.shot('02-filled');

  // ③ 真实点击「获取验证码」→ 从网络响应取 dev_code（联调开关开启时后端会回显）
  const clickedSend = await cdp.clickSelector('.sms-btn');
  console.log(`③ 点击「获取验证码」: ${clickedSend ? '已点击' : '未找到 .sms-btn'}`);
  await sleep(3000);
  console.log(`   后端回显 dev_code: ${cdp.devCode ? '已从网络响应捕获' : '未捕获（联调开关未开？）'}`);
  await cdp.shot('03-code-sent');

  // ④ 短信验证码 + 登录/注册
  if (cdp.devCode) {
    console.log('   短信验证码:', await typeAt(2, cdp.devCode) ? '已填写' : '失败');
  }
  // 坑（两个）：① 登录前必须勾选「我已阅读并同意《服务协议》」，否则提交被静默拦住、不发请求；
  //            ② uni-app H5 的 @tap **不吃** CDP 合成鼠标/触摸事件（实测鼠标、touchStart/End 均无效），
  //               必须用 JS 派发 MouseEvent('click')，并以出现勾选标记（.agree__tick）为准。
  const tickState = "(() => (document.querySelector('.agree__tick') ? 'checked' : 'unchecked'))()";
  if ((await cdp.eval(tickState)) !== 'checked') {
    await cdp.clickSelector('.agree__box');
    await sleep(250);
    if ((await cdp.eval(tickState)) !== 'checked') {
      await cdp.eval(`(() => { const el = document.querySelector('.agree__box'); el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); return true; })()`);
      await sleep(250);
    }
  }
  const agreedOk = (await cdp.eval(tickState)) === 'checked';
  console.log(`   同意协议勾选: ${agreedOk ? '已勾选 ✓' : '未勾选 ✗'}`);
  const clickedLogin = await cdp.clickSelector('.submit');
  console.log(`④ 点击「登录 / 注册」: ${clickedLogin ? '已点击' : '未找到 .submit'}`);
  // 轮询等待离开登录页（最多 12s），避免固定 sleep 后页面还在加载就判定失败
  let leftLogin = false;
  for (let i = 0; i < 24; i++) {
    await sleep(500);
    const b = await cdp.text();
    if (b && !/手机号登录/.test(b)) { leftLogin = true; break; }
  }
  await sleep(1500);
  await cdp.shot('04-after-login');
  const url = await cdp.eval('location.href');
  const body = await cdp.text();
  const loggedIn = !/手机号登录/.test(body);
  console.log(`   登录后 URL=${url}  页面是否离开登录页=${loggedIn ? '是 ✓' : '否 ✗'}${leftLogin ? '（轮询已确认离开）' : ''}`);

  // ⑤ 主链路：进入业务页（报价 / 我的 / 凭证）
  const navClicked = await cdp.eval(`(() => {
    const items = [...document.querySelectorAll('uni-view,uni-text')].filter(e => {
      const t = (e.innerText || '').trim();
      const r = e.getBoundingClientRect();
      return t && t.length <= 6 && r.width > 20 && r.height > 16 && /报价|我的|凭证|首页|工作台/.test(t) && e.children.length <= 1;
    });
    return JSON.stringify(items.slice(0, 6).map(e => {
      const r = e.getBoundingClientRect();
      return { text: e.innerText.trim(), x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
    }));
  })()`);
  console.log(`⑤ 候选导航: ${navClicked}`);
  const cand = JSON.parse(navClicked || '[]').find((c) => /报价/.test(c.text)) || JSON.parse(navClicked || '[]')[0];
  if (cand) {
    for (const t of ['mousePressed', 'mouseReleased']) await cdp.send('Input.dispatchMouseEvent', { type: t, x: cand.x, y: cand.y, button: 'left', clickCount: 1 });
    console.log(`   已点击「${cand.text}」`);
    await sleep(5000);
    await cdp.shot('05-main-link');
    const mainText = (await cdp.text()).split('\n').filter(Boolean).slice(0, 10);
    console.log('   页面文本:', JSON.stringify(mainText.slice(0, 8)));
  } else {
    console.log('   未找到可点导航（页面可能仍在加载）');
  }

  console.log('=== 浏览器控制台 error/warning ===');
  console.log(cdp.consoleErrors.length ? cdp.consoleErrors.slice(0, 10).map((l) => '   ' + l).join('\n') : '   无 ✓');
  console.log('=== 失败请求（4xx/5xx） ===');
  console.log(cdp.failedRequests.length ? cdp.failedRequests.slice(0, 10).map((l) => '   ' + l).join('\n') : '   无 ✓');
  if (await assertOwnBrowserOrRefuse()) {
    await cdp.send('Browser.close').catch(() => {});
    console.log('已关闭本脚本自己的调试实例（归属校验通过）');
  }
  ws.close();
  const bad = cdp.consoleErrors.some((l) => l.startsWith('error') || l.startsWith('exception')) || cdp.failedRequests.length > 0 || !loggedIn;
  console.log(`验收结论: ${bad ? '未通过 ✗' : '通过 ✓'}（截图目录 ${outDir}）`);
  process.exit(bad ? 1 : 0);
}

main().catch((e) => { console.error('验收失败:', e.message); process.exit(2); });
