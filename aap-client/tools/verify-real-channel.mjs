#!/usr/bin/env node
/**
 * 真实渠道拉取验证：用**真实 new-api 中转平台**的凭据跑「打渠道拉模型清单」全链路。
 *
 * 用法：
 *   set -a; . /e/env/aitoken-shop.env; set +a
 *   node tools/verify-real-channel.mjs
 *
 * ⚠️ 密钥只从环境变量读（`AITOKEN_BASE_URL` / `AITOKEN_API_KEY`），
 *    **不落仓库、不提交、不打印**。env 文件在仓库外（E:/env/）。
 *
 * 验证的链路（= new-api 的「获取模型列表」在本项目的等价物）：
 *   POST /credentials                             建凭证
 *   POST /credentials/{id}/precheck               后端 upstreamProbe **真打** {base_url}/models
 *   GET  /credentials/{id}  → model_list          渠道拉取结果是否落库
 */
const API = process.env.AAP_API ?? 'http://127.0.0.1:8084/api/v1'
const PHONE = process.env.AAP_PHONE ?? '13800138000'
const BASE_URL = process.env.AITOKEN_BASE_URL
const API_KEY = process.env.AITOKEN_API_KEY

if (!BASE_URL || !API_KEY) {
  console.error('缺少 AITOKEN_BASE_URL / AITOKEN_API_KEY（先 `. /e/env/aitoken-shop.env`）')
  process.exit(2)
}

const mask = (s) => (s ? `${s.slice(0, 6)}…${s.slice(-4)}` : '(空)')

async function call(method, path, { token, body } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    ...(body ? { body: JSON.stringify(body) } : {})
  })
  const json = await res.json().catch(() => null)
  return { status: res.status, code: json?.code, message: json?.message, data: json?.data }
}

async function login() {
  const sent = await call('POST', '/auth/sms/send', { body: { phone: PHONE, captcha: 'AB12' } })
  if (sent.code !== '0') throw new Error(`发码失败 ${sent.code} ${sent.message}`)
  const code = sent.data?.dev_code ?? sent.data?.devCode
  if (!code) throw new Error('未拿到 dev_code（后端需 AAP_SMS_EXPOSE_CODE=true）')
  const out = await call('POST', '/auth/sms/login', { body: { phone: PHONE, smsCode: String(code) } })
  if (out.code !== '0') throw new Error(`登录失败 ${out.code} ${out.message}`)
  return out.data.token
}

const SEP = '─'.repeat(74)
let pass = 0
let fail = 0
const ok = (m) => { pass++; console.log(`  ✓ ${m}`) }
const no = (m) => { fail++; console.log(`  ✗ ${m}`) }

const run = async () => {
  console.log(SEP)
  console.log('真实渠道拉取验证（new-api 中转平台 → 本项目 precheck → model_list）')
  console.log(`  上游 base_url = ${BASE_URL}`)
  console.log(`  上游 api_key  = ${mask(API_KEY)}   ← 打码，不回显`)
  console.log(SEP)

  const token = await login()
  ok(`供应商登录成功（${PHONE}），token len=${token.length}`)

  // ── 取凭证：api_key 指纹在同一供应商下唯一（E-1104）→ 已提交过就**复用**既有凭证 ──
  // ⚠️ 用户口径「所有测试数据不要删除」→ 这里绝不删旧凭证，改为按 base_url 命中复用。
  const listed = await call('GET', '/credentials?page=1&pageSize=50', { token })
  const rows = listed.data?.items ?? listed.data?.list ?? listed.data?.records ?? []
  const existing = Array.isArray(rows) ? rows.find((c) => c?.base_url === BASE_URL) : null

  let id
  let alias
  if (existing) {
    id = existing.id
    alias = existing.alias
    ok(`复用既有凭证 id=${id} alias=${alias}（api_key 指纹已存在，不重复建、不删数据）`)
  } else {
    alias = `真实渠道-${Date.now() % 100000}`
    const created = await call('POST', '/credentials', {
      token,
      body: { alias, base_url: BASE_URL, api_key: API_KEY, primary_flag: false }
    })
    if (created.code !== '0') throw new Error(`建凭证失败 ${created.code} ${created.message}`)
    id = created.data.id
    ok(`建凭证成功 id=${id} alias=${alias}`)
  }

  // 预检：后端会真打上游 /models
  const pre = await call('POST', `/credentials/${id}/precheck`, { token })
  if (pre.code !== '0') no(`预检失败 ${pre.code} ${pre.message}`)
  else ok(`预检成功 job=${pre.data.job_id ?? pre.data.jobId ?? '-'} status=${pre.data.status ?? '-'}`)

  const upstream = Array.isArray(pre.data?.models) ? pre.data.models : []
  upstream.length ? ok(`precheck 返回渠道模型 ${upstream.length} 个`) : no('precheck 未返回 models')

  // ── 回写 model_list（H5 页面 onSubmit 里做的就是这一步）──
  // ⚠️ 必须**剥掉 api_key**：后端 update 只要收到 api_key 就按「轮换密钥」处理
  //    → status 置回 PENDING_PRECHECK（需重新预检），把刚通过的 ACTIVE 打回。
  //    本次只是回写清单、密钥未变，带上它会把状态打坏（实测踩过）。
  if (upstream.length > 0) {
    const wrote = await call('PUT', `/credentials/${id}`, {
      token,
      body: { model_list: upstream.map((m) => ({ model_name: m })) }
    })
    wrote.code === '0'
      ? ok(`回写 model_list 成功（${upstream.length} 个，未带 api_key）`)
      : no(`回写失败 ${wrote.code} ${wrote.message}`)
  }

  // 详情：渠道拉取结果是否落库
  const detail = await call('GET', `/credentials/${id}`, { token })
  if (detail.code !== '0') throw new Error(`查详情失败 ${detail.code} ${detail.message}`)
  const list = Array.isArray(detail.data.model_list) ? detail.data.model_list : []
  const names = list.map((m) => m?.model_name).filter(Boolean)

  console.log(`\n  凭证状态: status=${detail.data.status} detection=${detail.data.detection_status}`)
  console.log(`  model_list 落库: ${names.length} 个`)
  console.log(`    ${names.join(', ')}`)

  names.length ? ok('渠道拉取的模型清单已落库（model_list 非空）') : no('model_list 仍为空')
  const same = upstream.length > 0 && names.length === upstream.length
  same ? ok(`落库数量与 precheck 返回一致（${names.length}）`) : no(`数量不一致 precheck=${upstream.length} 落库=${names.length}`)

  console.log(`\n${SEP}`)
  console.log(`真实渠道验证：通过 ${pass}，失败 ${fail}`)
  console.log(`新建凭证 id=${id}（**测试数据保留，未删除**）`)
  console.log(SEP)
  process.exit(fail === 0 ? 0 : 1)
}

run().catch((e) => {
  console.error('运行异常:', e.message)
  process.exit(1)
})
