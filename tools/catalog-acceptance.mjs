#!/usr/bin/env node
/**
 * 模型目录接口运行态验收（真实 HTTP 打 8084，不走 mock）。
 *
 * 为什么单独写：这套接口此前**一次都没在运行态跑过**（只过了编译与既有回归）。
 * 编译通过 ≠ 接口能用 —— 路由前缀、权限注解、MyBatis-Flex 查询、JSONB 写入
 * 都只有真打一次才知道。
 *
 * 用法：node tools/catalog-acceptance.mjs [baseUrl]
 * 依赖后端带 AAP_SMS_EXPOSE_CODE=true（拿 dev_code 免短信）。
 */
const BASE = process.argv[2] || 'http://127.0.0.1:8084/api/v1'
const ADMIN = '13900000001'

let pass = 0
const fails = []
const ok = (name, cond, extra) => {
  if (cond) {
    pass++
    console.log(`  ✓ ${name}`)
  } else {
    fails.push(name)
    console.log(`  ✗ ${name}${extra ? ' — ' + extra : ''}`)
  }
}

async function req(method, path, body, token) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body)
  })
  let json = null
  try {
    json = await res.json()
  } catch {
    /* 非 JSON 响应（如 401 空体） */
  }
  return { status: res.status, json, code: json?.code, data: json?.data, message: json?.message }
}

/** 登录拿 token（登录即注册；超管账号在建库时已预置）。 */
async function login(phone) {
  const send = await req('POST', '/auth/sms/send', { phone, captcha: 'AB12' })
  const devCode = send.data?.dev_code ?? send.data?.devCode
  if (!devCode) throw new Error(`未拿到 dev_code：${JSON.stringify(send).slice(0, 200)}`)
  const res = await req('POST', '/auth/sms/login', { phone, smsCode: String(devCode) })
  if (!res.data?.token) throw new Error(`登录失败：${JSON.stringify(res).slice(0, 200)}`)
  return { token: res.data.token, role: res.data.role }
}

const main = async () => {
  console.log(`### 模型目录接口运行态验收 — ${BASE}`)

  console.log('\n【准备】超管登录')
  const admin = await login(ADMIN)
  ok(`超管登录（role=${admin.role}）`, !!admin.token)

  const supplier = await login('13800138000')
  ok(`供应商登录（role=${supplier.role}）`, !!supplier.token)

  const suffix = Date.now().toString().slice(-6)

  console.log('\n【1. 新增厂商】POST /admin/catalog/vendors')
  const v = await req(
    'POST',
    '/admin/catalog/vendors',
    {
      name: `验收厂商-${suffix}`,
      vendorKey: `accv-${suffix}`,
      vendorType: 'DIRECT',
      region: '中国',
      website: 'https://example.com',
      baseUrl: 'https://api.example.com/v1',
      apiKey: 'sk-acc-1234567890abcd',
      defaultQps: 50,
      currency: 'CNY',
      enabled: true,
      description: '运行态验收'
    },
    admin.token
  )
  ok('厂商创建 code=0', v.code === '0', `${v.code} ${v.message ?? ''}`)
  ok('返回 id/vendorKey', !!v.data?.id && v.data?.vendorKey === `accv-${suffix}`)
  ok(
    'API Key 只回脱敏、不回明文',
    !!v.data?.apiKeyMask && !JSON.stringify(v.data).includes('sk-acc-1234567890abcd'),
    `apiKeyMask=${v.data?.apiKeyMask}`
  )
  const vendorId = v.data?.id

  console.log('\n【2. 厂商重名校验】同 vendorKey 再建一次')
  const dup = await req(
    'POST',
    '/admin/catalog/vendors',
    { name: 'X', vendorKey: `accv-${suffix}`, vendorType: 'DIRECT', baseUrl: 'https://x/v1' },
    admin.token
  )
  ok('重复 vendorKey 被拒（E-1001）', dup.code === 'E-1001', `实际 ${dup.code} ${dup.message ?? ''}`)

  console.log('\n【3. 新增模型】POST /admin/catalog/models')
  const m = await req(
    'POST',
    '/admin/catalog/models',
    {
      vendorId: String(vendorId),
      modelName: `验收模型-${suffix}`,
      modelUid: `acc-model-${suffix}`,
      modelType: 'CHAT',
      contextWindow: 128000,
      maxOutput: 16384,
      inputPrice: 0.0011,
      outputPrice: 0.0044,
      capabilities: ['FUNCTION_CALL', 'STREAM'],
      baseUrl: 'https://api.example.com/v1',
      apiKey: 'sk-model-secret-should-not-leak',
      enabled: true,
      remark: '运行态验收'
    },
    admin.token
  )
  ok('模型创建 code=0', m.code === '0', `${m.code} ${m.message ?? ''}`)
  ok('能力标签往返正确', JSON.stringify(m.data?.capabilities) === '["FUNCTION_CALL","STREAM"]', JSON.stringify(m.data?.capabilities))
  ok('价格按设计原样（不换算）', String(m.data?.inputPrice) === '0.0011' && String(m.data?.outputPrice) === '0.0044')
  ok('显式带出 priceUnit（D-ADM-4 单位口径）', m.data?.priceUnit === 'CNY/1K', `实际 ${m.data?.priceUnit}`)
  ok('模型 API Key 不回明文', !JSON.stringify(m.data ?? {}).includes('sk-model-secret-should-not-leak'))
  const modelId = m.data?.id

  console.log('\n【4. 缺失字段校验】不带必填项')
  const bad = await req('POST', '/admin/catalog/models', { vendorId: String(vendorId) }, admin.token)
  ok('缺模型名称/标识 → E-1001', bad.code === 'E-1001', `实际 ${bad.code}`)

  console.log('\n【5. 按厂商分组】GET /admin/catalog/models/grouped')
  const g = await req('GET', '/admin/catalog/models/grouped', undefined, admin.token)
  ok('分组查询 code=0', g.code === '0')
  const grp = (g.data ?? []).find((x) => x.vendor?.id === vendorId)
  ok('新厂商出现在分组中', !!grp, `分组数 ${(g.data ?? []).length}`)
  ok('该组下含新建模型', (grp?.models ?? []).some((x) => x.id === modelId))

  console.log('\n【6. H5 侧可用模型清单】GET /catalog/models（供应商可读）')
  const avail = await req('GET', '/catalog/models', undefined, supplier.token)
  ok('供应商可读 code=0', avail.code === '0', `${avail.code} ${avail.message ?? ''}`)
  ok('新模型出现在可用清单', (avail.data ?? []).some((x) => x.modelUid === `acc-model-${suffix}`))
  ok('可用清单不含管理端字段 apiKeyMask', !JSON.stringify(avail.data ?? []).includes('apiKeyMask'))

  console.log('\n【7. 供应商访问管理端接口必须 403】GET /admin/catalog/vendors')
  const forbid = await req('GET', '/admin/catalog/vendors', undefined, supplier.token)
  ok('供应商被拒（403 / E-1901）', forbid.status === 403 || forbid.code === 'E-1901', `实际 ${forbid.status} ${forbid.code}`)

  console.log('\n【8. 停用模型 → 退出可用清单，但管理端仍可见】')
  const off = await req('PUT', `/admin/catalog/models/${modelId}`, { enabled: false }, admin.token)
  ok('停用成功 code=0', off.code === '0', `${off.code} ${off.message ?? ''}`)
  const avail2 = await req('GET', '/catalog/models', undefined, supplier.token)
  ok('停用后不在 H5 可用清单', !(avail2.data ?? []).some((x) => x.modelUid === `acc-model-${suffix}`))
  const adm2 = await req('GET', '/admin/catalog/models', undefined, admin.token)
  ok('停用后管理端仍可见（可恢复）', (adm2.data ?? []).some((x) => x.id === modelId))

  console.log('\n【9. 复启用 → 回到可用清单】')
  const on = await req('PUT', `/admin/catalog/models/${modelId}`, { enabled: true }, admin.token)
  ok('复启用 code=0', on.code === '0')
  const avail3 = await req('GET', '/catalog/models', undefined, supplier.token)
  ok('复启用后回到 H5 可用清单', (avail3.data ?? []).some((x) => x.modelUid === `acc-model-${suffix}`))

  console.log(`\n=== 结果：${pass} 通过 / ${fails.length} 失败 ===`)
  if (fails.length) {
    console.log('失败项：')
    fails.forEach((f) => console.log('  -', f))
    process.exit(1)
  }
  console.log(`验收数据已落库：vendorId=${vendorId} modelId=${modelId} modelUid=acc-model-${suffix}`)
}

main().catch((e) => {
  console.error('验收脚本异常:', e.message)
  process.exit(2)
})
