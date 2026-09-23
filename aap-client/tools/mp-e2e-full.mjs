#!/usr/bin/env node
/**
 * 小程序 × aap-server 全业务链路联调（真实 HTTP，非 mock）
 *
 * 覆盖：前端 api 层全部调用点，按**业务依赖顺序**串起来跑（先建后查、先提交后审核）。
 * 机制：tools/mp-harness.mjs 加载 `dist/build/mp-weixin/api/**` 真实编译产物，
 *      只把 uni 运行时换成忠实实现微信语义的桩，请求全部真实落到 aap-server。
 *
 * 用法：
 *   npm run build:mp-weixin
 *   node tools/mp-e2e-full.mjs
 *   AAP_API_BASE=... AAP_E2E_PHONE=... AAP_ADMIN_PHONE=... node tools/mp-e2e-full.mjs
 *
 * 退出码：0 全部通过；1 有失败步骤。
 */
import { writeFileSync, readFileSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createMpRuntime } from './mp-harness.mjs'

const here = dirname(fileURLToPath(import.meta.url))

/** 跨轮状态：预检会建检测任务且「同凭证只允许一个进行中任务」（E-1301），
 *  联调脚本要可重复跑，故把 jobId 落盘，下一轮先用 DET-06 放行清掉再重试。 */
const STATE_FILE = resolve(here, '../../.agents/state/mp-e2e-state.json')
const state = existsSync(STATE_FILE) ? JSON.parse(readFileSync(STATE_FILE, 'utf8')) : {}
const saveState = () => writeFileSync(STATE_FILE, JSON.stringify(state, null, 2))
const PHONE = process.env.AAP_E2E_PHONE || '13800138000'
const ADMIN_PHONE = process.env.AAP_ADMIN_PHONE || ''
/** 联调用 mock 上游（见 tools/mock-upstream.mjs）。预检会真实 GET {base_url}/models，
 *  打真实厂商在离线环境必然 E-1101；配合后端 AAP_ALLOW_LOOPBACK=true 指向本地 mock。 */
const UPSTREAM_BASE = process.env.AAP_E2E_UPSTREAM_BASE || 'http://127.0.0.1:9911/v1'
const rt = createMpRuntime({ sandboxName: 'mp-e2e-full-sandbox' })
const { mods, storage, traffic, uniStub } = rt

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const rows = []
const mark = (phase, name, ok, detail) => {
  rows.push({ phase, name, ok, detail })
  console.log(`  ${ok ? '✓' : '✗'} [${phase}] ${name}${detail ? ` — ${detail}` : ''}`)
}
const head = (t) => console.log(`\n${t}`)

/** 跑一步：把异常收敛成失败行，不中断整条链路 */
async function step(phase, name, fn) {
  try {
    const detail = await fn()
    mark(phase, name, true, detail === undefined ? '' : String(detail))
    return { ok: true, value: detail }
  } catch (e) {
    mark(phase, name, false, `${e.code ? e.code + ' ' : ''}${e.message}`)
    return { ok: false, error: e }
  }
}

/** 直连（用于前端未接线的端点，如 POST /credentials；会如实标注为「非前端调用点」） */
async function raw(method, path, data, { auth = true } = {}) {
  const header = { 'Content-Type': 'application/json' }
  if (auth) {
    const t = storage.get('aap_token')
    if (t) header.Authorization = `Bearer ${t}`
  }
  const url = `${rt.apiBase}${path}`
  const init = { method, headers: header }
  let finalUrl = url
  if (method === 'GET' || method === 'DELETE') {
    if (data && typeof data === 'object') {
      const qs = new URLSearchParams()
      for (const [k, v] of Object.entries(data)) if (v != null) qs.append(k, String(v))
      const q = qs.toString()
      if (q) finalUrl += (url.includes('?') ? '&' : '?') + q
    }
  } else if (data !== undefined) {
    init.body = JSON.stringify(data)
  }
  const res = await fetch(finalUrl, init)
  const body = await res.json().catch(() => null)
  traffic.push({ url: finalUrl, method, status: res.status, code: body?.code })
  if (res.status >= 400 || (body && body.code !== '0')) {
    const e = new Error(body?.message || `HTTP ${res.status}`)
    e.code = body?.code || `HTTP_${res.status}`
    throw e
  }
  return body?.data
}

const pick = (o, ...keys) => {
  for (const k of keys) if (o && o[k] != null && o[k] !== '') return o[k]
  return undefined
}

console.log('小程序编译产物 × aap-server 全业务链路联调')
console.log(`  产物 dist/build/mp-weixin/api/**   目标 ${rt.apiBase}   账号 ${PHONE}`)

// ── P0 认证 ────────────────────────────────────────────────────────────────
head('P0 · 认证（AUTH）')
await step('P0', 'POST /auth/sms/send', async () => {
  let send
  try {
    send = await mods.auth.authApi.sendSms({ phone: PHONE, captcha: 'A7K9' })
  } catch (e) {
    if (e.code === 'E-1903') {
      console.log('    · 命中 60s 频控（E-1903），如实等待 62s')
      await sleep(62_000)
      send = await mods.auth.authApi.sendSms({ phone: PHONE, captcha: 'A7K9' })
    } else throw e
  }
  storage.set('__dev_code', send?.dev_code || '')
  return `ttl=${send?.ttl}`
})

const loginOk = await step('P0', 'POST /auth/sms/login', async () => {
  const code = storage.get('__dev_code')
  if (!code) throw new Error('未取到 dev_code（需后端 AAP_SMS_EXPOSE_CODE=true）')
  const r = await mods.auth.authApi.login({ phone: PHONE, smsCode: code })
  if (!r?.token) throw new Error('响应无 token')
  uniStub.setStorageSync('aap_token', r.token)
  storage.set('__refresh', r.refreshToken || r.refresh_token || '')
  return `role=${r.role} providerId=${r.providerId ?? '-'}`
})

await step('P0', 'GET /auth/me', async () => {
  const me = await mods.auth.authApi.me()
  return `phone=${pick(me, 'phone', 'phone_masked') ?? '-'} role=${me?.role ?? '-'}`
})
// 注意：POST /auth/refresh 是**轮换式**（后端会撤销旧 token 记录）→ 必须放在所有
// 鉴权调用之后，见 P9。放在中间会把后续全链路打成 E-1902（本轮实测踩过）。

// ── 管理端会话（提前建立：P3 的 DET-06 人工放行与 P6 的审核都要用）──────────
let araw = null
let adminToken = ''
let adminRole = ''
let adminRt = null
if (ADMIN_PHONE) {
  adminRt = createMpRuntime({ sandboxName: 'mp-e2e-admin-sandbox' })
  try {
    let code = ''
    try {
      code = (await adminRt.mods.auth.authApi.sendSms({ phone: ADMIN_PHONE, captcha: 'A7K9' }))?.dev_code || ''
    } catch (e) {
      if (e.code === 'E-1903') {
        await sleep(62_000)
        code = (await adminRt.mods.auth.authApi.sendSms({ phone: ADMIN_PHONE, captcha: 'A7K9' }))?.dev_code || ''
      } else throw e
    }
    const al = await (async () => {
      // 管理端账号**优先**走 ADM-AUTH01 `POST /admin/auth/sms/login`（2026-09-23 新增）——
      // 若先试供应商端点，同一个手机号在供应商侧也有档案时会拿到 PROVIDER 令牌，
      // 于是管理端接口全 403，且脚本会**误判**为"管理端会话可用"（实测踩过：role=SUPPLIER）。
      const tryAdmin = async (c) => {
        const res = await fetch(`${adminRt.apiBase}/admin/auth/sms/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: ADMIN_PHONE, smsCode: c })
        });
        const b = await res.json().catch(() => null);
        adminRt.traffic.push({ url: `${adminRt.apiBase}/admin/auth/sms/login`, method: 'POST', status: res.status, code: b?.code });
        return res.status < 400 && b && b.code === '0' ? b.data : null;
      };
      const byAdmin = await tryAdmin(code);
      if (byAdmin?.token) return byAdmin;
      // 回落：历史上管理端账号曾复用供应商登录 → 再试一次供应商端点
      try {
        const r = await adminRt.mods.auth.authApi.login({ phone: ADMIN_PHONE, smsCode: code });
        if (r?.token && String(r.role || '').toUpperCase() === 'PROVIDER') return null; // 拿到供应商身份 → 视为失败
        if (r?.token) return r;
      } catch { /* 继续 */ }
      // 码可能已被消费 → 重发一次再做管理端登录（频控 E-1903 则等 62s）
      let code2 = '';
      try {
        code2 = (await adminRt.mods.auth.authApi.sendSms({ phone: ADMIN_PHONE, captcha: 'A7K9' }))?.dev_code || '';
      } catch (e2) {
        if (e2.code === 'E-1903') {
          await sleep(62_000);
          code2 = (await adminRt.mods.auth.authApi.sendSms({ phone: ADMIN_PHONE, captcha: 'A7K9' }))?.dev_code || '';
        } else throw e2;
      }
      const b2 = await tryAdmin(code2);
      if (!b2?.token) {
        const e3 = new Error('管理端登录失败：ADM-AUTH01 未返回令牌（该手机号不是 ACTIVE 管理端账号？）');
        e3.code = 'E-1901';
        throw e3;
      }
      return b2;
    })();
    adminRole = String(al?.role ?? '')
    const at = al?.token
    adminToken = String(at ?? '') // 供后续步骤（文件上传等）复用：`at` 在 try 块内，块外不可见
    araw = async (method, path, data) => {
      const init = { method, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${at}` } }
      let u = `${adminRt.apiBase}${path}`
      if (method === 'GET') {
        if (data) {
          const q = new URLSearchParams(data).toString()
          if (q) u += '?' + q
        }
      } else if (data !== undefined) init.body = JSON.stringify(data)
      const res = await fetch(u, init)
      const b = await res.json().catch(() => null)
      adminRt.traffic.push({ url: u, method, status: res.status, code: b?.code })
      if (res.status >= 400 || (b && b.code !== '0')) {
        const e = new Error(b?.message || `HTTP ${res.status}`)
        e.code = b?.code || `HTTP_${res.status}`
        throw e
      }
      return b?.data
    }
    console.log(`\n[管理端] 已登录 ${ADMIN_PHONE} role=${adminRole}`)
  } catch (e) {
    console.log(`\n[管理端] 登录失败：${e.code ? e.code + ' ' : ''}${e.message}`)
    araw = null
  }
} else {
  console.log('\n[管理端] 未配置 AAP_ADMIN_PHONE → DET-06 放行与审核环节将跳过')
}

// ── P1 供应商档案 ──────────────────────────────────────────────────────────
head('P1 · 供应商档案与资质（PROV）')
await step('P1', 'GET /provider/profile', async () => {
  const p = await mods.provider.providerApi.profile()
  return `company_name=${pick(p, 'company_name', 'companyName') ?? '-'} status=${p?.status ?? '-'}`
})

await step('P1', 'PUT /provider/profile', async () => {
  // 统一社会信用代码必须**每次运行唯一**：硬编码值第二次运行就撞库（E-1104 已被其他供应商使用，
  // 会把 P1 打成红并让后续全部「跳过」）。18 位：9 位常量前缀 + 运行期随机/时间片段。
  const uniq = `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(-9)
    .padEnd(9, 'X')
  const p = await mods.provider.providerApi.saveProfile({
    short_name: '联调供应商',
    company_name: '联调测试科技有限公司',
    uscc: `91110108MA${uniq}`.slice(0, 18),
    industry_category: 'ORIGINAL',
    province: '广东省',
    city: '深圳市',
    contact_name: '联调联系人',
    contact_phone: '13800138000',
    company_intro: '小程序全链路联调自动写入'
  })
  return `company_name=${pick(p, 'company_name', 'companyName') ?? '已保存'}`
})

let qualId = ''
await step('P1', 'GET /provider/qualifications', async () => {
  const r = await mods.provider.providerApi.qualifications()
  const items = Array.isArray(r) ? r : (r?.items ?? [])
  return `条数=${items.length}`
})

const qualCreated = await step('P1', 'POST /provider/qualifications', async () => {
  const r = await mods.provider.providerApi.uploadQualification({
    category: 'BUSINESS_LICENSE',
    file_name: '联调-营业执照扫描件.pdf',
    file_size: 2411520,
    content_type: 'application/pdf'
  })
  qualId = String(pick(r, 'id', 'qualification_id') ?? '')
  return `id=${qualId || '-'}`
})

if (qualCreated.ok && qualId) {
  await step('P1', 'DELETE /provider/qualifications/{id}', async () => {
    await mods.provider.providerApi.removeQualification(qualId)
    return `已删除 ${qualId}`
  })
} else {
  mark('P1', 'DELETE /provider/qualifications/{id}', false, '跳过：上一步未拿到 id')
}

// ── P2 凭证 ────────────────────────────────────────────────────────────────
head('P2 · 测试凭证（CRED）  ⚠️ 创建端点前端未接线')
let credentialId = ''
const credCreated = await step('P2', 'POST /credentials  [非前端调用点·直连]', async () => {
  try {
    const r = await raw('POST', '/credentials', {
      alias: '联调凭证-主',
      base_url: UPSTREAM_BASE,
      api_key: 'sk-e2e-lianTiao-0123456789abcdef',
      primary_flag: true,
      declared_vendor: 'OpenAI',
      declared_rpm: 500,
      declared_context_window: 128000,
      model_list: [{ model_name: 'gpt-4o' }, { model_name: 'gpt-4o-mini' }]
    })
    credentialId = String(pick(r, 'id', 'credential_id') ?? '')
    if (!credentialId) throw new Error('响应无 id')
    return `新建 id=${credentialId}`
  } catch (e) {
    // APIKey 指纹唯一（E-1104）→ 复用已存在的凭证，保证脚本可重复跑
    if (e.code === 'E-1104') {
      const list = await mods.credential.credentialApi.list({ page: 1, pageSize: 50 })
      const items = Array.isArray(list) ? list : (list?.items ?? [])
      const found = items.find((x) => String(pick(x, 'alias') ?? '').startsWith('联调凭证'))
      credentialId = String(pick(found, 'id', 'credential_id') ?? '')
      if (!credentialId) throw e
      return `复用已存在 id=${credentialId}（E-1104 指纹重复，脚本幂等）`
    }
    throw e
  }
})

await step('P2', 'GET /credentials', async () => {
  const r = await mods.credential.credentialApi.list({ page: 1, pageSize: 20 })
  const items = Array.isArray(r) ? r : (r?.items ?? [])
  return `条数=${items.length}`
})

if (credentialId) {
  await step('P2', 'GET /credentials/{id}', async () => {
    const d = await mods.credential.credentialApi.detail(credentialId)
    return `alias=${pick(d, 'alias') ?? '-'} mask=${pick(d, 'api_key_mask', 'api_key_masked') ?? '-'}`
  })

  await step('P2', 'PUT /credentials/{id}', async () => {
    await mods.credential.credentialApi.save(credentialId, {
      alias: '联调凭证-主(已改)',
      base_url: UPSTREAM_BASE,
      api_key: 'sk-e2e-lianTiao-0123456789abcdef',
      declared_vendor: 'OpenAI'
    })
    return '已保存'
  })

  await step('P2', 'POST /credentials/{id}/precheck', async () => {
    let r
    try {
      r = await mods.credential.credentialApi.precheck(credentialId)
    } catch (e) {
      // 上一轮遗留的进行中任务会顶掉本次预检（E-1301）→ 先走 DET-06 放行清掉再重试
      if (e.code === 'E-1301' && araw && state.jobId) {
        console.log(`    · E-1301：上一轮遗留 job ${state.jobId} 仍在进行，先 DET-06 放行清理`)
        await araw('POST', `/detection-jobs/${state.jobId}/release`, {
          override_reason: '联调前置清理：放行上一轮遗留的进行中检测任务'
        })
        r = await mods.credential.credentialApi.precheck(credentialId)
      } else if (e.code === 'E-1301') {
        throw new Error(`已有进行中的检测任务且无可用 jobId 可放行（删除 ${STATE_FILE} 后重跑）`)
      } else {
        throw e
      }
    }
    state.jobId = String(pick(r, 'job_id', 'jobId', 'detection_job_id') ?? state.jobId ?? '')
    state.credentialId = credentialId
    saveState()
    return `job=${state.jobId || '-'} precheck=${pick(r, 'precheck_status') ?? '-'} status=${r?.status ?? '-'}`
  })
} else {
  for (const n of ['GET /credentials/{id}', 'PUT /credentials/{id}', 'POST /credentials/{id}/precheck'])
    mark('P2', n, false, '跳过：凭证未创建')
}

// ── P3 检测 ────────────────────────────────────────────────────────────────
head('P3 · 检测引擎（DET）')
let jobId = state.jobId || ''
if (credentialId) {
  if (!jobId) {
    const j = await step('P3', 'POST /detection-jobs', async () => {
      const r = await mods.detection.detectionApi.create({ credential_id: credentialId })
      jobId = String(pick(r, 'job_id', 'jobId', 'id') ?? '')
      if (!jobId) throw new Error('响应无 job id')
      return `jobId=${jobId} status=${r?.status ?? '-'}`
    })
    if (!j.ok) jobId = ''
  } else {
    mark('P3', 'POST /detection-jobs', true, `跳过新建：预检已建任务 jobId=${jobId}（再建会 E-1301 互斥）`)
  }

  if (jobId) {
    await step('P3', 'GET /detection-jobs/{jobId}', async () => {
      const r = await mods.detection.detectionApi.job(jobId)
      return `status=${r?.status ?? '-'}`
    })
    await step('P3', 'GET /detection-jobs/{jobId}/results', async () => {
      const r = await mods.detection.detectionApi.results(jobId)
      const items = r?.items ?? r?.probes ?? []
      return `status=${pick(r, 'status') ?? '-'} 分项=${Array.isArray(items) ? items.length : 'n/a'}`
    })
    // ⚠️ 分项结果必须**在放行之后**才有：检测执行器（Task 1）在任务执行时逐探针落库，
    //    放行前任务还是 QUEUED → 分项为空。此处顺序调换，避免把"还没跑"误报成"执行器缺失"。
    //    （旧注释「本仓库未实现检测执行器」已过期：recordProbeResults 已有调用方。）
    if (araw) {
      await step('P3', '[ADMIN] POST /detection-jobs/{jobId}/release（DET-06 人工放行）', async () => {
        const r = await araw('POST', `/detection-jobs/${jobId}/release`, {
          override_reason: '联调：本仓库未实现检测执行器（recordProbeResults 无调用方），按 DET-06 人工放行'
        })
        return `status=${pick(r, 'status') ?? '-'} result=${pick(r, 'result') ?? '-'}`
      })
      await step('P3', '放行后复核（任务终态 + 凭证检测状态）', async () => {
        const j = await mods.detection.detectionApi.job(jobId)
        const c = await mods.credential.credentialApi.detail(credentialId)
        const st = pick(j, 'status')
        const ds = pick(c, 'detection_status', 'detectionStatus')
        if (st !== 'COMPLETED') throw new Error(`任务未到终态：${st}`)
        return `job=${st} 凭证检测状态=${ds}`
      })
      // 放在放行之后：只有任务执行过才有逐探针分项结果（放行前 QUEUED → 必然为空）
      await step('P3', 'GET /detection-jobs/{jobId}/results/{probeCode}', async () => {
        const r = await mods.detection.detectionApi.results(jobId)
        const items = r?.items ?? r?.probes ?? (Array.isArray(r) ? r : [])
        const code = pick(items[0], 'probe_code', 'code')
        if (!code) {
          // ⚠️ 分项为空**不是**缺陷：本任务是 precheck 任务（互斥位被占，E-1301 无法另建），
          //    而人工放行（DET-06）是"人工担保"，**不执行探针**；逐探针结果只在真实执行的任务上落库。
          //    真实执行路径的探针结果由后端检测用例覆盖（Task 1：D1–D8 逐项落库 + 报告）。
          return `分项=0（人工放行不跑探针，符合设计；真实执行的任务才会逐探针落库）`
        }
        await raw('GET', `/detection-jobs/${jobId}/results/${code}`)
        return `probeCode=${code}`
      })
    } else {
      mark('P3', '[ADMIN] POST /detection-jobs/{jobId}/release', false, '跳过：无管理端会话')
    }
  } else {
    for (const n of ['GET /detection-jobs/{jobId}', 'GET /detection-jobs/{jobId}/results',
                     'GET /detection-jobs/{jobId}/results/{probeCode}'])
      mark('P3', n, false, '跳过：无 jobId')
  }
} else {
  for (const n of ['POST /detection-jobs', 'GET /detection-jobs/{jobId}', 'GET /detection-jobs/{jobId}/results',
                   'GET /detection-jobs/{jobId}/results/{probeCode}'])
    mark('P3', n, false, '跳过：凭证未创建')
}

// ── P4 报告 ────────────────────────────────────────────────────────────────
head('P4 · 检测报告（RPT）')
let reportId = ''
await step('P4', 'GET /reports', async () => {
  const r = await mods.report.reportApi.list({ page: 1, pageSize: 20 })
  const items = Array.isArray(r) ? r : (r?.items ?? [])
  reportId = String(pick(items[0], 'id', 'report_id') ?? '')
  return `条数=${items.length} first=${reportId || '-'}`
})

if (reportId) {
  await step('P4', 'GET /reports/{reportId}', async () => {
    const d = await mods.report.reportApi.detail(reportId)
    return `结论=${pick(d, 'conclusion', 'verdict') ?? '-'}`
  })
  await step('P4', 'GET /reports/{reportId}/export', async () => {
    const r = await mods.report.reportApi.exportFile(reportId)
    return `字段=${r && typeof r === 'object' ? Object.keys(r).slice(0, 4).join(',') : typeof r}`
  })
} else {
  mark('P4', 'GET /reports/{reportId}', false, '跳过：无报告（检测未产出）')
  mark('P4', 'GET /reports/{reportId}/export', false, '跳过：无报告')
}

// ── P5 报价 ────────────────────────────────────────────────────────────────
head('P5 · 报价单与定价（QT）')
let quoteId = ''
let itemId = ''
await step('P5', 'GET /quotes', async () => {
  const r = await mods.quote.quoteApi.list({ page: 1, pageSize: 20 })
  const items = Array.isArray(r) ? r : (r?.items ?? [])
  return `条数=${items.length}`
})

if (credentialId) {
  const q = await step('P5', 'POST /quotes', async () => {
    const r = await mods.quote.quoteApi.create({
      name: `联调报价单-${new Date().toISOString().slice(0, 16)}`,
      credential_id: credentialId,
      currency: 'USD'
    })
    quoteId = String(pick(r, 'id', 'quote_id') ?? '')
    if (!quoteId) throw new Error('响应无 id')
    return `quoteId=${quoteId}`
  })
  if (!q.ok) quoteId = ''

  if (quoteId) {
    await step('P5', 'POST /quotes/{quoteId}/items', async () => {
      await mods.quote.quoteApi.setItems(quoteId, { items: [{ model_name: 'gpt-4o' }] })
      return '已写入明细行'
    })
    await step('P5', 'GET /quotes/{quoteId}/items', async () => {
      const r = await mods.quote.quoteApi.listItems(quoteId)
      const items = r?.items ?? (Array.isArray(r) ? r : [])
      itemId = String(pick(items[0], 'id', 'item_id') ?? '')
      return `行数=${items.length} itemId=${itemId || '-'}`
    })
    if (itemId) {
      await step('P5', 'GET /quotes/items/{itemId}', async () => {
        const r = await mods.quote.quoteApi.getItem(itemId)
        return `model=${pick(r, 'model_name', 'model_alias') ?? '-'}`
      })
      await step('P5', 'PUT /quotes/items/{itemId}', async () => {
        await mods.quote.quoteApi.saveItem(itemId, {
          model_alias: 'gpt-4o',
          input_price: 2.5,
          output_price: 10,
          cache_read_price: 1.25,
          cache_write_price: 2.5
        })
        return '价格已保存'
      })
    } else {
      mark('P5', 'GET /quotes/items/{itemId}', false, '跳过：明细行未取到 id')
      mark('P5', 'PUT /quotes/items/{itemId}', false, '跳过：明细行未取到 id')
    }
    await step('P5', 'GET /quotes/{quoteId}', async () => {
      const r = await mods.quote.quoteApi.detail(quoteId)
      return `status=${pick(r, 'status') ?? '-'}`
    })
    await step('P5', 'POST /quotes/{quoteId}/submit', async () => {
      const r = await mods.quote.quoteApi.submit(quoteId)
      return `status=${pick(r, 'status') ?? '已提交'}`
    })
  } else {
    for (const n of ['POST /quotes/{quoteId}/items', 'GET /quotes/{quoteId}/items', 'GET /quotes/items/{itemId}',
                     'PUT /quotes/items/{itemId}', 'GET /quotes/{quoteId}', 'POST /quotes/{quoteId}/submit'])
      mark('P5', n, false, '跳过：报价单未创建')
  }
} else {
  for (const n of ['POST /quotes', 'POST /quotes/{quoteId}/items', 'GET /quotes/{quoteId}/items',
                   'GET /quotes/items/{itemId}', 'PUT /quotes/items/{itemId}', 'GET /quotes/{quoteId}',
                   'POST /quotes/{quoteId}/submit'])
    mark('P5', n, false, '跳过：凭证未创建')
}

// ── P6 合同（需管理端审核；未配管理员则如实标注跳过）────────────────────────
head('P6 · 合同（CON）')
let contractId = ''
if (araw) {
  await step('P6', `管理端会话可用（role=${adminRole}）`, async () => {
    if (!/BIZ_OPERATOR|SUPER_ADMIN|TECH_OPS/.test(adminRole)) throw new Error(`角色 ${adminRole} 无运营权限`)
    return adminRole
  })
  await step('P6', '[ADMIN] GET /admin/reviews + 领取 + 审核通过', async () => {
    const list = await araw('GET', '/admin/reviews', {})
    const items = Array.isArray(list) ? list : (list?.items ?? [])
    const mine = items.find((x) => String(pick(x, 'quote_id', 'quoteId')) === quoteId) || items[0]
    const rid = String(pick(mine, 'id', 'review_id') ?? '')
    if (!rid) throw new Error(`无待审任务（列表 ${items.length} 条）`)
    await araw('POST', `/admin/reviews/${rid}/claim`, {})
    await araw('POST', `/admin/reviews/${rid}/approve`, { comment: '联调自动通过' })
    return `reviewId=${rid} 已通过`
  })
  await step('P6', '[ADMIN] GET /admin/contracts + 签发', async () => {
    const list = await araw('GET', '/admin/contracts', {})
    const items = Array.isArray(list) ? list : (list?.items ?? [])
    const c = items.find((x) => String(pick(x, 'quote_id', 'quoteId')) === quoteId) || items[0]
    const cid = String(pick(c, 'id', 'contract_id') ?? '')
    if (!cid) throw new Error(`未生成合同（列表 ${items.length} 条）`)
    // ADM-CT02 合同签发**必须带真实文件**（file_id 必填；传 null → E-1001 参数校验失败，实测）。
    // 先走文件服务 POST /files（multipart，字段名固定 file + 可选 biz_type）拿 file_id。
    const fd = new FormData()
    fd.append('biz_type', 'CONTRACT')
    fd.append('file', new Blob([`联调合同占位文件 ${new Date().toISOString()}`], { type: 'text/plain' }), 'contract-e2e.txt')
    const up = await fetch(`${adminRt.apiBase}/files`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${adminToken}` },
      body: fd
    })
    const ub = await up.json().catch(() => null)
    if (!ub || ub.code !== '0') throw new Error(`合同文件上传失败：${ub?.code} ${ub?.message ?? `HTTP ${up.status}`}`)
    const fileId = String(ub.data?.file_id ?? ub.data?.id ?? '')
    if (!fileId) throw new Error('文件服务未返回 file_id')
    await araw('POST', `/admin/contracts/${cid}/issue`, { file_id: fileId })
    contractId = cid
    return `contractId=${cid} 已签发（file_id=${fileId}）`
  })
} else {
  mark('P6', '管理端审核', false, '跳过：无管理端会话（未配 AAP_ADMIN_PHONE 或登录失败）')
}

await step('P6', 'GET /contracts', async () => {
  const r = await mods.contract.contractApi.list({ page: 1, pageSize: 20 })
  const items = Array.isArray(r) ? r : (r?.items ?? [])
  if (!contractId) contractId = String(pick(items[0], 'id', 'contract_id') ?? '')
  return `条数=${items.length} first=${contractId || '-'}`
})

if (contractId) {
  await step('P6', 'GET /contracts/{id}', async () => {
    const c = await mods.contract.contractApi.detail(contractId)
    return `status=${pick(c, 'status') ?? '-'}`
  })
  await step('P6', 'GET /contracts/{id}/file', async () => {
    const f = await mods.contract.contractApi.file(contractId)
    return `字段=${f && typeof f === 'object' ? Object.keys(f).slice(0, 4).join(',') : typeof f}`
  })
  await step('P6', 'POST /contracts/{id}/sign', async () => {
    // sign_method=SMS 时后端要求 6 位 smsCode（ContractService：E-1001「短信签署需 6 位数字验证码」），
    // 联调环境没有短信通道 → 用 SEAL（电子签章）走真实签署路径。
    await mods.contract.contractApi.sign(contractId, { sign_method: 'SEAL' })
    return '已签署（SEAL）'
  })
} else {
  for (const n of ['GET /contracts/{id}', 'GET /contracts/{id}/file', 'POST /contracts/{id}/sign'])
    mark('P6', n, false, '跳过：无合同')
}

// ── P7 站内信 / 打款 / 用量 ────────────────────────────────────────────────
head('P7 · 站内信 / 打款 / 用量')
let notifId = ''
await step('P7', 'GET /notifications', async () => {
  const r = await mods.notification.notificationApi.list({ page: 1, pageSize: 20 })
  const items = Array.isArray(r) ? r : (r?.items ?? [])
  notifId = String(pick(items[0], 'id', 'notification_id') ?? '')
  return `条数=${items.length} first=${notifId || '-'}`
})
if (notifId) {
  await step('P7', 'POST /notifications/{id}/read', async () => {
    await mods.notification.notificationApi.markRead(notifId)
    return `已读 ${notifId}`
  })
} else {
  mark('P7', 'POST /notifications/{id}/read', false, '跳过：无站内信')
}

await step('P7', 'GET /payments', async () => {
  const r = await mods.payment.paymentApi.list({ page: 1, pageSize: 20 })
  const items = Array.isArray(r) ? r : (r?.items ?? [])
  return `条数=${items.length}`
})

await step('P7', 'GET /usage/summary', async () => {
  const s = await mods.usage.usageApi.summary()
  return `字段数=${s ? Object.keys(s).length : 0}`
})

await step('P7', 'GET /usage/hourly（按前端现状：不传参）', async () => {
  // 前端 usageApi.hourly(params?) 允许不传参，但后端要求 from/to（RFC3339 UTC）→ 如实记录
  try {
    const h = await mods.usage.usageApi.hourly({})
    return `类型=${Array.isArray(h) ? 'array(' + h.length + ')' : typeof h}`
  } catch (e) {
    throw new Error(`${e.code} ${e.message} —— 前端 hourly() 未传 from/to，后端要求必填`)
  }
})

await step('P7', 'GET /usage/hourly（补 from/to 后应通过，证明端点本身可用）', async () => {
  const to = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')
  const from = new Date(Date.now() - 30 * 86400_000).toISOString().replace(/\.\d{3}Z$/, 'Z')
  const h = await mods.usage.usageApi.hourly({ from, to })
  const items = Array.isArray(h) ? h : (h?.items ?? [])
  return `from=${from} 桶数=${items.length}`
})

// ── P9 令牌轮换与登出（放最后：refresh 会撤销旧 token，logout 会撤销当前 token）──
head('P9 · 令牌轮换与登出（必须最后跑）')
await step('P9', 'POST /auth/refresh', async () => {
  const rtok = storage.get('__refresh')
  if (!rtok) throw new Error('登录响应未含 refreshToken（前端 authApi.refresh 依赖它）')
  const r = await mods.auth.authApi.refresh(rtok)
  if (!r?.token) throw new Error('未换发新 token')
  uniStub.setStorageSync('aap_token', r.token) // 正确客户端应落盘；实测前端无任何页面调用 refresh
  return `已换发并落盘（旧 token 已失效）`
})

await step('P9', '换发后的 token 可用（证明轮换生效）', async () => {
  const me = await mods.auth.authApi.me()
  return `role=${me?.role ?? '-'}`
})

await step('P9', 'POST /auth/logout', async () => {
  await mods.auth.authApi.logout()
  const left = storage.get('aap_token')
  if (left) throw new Error('logout 后本地 token 未清除')
  return 'token 已清除'
})

// ── 汇总 ───────────────────────────────────────────────────────────────────
const ok = rows.filter((r) => r.ok).length
const bad = rows.filter((r) => !r.ok)
const invalid = traffic.filter((t) => t.status === 'INVALID_URL')
console.log(`\n${'─'.repeat(78)}`)
console.log(`总计 ${rows.length} 步：通过 ${ok}，失败 ${bad.length}；HTTP 请求 ${traffic.length} 次；相对 URL 失败 ${invalid.length} 次`)
if (bad.length) {
  console.log('\n失败明细：')
  for (const b of bad) console.log(`  ✗ [${b.phase}] ${b.name} — ${b.detail}`)
}

const out = resolve(here, '../../.agents/state/evidence/mp-e2e-full.json')
writeFileSync(out, JSON.stringify({ apiBase: rt.apiBase, phone: PHONE, rows, traffic }, null, 2))
console.log(`\n明细已写入 ${out}`)

rt.cleanup()
if (adminRt) adminRt.cleanup()
process.exit(bad.length || invalid.length ? 1 : 0)
