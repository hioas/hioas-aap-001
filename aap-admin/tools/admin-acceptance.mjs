#!/usr/bin/env node
/**
 * 管理端联调验收 · Playwright + 本地 Chrome（有头）
 *
 * 用法：node tools/admin-acceptance.mjs [baseUrl] [outDir] [phone]
 *   baseUrl 默认 http://127.0.0.1:5174（aap-admin dev server）
 *   outDir  默认 evidence/admin
 *   phone   默认 13900000001（dev 库 SUPER_ADMIN）
 *
 * 环境变量：
 *   AAP_HEADLESS=1   改无头（默认有头，用户要求过程可见）
 *   AAP_SLOWMO=250   每步放慢，便于人眼跟随
 *   AAP_CHROME       自定义 Chrome 可执行路径
 *
 * 为什么必须真浏览器：Node 侧直调接口只能证「接口通」，证不了
 * 「页面渲染出来、参数传对、按钮点得动」。上一轮在供应商端已经踩过
 * 「接口全绿但页面带不出模型」的假绿（缺陷10）。
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:5174';
const OUT = process.argv[3] || 'evidence/admin';
const PHONE = process.argv[4] || '13900000001';
const HEADLESS = process.env.AAP_HEADLESS === '1';
const SLOWMO = Number(process.env.AAP_SLOWMO || 0);

mkdirSync(OUT, { recursive: true });

/** 路由 → 期望标题（与 src/router meta.title 一致） */
const ROUTES = [
  ['/dashboard', '进件状态看板'],
  ['/usage', '用量统计'],
  ['/models', '模型管理'],
  ['/providers', '供应商管理'],
  ['/detection', '检测中心'],
  ['/reviews', '报价审核'],
  ['/contracts', '合同与结算'],
  ['/compilation', '编译确认台'],
  ['/sync', 'new-api 同步']
];

/**
 * 每页的**业务内容判据**（防空转假绿）。
 *
 * 只判「不空白 + 标题对」是不够的：骨架页也满足这两条，会得到误导性的全绿。
 * 已实现的页面必须再满足各自的业务特征，未实现的页面必须**明确带「待实现」徽章** ——
 * 这样「实现了但没渲染出内容」和「还是骨架」都不会被混过去。
 */
const CONTENT_GATES = {
  '/dashboard': {
    require: ['[data-testid="kpi-row"]', '[data-testid="intake-table"]'],
    textAny: ['进件总数', '进件漏斗', '最近进件动态']
  },
  '/reviews': {
    require: ['[data-testid="design-prd-conflict"]', '[data-testid="refresh-pool"]'],
    textAny: ['待审核列表', '审核决策']
  },
  '/contracts': {
    require: ['[data-testid="contract-kpi"]', '[data-testid="contract-table"]'],
    textAny: ['合同与结算台账', '待打款批次', '结算台账明细']
  },
  '/usage': {
    require: ['[data-testid="usage-kpi"]', '[data-testid="usage-chart"]', '[data-testid="model-table"]'],
    textAny: ['总请求数', '调用与消耗趋势', '模型维度用量']
  }
};

const rows = [];
const record = (name, ok, detail = '') => {
  rows.push({ name, ok, detail });
  console.log(`  ${ok ? '✓' : '✗'} ${name}${detail ? ` — ${detail}` : ''}`);
};

/** 收集 /api/v1 的真实调用流水（只看后端业务接口，避免把源码模块请求算进来） */
function attachApiLog(page) {
  const calls = [];
  const errors = [];
  page.on('response', async (res) => {
    const url = res.url();
    if (!url.includes('/api/v1/')) return;
    const rec = { method: res.request().method(), url, status: res.status(), postData: res.request().postData() ?? null };
    try {
      const body = await res.json();
      rec.code = body?.code ?? null;
      rec.message = body?.message ?? null;
      rec.data = body?.data ?? null;
    } catch {
      rec.code = null;
    }
    calls.push(rec);
  });
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const t = m.text();
    // favicon 404 是浏览器默认请求，与产品无关 —— 不过滤会污染「控制台报错」判据
    if (/favicon/i.test(t) || /Failed to load resource.*404/.test(t)) return;
    errors.push(t.slice(0, 200));
  });
  page.on('pageerror', (e) => errors.push(`exception: ${e.message}`.slice(0, 200)));
  return { calls, errors };
}

async function main() {
  const browser = await chromium.launch({
    channel: 'chrome', // 用本地已安装的 Chrome，不下载 Chromium
    headless: HEADLESS,
    slowMo: SLOWMO,
    args: ['--start-maximized']
  });
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const { calls, errors } = attachApiLog(page);

  console.log(`管理端联调  base=${BASE}  账号=${PHONE}  浏览器=本地Chrome(${HEADLESS ? '无头' : '有头'})\n`);

  // ── 1. 登录页 ────────────────────────────────────────────────────────
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  // ⚠️ Element Plus 把 data-testid **透传到内层 `<input class="el-input__inner">` 自身**，
  //    不是外层包装 div。所以选择器就是 `[data-testid="phone"]`，
  //    写成 `[data-testid="phone"] input` 会找不到元素（实测踩过）。
  const phoneInput = page.locator('[data-testid="phone"]');
  try {
    await phoneInput.waitFor({ state: 'visible', timeout: 25000 });
    record('登录页渲染', true);
  } catch {
    record('登录页渲染', false, '25s 内未出现手机号输入框（dev server 在跑吗？）');
    return finish(browser, calls);
  }

  const captcha = (await page.locator('[data-testid="captcha-text"]').innerText()).trim();
  record('读到图形验证码', !!captcha, captcha);

  await phoneInput.fill(PHONE);
  await page.locator('[data-testid="captcha"]').fill(captcha);

  const beforeSms = calls.length;
  await page.locator('[data-testid="sms-btn"]').click();
  await page.waitForTimeout(1200);
  const smsCall = calls.slice(beforeSms).find((c) => c.url.includes('/auth/sms/send'));
  record('点「获取验证码」发出请求', !!smsCall, smsCall ? `code=${smsCall.code}` : '未发出');

  // dev 回显：后端 AAP_SMS_EXPOSE_CODE=true 时页面会渲染 dev-code
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
    record('登录成功且 token 落 storage', true, `len=${String(await page.evaluate(() => localStorage.getItem('aap_admin_token'))).length}`);
  } catch {
    const err = await page.locator('[data-testid="login-error"]').innerText().catch(() => '(无错误提示)');
    record('登录成功且 token 落 storage', false, err);
    await page.screenshot({ path: join(OUT, 'login-failed.png'), fullPage: true });
    return finish(browser, calls);
  }
  await page.screenshot({ path: join(OUT, '01-after-login.png'), fullPage: true });

  // ── 2. 逐页核对（渲染 / 标题 / 接口 / 控制台） ────────────────────────
  for (const [route, title] of ROUTES) {
    const before = calls.length;
    errors.length = 0;

    await page.goto(`${BASE}/#${route}`, { waitUntil: 'domcontentloaded' });
    // ⚠️ 同 hash 的 goto **不会重载**（浏览器把 hash 变更当路由内跳转）：
    //    登录后已停在 /dashboard，循环里再 goto 到 /dashboard 就不会重新挂载 →
    //    该页的取数请求被算在循环之前，显示成「接口 0 次」这种**误导性的假象**。
    //    所以目标 hash 与当前一致时，强制 reload。
    const sameHash = await page.evaluate((r) => location.hash === `#${r}`, route);
    if (sameHash) await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1600);

    const state = await page.evaluate(() => {
      const app = document.querySelector('#app');
      const h1 = document.querySelector('.topbar__title');
      const body = (document.body.innerText || '').trim();
      return {
        h1: h1 ? h1.innerText.trim() : null,
        textLen: body.length,
        blank: !app || app.children.length === 0 || body.length < 40,
        hasNav: !!document.querySelector('.sidebar'),
        hasLoginForm: !!document.querySelector('[data-testid="phone"]')
      };
    });

    const seg = calls.slice(before).filter((c) => c.url.includes('/api/v1/'));
    const bad = seg.filter((c) => c.code !== '0' && c.code !== null);
    const errs = [...errors];

    // 业务内容判据：已实现页必须渲染出业务特征；未实现页必须明确带「待实现」徽章
    const gate = CONTENT_GATES[route];
    const gateState = await page.evaluate(
      ({ require: req, textAny }) => {
        const missing = (req || []).filter((s) => !document.querySelector(s));
        const text = document.body.innerText || '';
        const hitAny = !textAny || textAny.some((t) => text.includes(t));
        return { missing, hitAny, isStub: text.includes('待实现') };
      },
      { require: gate?.require, textAny: gate?.textAny }
    );

    const problems = [];
    if (state.hasLoginForm) problems.push('被踢回登录页（401 未续期）');
    if (state.blank) problems.push(`页面空白（textLen=${state.textLen}）`);
    if (!state.hasNav) problems.push('外壳未渲染（无侧栏）');
    if (state.h1 !== title) problems.push(`标题不符：期望「${title}」实际「${state.h1}」`);
    if (gate) {
      if (gateState.missing.length) problems.push(`缺少业务节点：${gateState.missing.join('、')}`);
      if (!gateState.hitAny) problems.push(`未渲染出业务文案（期望含 ${gate.textAny.join(' / ')} 之一）`);
      if (gateState.isStub) problems.push('已登记为已实现，但仍显示「待实现」徽章');
    } else if (!gateState.isStub) {
      problems.push('尚未实现却缺少「待实现」徽章（状态不明，无法区分完成度）');
    }
    if (bad.length) problems.push(`异常接口 ${bad.length} 条：${bad.map((b) => `${b.method} ${b.url.split('/api/v1')[1]?.split('?')[0]} → ${b.code} ${b.message ?? ''}`).join('；')}`);
    if (errs.length) problems.push(`控制台报错 ${errs.length} 条：${errs[0]}`);

    await page.screenshot({ path: join(OUT, `page${route.replace(/\//g, '-')}.png`), fullPage: true });
    record(
      `${route}  ${title}`,
      problems.length === 0,
      problems.length ? problems.join(' | ') : `${gate ? '业务内容已渲染' : '骨架（含待实现徽章）'}；接口 ${seg.length} 次，控制台 0 报错`
    );
  }

  return finish(browser, calls);
}

function finish(browser, calls = []) {
  const pass = rows.filter((r) => r.ok).length;
  const fail = rows.length - pass;
  console.log(`\n${'─'.repeat(78)}`);
  console.log(`管理端联调：通过 ${pass}，失败 ${fail}`);
  if (fail) {
    console.log('失败明细：');
    for (const r of rows.filter((x) => !x.ok)) console.log(`  ✗ ${r.name} — ${r.detail}`);
  }
  if (calls.length) {
    console.log(`\n真实 HTTP 调用流水（/api/v1，共 ${calls.length} 次）：`);
    for (const c of calls.slice(-14)) {
      console.log(`  ${String(c.status).padEnd(4)} ${c.method.padEnd(6)} ${c.url.split('/api/v1')[1]?.split('?')[0]}  code=${c.code ?? '-'}`);
    }
  }
  writeFileSync(
    join(OUT, 'admin-acceptance.json'),
    JSON.stringify({ base: BASE, phone: PHONE, headless: HEADLESS, rows, calls }, null, 2),
    'utf8'
  );
  console.log(`\n明细已写入 ${join(OUT, 'admin-acceptance.json')}`);
  return browser.close().then(() => process.exit(fail ? 1 : 0));
}

main().catch(async (e) => {
  console.error('联调失败:', e.message);
  process.exit(2);
});
