#!/usr/bin/env node
/**
 * 有头 CDP 内核（零依赖）—— 从 `tools/cdp-acceptance.mjs` 抽出，供链路驱动器复用。
 *
 * 已踩过的坑（务必保留，改之前先看注释）：
 *   1. uni-app H5 的点击绑定在 `<uni-view>` 上，靠 innerText 找节点点不动 → 用真实鼠标事件。
 *   2. 输入框必须用 **原生 setter + CustomEvent(detail.value)**：uni-app 的 v-model 从
 *      `e.detail.value` 取值，普通 Event 没有 detail，值看着进去了、框架内部状态仍是空。
 *   3. `@tap` **不吃** CDP 合成鼠标/触摸事件 → 需要 JS 派发 `MouseEvent('click')` 兜底。
 *   4. 绝不关别人的浏览器：只有 user-data-dir 是本脚本自己的 profile 才允许 Browser.close。
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const stamp = () => new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15);
const BS = String.fromCharCode(92);

export const CHROME_CANDIDATES = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  join(process.env.LOCALAPPDATA || '', 'Google', 'Chrome', 'Application', 'chrome.exe')
];

export function findChrome() {
  const hit = CHROME_CANDIDATES.find((p) => p && existsSync(p));
  if (!hit) throw new Error('未找到 Chrome，检查 CHROME_CANDIDATES');
  return hit;
}

export class Cdp {
  constructor(ws, { recordApi = false } = {}) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    this.consoleErrors = []; this.failedRequests = [];
    this.apiCalls = [];            // { method, url, status, code, message }
    this._req = new Map();         // requestId -> { method, url }
    this._pendingBodies = [];
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
        return;
      }
      this._onEvent(m, recordApi);
    });
  }
  _onEvent(m, recordApi) {
    if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
      this.consoleErrors.push(`${m.params.type}: ${(m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 160)}`);
    }
    if (m.method === 'Runtime.exceptionThrown') {
      this.consoleErrors.push(`exception: ${m.params.exceptionDetails?.exception?.description ?? m.params.exceptionDetails?.text}`);
    }
    if (m.method === 'Network.requestWillBeSent') {
      const { requestId, request } = m.params;
      if (request.url.includes('/api/')) this._req.set(requestId, { method: request.method, url: request.url, postData: request.postData });
    }
    if (m.method === 'Network.responseReceived') {
      const { requestId, response } = m.params;
      if (response.status >= 400 && !response.url.includes('favicon')) {
        this.failedRequests.push(`${response.status} ${m.params.type} ${response.url}`);
      }
      const rec = this._req.get(requestId);
      if (rec) rec.status = response.status;
    }
    if (m.method === 'Network.loadingFinished' && this._req.has(m.params.requestId)) {
      const rec = this._req.get(m.params.requestId);
      this._req.delete(m.params.requestId);
      if (recordApi) {
        this._pendingBodies.push(
          this.send('Network.getResponseBody', { requestId: m.params.requestId })
            .then((r) => {
              let code = null; let message = null; let data = null;
              try {
                const j = JSON.parse(r.body);
                code = j.code ?? null; message = j.message ?? null; data = j.data ?? null;
              } catch { /* 非 JSON */ }
              // 登录链路要用：后端 `app.sms.expose-code=true` 时回显 dev_code
              if (rec.url.includes('/auth/sms/send') && data?.dev_code) this.devCode = data.dev_code;
              // 保留业务数据的浅快照（截断），供「断言业务结果而非状态码」使用：
              // HTTP 200 + code=0 可能是假绿（如检测结果恒空）
              let snap = null;
              try { snap = data === null ? null : JSON.parse(JSON.stringify(data).slice(0, 800)); } catch { snap = '(不可序列化)'; }
              this.apiCalls.push({ ...rec, code, message, data: snap });
            })
            .catch(() => this.apiCalls.push({ ...rec, code: '?', message: '(响应体不可读)' }))
        );
      }
    }
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
  async settle() { await Promise.allSettled(this._pendingBodies); this._pendingBodies = []; }

  /** 真实鼠标左键点击（元素中心）：先滚入视口，避免点到视口外落空 */
  async clickSelector(selector) {
    await this.eval(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (el) el.scrollIntoView({ block: 'center', inline: 'center' }); return true; })()`);
    await sleep(300);
    const box = await this.eval(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el) return null;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) return null;
      return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2),
               inView: (r.x + r.width / 2) >= 0 && (r.y + r.height / 2) >= 0 && (r.x + r.width / 2) <= innerWidth && (r.y + r.height / 2) <= innerHeight };
    })()`);
    if (!box) return false;
    for (const type of ['mousePressed', 'mouseReleased']) {
      await this.send('Input.dispatchMouseEvent', { type, x: box.x, y: box.y, button: 'left', clickCount: 1 });
    }
    return true;
  }

  /** `@tap` 不吃合成事件时的兜底：JS 派发 MouseEvent('click') */
  async jsClick(selector) {
    return this.eval(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return false; el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); return true; })()`);
  }

  /** 点 selector，若 predicate 仍不满足则用 jsClick 兜底重试 */
  async clickUntil(selector, predicate, { tries = 3, gap = 350 } = {}) {
    await this.clickSelector(selector);
    for (let i = 0; i < tries; i++) {
      await sleep(gap);
      if (await predicate()) return true;
      await this.jsClick(selector);
    }
    await sleep(gap);
    return await predicate();
  }

  /**
   * uni-app v-model 安全写值（见文件头坑 2）。
   *
   * 坑 5：H5 里 `<input>` 会编译成 `<uni-input>` **包裹元素**，`data-testid` 往往落在包裹层上，
   *       而 `HTMLInputElement.prototype` 的 value setter 只能 call 在真正的 `<input>` 上，
   *       否则抛 Illegal invocation（表现为 CDP 返回 `Uncaught`）。
   *       所以要先向下找到内层 input，事件也要在内层派发（uni-app 监听的是内层 input 事件）。
   */
  async setInput(selector, text) {
    return this.eval(`(() => {
      const host = document.querySelector(${JSON.stringify(selector)});
      if (!host) return 'NOT_FOUND';
      const el = host.tagName === 'INPUT' ? host : (host.querySelector && host.querySelector('input'));
      if (!el) return 'NO_INNER_INPUT';
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      el.focus();
      setter.call(el, ${JSON.stringify(text)});
      const fire = (type) => el.dispatchEvent(new CustomEvent(type, { bubbles: true, cancelable: true, detail: { value: ${JSON.stringify(text)} } }));
      fire('input'); fire('change'); fire('blur');
      return el.value === ${JSON.stringify(text)} ? true : 'MISMATCH:' + el.value;
    })()`);
  }

  async text() { return this.eval('document.body ? document.body.innerText : ""'); }
  async url() { return this.eval('location.href'); }

  async shot(outDir, step) {
    mkdirSync(outDir, { recursive: true });
    const r = await this.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    const file = join(outDir, `${stamp()}-${step}.png`);
    writeFileSync(file, Buffer.from(r.data, 'base64'));
    console.log(`  [截图] ${file}`);
    return file;
  }

  /** 轮询等待页面文本稳定（避免固定 sleep 后页面还在加载就判定） */
  async waitForText(needle, { timeoutMs = 12000, gap = 500 } = {}) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const t = await this.text();
      if (needle instanceof RegExp ? needle.test(t) : t.includes(needle)) return true;
      await sleep(gap);
    }
    return false;
  }
}

/** 启动有头 Chrome（独立 user-data-dir；绝不碰用户正在用的浏览器） */
export async function launchHeaded({ port, url, profileSuffix = '' }) {
  const chrome = findChrome();
  const profile = join(tmpdir(), `aap-cdp-profile-${port}${profileSuffix}`);
  const child = spawn(chrome, [
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--enable-automation',
    '--window-size=1440,900', '--window-position=40,40', url
  ], { detached: true, stdio: 'ignore' });
  child.unref();
  return { chrome, profile };
}

export async function portAlive(port) {
  try { return (await fetch(`http://127.0.0.1:${port}/json/version`)).ok; } catch { return false; }
}

export async function targetWs(port) {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* 未就绪 */ }
    await sleep(500);
  }
  throw new Error('CDP 未就绪');
}

/** 归属守卫：只有 profile 属于本脚本才允许关闭该调试实例 */
export function makeOwnershipGuard(cdp, profile) {
  const win = profile.toLowerCase();
  const posix = win.split(BS).join('/');
  return async function assertOwnBrowserOrRefuse() {
    try {
      const info = await cdp.send('Browser.getBrowserCommandLine');
      const args = (info.arguments || []).join(' ').toLowerCase();
      if (!args.includes(posix) && !args.includes(win)) {
        console.error('拒绝操作：该调试实例不属于本脚本（profile 不匹配），可能是其他项目的工作浏览器');
        return false;
      }
      return true;
    } catch { return false; }
  };
}
