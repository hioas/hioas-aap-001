#!/usr/bin/env node
/**
 * H5 全页冒烟（**有头浏览器** + CDP）—— 登录态下逐页访问，每页录 API 流水 + 控制台错误。
 *
 * 与 `h5-chain.mjs` 的分工：
 *   - h5-chain.mjs：沿主业务链逐环驱动并断言（需后端能力齐备）
 *   - 本脚本：**旁路扫全量页面**，不依赖业务链是否通，专找前端自身的渲染/调用缺陷
 *
 * 用法：node tools/h5-smoke.mjs [baseUrl] [outDir] [phone]
 * 环境变量：AAP_CDP_PORT / AAP_CLOSE=1
 */
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { Cdp, sleep, launchHeaded, portAlive, targetWs, makeOwnershipGuard, loginAndVerify } from './lib/cdp-harness.mjs';

const [baseUrl = 'http://localhost:5173', outDir = 'evidence/h5-smoke', phone = '13800138000'] =
  process.argv.slice(2);
const PORT = Number(process.env.AAP_CDP_PORT || 9600 + (process.pid % 300));
const KEEP_OPEN = process.env.AAP_CLOSE !== '1';
mkdirSync(outDir, { recursive: true });

/**
 * 页面清单**从 `src/pages.json` 读**，不手写。
 *
 * 踩过的坑（2026-09-19）：手写清单时把 `pages/credentials/index` 简写成 `pages/credentials`，
 * 结果是**无效路由 → 13 个页面全白**，而且白页截图字节数完全一致（4888B）才被我识破。
 * uni-app H5 的 hash 路由必须与 pages.json 的 path **逐字一致**。
 */
function loadPages() {
  const raw = readFileSync(new URL('../src/pages.json', import.meta.url), 'utf8');
  const doc = JSON.parse(raw);
  return (doc.pages || [])
    .map((p) => [p.path, p.style?.navigationBarTitleText || p.path])
    .filter(([path]) => path !== 'pages/login/index'); // 已登录，跳过登录页
}

let cdp;
const rows = [];
const watchdog = setTimeout(() => { console.error('\n看门狗超时：冒烟未在 480s 内完成'); process.exit(3); }, 480000);
watchdog.unref?.();

async function login() {
  const { captcha } = await loginAndVerify(cdp, { baseUrl, phone, outDir });
  console.log(`登录成功（${phone}，图形验证码=${captcha}，aap_token 已落 storage ✓）`);
}

async function main() {
  if (await portAlive(PORT)) { console.error(`端口 ${PORT} 被占用，请换 AAP_CDP_PORT`); process.exit(4); }
  console.log(`启动有头 Chrome（端口 ${PORT}）→ ${baseUrl}`);
  const { profile } = await launchHeaded({ port: PORT, url: baseUrl });
  const ws = new WebSocket(await targetWs(PORT));
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  cdp = new Cdp(ws, { recordApi: true });
  const guard = makeOwnershipGuard(cdp, profile);
  for (const d of ['Page', 'Runtime', 'Network']) await cdp.send(`${d}.enable`);

  await login();

  const PAGES = loadPages();
  console.log(`待访问页面 ${PAGES.length} 个（清单来自 src/pages.json）`);

  for (const [path, label] of PAGES) {
    const mark = cdp.apiCalls.length;
    const errMark = cdp.consoleErrors.length;
    await cdp.eval(`location.hash = '#/${path}'`);
    await sleep(900);
    await cdp.send('Page.reload');
    await sleep(2600);
    await cdp.waitForText(/.{20,}/, { timeoutMs: 8000 });
    await cdp.settle();
    const text = await cdp.text();
    const lines = text.split('\n').map((s) => s.trim()).filter(Boolean);
    const url = await cdp.url();
    // 路由必须与 pages.json 逐字一致；不一致说明是**驱动器传错路由**，不是页面缺陷
    const hashOk = url.includes(`#/${path}`);
    const routeBad = !hashOk;
    const renderOk = text.length >= 30;
    const shot = await cdp.shot(outDir, path.replace(/\//g, '_'));
    const calls = cdp.apiCalls.slice(mark);
    const errs = cdp.consoleErrors.slice(errMark);
    const bad = calls.filter((c) => c.code && c.code !== '0');
    const aborted = calls.filter((c) => c.aborted);
    rows.push({
      path, label, routeBad, renderOk, chars: text.length, head: lines.slice(0, 4).join(' / '),
      api: calls.map((c) => `${c.method} ${c.url.replace(/^https?:\/\/[^/]+/, '').split('?')[0]} → ${c.aborted ? '(被打断)' : c.code}`),
      badApi: bad.map((c) => `${c.method} ${c.url.replace(/^https?:\/\/[^/]+/, '').split('?')[0]} → ${c.code} ${c.message ?? ''}`),
      abortedApi: aborted.map((c) => `${c.method} ${c.url.replace(/^https?:\/\/[^/]+/, '').split('?')[0]}`),
      consoleErrors: errs, shot
    });
    const flag = routeBad ? '✗路由' : !renderOk ? '✗空白' : bad.length ? '⚠接口' : errs.length ? '⚠控制台' : '✓';
    console.log(`  ${flag} ${path.padEnd(26)} ${label.padEnd(16)} ${String(text.length).padStart(4)}字 ${bad.length ? `错误接口 ${bad.length}` : ''} ${aborted.length ? `(被打断 ${aborted.length})` : ''} ${errs.length ? `控制台 ${errs.length}` : ''}`);
  }

  console.log('\n' + '─'.repeat(78));
  const routeBad = rows.filter((r) => r.routeBad);
  const blank = rows.filter((r) => !r.routeBad && !r.renderOk);
  const withBadApi = rows.filter((r) => r.badApi.length);
  const withErr = rows.filter((r) => r.consoleErrors.length);
  const abortedCount = rows.reduce((n, r) => n + r.abortedApi.length, 0);
  console.log(`页面 ${rows.length}：渲染正常 ${rows.length - routeBad.length - blank.length}，路由不符 ${routeBad.length}，空白页 ${blank.length}，异常接口 ${withBadApi.length}，控制台报错 ${withErr.length}`);
  if (abortedCount) console.log(`（另有 ${abortedCount} 次请求被页面 reload 打断 —— 工具时序产物，不计入失败）`);
  if (routeBad.length) { console.log('路由不符（驱动器问题，不是页面缺陷）：'); for (const r of routeBad) console.log(`  ✗ ${r.path}`); }
  if (blank.length) { console.log('空白页：'); for (const r of blank) console.log(`  ✗ ${r.path}（${r.label}）控制台=${r.consoleErrors.slice(0, 2).join(' | ') || '无'}`); }
  if (withBadApi.length) {
    console.log('接口返回非 0 业务码：');
    for (const r of withBadApi) for (const b of r.badApi) console.log(`  ⚠ ${r.path}  ${b}`);
  }
  if (withErr.length) { console.log('控制台报错：'); for (const r of withErr) console.log(`  ⚠ ${r.path}  ${r.consoleErrors.slice(0, 2).join(' | ')}`); }

  const rf = join(outDir, 'h5-smoke-result.json');
  writeFileSync(rf, JSON.stringify({ at: new Date().toISOString(), baseUrl, phone, rows }, null, 2));
  console.log(`明细已写入 ${rf}`);

  if (KEEP_OPEN) {
    console.log(`\n浏览器保持打开。profile=${profile}`);
    ws.close();
    process.exit(routeBad.length || blank.length ? 1 : 0);
  }
  if (await guard()) await cdp.send('Browser.close').catch(() => {});
  ws.close();
  process.exit(routeBad.length || blank.length ? 1 : 0);
}

main().catch((e) => { console.error('冒烟失败:', String(e && e.message ? e.message : e)); process.exit(2); });
