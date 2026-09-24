#!/usr/bin/env node
/**
 * 管理端「上架同步」UI 闭环验收（ADM-S07 / ADM-S08 / ADM-S09 + ADM-S02）
 *
 * 用法：node tools/publish-e2e.mjs [baseUrl] [outDir] [phone]
 *   baseUrl 默认 http://127.0.0.1:5174（aap-admin dev server）
 *   outDir  默认 evidence/publish-e2e
 *   phone   默认 13800000221（dev 库 SUPER_ADMIN）
 *
 * 与 admin-acceptance.mjs 的分工：
 *   前者证「页面渲染 + 入口能点开 + 字段齐全」；
 *   本脚本证**闭环真的走完**：在 UI 上发起上架 → 执行 → 渠道真出现在绑定表里。
 *   两者都要跑：只有前者会漏掉「按钮在、点了没反应」；只有后者会漏掉「入口没了」。
 *
 * 为什么必须真浏览器：ADM-S07/S08/S09 接线的意义就是「管理端能操作上架」，
 * 接口层已由后端契约测试（SyncPublishContractTest 7/7）与 tools/biz-closure-e2e.py
 * 覆盖 —— 再写一个纯接口脚本等于重复，证不到 UI 这一半（技能里登过的盲区）。
 *
 * 幂等：每次用带时间戳的渠道名 `AAP-UI-<epoch>`（ADM-S08 幂等键含 channel_name），
 * 故重复跑不会复用旧任务、也不会撞唯一索引；上游是本地桩（127.0.0.1:9911），多建渠道无害。
 *
 * 证据脱敏：写盘前按键名 + JWT 形状替换成 <redacted len=N>（机器判据，不靠人眼）。
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:5174';
const OUT = process.argv[3] || 'evidence/publish-e2e';
const PHONE = process.argv[4] || '13800000221';
const HEADLESS = process.env.AAP_HEADLESS === '1';

mkdirSync(OUT, { recursive: true });

const rows = [];
const record = (name, ok, detail = '') => {
  rows.push({ name, ok, detail });
  console.log(`  ${ok ? '✓' : '✗'} ${name}${detail ? ` — ${detail}` : ''}`);
};

const JWT_RE = /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g;
const SECRET_KEY = /^(token|access_token|refresh_token|api_key|apikey|authorization|password|secret|credential|api_key_cipher|password_hash)$/i;

function redact(value) {
  if (typeof value === 'string') return value.replace(JWT_RE, (m) => `<redacted len=${m.length}>`);
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = SECRET_KEY.test(k) ? `<redacted len=${String(v ?? '').length}>` : redact(v);
    return out;
  }
  return value;
}

/**
 * 同源 fetch：带登录 token 直接打后端（经 dev server 代理），用于「页面之外」的事实核对。
 * ⚠️ 后端信封是 `{code, message, data}`（前端 `request()` 会剥掉外层，脚本直连**不会**）——
 *    这里统一剥到 `data`，否则 `body.items` 全是 undefined，会被误读成「库里没有数据」。
 */
async function api(page, path) {
  return page.evaluate(async (p) => {
    const res = await fetch(p, { headers: { Authorization: `Bearer ${localStorage.getItem('aap_admin_token')}` } });
    const raw = await res.json().catch(() => null);
    return { status: res.status, code: raw?.code ?? null, body: raw?.data ?? raw, raw };
  }, path);
}

async function login(page) {
  // 频控：同一手机号 60s 内二次索码 → 429 E-1903。实测过，所以这里显式等待后重试一次，
  // 并把「本轮是否吃频控」写进证据（否则会被读成「登录坏了」）。
  for (let attempt = 1; attempt <= 2; attempt++) {
    await page.goto(BASE, { waitUntil: 'domcontentloaded' });
    await page.locator('[data-testid="phone"]').waitFor({ state: 'visible', timeout: 25000 });
    const captcha = (await page.locator('[data-testid="captcha-text"]').innerText()).trim();
    await page.locator('[data-testid="phone"]').fill(PHONE);
    await page.locator('[data-testid="captcha"]').fill(captcha);

    const smsPromise = page.waitForResponse((r) => r.url().includes('/auth/sms/send'), { timeout: 15000 });
    await page.locator('[data-testid="sms-btn"]').click();
    let smsCode = null;
    try {
      smsCode = (await (await smsPromise).json())?.code ?? null;
    } catch {
      /* 响应没抓到：下面按拿不到码处理 */
    }
    if (smsCode === 'E-1903' && attempt === 1) {
      console.log('     · 命中短信频控 E-1903，等 65s 后重试一次');
      await page.waitForTimeout(65000);
      continue;
    }
    if (smsCode !== '0') return { ok: false, note: `取码失败 code=${smsCode}`, attempts: attempt };

    let devCode = '';
    try {
      await page.locator('[data-testid="dev-code"]').waitFor({ state: 'visible', timeout: 8000 });
      devCode = (await page.locator('[data-testid="dev-code"]').innerText()).replace(/\D/g, '');
    } catch {
      /* 生产不回显 */
    }
    if (!devCode) return { ok: false, note: '未拿到 dev 回显码（后端需 AAP_SMS_EXPOSE_CODE=true）', attempts: attempt };

    await page.locator('[data-testid="sms-code"]').fill(devCode);
    await page.locator('[data-testid="submit"]').click();
    try {
      await page.waitForFunction(() => !!localStorage.getItem('aap_admin_token'), null, { timeout: 15000 });
      return { ok: true, attempts: attempt };
    } catch {
      const err = await page.locator('[data-testid="login-error"]').innerText().catch(() => '(无提示)');
      return { ok: false, note: `登录未落地：${err}`, attempts: attempt };
    }
  }
  return { ok: false, note: '频控重试后仍未登录', attempts: 2 };
}

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: HEADLESS, args: ['--start-maximized'] });
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, locale: 'zh-CN' });
  const page = await context.newPage();

  const calls = [];
  const consoleErrors = [];
  page.on('response', async (res) => {
    const url = res.url();
    if (!url.includes('/api/v1/')) return;
    let code = null;
    let body = null;
    try {
      body = await res.json();
      code = body?.code ?? null;
    } catch {
      /* 非 JSON 响应（如文件流） */
    }
    const entry = {
      method: res.request().method(),
      url: url.split('/api/v1')[1] || url,
      status: res.status(),
      code
    };
    if (body && typeof body === 'object') entry.body = redact(body);
    calls.push(entry);
  });
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text());
  });
  page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`));

  const finish = async (note = '') => {
    const pass = rows.filter((r) => r.ok).length;
    const fail = rows.length - pass;
    console.log(`\n${'─'.repeat(78)}`);
    console.log(`UI 上架闭环：通过 ${pass}，失败 ${fail}${note ? ` ｜ ${note}` : ''}`);
    for (const r of rows.filter((x) => !x.ok)) console.log(`  ✗ ${r.name} — ${r.detail}`);
    writeFileSync(
      join(OUT, 'publish-e2e.json'),
      JSON.stringify(redact({ base: BASE, phone: PHONE, rows, calls, consoleErrors }), null, 2),
      'utf8'
    );
    console.log(`明细已写入 ${join(OUT, 'publish-e2e.json')}`);
    await browser.close();
    return fail ? 1 : 0;
  };

  console.log(`UI 上架闭环验收  base=${BASE}  账号=${PHONE}  浏览器=本地Chrome(${HEADLESS ? '无头' : '有头'})\n`);

  // ── 0. 登录（鉴权失败 ⇒ 本轮无效，必须显式退出，不能落成与正常轮同形的证据） ──
  const auth = await login(page);
  record('超管登录', auth.ok, auth.ok ? `第 ${auth.attempts} 次取码成功` : auth.note);
  if (!auth.ok) return finish('本轮无效：未登录，后续步骤未执行');

  // ── 1. 找「已人工确认」的编译产物（闸门③ 的前置，不绕过） ──
  const comp = await api(page, '/api/v1/admin/compilations?page=1&pageSize=50');
  const confirmed = (comp.body?.items ?? []).find((c) => c.gate_status === 'CONFIRMED' && c.provider_id);
  record(
    '找到 gate_status=CONFIRMED 的编译产物',
    !!confirmed,
    confirmed
      ? `compilation_id=${confirmed.compilation_id} provider_id=${confirmed.provider_id}`
      : `响应体=${JSON.stringify(comp.body)?.slice(0, 400)}`
  );
  if (!confirmed) {
    await page.screenshot({ path: join(OUT, 'no-confirmed-compilation.png'), fullPage: true });
    return finish('本轮无效：无已确认编译产物，闸门③ 无法通过（不是 UI 缺陷）');
  }

  const providers = await api(page, '/api/v1/admin/providers?page=1&pageSize=100');
  const provider = (providers.body?.items ?? []).find((p) => String(p.id) === String(confirmed.provider_id));
  const providerLabel = provider?.company_name || provider?.provider_code || String(confirmed.provider_id);
  record('解析供应商显示名', !!provider, `provider_id=${confirmed.provider_id} → ${providerLabel}`);

  // ── 2. 进同步页，点「立即同步」打开上架对话框 ──
  await page.goto(`${BASE}/#/sync`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="btn-sync-now"]', { timeout: 20000 });
  await page.click('[data-testid="btn-sync-now"]');
  await page.waitForSelector('[data-testid="publish-dialog"]', { timeout: 8000 });
  record('打开「发起上架同步」对话框', true);

  // 供应商：el-select（filterable）的 `data-testid` 落在**宿主 div** 上，不像 el-input 那样透传到内层 input，
  // 直接 fill 宿主报 "Element is not an <input>"；而且 fill 不触发键盘事件时过滤不会刷新。
  // 实测可行路径：点开 → 在内层 input 上**逐字键入**（触发 input 事件）→ 点浮层里可见的项。
  // 值的读取也不能看宿主 innerText（为空），要看 `.el-select__selected-item`。
  const channelName = `AAP-UI-${Date.now()}`;
  const provSel = page.locator('[data-testid="publish-provider"]');
  await provSel.click();
  await page.waitForTimeout(500);
  try {
    await provSel.locator('input').first().pressSequentially(providerLabel.slice(0, 8), { delay: 45 });
  } catch {
    /* 无 filterable 输入框：直接走下面的选项点击 */
  }
  await page.waitForTimeout(900);
  // 用**文本精确匹配**定位选项（不取 first()：页面上其它 el-select 的浮层也在同一个全局容器里，
  // 取第一个可见项可能点到别的下拉的选项，症状是「点了没反应」而不是报错）。
  const opt = page.locator('.el-select-dropdown__item:visible', { hasText: providerLabel }).first();
  if (await opt.count()) {
    await opt.click();
  } else {
    const sample = (await page.locator('.el-select-dropdown__item:visible').allInnerTexts()).slice(0, 8);
    record('下拉候选诊断', false, `未找到含「${providerLabel}」的项；可见项=${sample.join(' | ') || '(空)'}`);
  }
  await page.waitForTimeout(500);
  const chosen = (
    await page.locator('[data-testid="publish-provider"] .el-select__selected-item').allInnerTexts()
  )
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
  record('供应商下拉选中', !!chosen, `下拉显示="${chosen}"`);
  if (!chosen) {
    await page.screenshot({ path: join(OUT, 'provider-select-failed.png'), fullPage: true });
    return finish('本轮中断：供应商未选中（前端会拦住提交，不会发出 ADM-S08）');
  }

  await page.locator('[data-testid="publish-compilation"]').fill(String(confirmed.compilation_id));
  await page.locator('[data-testid="publish-channel-name"]').fill(channelName);
  record('填写表单（编译产物 / 唯一渠道名）', true, `channel_name=${channelName}`);

  const beforeCreate = calls.length;
  await page.click('[data-testid="publish-submit"]');
  await page.waitForTimeout(2500);
  const createCall = calls.slice(beforeCreate).find((c) => c.url.startsWith('/admin/sync/tasks') && c.method === 'POST');
  record(
    'ADM-S08 发起上架同步',
    createCall?.code === '0',
    createCall ? `POST ${createCall.url} → ${createCall.status} code=${createCall.code}${createCall.code !== '0' ? `（${createCall.body?.message ?? ''}）` : ''}` : '未发出请求'
  );
  if (createCall?.code !== '0') {
    await page.screenshot({ path: join(OUT, 'create-failed.png'), fullPage: true });
    return finish(`本轮中断：ADM-S08 未成功（code=${createCall?.code ?? '-'}），未执行上架`);
  }
  // ⚠️ 事件里存的是**整个信封** `{code,message,data}`（前端 `request()` 才剥壳，脚本直连没有）
  const taskPayload = createCall.body?.data ?? createCall.body ?? {};
  const taskId = taskPayload.id || taskPayload.task_id;
  const taskNo = taskPayload.task_no ?? '';
  record('拿到任务号', !!taskId, `task_no=${taskNo || '(空)'} task_id=${taskId}`);

  // ── 3. 在任务表找到该任务行，点「执行」并确认（ADM-S09 真写上游） ──
  await page.waitForTimeout(1200);
  const rowSelector = taskNo ? `tr:has-text("${taskNo}")` : 'tbody tr';
  let rowFound = false;
  try {
    await page.waitForSelector(rowSelector, { timeout: 8000 });
    rowFound = true;
  } catch {
    /* 表格可能未刷新到该行 */
  }
  record(
    '任务表出现新建任务行',
    rowFound,
    rowFound ? (taskNo ? `匹配 ${taskNo}` : 'task_no 为空，按首行兜底定位') : '未在表格中找到该任务号'
  );

  const beforeExec = calls.length;
  if (rowFound) {
    await page.locator(`${rowSelector} [data-testid="task-execute"]`).first().click();
    // ElMessageBox 二次确认
    try {
      await page.waitForSelector('.el-message-box__btns .el-button--primary', { timeout: 6000 });
      await page.click('.el-message-box__btns .el-button--primary');
      record('写操作二次确认弹窗出现并确认', true);
    } catch {
      record('写操作二次确认弹窗出现并确认', false, '未出现确认框');
    }
    await page.waitForTimeout(3000);
  } else {
    // 表格没渲染出来也不能静默跳过：直接用任务号点详情刷新一次再试
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    try {
      await page.waitForSelector(rowSelector, { timeout: 8000 });
      await page.locator(`${rowSelector} [data-testid="task-execute"]`).first().click();
      await page.waitForSelector('.el-message-box__btns .el-button--primary', { timeout: 6000 });
      await page.click('.el-message-box__btns .el-button--primary');
      await page.waitForTimeout(3000);
    } catch {
      /* 下面用接口流水判：没点成就不该有 execute 调用 */
    }
  }
  const execCall = calls.slice(beforeExec).find((c) => c.url.includes('/execute') && c.method === 'POST');
  record(
    'ADM-S09 执行上架',
    execCall?.code === '0',
    execCall ? `POST ${execCall.url} → ${execCall.status} code=${execCall.code}` : '未发出 execute 请求（UI 未点中？）'
  );

  // ── 4. 独立核对事实（不信 UI 文案）：绑定表里该渠道真的存在且已启用 ──
  const bindings = await api(page, '/api/v1/admin/channel-bindings?page=1&pageSize=100');
  const binding = (bindings.body?.items ?? []).find((b) => b.channel_name === channelName);
  record(
    '渠道绑定表出现该渠道',
    !!binding,
    binding ? `binding_id=${binding.binding_id} channel_id=${binding.channel_id} status=${binding.status}` : `未找到 channel_name=${channelName}`
  );
  record(
    '渠道状态已启用且回读一致',
    !!binding && binding.status === 'ENABLED' && !!binding.last_readback_hash,
    binding ? `status=${binding.status} last_synced_at=${binding.last_synced_at ?? '—'} readback=${binding.last_readback_hash ? '有' : '无'}` : '无绑定行'
  );

  // 任务的终态（从详情接口读，不看弹窗文案）
  const detail = await api(page, `/api/v1/admin/sync/tasks/${encodeURIComponent(taskId)}`);
  const finalTask = detail.body?.task ?? detail.body;
  const okTask = !!finalTask && !['FAILED', 'MANUAL'].includes(finalTask.status);
  record(
    '任务终态非失败',
    okTask,
    finalTask
      ? `status=${finalTask.status} readback_equal=${finalTask.readback_equal} operations=${(finalTask.operations ?? []).length} 条`
      : `详情响应 ${detail.status} code=${detail.code}`
  );

  // ── 5. 页面侧判据：无未放行错误码、无控制台报错、样式仍在 ──
  // ⚠️ 登录阶段的短信频控 429 E-1903 属**已知且预期**（同一身份 60s 内二次索码，脚本自己也等了 65s 才重试）——
  //    显式声明放行，不把它算成产品失败；其它任何非 0 业务码照旧失败。
  const ALLOWED = [/^\/auth\/sms\/send/];
  const bad = calls.filter((c) => c.code !== '0' && c.code !== null && !ALLOWED.some((r) => r.test(c.url)));
  const allowedCalls = calls.filter((c) => c.code !== '0' && c.code !== null && ALLOWED.some((r) => r.test(c.url)));
  record(
    '无异常业务码',
    bad.length === 0,
    bad.length
      ? bad.map((b) => `${b.url}→${b.code}`).join('；')
      : `${calls.length} 次调用全部 code=0${allowedCalls.length ? `（含已声明放行 ${allowedCalls.map((a) => a.code).join('/')}：短信频控）` : ''}`
  );
  // 控制台只收真正的 JS 异常：429 那条是浏览器对已知频控请求的 resource 报错，与接口层重复计数
  const realConsoleErrors = consoleErrors.filter((t) => !/Failed to load resource/.test(t));
  record('控制台 0 报错', realConsoleErrors.length === 0, realConsoleErrors[0] ?? `（已忽略 ${consoleErrors.length} 条资源加载类噪声）`);

  const styles = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    const bar = document.querySelector('[data-testid="btn-sync-now"]');
    return {
      tokenPage: root.getPropertyValue('--c-page').trim(),
      btnRadius: bar ? getComputedStyle(bar).borderRadius : null,
      btnBg: bar ? getComputedStyle(bar).backgroundColor : null
    };
  });
  record('同步页样式未退化', !!styles.tokenPage && !!styles.btnBg, `--c-page=${styles.tokenPage} 主按钮=${styles.btnBg}`);

  await page.screenshot({ path: join(OUT, 'after-publish.png'), fullPage: true });
  return finish();
}

main()
  .then((code) => process.exit(code))
  .catch(async (e) => {
    console.error('UI 上架闭环失败:', e.message);
    process.exit(2);
  });
