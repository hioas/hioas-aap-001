#!/usr/bin/env node
/**
 * H5 前后端联调链路驱动器（**有头浏览器** + CDP，零依赖）
 *
 * 为什么必须走浏览器：Node 侧直调 API 只能证明「后端接口通」，证明不了
 *   「页面把参数拼对了、把响应渲染对了、用户点得动」。所以链条在真实浏览器里跑。
 *
 * 与 `tools/cdp-acceptance.mjs` 的分工：
 *   - cdp-acceptance.mjs：登录 + 浅层导航的「能开、能点、能登录」验收
 *   - 本脚本：登录后**沿业务链逐环驱动真实 UI，并断言真实 HTTP 调用**（方法/路径/业务码）
 *
 * 用法：
 *   node tools/h5-chain.mjs [baseUrl] [outDir] [phone]
 * 环境变量：
 *   AAP_CDP_PORT   默认 9400+(pid%500)，避开 aim 项目固定占用的 9223
 *   AAP_CLOSE=1    跑完关闭浏览器（默认**保持打开**，便于人工核对页面）
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  Cdp, sleep, launchHeaded, portAlive, targetWs, makeOwnershipGuard, loginAndVerify
} from './lib/cdp-harness.mjs';

const [baseUrl = 'http://localhost:5173', outDir = 'evidence/h5-chain', phone = '13800138000'] =
  process.argv.slice(2);
const PORT = Number(process.env.AAP_CDP_PORT || 9400 + (process.pid % 500));
const KEEP_OPEN = process.env.AAP_CLOSE !== '1';

mkdirSync(outDir, { recursive: true });
const results = [];
const api = () => cdp.apiCalls;

/** 步骤执行器：任何异常都记为失败并继续（联调要看到全貌，不是第一处就停） */
async function step(name, fn) {
  process.stdout.write(`\n[${results.length + 1}] ${name}\n`);
  try {
    const detail = await fn();
    results.push({ name, ok: true, detail: detail ?? '' });
    console.log(`  ✓ ${detail ?? ''}`);
  } catch (e) {
    results.push({ name, ok: false, detail: e.message });
    console.log(`  ✗ ${e.message}`);
  }
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

/** 在页面里按可见文本找元素并点它（uni-app 的点击目标在 <uni-view> 上） */
async function clickText(re, { tag = 'uni-view,uni-text,uni-button,view,text' } = {}) {
  const found = await cdp.eval(`(() => {
    const cands = [...document.querySelectorAll(${JSON.stringify(tag)})].filter((e) => {
      const t = (e.innerText || '').trim();
      if (!t || t.length > 12) return false;
      const r = e.getBoundingClientRect();
      return r.width > 20 && r.height > 16;
    });
    const hit = cands.find((e) => ${re}.test(e.innerText.trim()));
    if (!hit) return null;
    const r = hit.getBoundingClientRect();
    return { text: hit.innerText.trim(), x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
  })()`);
  if (!found) return null;
  for (const type of ['mousePressed', 'mouseReleased']) {
    await cdp.send('Input.dispatchMouseEvent', { type, x: found.x, y: found.y, button: 'left', clickCount: 1 });
  }
  return found.text;
}

const called = (method, pathPart) =>
  api().filter((c) => c.method === method && c.url.includes(pathPart));

let cdp;
let guard;
const watchdog = setTimeout(() => { console.error('\n看门狗超时：链路未在 240s 内完成'); process.exit(3); }, 240000);
watchdog.unref?.();

async function main() {
  if (await portAlive(PORT)) {
    console.error(`端口 ${PORT} 已有调试实例在监听：**拒绝复用**（可能是其他项目正在用的浏览器）。请用 AAP_CDP_PORT=<空闲端口> 重跑。`);
    process.exit(4);
  }
  console.log(`启动有头 Chrome（独立 profile，端口 ${PORT}）→ ${baseUrl}`);
  const { profile } = await launchHeaded({ port: PORT, url: baseUrl });

  const ws = new WebSocket(await targetWs(PORT));
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  cdp = new Cdp(ws, { recordApi: true });
  guard = makeOwnershipGuard(cdp, profile);
  for (const d of ['Page', 'Runtime', 'Network']) await cdp.send(`${d}.enable`);

  // ═══ ① 登录（真实 UI：读页面验证码 → 获取验证码 → 取 dev_code → 勾协议 → 登录）═══
  await step('① 打开登录页', async () => {
    await cdp.send('Page.navigate', { url: baseUrl });
    // 轮询等渲染（固定 sleep 会偶发「未渲染」，实测踩过：5s 不够 → 误报）
    const ok = await cdp.waitForText(/登录/, { timeoutMs: 15000 });
    assert(ok, '登录页未渲染出「登录」字样');
    await cdp.shot(outDir, '01-login');
    return `title="${await cdp.eval('document.title')}"`;
  });

  await step('② 登录（逐环硬校验：验证码 → dev_code → token 落 storage）', async () => {
    const { captcha, token } = await loginAndVerify(cdp, { baseUrl, phone, outDir });
    const login = called('POST', '/auth/sms/login');
    return `图形验证码=${captcha}；dev_code 已捕获；aap_token(${String(token).length} 字符) 已落 storage；`
      + `POST /auth/sms/login → code=${login[0]?.code ?? '未捕获'}`;
  });

  // ═══ ② 业务链：凭证 → 检测 → 报告 → 报价 ═══
  const goto = async (hash, expectText) => {
    await cdp.eval(`location.hash = ${JSON.stringify(hash)}`);
    await sleep(1200);
    // 同 hash 不会触发路由变化 → 强制 reload
    await cdp.send('Page.reload');
    await sleep(2500);
    await cdp.waitForText(expectText, { timeoutMs: 10000 });
  };

  await step('⑤ 凭证列表页可开', async () => {
    await goto('#/pages/credentials/index', /凭证|接入/);
    const t = await cdp.text();
    assert(/凭证/.test(t), '凭证列表页未渲染');
    const list = called('GET', '/credentials');
    await cdp.shot(outDir, '05-credentials');
    return `GET /credentials → ${list.length ? `code=${list[0].code}` : '本次未发（可能用缓存）'}`;
  });

  await step('⑥ 进入「接入凭证」页', async () => {
    const hit = await clickText(/接入凭证|新增凭证/);
    if (!hit) {
      await cdp.eval(`location.hash = '#/pages/credential-submit/index'`);
      await cdp.send('Page.reload');
      await sleep(3000);
    }
    const ok = await cdp.waitForText(/接入凭证/, { timeoutMs: 10000 });
    await cdp.shot(outDir, '06-submit-form');
    assert(ok, `未进入接入凭证页（点击命中=${hit ?? '无'}）`);
    return `命中入口=${hit ?? '直接路由跳转'}`;
  });

  await step('⑦ 填表并保存草稿 → 断言 POST /credentials（缺陷4 的修复点）', async () => {
    const alias = `联调凭证${Date.now() % 100000}`;
    const a = await cdp.setInput('[data-testid="alias-input"]', alias);
    assert(a === true, `名称写入失败: ${a}`);
    const b = await cdp.setInput('[data-testid="baseurl-input"]', 'http://127.0.0.1:9911/v1');
    assert(b === true, `BaseURL 写入失败: ${b}`);
    await cdp.clickUntil('[data-testid="apikey-edit"]', async () => await cdp.eval(`!!document.querySelector('[data-testid="apikey-input"]')`));
    const c = await cdp.setInput('[data-testid="apikey-input"]', `sk-chain-${Date.now()}`);
    assert(c === true, `APIKey 写入失败: ${c}`);
    await cdp.shot(outDir, '07-form-filled');

    const before = called('POST', '/credentials').length;
    await cdp.clickUntil('[data-testid="save-btn"]', async () => called('POST', '/credentials').length > before, { tries: 6, gap: 800 });
    await sleep(2500);
    await cdp.settle();
    const post = called('POST', '/credentials');
    await cdp.shot(outDir, '08-saved');
    assert(post.length > 0, '点击保存后仍未发出 POST /credentials（缺陷4 未修复？）');
    assert(post[0].code === '0', `POST /credentials → code=${post[0].code} ${post[0].message ?? ''}`);
    const put = called('PUT', '/credentials/');
    return `POST /credentials → code=${post[0].code}；PUT 保存 → ${put.length ? `code=${put[0].code}` : '未发出'}`;
  });

  await step('⑧ 提交检测 → 断言 precheck', async () => {
    const before = called('POST', '/precheck').length;
    await cdp.clickUntil('[data-testid="submit-btn"]', async () => called('POST', '/precheck').length > before, { tries: 6, gap: 1000 });
    await sleep(3000);
    await cdp.settle();
    const pre = called('POST', '/precheck');
    await cdp.shot(outDir, '09-precheck');
    assert(pre.length > 0, '未发出 POST /credentials/{id}/precheck');
    return `POST /credentials/{id}/precheck → code=${pre[0].code} ${pre[0].message ?? ''}`;
  });

  await step('⑨ 检测进行中页可开', async () => {
    const t = await cdp.text();
    const onDetecting = /检测/.test(t);
    await cdp.shot(outDir, '10-detecting');
    return onDetecting ? '页面已进入检测相关视图' : `当前文本片段：${t.split('\n').filter(Boolean).slice(0, 3).join(' / ')}`;
  });

  await step('⑩ 报价单列表页可开', async () => {
    await goto('#/pages/quotes/index', /报价/);
    const list = called('GET', '/quotes');
    await cdp.shot(outDir, '11-quotes');
    return `GET /quotes → ${list.length ? `code=${list[0].code}` : '本次未发'}`;
  });

  /**
   * ⑪ 关键：断言**业务结果**，不是状态码。
   *
   * 联调实测（2026-09-19）：`POST /credentials/{id}/precheck` 会建出 DetectionJob，
   * 但全仓库无 `recordProbeResults` 的调用方 → 任务**永停 QUEUED**，
   * `/results` 永远返回 `{total: 0, items: []}`（HTTP 200 + code=0，**假绿**）。
   * 只看状态码的联调会把它判成通过，所以这一步专门盯业务结果。
   */
  await step('⑪ 检测任务是否真被执行（断言业务结果，非状态码）', async () => {
    const jobs = called('GET', '/detection-jobs/').filter((c) => !c.url.includes('/results'));
    assert(jobs.length > 0, '检测进行中页未查询过 detection-jobs');
    const last = jobs[jobs.length - 1];
    const st = last.data?.status ?? '(无 status 字段)';
    const results = called('GET', '/results');
    const total = results.length ? results[results.length - 1].data?.total : undefined;
    await sleep(3000);
    assert(
      st !== 'QUEUED' && st !== 'PENDING',
      `检测任务仍停在 ${st}（started_at=${last.data?.started_at ?? 'null'}）→ 检测执行器缺失，`
      + `结果恒空（total=${total ?? '未查询'}）。这是业务结果失败，不是 HTTP 失败`
    );
    return `job status=${st}，results.total=${total}`;
  });

  // ═══ 汇总 ═══
  await cdp.settle();
  console.log('\n' + '─'.repeat(78));
  console.log('真实 HTTP 调用流水（/api/）：');
  for (const c of api()) {
    const p = c.url.replace(/^https?:\/\/[^/]+/, '');
    console.log(`  ${String(c.status).padEnd(4)} ${c.method.padEnd(6)} ${p.padEnd(46)} code=${c.code}${c.message ? ` ${c.message}` : ''}`);
  }
  console.log('─'.repeat(78));
  const pass = results.filter((r) => r.ok).length;
  console.log(`步骤 ${results.length}：通过 ${pass}，失败 ${results.length - pass}；真实 HTTP ${api().length} 次`);
  if (results.some((r) => !r.ok)) {
    console.log('失败明细：');
    for (const r of results.filter((x) => !x.ok)) console.log(`  ✗ ${r.name} — ${r.detail}`);
  }
  const errs = cdp.consoleErrors.filter((l) => l.startsWith('error') || l.startsWith('exception'));
  console.log(`控制台 error/exception：${errs.length ? errs.slice(0, 5).join(' | ') : '无 ✓'}`);

  const report = { at: new Date().toISOString(), baseUrl, phone, steps: results, apiCalls: api() };
  const rf = join(outDir, 'h5-chain-result.json');
  writeFileSync(rf, JSON.stringify(report, null, 2));
  console.log(`明细已写入 ${rf}`);

  if (KEEP_OPEN) {
    console.log(`\n浏览器保持打开（人工核对页面）。profile=${profile}`);
    console.log('确认完再关：设 AAP_CLOSE=1 重跑，或在浏览器里直接关闭窗口。');
    ws.close();
    process.exit(results.some((r) => !r.ok) ? 1 : 0);
  }
  if (await guard()) { await cdp.send('Browser.close').catch(() => {}); console.log('已关闭本脚本自己的调试实例（归属校验通过）'); }
  ws.close();
  process.exit(results.some((r) => !r.ok) ? 1 : 0);
}

main().catch((e) => { console.error('链路驱动失败:', e.message); process.exit(2); });
