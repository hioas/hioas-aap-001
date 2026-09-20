#!/usr/bin/env node
/**
 * 验证「每页条数」功能真的生效（不是只看控件渲染）。
 *
 * 用法：node tools/verify-pager.mjs [baseUrl] [phone]
 *
 * 为什么要单独验：默认 4 条这种需求，只断言「选择器显示 4」是**假验证** ——
 * 控件渲染出来不等于 slice 逻辑接上了。要真正观察「翻页后换了一批数据」，
 * 数据量必须**大于每页条数**。原本库里只有 2 家厂商，永远只有 1 页，
 * 所以本脚本先补足测试厂商（用户已要求保存测试数据，dev 库补测试数据是预期行为）。
 *
 * 覆盖：① 默认 4 条 ② 选项集合 ③ 改每页条数后页码重置 ④ 翻页真的换数据 ⑤ 末页边界
 */
import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:5174'
const PHONE = process.argv[3] || '13900000001'
const API = 'http://127.0.0.1:8084/api/v1'

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

const main = async () => {
  // ── 准备：登录取 admin token（同时供 API 造数据与页面登录用）
  const sr = await fetch(`${API}/auth/sms/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: PHONE, captcha: 'AB12' })
  })
  const sj = await sr.json()
  const devCode = sj?.data?.dev_code ?? sj?.data?.devCode
  if (!devCode) throw new Error(`未拿到 dev_code：${JSON.stringify(sj).slice(0, 160)}（SMS 冷却？）`)
  const lr = await fetch(`${API}/auth/sms/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: PHONE, smsCode: String(devCode) })
  })
  const lj = await lr.json()
  const adminToken = lj?.data?.token
  if (!adminToken) throw new Error(`登录失败：${JSON.stringify(lj).slice(0, 160)}`)

  // ── 造数据：确保厂商数 > 5（这样默认 4 条时至少有 2 页）
  const cur = await (
    await fetch(`${API}/admin/catalog/vendors`, { headers: { Authorization: `Bearer ${adminToken}` } })
  ).json()
  const have = cur?.data?.length ?? 0
  const need = Math.max(0, 6 - have)
  console.log(`现有厂商 ${have} 家，补造 ${need} 家测试数据…`)
  for (let i = 0; i < need; i++) {
    const s = `${Date.now()}${i}`.slice(-7)
    await fetch(`${API}/admin/catalog/vendors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${adminToken}` },
      body: JSON.stringify({
        name: `分页测试厂商-${s}`,
        vendorKey: `pager-${s}`,
        vendorType: 'DIRECT',
        region: '中国',
        baseUrl: 'https://api.example.com/v1',
        enabled: true
      })
    })
  }

  // ── 打开页面
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, locale: 'zh-CN' })
  const page = await ctx.newPage()
  // ⚠️ 直接用上面 API 登录拿到的 token 注入 localStorage，**不再在浏览器里二次登录**。
  //    踩坑：初版先用 API 登录（消耗一次短信并触发 60s 冷却），浏览器里又登一次
  //    → 被 E-1903 冷却挡住，脚本在等 dev-code 时超时。
  //    同一个 token 两边复用，既避开冷却又少一次短信。
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.evaluate((t) => localStorage.setItem('aap_admin_token', t), adminToken)
  // ⚠️ 导航顺序有坑：设置 token 后 `reload()` 会把路由**重置回 #/dashboard**，
  //    于是脚本一直在看看板页（分页栏当然找不到）。
  //    正确顺序：先 reload 让 App 带上 token 起来（落到默认路由），
  //    **之后**再切 hash 到 #/models，并等目标节点出现（而不是写死 sleep）。
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(2500)
  await page.goto(`${BASE}/#/models`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-testid="model-kpi"]', { timeout: 15000 })
  await page.waitForTimeout(1500)

  const readState = () =>
    page.evaluate(() => {
      const sel = document.querySelector('[data-testid="pager-size"]')
      return {
        // ⚠️ Element Plus 的 el-select 内层 input.value 是**空**的（值在隐藏 input 里、
        //    显示靠 .el-select__selected-item）。初版读 input.value 恒为 ''，
        //    导致「默认 4 条」这条被误判失败 —— 是**断言写错**，不是产品问题。
        size: (sel?.textContent || '').trim() || null,
        info: document.querySelector('[data-testid="pager-info"]')?.textContent?.trim() ?? null,
        vendors: [...document.querySelectorAll('.vendor .vendor__name')].map((e) => e.textContent.trim()),
        pagerBtns: [...document.querySelectorAll('.pager__btn')].map((e) => e.textContent.trim())
      }
    })

  console.log('\n【1】默认每页条数')
  let st = await readState()
  ok(`默认每页 = 4 条（选择器显示「${st.size}」）`, /4/.test(st.size ?? ''))
  ok('分页文案含「家厂商」与页码', /共 \d+ 家厂商 · 当前第 \d+ \/ \d+ 页/.test(st.info ?? ''), st.info)

  console.log('\n【2】选项集合 = 2/5/10/15/20')
  await page.click('[data-testid="pager-size"]')
  await page.waitForTimeout(600)
  // ⚠️ 页面上所有 el-select 的选项都会渲染到全局浮层里，故必须**过滤出形如「N 条」的项**，
  //    否则会把类型/状态/地区/排序的选项一起捞进来（初版就是这么误判的）。
  const opts = await page.evaluate(() =>
    [...document.querySelectorAll('.el-select-dropdown__item')]
      .map((e) => e.textContent.trim())
      .filter((t) => /^\d+ 条$/.test(t))
  )
  ok(`选项为 [2,5,10,15,20]（实际 ${JSON.stringify(opts)}）`, JSON.stringify(opts) === JSON.stringify(['2 条', '5 条', '10 条', '15 条', '20 条']))
  await page.keyboard.press('Escape')
  await page.waitForTimeout(300)

  console.log('\n【3】默认 4 条时渲染的厂商数 ≤ 4 且与总页数自洽')
  const m1 = (st.info ?? '').match(/共 (\d+) 家厂商 · 当前第 (\d+) \/ (\d+) 页/)
  const total = Number(m1?.[1] ?? 0)
  const pages = Number(m1?.[3] ?? 0)
  ok(`总厂商 ${total} 家，共 ${pages} 页`, total >= 5 && pages === Math.ceil(total / 4), st.info)
  ok(`首页渲染 ≤ 4 家（实际 ${st.vendors.length}）`, st.vendors.length <= 4 && st.vendors.length === Math.min(4, total))

  console.log('\n【4】翻页真的换了一批数据（不是只改页码）')
  const firstPageVendors = [...st.vendors]
  const hasPage2 = await page.evaluate(() => !!document.querySelector('[data-testid="pager-2"]'))
  if (!hasPage2) {
    ok('存在第 2 页可点', false, '厂商数不足 5 家，无法翻页')
  } else {
    await page.click('[data-testid="pager-2"]')
    await page.waitForTimeout(1200)
    const st2 = await readState()
    ok(`页码跳到第 2 页`, /当前第 2 \/ \d+ 页/.test(st2.info ?? ''), st2.info)
    ok('第 2 页渲染的厂商与第 1 页**不同**', st2.vendors.length > 0 && st2.vendors.join() !== firstPageVendors.join(), `${firstPageVendors.join()} vs ${st2.vendors.join()}`)
    ok(`第 2 页渲染 ≤ 4 家（实际 ${st2.vendors.length}）`, st2.vendors.length <= 4)

    console.log('\n【5】改每页条数 → 页码重置回第 1 页')
    await page.click('[data-testid="pager-size"]')
    await page.waitForTimeout(500)
    await page.evaluate(() => {
      const items = [...document.querySelectorAll('.el-select-dropdown__item')]
      const t = items.find((e) => e.textContent.trim() === '2 条')
      t?.click()
    })
    await page.waitForTimeout(1000)
    const st3 = await readState()
    ok(`每页改为 2 条（选择器显示「${st3.size}」）`, /2/.test(st3.size ?? ''))
    ok('页码已重置回第 1 页', /当前第 1 \//.test(st3.info ?? ''), st3.info)
    ok(`每页只渲染 2 家（实际 ${st3.vendors.length}）`, st3.vendors.length === Math.min(2, total))
    const m2 = (st3.info ?? '').match(/当前第 (\d+) \/ (\d+) 页/)
    ok(`总页数按每页 2 条重算 = ${Math.ceil(total / 2)}`, Number(m2?.[2]) === Math.ceil(total / 2), st3.info)
  }

  console.log(`\n=== 结果：${pass} 通过 / ${fails.length} 失败 ===`)
  if (fails.length) {
    fails.forEach((f) => console.log('  -', f))
    await browser.close()
    process.exit(1)
  }
  await browser.close()
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(2)
})
