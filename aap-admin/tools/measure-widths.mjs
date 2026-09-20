#!/usr/bin/env node
/**
 * 量取模型管理页里「厂商分组模块」与「分页栏」的实际宽度，验证两者对齐。
 *
 * 用法：node tools/measure-widths.mjs [baseUrl] [phone]
 *
 * 为什么要实测而不是看 CSS 推理：两者同为 aap-card__body 的子元素**理论上**同宽，
 * 但父容器 padding / box-sizing / 自身 padding 任一环节都能让实际宽度差几像素 ——
 * 「看起来对齐」和「量出来对齐」是两回事。用户明确要求两者一致，就必须量。
 */
import { chromium } from 'playwright'

const BASE = process.argv[2] || 'http://127.0.0.1:5174'
const PHONE = process.argv[3] || '13900000001'

const main = async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, locale: 'zh-CN' })
  const page = await ctx.newPage()

  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.locator('[data-testid="phone"]').waitFor({ state: 'visible', timeout: 25000 })
  const captcha = (await page.locator('[data-testid="captcha-text"]').innerText()).trim()
  await page.locator('[data-testid="phone"]').fill(PHONE)
  await page.locator('[data-testid="captcha"]').fill(captcha)
  await page.locator('[data-testid="sms-btn"]').click()
  await page.locator('[data-testid="dev-code"]').waitFor({ state: 'visible', timeout: 12000 })
  const code = (await page.locator('[data-testid="dev-code"]').innerText()).replace(/\D/g, '')
  await page.locator('[data-testid="sms-code"]').fill(code)
  await page.locator('[data-testid="submit"]').click()
  await page.waitForFunction(() => !!localStorage.getItem('aap_admin_token'), null, { timeout: 15000 })

  await page.goto(`${BASE}/#/models`, { waitUntil: 'domcontentloaded' })
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(3000)

  const m = await page.evaluate(() => {
    const box = (sel) => {
      const e = document.querySelector(sel)
      if (!e) return null
      const r = e.getBoundingClientRect()
      const cs = getComputedStyle(e)
      return {
        x: Math.round(r.x),
        w: Math.round(r.width),
        pad: cs.padding,
        border: cs.borderTopWidth,
        bg: cs.backgroundColor,
        radius: cs.borderRadius
      }
    }
    return {
      vendorCount: document.querySelectorAll('.vendor').length,
      vendor: box('.vendor'),
      pager: box('.pager'),
      body: box('.aap-card__body'),
      info: document.querySelector('[data-testid="pager-info"]')?.textContent?.trim() ?? null
    }
  })

  console.log('厂商分组模块 (.vendor):', JSON.stringify(m.vendor))
  console.log('分页栏      (.pager) :', JSON.stringify(m.pager))
  console.log('内容区      (__body) :', JSON.stringify(m.body))
  console.log('分页文案:', m.info)
  console.log(`页面上 .vendor 数量: ${m.vendorCount}`)

  if (!m.vendor || !m.pager) {
    console.log('\n⚠️ 缺少对比对象（可能是空目录：没有厂商时 .vendor 与分页栏都不渲染）')
  } else {
    const dw = m.pager.w - m.vendor.w
    const dx = m.pager.x - m.vendor.x
    console.log(`\n宽度差 = ${dw}px，左边界差 = ${dx}px`)
    console.log(dw === 0 && dx === 0 ? '✅ 宽度与左边界完全一致' : '❌ 未对齐')
    const boxy = m.pager.border !== '0px' || (m.pager.bg && !/rgba\(0, 0, 0, 0\)/.test(m.pager.bg))
    console.log(boxy ? `❌ 仍有框体：border=${m.pager.border} bg=${m.pager.bg}` : '✅ 已去掉框体（无边框、透明背景）')
  }

  await browser.close()
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(1)
})
