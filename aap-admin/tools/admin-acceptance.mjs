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
  },
  '/models': {
    // ⚠️ 本页判据已随 D-ADM-3 修复而更新（原先要求「缺口横幅 + 放行 E-1501」）。
    //    D-ADM-3 已由 V9 迁移 + /admin/catalog/* 解开（后端运行态 24/24 验证），
    //    本页改为真实读模型目录，**不再有 E-1501 放行** —— 出现任何错误码都算回归。
    // ⚠️ 按用户口径移除了「批量管理」与「新增模型」两个按钮（与设计稿 page-3 不同），
    //    故这里**不再断言**它们存在；同时反向断言它们**不该出现**，
    //    以免以后有人「照设计稿还原」又把它们加回来。
    require: ['[data-testid="model-kpi"]', '[data-testid="btn-add-vendor"]'],
    textAny: ['按厂商分组', '接入厂商', '已接入模型', '启用中模型'],
    mustMatch: [
      /接入厂商/,
      /已接入模型/,
      /启用中模型/,
      // 分页：设计稿 page-3 有分页栏。⚠️ 曾一度被误读成「不要分页」并加了 mustNotMatch
      // 反向断言 —— 已删除；用户原话实为**缺陷报告**（缺分页功能），故这里改成正向断言。
      /共 \d+ 家厂商 · 当前第 \d+ \/ \d+ 页/
    ],
    mustNotMatch: [/批量管理/, /^新增模型$/m],
    // 抽屉必须真能打开并渲染设计稿字段。
    // 「新增模型」已按用户口径移除一级入口 → 模型抽屉改为**可选**：
    //   页面上存在厂商行内「添加模型」时才校验（空目录时不可达，不算失败）。
    drawers: [
      {
        open: '[data-testid="btn-add-vendor"]',
        expect: [
          '[data-testid="drawer-vendor"]',
          '[data-testid="v-name"]',
          '[data-testid="v-key"]',
          '[data-testid="v-type"]',
          '[data-testid="v-baseurl"]',
          '[data-testid="v-save"]'
        ]
      },
      {
        open: '[data-testid="btn-add-model-inline"]',
        optional: true,
        expect: [
          '[data-testid="drawer-model"]',
          '[data-testid="m-vendor"]',
          '[data-testid="m-name"]',
          '[data-testid="m-uid"]',
          '[data-testid="m-save"]'
        ]
      }
    ]
  },
  // 页 4：供应商管理（page-4-pc）。判据必须能区分「真取到数」与「只有壳」：
  // 表头「接入线路 / 档案完整度」是设计稿独有列，骨架页没有。
  '/providers': {
    require: ['[data-testid="provider-count"]', '[data-testid="provider-table"]', '[data-testid="page-summary"]'],
    textAny: ['新增供应商', '接入线路', '档案完整度'],
    mustMatch: [/共 \d+ 家/, /共 \d+ 条，每页 \d+ 条/]
  },
  // 页 5：检测中心（page-5-pc）。任务监控**无列表接口**（D-ADM-5）→ 页面必须显式声明缺口；
  // 真实能力是「人工放行（DET-06）」与「检测项配置（ADM-CFG01…05）」两张卡。
  '/detection': {
    require: ['[data-testid="detection-gap-banner"]', '[data-testid="detection-kpi"]', '[data-testid="cfg-table"]'],
    textAny: ['检测项配置', '人工放行', '无数据来源'],
    mustMatch: [/D-ADM-5/]
  },
  // 页 8：new-api 同步（page-8-pc）。上游模型清单未配置 ACTIVE 端点 → 预期 E-1501（已登记形态）；
  // 页面把它渲染成「接口异常」标签，属**被处理的状态**。
  '/sync': {
    require: ['[data-testid="sync-kpi"]', '[data-testid="binding-table"]', '[data-testid="sync-task-table"]'],
    textAny: ['渠道价格同步状态', '同步任务与日志', '渠道总数'],
    allowCodes: ['E-1501']
  }
};

const rows = [];
const record = (name, ok, detail = '') => {
  rows.push({ name, ok, detail });
  console.log(`  ${ok ? '✓' : '✗'} ${name}${detail ? ` — ${detail}` : ''}`);
};

/**
 * 证据落盘前**必须**脱敏（真实教训，2026-09-19 夜）。
 *
 * 验收脚本把后端响应体原样写进证据 JSON，其中 `/auth/sms/login` 的响应含
 * **真实 access token（307 字符 JWT）与 refresh token（43 字符）** ——
 * 一旦入库就等于把可用凭据写进 git 历史。而**看日志根本发现不了**：
 * 工具输出层会把 JWT 打码显示成 `eyJhbG...xxxx`，肉眼看是「已经脱敏了」。
 * 所以守卫必须落在**写文件这一步**（机器判据），而不是靠人眼。
 *
 * 规则：键名命中 token/secret/password/apikey/authorization 且长度 ≥16 的值，
 * 以及任何真 JWT 形状的字符串，一律换成 `<redacted len=N>`（保留长度作为证据）。
 * 独立复核：`python tools/evidence-secrets.py`（命中即 exit 1）。
 */
const SECRET_KEY = /(token|secret|password|passwd|api_?key|authorization|credential)/i;
const JWT_SHAPE = /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g;
const mask = (v) => `<redacted len=${String(v).length}>`;

function redact(node) {
  if (Array.isArray(node)) return node.map(redact);
  if (node && typeof node === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(node)) {
      out[k] = typeof v === 'string' && SECRET_KEY.test(k) && v.length >= 16 && !v.startsWith('<redacted')
        ? mask(v)
        : redact(v);
    }
    return out;
  }
  if (typeof node === 'string') return node.replace(JWT_SHAPE, mask);
  return node;
}

/**
 * 全局样式门禁（每页都查）。
 *
 * 教训：判据只查「DOM 节点 + 文本」时，**CSS 整块失效也能全绿** ——
 * 实测 tokens.css 的文件头注释里出现了「星号紧跟斜杠」把注释提前终止，
 * 紧随其后的 `:root{...}` 整块被丢弃 → 设计令牌全丢、页面毫无样式，
 * 而当时 14 条判据全部通过。所以样式必须进判据。
 *
 * 判据用**计算样式**（不是看有没有 class）：
 *   - 页面底色 = slate-100 rgb(241,245,249)
 *   - 正文字号 = 12px（令牌 --fs-base）
 *   - 侧栏底色 = slate-900 rgb(15,23,42)
 *   - 卡片圆角 = 14px（令牌 --r-card）且白底
 */
async function checkGlobalStyles(page) {
  return page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    const cs = (sel, prop) => {
      const e = document.querySelector(sel);
      return e ? getComputedStyle(e)[prop] : null;
    };
    return {
      tokenPage: root.getPropertyValue('--c-page').trim(),
      bodyBg: cs('body', 'backgroundColor'),
      bodyFontSize: cs('body', 'fontSize'),
      sidebarBg: cs('.sidebar', 'backgroundColor'),
      cardRadius: cs('.aap-card', 'borderRadius'),
      cardBg: cs('.aap-card', 'backgroundColor')
    };
  });
}

function styleProblems(s) {
  const p = [];
  if (!s.tokenPage) p.push('CSS 变量 --c-page 未定义（tokens.css 未生效 / 注释提前终止）');
  if (s.bodyBg !== 'rgb(241, 245, 249)') p.push(`页面底色异常：${s.bodyBg}（应为 rgb(241,245,249)）`);
  if (s.bodyFontSize !== '12px') p.push(`正文字号异常：${s.bodyFontSize}（应为 12px）`);
  if (s.sidebarBg !== 'rgb(15, 23, 42)') p.push(`侧栏底色异常：${s.sidebarBg}（应为 rgb(15,23,42)）`);
  if (s.cardRadius !== '14px') p.push(`卡片圆角异常：${s.cardRadius}（应为 14px）`);
  if (s.cardBg !== 'rgb(255, 255, 255)') p.push(`卡片底色异常：${s.cardBg}（应为白）`);
  return p;
}

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
    // 浏览器级的资源加载失败（favicon / 非 2xx 的 XHR）会在这里重复出现，
    // 而**接口层面的真实结果已由 response 监听器精确捕获**（含业务码）。
    // 两者都算会重复计数，并把「已声明的预期错误码」也误报成控制台报错 → 只认后者。
    if (/favicon/i.test(t) || /Failed to load resource/i.test(t)) return;
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

  // 登录页也要过样式门禁（此时已在后台页，回头验一次登录页样式）
  await page.goto(`${BASE}/#/login`, { waitUntil: 'domcontentloaded' });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
  const loginStyle = await checkGlobalStyles(page);
  const loginStyleBad = styleProblems(loginStyle);
  record('全局样式（登录页）', loginStyleBad.length === 0, loginStyleBad.join(' | ') || `--c-page=${loginStyle.tokenPage}，body=${loginStyle.bodyBg}/${loginStyle.bodyFontSize}`);

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

    const gate = CONTENT_GATES[route];
    const seg = calls.slice(before).filter((c) => c.url.includes('/api/v1/'));
    const allow = new Set(gate?.allowCodes ?? []);
    const bad = seg.filter((c) => c.code !== '0' && c.code !== null && !allow.has(String(c.code)));
    const allowed = seg.filter((c) => c.code !== '0' && c.code !== null && allow.has(String(c.code)));
    const errs = [...errors];

    // 业务内容判据：已实现页必须渲染出业务特征；未实现页必须明确带「待实现」徽章
    const gateState = await page.evaluate(
      ({ require: req, textAny, must, mustNot }) => {
        const missing = (req || []).filter((s) => !document.querySelector(s));
        const text = document.body.innerText || '';
        const hitAny = !textAny || textAny.some((t) => text.includes(t));
        // mustMatch：用**正则**判文案形态（例如「共 7 家」「共 7 条，每页 20 条」），
        // 比固定字符串更抗数据变化，同时能抓住「渲染了但没取到数」（共 0 家 也会命中，
        // 所以它只用来判「渲染形态」，取数真假由接口流水与下面的 allowCodes 判）。
        const mustMiss = (must || []).filter((src) => !new RegExp(src).test(text));
        // mustNotMatch：**反向**判据 —— 文案不该出现（例如用户口径要求厂商分组不分页，
        // 就断言页面里没有「共 N 家厂商 · 当前第 x / y 页」这类分页文案）
        const mustNotHit = (mustNot || []).filter((src) => new RegExp(src).test(text));
        const root = getComputedStyle(document.documentElement);
        const cs = (sel, prop) => {
          const e = document.querySelector(sel);
          return e ? getComputedStyle(e)[prop] : null;
        };
        return {
          missing,
          mustMiss,
          mustNotHit,
          hitAny,
          isStub: text.includes('待实现'),
          styles: {
            tokenPage: root.getPropertyValue('--c-page').trim(),
            bodyBg: cs('body', 'backgroundColor'),
            bodyFontSize: cs('body', 'fontSize'),
            sidebarBg: cs('.sidebar', 'backgroundColor'),
            cardRadius: cs('.aap-card', 'borderRadius'),
            cardBg: cs('.aap-card', 'backgroundColor')
          }
        };
      },
      { require: gate?.require, textAny: gate?.textAny, must: gate?.mustMatch?.map((r) => r.source), mustNot: gate?.mustNotMatch?.map((r) => r.source) }
    );

    const problems = [];
    const styleBad = styleProblems(gateState.styles ?? {});
    if (styleBad.length) problems.push(`样式异常：${styleBad.join('；')}`);
    if (state.hasLoginForm) problems.push('被踢回登录页（401 未续期）');
    if (state.blank) problems.push(`页面空白（textLen=${state.textLen}）`);
    if (!state.hasNav) problems.push('外壳未渲染（无侧栏）');
    if (state.h1 !== title) problems.push(`标题不符：期望「${title}」实际「${state.h1}」`);
    if (gate) {
      if (gateState.missing.length) problems.push(`缺少业务节点：${gateState.missing.join('、')}`);
      if (!gateState.hitAny) problems.push(`未渲染出业务文案（期望含 ${gate.textAny.join(' / ')} 之一）`);
      if (gateState.mustMiss?.length) problems.push(`文案形态不符：${gateState.mustMiss.join('、')}`);
      if (gateState.mustNotHit?.length) problems.push(`出现了不该有的文案：${gateState.mustNotHit.join('、')}`);
      if (gateState.isStub) problems.push('已登记为已实现，但仍显示「待实现」徽章');
    } else if (!gateState.isStub) {
      problems.push('尚未实现却缺少「待实现」徽章（状态不明，无法区分完成度）');
    }
    if (bad.length) problems.push(`异常接口 ${bad.length} 条：${bad.map((b) => `${b.method} ${b.url.split('/api/v1')[1]?.split('?')[0]} → ${b.code} ${b.message ?? ''}`).join('；')}`);
    if (errs.length) problems.push(`控制台报错 ${errs.length} 条：${errs[0]}`);

    // 抽屉校验（可选，声明在 gate.drawers）：点开抽屉，确认设计稿要求的字段真的渲染出来。
    // 有这一条才能区分「按钮存在」与「按钮真能打开表单」—— 只查按钮存在会漏掉一大类假完成。
    // optional: true 表示入口在空数据下不可达（如无厂商时没有行内「添加模型」），跳过不算失败。
    let drawerNote = '';
    for (const d of gate?.drawers ?? []) {
      const has = await page.evaluate((sel) => !!document.querySelector(sel), d.open);
      if (!has) {
        if (d.optional) {
          console.log(`     · 抽屉入口 ${d.open} 不存在（optional，跳过）`);
          continue;
        }
        problems.push(`抽屉入口不存在：${d.open}`);
        continue;
      }
      try {
        await page.click(d.open, { timeout: 8000 });
        // 抽屉有开合动画，等选择器出现而不是写死 sleep
        await page.waitForFunction(
          (sels) => sels.every((s) => document.querySelector(s)),
          d.expect,
          { timeout: 8000 }
        );
        const miss = await page.evaluate(
          (sels) => sels.filter((s) => !document.querySelector(s)),
          d.expect
        );
        if (miss.length) problems.push(`抽屉 ${d.open} 缺少字段：${miss.join('、')}`);
        else drawerNote += `；抽屉 ${d.open} 字段齐全（${d.expect.length} 项）`;
        // 关掉抽屉，避免影响后续页面截图
        await page.keyboard.press('Escape');
        await page.waitForTimeout(400);
      } catch (e) {
        problems.push(`抽屉 ${d.open} 未打开或字段未渲染：${String(e.message).split('\n')[0]}`);
      }
    }

    await page.screenshot({ path: join(OUT, `page${route.replace(/\//g, '-')}.png`), fullPage: true });
    record(
      `${route}  ${title}`,
      problems.length === 0,
      problems.length
        ? problems.join(' | ')
        : `${gate ? '业务内容已渲染' : '骨架（含待实现徽章）'}；接口 ${seg.length} 次${
            allowed.length ? `（含已声明放行 ${allowed.map((a) => a.code).join('/')}）` : ''
          }${drawerNote}，控制台 0 报错`
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
    JSON.stringify(redact({ base: BASE, phone: PHONE, headless: HEADLESS, rows, calls }), null, 2),
    'utf8'
  );
  console.log(`\n明细已写入 ${join(OUT, 'admin-acceptance.json')}`);
  return browser.close().then(() => process.exit(fail ? 1 : 0));
}

main().catch(async (e) => {
  console.error('联调失败:', e.message);
  process.exit(2);
});
