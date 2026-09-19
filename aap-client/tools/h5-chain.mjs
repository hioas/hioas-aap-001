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

/** 后端基址（Node 侧直调用） */
const API_BASE = process.env.AAP_API_BASE || 'http://127.0.0.1:8084/api/v1';
/** 管理端账号：H5/小程序应用是**供应商端**，管理动作（放行/审核/签发）不在应用里 → 只能走 API */
const ADMIN_PHONE = process.env.AAP_ADMIN_PHONE || '13900000001';

/** Node 侧直调后端；任何异常都收敛成 {code,message}，不抛（让步骤给出可读失败） */
async function apiCall(method, path, token, body) {
  const res = await fetch(API_BASE + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return { code: '?', message: text.slice(0, 200), httpStatus: res.status };
  }
}

let _adminToken = '';
/**
 * 管理端登录（真实验证码流程，不绕库）。
 *
 * 记忆化：SMS 有 60s 冷却，同一轮链路里多次需要管理端会话时不能重复发码。
 */
async function adminLogin() {
  if (_adminToken) return _adminToken;
  const send = await apiCall('POST', '/auth/sms/send', null, { phone: ADMIN_PHONE, captcha: 'A7K9' });
  const code = send?.data?.dev_code;
  if (!code) {
    throw new Error(`管理端取码失败：${send.code} ${send.message}（检查 AAP_SMS_EXPOSE_CODE 是否开、是否 60s 冷却）`);
  }
  const login = await apiCall('POST', '/auth/sms/login', null, { phone: ADMIN_PHONE, smsCode: code });
  const token = login?.data?.token;
  if (!token) throw new Error(`管理端登录失败：${login.code} ${login.message}`);
  _adminToken = token;
  return token;
}

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
   * ⑪ 缺陷 1 的**特征化断言**：不干预时检测任务确实永停 QUEUED。
   *
   * 这是「已知缺陷」的证据步，不是「期望行为」——它现在**故意断言「卡住」**：
   * 一旦有人补上检测执行器，这一步会红，提示把它改成「任务应推进」。
   * 只有状态码的联调会把它判成通过（HTTP 200 + code=0），所以必须断言业务结果。
   */
  await step('⑪ 缺陷1 证据：不干预时检测任务永停 QUEUED（特征化断言）', async () => {
    const jobs = called('GET', '/detection-jobs/').filter((c) => !c.url.includes('/results'));
    assert(jobs.length > 0, '检测进行中页未查询过 detection-jobs');
    const last = jobs[jobs.length - 1];
    const st = last.data?.status ?? '(无 status 字段)';
    const results = called('GET', '/results');
    const total = results.length ? results[results.length - 1].data?.total : undefined;
    assert(
      st === 'QUEUED' || st === 'PENDING',
      `任务状态是 ${st}（不是 QUEUED）→ 检测执行器可能已被补上，请把本步改成「任务应推进」`
    );
    assert(
      (total ?? 0) === 0,
      `results.total=${total}（不是 0）→ 分项结果已有数据，本步假设不成立，请更新`
    );
    return `status=${st} · started_at=${last.data?.started_at ?? 'null'} · results.total=${total}`
      + ` ← 检测执行器缺失（引擎为外部组件，本仓库只留 recordProbeResults 回调口）`;
  });

  // ═══ ③ 管理端 DET-06 人工放行（后端**已设计**的正规出口，不改后端）═══
  let releasedJobId = '';

  await step('⑫ 管理端 DET-06 人工放行（真实鉴权 + 理由必填 + 审计）', async () => {
    const jobs = called('GET', '/detection-jobs/').filter((c) => !c.url.includes('/results'));
    const jobId = jobs[jobs.length - 1]?.url.match(/detection-jobs\/(\d+)/)?.[1];
    assert(jobId, '未能从检测页的请求里解析出 jobId');
    releasedJobId = jobId;

    const adminToken = await adminLogin();
    const res = await apiCall('POST', `/detection-jobs/${jobId}/release`, adminToken, {
      override_reason: 'H5 联调推进链路：检测执行器为外部引擎组件，本仓库无执行器，走 DET-06 正规人工放行'
    });
    assert(res.code === '0', `DET-06 放行失败：${res.code} ${res.message}`);
    return `jobId=${jobId} 已放行 → status=${res.data?.status ?? '?'}`;
  });

  await step('⑬ 放行后检测任务真的推进了（业务结果断言）', async () => {
    assert(releasedJobId, '上一步未拿到 jobId');
    // 必须用**供应商本人**的 token 读：DET-01…05 限供应商本人，管理端读会 404 E-1304
    // （实测踩过：用管理端 token 读 → data=null → status=undefined）
    const supplierToken = await cdp.eval(`localStorage.getItem('aap_token')`);
    assert(supplierToken, '浏览器 storage 里没有 aap_token，无法以供应商身份读任务');
    const job = await apiCall('GET', `/detection-jobs/${releasedJobId}`, supplierToken);
    const st = job.data?.status;
    assert(job.code === '0', `读检测任务失败：${job.code} ${job.message}`);
    assert(st && st !== 'QUEUED' && st !== 'PENDING', `放行后任务仍是 ${st} —— DET-06 未生效`);
    return `status=${st} · started_at=${job.data?.started_at ?? 'null'} · finished_at=${job.data?.finished_at ?? 'null'}`;
  });

  await step('⑭ 检测报告页在浏览器里渲染出内容', async () => {
    await goto('#/pages/report/index', /报告/);
    const t = await cdp.text();
    const reports = called('GET', '/reports');
    await cdp.shot(outDir, '12-report');
    assert(t.length >= 30, `报告页文本过短（${t.length} 字）→ 可能仍是空态`);
    return `${t.length} 字；GET /reports → ${reports.length ? `code=${reports[0].code}` : '本次未发'}`;
  });

  await step('⑮ 报告数据真实可取（业务结果断言，非状态码）', async () => {
    const supplierToken = await cdp.eval(`localStorage.getItem('aap_token')`);
    const list = await apiCall('GET', '/reports?page=1&pageSize=10', supplierToken);
    assert(list.code === '0', `GET /reports 失败：${list.code} ${list.message}`);
    const items = list.data?.items ?? list.data?.list ?? [];
    assert(items.length > 0, `报告列表为空（total=${list.data?.total ?? '?'}）—— 检测完成应产出报告（AC-18 1:1）`);
    const id = items[0].id ?? items[0].report_id;
    const one = await apiCall('GET', `/reports/${id}`, supplierToken);
    assert(one.code === '0', `GET /reports/{id} 失败：${one.code} ${one.message}`);
    const fields = Object.keys(one.data ?? {}).length;
    return `报告数=${items.length} · 首份 id=${id} · 详情字段=${fields}`;
  });

  // ═══ ④ 报价单创建（选主体 → 凭证 → 模型 → 定价 → 提交）═══
  // 坑：本页所有入口都是 `<view @tap>`，**CDP 合成鼠标事件点不动**（实测：
  //     点 new-quote 后 hash 不变）→ 一律走 clickUntil（内含 jsClick 兜底），
  //     判据用「目标状态是否出现」而不是「点过了」。
  await step('⑯ 报价单列表 →「新建报价」', async () => {
    await goto('#/pages/quotes/index', /报价/);
    const before = await cdp.eval('location.hash');
    const ok = await cdp.clickUntil(
      '[data-testid="new-quote"]',
      async () => (await cdp.eval('location.hash')) !== before,
      { tries: 4, gap: 700 }
    );
    assert(ok, `点「新建报价」未跳转（@tap 未响应），hash 仍是 ${before}`);
    assert(await cdp.waitForText(/新增报价单/, { timeoutMs: 10000 }), '未进入新增报价单页');
    await cdp.shot(outDir, '13-quote-models');
    return `落点=${await cdp.eval('location.hash')}`;
  });

  await step('⑰ 选报价主体 + 填报价单名称', async () => {
    const opened = await cdp.clickUntil(
      '[data-testid="subject-select"]',
      async () => (await cdp.eval(`document.querySelectorAll('[data-testid^="subject-option-"]').length`)) > 0,
      { tries: 3, gap: 700 }
    );
    assert(opened, '主体选择器未展开（subject-panel 没出现）');
    const optCount = await cdp.eval(`document.querySelectorAll('[data-testid^="subject-option-"]').length`);
    await cdp.clickUntil(
      '[data-testid^="subject-option-"]',
      async () => (await cdp.eval(`document.querySelectorAll('[data-testid="subject-panel"]').length`)) === 0,
      { tries: 3, gap: 600 }
    );
    const subject = await cdp.eval(`document.querySelector('[data-testid="subject-value"]')?.innerText.trim()`);

    const name = `联调H5-${Date.now() % 100000}`;
    const w = await cdp.setInput('[data-testid="name-input"]', name);
    assert(w === true, `报价单名称写入失败: ${w}`);
    await cdp.shot(outDir, '14-subject-name');
    return `主体=${subject ?? '?'}（面板选项 ${optCount} 个）；名称=${name}`;
  });

  await step('⑱ 选凭证 → 模型列表带出 → 全选模型', async () => {
    const opened = await cdp.clickUntil(
      '[data-testid="cred-select"]',
      async () => (await cdp.eval(`document.querySelectorAll('[data-testid^="cred-option-"]').length`)) > 0,
      { tries: 3, gap: 700 }
    );
    assert(opened, '凭证选择器未展开 —— 是否还没有「检测通过」的可用凭证？');
    const credCount = await cdp.eval(`document.querySelectorAll('[data-testid^="cred-option-"]').length`);
    await cdp.clickUntil(
      '[data-testid^="cred-option-"]',
      async () => (await cdp.eval(`document.querySelectorAll('[data-testid="cred-panel"]').length`)) === 0,
      { tries: 3, gap: 700 }
    );
    // 模型列表「按凭证实时带出」→ 轮询等它出来，再点全选
    let modelCount = 0;
    for (let i = 0; i < 10 && modelCount === 0; i++) {
      await sleep(900);
      modelCount = await cdp.eval(`document.querySelectorAll('[data-testid^="model-row-"]').length`);
    }
    assert(modelCount > 0, '选了凭证后模型列表仍为空（带不出模型）');
    // ⚠️ 本页（quote-models）的行 testid 是 `model-row-{name}`，`@tap` 挂在**行**上；
    //    `model-check-0-0` 是「接入凭证」页的 testid，点它会命中不存在的元素（实测踩过）。
    //    判据也必须解析**分子**：`已选 0 / 10` 里的分母 10 会让 /[1-9]/ 误判成已选中。
    const selectedCountNow = async () => {
      const t = await cdp.eval(`document.querySelector('[data-testid="chip-model-count"]')?.innerText || ''`);
      const m = /已选\s*(\d+)/.exec(t);
      return m ? Number(m[1]) : 0;
    };
    // 只勾第 1 个模型：定价页是**逐模型**定价的（一次一个 itemId），
    // 全选 10 个要点 10 轮，对「验证链路能通」没有额外价值。
    await cdp.clickUntil(
      '[data-testid^="model-row-"]',
      async () => (await selectedCountNow()) >= 1,
      { tries: 4, gap: 700 }
    );
    const selectedNum = await selectedCountNow();
    assert(selectedNum >= 1, `勾选模型未生效（已选 ${selectedNum}）`);
    const selected = await cdp.eval(`document.querySelector('[data-testid="chip-model-count"]')?.innerText.trim()`);
    const cred = await cdp.eval(`document.querySelector('[data-testid="cred-value"]')?.innerText.trim()`);
    await cdp.shot(outDir, '15-cred-models');
    return `凭证=${cred ?? '?'}（面板选项 ${credCount} 个）；模型行=${modelCount}；已选=${selected ?? '?'}`;
  });

  let savedQuoteId = '';

  await step('⑲ 保存报价单 → 断言 POST /quotes 与明细写入', async () => {
    const before = called('POST', '/quotes').length;
    await cdp.clickUntil(
      '[data-testid="btn-save"]',
      async () => called('POST', '/quotes').length > before,
      { tries: 6, gap: 900 }
    );
    await sleep(3500);
    await cdp.settle();
    const post = called('POST', '/quotes');
    const itemCalls = api().filter((c) => c.method === 'POST' && /\/quotes\/\d+\/items/.test(c.url));
    await cdp.shot(outDir, '16-quote-saved');
    assert(post.length > 0, '点「保存」后未发出 POST /quotes');
    assert(post[0].code === '0', `POST /quotes → ${post[0].code} ${post[0].message}`);
    assert(itemCalls.length > 0, '报价单已创建但未写入明细行（POST /quotes/{id}/items）');
    assert(itemCalls[0].code === '0', `写明细 → ${itemCalls[0].code} ${itemCalls[0].message}`);
    savedQuoteId = String(post[0].data?.id ?? '');
    assert(savedQuoteId, '未能从 POST /quotes 响应里取到报价单 id');
    return `POST /quotes code=0（id=${savedQuoteId}）；明细写入 code=${itemCalls[0].code}`;
  });

  await step('⑳ 模型定价 → 保存价格（PUT /quotes/items/{itemId}）', async () => {
    assert(savedQuoteId, '上一步未拿到报价单 id');
    await goto(`#/pages/model-pricing/index?quoteId=${savedQuoteId}`, /模型定价/);
    // ⚠️ 开关状态只能看 class：本页 checkbox 只有 :class="{'check--on': f.enabled}"，
    //    **没有 data-checked 属性**。且设计稿默认就启用了输入价/输出价 ——
    //    无条件点一下会把它们**关掉** → buildItemPayload 跳过未启用字段 → E-1001 输入价必填（V3）。
    const switchOn = async (field) =>
      (await cdp.eval(`(document.querySelector('[data-testid="check-${field}"]')?.className || '').includes('check--on')`)) === true;
    for (const [field, value] of [['input_price', '2.5'], ['output_price', '10']]) {
      if (!(await switchOn(field))) {
        await cdp.clickUntil(`[data-testid="check-${field}"]`, () => switchOn(field), { tries: 3, gap: 500 });
      }
      assert(await switchOn(field), `价格字段 ${field} 未能启用`);
      const w = await cdp.setInput(`[data-testid="price-${field}"]`, value);
      assert(w === true, `价格 ${field} 写入失败: ${w}`);
      // 回读要走**内层 input**：`price-*` 是 <uni-input> 宿主，宿主上的 .value 是 undefined
      const got = await cdp.eval(
        `(() => { const h = document.querySelector('[data-testid="price-${field}"]');` +
          ` const el = h && h.tagName === 'INPUT' ? h : (h && h.querySelector && h.querySelector('input'));` +
          ` return el ? el.value : null; })()`
      );
      assert(String(got) === value, `价格 ${field} 回读不一致: ${got}`);
    }
    await cdp.shot(outDir, '17-pricing');
    const before = api().filter((c) => c.method === 'PUT' && c.url.includes('/quotes/items/')).length;
    await cdp.clickUntil(
      '[data-testid="save-bottom"]',
      async () => api().filter((c) => c.method === 'PUT' && c.url.includes('/quotes/items/')).length > before,
      { tries: 6, gap: 900 }
    );
    await sleep(3000);
    await cdp.settle();
    const puts = api().filter((c) => c.method === 'PUT' && c.url.includes('/quotes/items/'));
    assert(puts.length > 0, '点「保存价格」后未发出 PUT /quotes/items/{itemId}');
    assert(puts[0].code === '0', `保存价格 → ${puts[0].code} ${puts[0].message}`);
    // 真判据：请求体里**必须真的带上输入价**。只看 code=0 会漏掉「价格没进请求体」
    // 这种假绿（服务端只在提交时才做 V3 必填校验，保存时可能放过）。
    const body = String(puts[0].postData ?? '');
    assert(/input_price/.test(body), `PUT 请求体未带 input_price：${body.slice(0, 300)}`);
    return `PUT /quotes/items/{itemId} → code=${puts[0].code}；体=${body.slice(0, 160)}`;
  });

  await step('㉑ 报价预览 → 提交报价单（POST /quotes/{id}/submit）', async () => {
    assert(savedQuoteId, '未拿到报价单 id');
    await goto(`#/pages/quote-preview/index?quoteId=${savedQuoteId}`, /预览|报价/);
    // 确认勾选框：判据必须是**状态真的翻转**（data-checked=true），
    // 用 `async () => true` 会在第一次点击后立即返回 —— 点没点中都不知道。
    await cdp.clickUntil(
      '[data-testid="confirm-check"]',
      async () => (await cdp.eval(`document.querySelector('[data-testid="confirm-check"]')?.getAttribute('data-checked')`)) === 'true',
      { tries: 4, gap: 600 }
    );
    const checked = await cdp.eval(`document.querySelector('[data-testid="confirm-check"]')?.getAttribute('data-checked')`);
    assert(checked === 'true', `确认勾选框未生效（data-checked=${checked}）—— 提交门禁会拦下`);
    await cdp.shot(outDir, '18-preview');
    const before = called('POST', '/submit').length;
    await cdp.clickUntil(
      '[data-testid="btn-submit"]',
      async () => called('POST', '/submit').length > before,
      { tries: 6, gap: 900 }
    );
    await sleep(3500);
    await cdp.settle();
    const subs = api().filter((c) => c.method === 'POST' && c.url.includes('/submit'));
    await cdp.shot(outDir, '19-submitted');
    assert(subs.length > 0, '点「提交」后未发出 POST /quotes/{id}/submit');
    assert(subs[0].code === '0', `提交报价单 → ${subs[0].code} ${subs[0].message}`);
    return `POST /quotes/{id}/submit → code=${subs[0].code}`;
  });

  await step('㉒ 提交后状态真的变了（业务结果断言，非状态码）', async () => {
    const supplierToken = await cdp.eval(`localStorage.getItem('aap_token')`);
    const one = await apiCall('GET', `/quotes/${savedQuoteId}`, supplierToken);
    assert(one.code === '0', `GET /quotes/{id} → ${one.code} ${one.message}`);
    const st = one.data?.status;
    assert(st && st !== 'DRAFT', `提交后状态仍是 ${st}（应离开 DRAFT）`);
    return `报价单 ${one.data?.quote_no ?? savedQuoteId} status=${st}`;
  });

  await step('㉓ 报价单出现在列表里且状态已更新（业务结果断言）', async () => {
    const supplierToken = await cdp.eval(`localStorage.getItem('aap_token')`);
    const list = await apiCall('GET', '/quotes?page=1&pageSize=20', supplierToken);
    assert(list.code === '0', `GET /quotes 失败：${list.code} ${list.message}`);
    const items = list.data?.items ?? list.data?.list ?? [];
    assert(items.length > 0, `报价单列表为空（total=${list.data?.total ?? '?'}）`);
    const draft = items.filter((q) => ['DRAFT', 'SUBMITTED'].includes(q.status));
    return `报价单 ${items.length} 张，其中草稿/已提交 ${draft.length} 张；最新=${items[0].quote_no ?? items[0].id} status=${items[0].status}`;
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
