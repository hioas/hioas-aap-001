#!/usr/bin/env node
/**
 * 单页文本探针：登录后打开指定 hash，打印页面可见文本与关键 testid 状态。
 * 用途：核对某页是否真的渲染出**业务内容**（而不是只有外壳的「假绿」）。
 *
 * 用法：node tools/peek-page.mjs <hash> [phone]
 */
import { chromium } from 'playwright';

const HASH = process.argv[2] || '/reviews';
const PHONE = process.argv[3] || '13900000001';
const BASE = process.env.AAP_ADMIN_BASE || 'http://127.0.0.1:5174';

const main = async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 900 }, locale: 'zh-CN' });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });

  await p.goto(BASE, { waitUntil: 'domcontentloaded' });
  await p.locator('[data-testid="phone"]').waitFor({ state: 'visible', timeout: 25000 });
  const cap = (await p.locator('[data-testid="captcha-text"]').innerText()).trim();
  await p.locator('[data-testid="phone"]').fill(PHONE);
  await p.locator('[data-testid="captcha"]').fill(cap);
  await p.locator('[data-testid="sms-btn"]').click();
  await p.locator('[data-testid="dev-code"]').waitFor({ state: 'visible', timeout: 10000 });
  const code = (await p.locator('[data-testid="dev-code"]').innerText()).replace(/\D/g, '');
  await p.locator('[data-testid="sms-code"]').fill(code);
  await p.locator('[data-testid="submit"]').click();
  await p.waitForFunction(() => !!localStorage.getItem('aap_admin_token'), null, { timeout: 15000 });

  await p.goto(`${BASE}/#${HASH}`, { waitUntil: 'domcontentloaded' });
  await p.reload({ waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(3000);

  const info = await p.evaluate(() => ({
    hash: location.hash,
    title: document.querySelector('.topbar__title')?.innerText?.trim() ?? null,
    text: (document.body.innerText || '').trim(),
    testids: [...document.querySelectorAll('[data-testid]')].map((e) => e.getAttribute('data-testid'))
  }));

  console.log(`hash: ${info.hash}`);
  console.log(`标题: ${info.title}`);
  console.log(`testid(${info.testids.length}): ${info.testids.join(' | ')}`);
  console.log('--- 可见文本 ---');
  console.log(info.text.split('\n').filter(Boolean).map((l) => '  ' + l).join('\n').slice(0, 2600));
  console.log('--- 控制台 ---');
  console.log(errs.length ? errs.slice(0, 5).join('\n') : '  无报错 ✓');

  await b.close();
};

main().catch((e) => { console.error('探针失败:', e.message); process.exit(2); });
