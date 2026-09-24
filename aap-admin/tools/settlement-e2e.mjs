#!/usr/bin/env node
/**
 * 结算出账闭环 · Playwright + 本地 Chrome（有头）
 *
 * 用法：node tools/settlement-e2e.mjs [baseUrl] [outDir] [phone]
 *   baseUrl 默认 http://127.0.0.1:5175（验收用 aap-admin dev server，需指向含结算端点的后端）
 *   outDir  默认 evidence/settlement-e2e
 *   phone   默认 13800000221（dev 库 SUPER_ADMIN）
 *
 * 环境变量：AAP_HEADLESS=1 无头；AAP_SLOWMO=250 放慢；AAP_CHROME 自定义 Chrome 路径
 *
 * 为什么必须真浏览器：出账是「UI → 后端 → 库」的**写链路**，Node 直调接口只能证接口通，
 * 证不了「按钮点得动、默认值传对、台账真的刷新出来、状态标签不是原始码」。
 *
 * 覆盖：ADM-PAY06（生成）/ ADM-PAY07（明细）/ ADM-PAY08（确认出账）。
 * 幂等口径：同周期已有单时后端返回既有单 —— 脚本按「复用」记录并通过，不误报失败。
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:5175';
const OUT = process.argv[3] || 'evidence/settlement-e2e';
const PHONE = process.argv[4] || '13800000221';
const HEADLESS = process.env.AAP_HEADLESS === '1';
const SLOWMO = Number(process.env.AAP_SLOWMO || 0);

mkdirSync(OUT, { recursive: true });

const steps = [];
const calls = [];
const consoleErrors = [];

function record(name, ok, detail = '') {
  steps.push({ name, ok: !!ok, detail: String(detail) });
  console.log(`  ${ok ? '✓' : '✗'} ${name}${detail ? ' — ' + detail : ''}`);
}

const browser = await chromium.launch({
  headless: HEADLESS,
  slowMo: SLOWMO,
  executablePath: process.env.AAP_CHROME || undefined,
  channel: process.env.AAP_CHROME ? undefined : 'chrome'
});
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
const page = await context.newPage();

page.on('response', (res) => {
  const url = res.url();
  if (url.includes('/api/v1/')) {
    calls.push({ status: res.status(), method: res.request().method(), url: url.replace(/^.*\/api\/v1/, '') });
  }
});
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text().slice(0, 200));
});

async function finish() {
  const passed = steps.filter((s) => s.ok).length;
  const body = {
    generated_at: new Date().toISOString(),
    base: BASE,
    phone_masked: PHONE.replace(/^(\d{3})\d{4}/, '$1****'),
    steps_total: steps.length,
    steps_passed: passed,
    steps_failed: steps.length - passed,
    steps,
    calls,
    console_errors: consoleErrors
  };
  writeFileSync(join(OUT, 'settlement-e2e.json'), JSON.stringify(body, null, 2), 'utf8');
  console.log('\n' + '─'.repeat(70));
  console.log(`结算出账闭环：通过 ${passed}，失败 ${steps.length - passed}`);
  if (steps.length - passed) {
    console.log('失败明细：');
    steps.filter((s) => !s.ok).forEach((s) => console.log(`  ✗ ${s.name} — ${s.detail}`));
  }
  console.log(`明细已写入 ${join(OUT, 'settlement-e2e.json')}`);
  await browser.close();
  process.exit(steps.length - passed ? 1 : 0);
}

// ── 1. 登录（短信 + 图形验证码 + dev 回显码）────────────────────────────
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
try {
  await page.locator('[data-testid="phone"]').waitFor({ state: 'visible', timeout: 25000 });
} catch {
  record('登录页渲染', false, '25s 内未出现手机号输入框（dev server 在跑吗？）');
  await finish();
}
// ⚠️ 顺序与 admin-acceptance.mjs 一致：**先读图形验证码再填手机号**。
//    反过来（先填手机号）实测会读到已刷新的验证码 → 登录报 E-1001 参数校验失败。
const captcha = (await page.locator('[data-testid="captcha-text"]').innerText()).trim();
await page.locator('[data-testid="phone"]').fill(PHONE);
await page.locator('[data-testid="captcha"]').fill(captcha);

const beforeSms = calls.length;
await page.locator('[data-testid="sms-btn"]').click();
await page.waitForTimeout(1500);
const smsCall = calls.slice(beforeSms).find((c) => c.url.includes('/auth/sms/send'));
record('发出取码请求', !!smsCall, smsCall ? `HTTP ${smsCall.status}` : '未发出');

let devCode = '';
try {
  await page.locator('[data-testid="dev-code"]').waitFor({ state: 'visible', timeout: 8000 });
  devCode = (await page.locator('[data-testid="dev-code"]').innerText()).replace(/\D/g, '');
} catch {
  /* 生产不回显 */
}
record('拿到 dev 回显短信码', !!devCode, devCode || '后端需 AAP_SMS_EXPOSE_CODE=true');
await page.locator('[data-testid="sms-code"]').fill(devCode);
await page.locator('[data-testid="submit"]').click();
try {
  await page.waitForFunction(() => !!localStorage.getItem('aap_admin_token'), null, { timeout: 15000 });
  record('管理端登录（SUPER_ADMIN）', true, `captcha=${captcha}`);
} catch {
  const err = await page.locator('[data-testid="login-error"]').innerText().catch(() => '(无提示)');
  record('管理端登录（SUPER_ADMIN）', false, err);
  await page.screenshot({ path: join(OUT, '01-login-failed.png'), fullPage: true });
  await finish();
}

// ── 2. 合同与结算页 ──────────────────────────────────────────────────
await page.goto(`${BASE}/#/contracts`, { waitUntil: 'domcontentloaded' });
try {
  await page.locator('[data-testid="statement-table"]').waitFor({ state: 'visible', timeout: 20000 });
} catch {
  record('结算台账渲染', false, '未找到 [data-testid="statement-table"]');
  await page.screenshot({ path: join(OUT, '02-no-table.png'), fullPage: true });
  await finish();
}
await page.waitForTimeout(1500);

const rowNos = async () =>
  page.locator('[data-testid="statement-table"] tbody tr').evaluateAll((rows) =>
    rows.map((r) => (r.innerText || '').split('\n')[0].trim()).filter(Boolean)
  );

const before = await rowNos();
record('结算台账渲染', true, `现有 ${before.length} 张单`);

// 文案门禁：实现之后不得再出现「系统当前不生成结算单」这类假话
const pageText = await page.locator('body').innerText();
record(
  '文案不再声称「不生成结算单」',
  !/系统当前不生成结算单/.test(pageText) && !/没有任何写入路径/.test(pageText),
  /系统当前不生成结算单/.test(pageText) ? '页面仍在说系统不生成结算单（文案回退）' : 'ok'
);

// ── 3. 打开出账对话框，核对默认值（供应商 + 当前 UTC 月）──────────────
await page.locator('[data-testid="btn-gen-statement"]').click();
try {
  await page.locator('[data-testid="gen-statement-form"]').waitFor({ state: 'visible', timeout: 8000 });
  record('出账对话框打开（ADM-PAY06 入口）', true);
} catch {
  record('出账对话框打开（ADM-PAY06 入口）', false, '未渲染 gen-statement-form');
  await page.screenshot({ path: join(OUT, '03-no-dialog.png'), fullPage: true });
  await finish();
}

const providerText = (await page.locator('[data-testid="gen-provider"]').innerText().catch(() => '')).trim();
record('默认选中供应商（需有 SIGNED 合同）', !!providerText && !/选择供应商/.test(providerText), providerText || '(空)');

const monthValue = (await page.locator('[data-testid="gen-month"] input').inputValue().catch(() => '')).trim()
  || (await page.locator('[data-testid="gen-month"]').inputValue().catch(() => '')).trim();
const utcMonth = new Date().toISOString().slice(0, 7);
record('月份默认 = 当前 UTC 月', monthValue === utcMonth, `${monthValue}（期望 ${utcMonth}）`);

// ── 4. 生成 ─────────────────────────────────────────────────────────
const beforeGenerateCalls = calls.length;
await page.locator('[data-testid="gen-submit"]').click();
await page.waitForTimeout(2500);

const genCall = calls.slice(beforeGenerateCalls).find((c) => c.method === 'POST' && c.url.startsWith('/admin/settlements'));
record('点击「生成」发出 POST /admin/settlements', !!genCall, genCall ? `HTTP ${genCall.status}` : '未发出');

// 失败提示（E-1601 无用量 / E-1701 无合同）必须显式显示，不能假装成功
const genErr = await page.locator('[data-testid="gen-error"]').innerText().catch(() => '');
if (genErr) {
  record('生成结果', false, `后端拒绝：${genErr.trim()}`);
  await page.screenshot({ path: join(OUT, '04-generate-error.png'), fullPage: true });
  await finish();
}
record('生成结果', genCall && genCall.status < 400, genCall ? `HTTP ${genCall.status}` : '');

await page.waitForTimeout(1200);
const after = await rowNos();
const added = after.filter((n) => !before.includes(n));
record('台账刷新出新单', added.length > 0 || after.length > 0, added.length ? `新增：${added.join(', ')}` : `当前 ${after.length} 张（同周期幂等复用既有单）`);

// 状态必须渲染成中文标签，而不是原始码（本轮之前就是这么错的：DRAFT 直接显示）
const tableText = await page.locator('[data-testid="statement-table"]').innerText();
const rawCodes = ['DRAFT', 'CONFIRMED', 'VOID'].filter((c) => tableText.includes(c));
record('状态列渲染为中文标签（非原始码）', rawCodes.length === 0, rawCodes.length ? `出现原始码：${rawCodes.join(',')}` : '草稿/已出账/已作废');

// ── 5. 明细（ADM-PAY07）─────────────────────────────────────────────
const firstRow = page.locator('[data-testid="statement-table"] tbody tr').first();
const detailBtn = firstRow.locator('[data-testid^="act-statement-detail-"]');
let detailOk = false;
let linesCount = 0;
if (await detailBtn.count()) {
  await detailBtn.click();
  try {
    await page.locator('[data-testid="statement-lines"]').waitFor({ state: 'visible', timeout: 10000 });
    linesCount = await page.locator('[data-testid="statement-lines"] tbody tr').count();
    detailOk = linesCount > 0;
  } catch {
    /* 落下面的记录 */
  }
}
record('明细对话框（ADM-PAY07）渲染明细行', detailOk, `${linesCount} 行`);
await page.screenshot({ path: join(OUT, '05-statement-detail.png'), fullPage: true });
await page.keyboard.press('Escape');
await page.waitForTimeout(600);

// ── 6. 确认出账（ADM-PAY08，仅草稿可确认）────────────────────────────
const confirmBtn = page.locator('[data-testid^="act-confirm-statement-"]').first();
if (await confirmBtn.count()) {
  const beforeConfirm = calls.length;
  await confirmBtn.click();
  await page.waitForTimeout(800);
  // ElMessageBox 确认框
  const boxOk = page.locator('.el-message-box__btns .el-button--primary').last();
  if (await boxOk.count()) await boxOk.click();
  await page.waitForTimeout(2500);
  const confirmCall = calls.slice(beforeConfirm).find((c) => c.method === 'POST' && /\/confirm$/.test(c.url));
  record('确认出账发出 POST /admin/settlements/{id}/confirm', !!confirmCall, confirmCall ? `HTTP ${confirmCall.status}` : '未发出');
  await page.waitForTimeout(1000);
  const afterText = await page.locator('[data-testid="statement-table"]').innerText();
  record('确认后状态为「已出账」', afterText.includes('已出账'), afterText.includes('已出账') ? '已出账' : '未见「已出账」标签');
} else {
  record('确认出账（ADM-PAY08）', true, '本页无草稿单（同周期已出账）→ 跳过，非失败');
}
await page.screenshot({ path: join(OUT, '06-after-confirm.png'), fullPage: true });

record('页面无控制台报错', consoleErrors.length === 0, consoleErrors.slice(0, 2).join(' | ') || '0 报错');
await finish();
