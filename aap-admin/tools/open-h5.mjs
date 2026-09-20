#!/usr/bin/env node
/**
 * 打开 aap-client 的 H5 供应商端并**保持浏览器不关闭**（供人工查看）。
 *
 * 用法：node tools/open-h5.mjs [url]
 *   默认 url = http://localhost:5173
 *
 * 依赖 playwright —— 装在本工程（aap-admin）内。Node 的 ESM 按**脚本所在目录**
 * 解析依赖，所以这个脚本放在 aap-admin/tools/ 下，而不是 aap-client/tools/。
 *
 * 不自动登录：H5 端用短信验证码登录（60s 冷却），人工在页面上点更合适。
 * 与 open-admin.mjs 的区别就是这个 —— 那边是管理端，能自动登录。
 */
import { chromium } from 'playwright'

const URL = process.argv[2] || 'http://localhost:5173'

const main = async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: false, args: ['--start-maximized'] })
  const ctx = await browser.newContext({ viewport: { width: 430, height: 900 }, locale: 'zh-CN' })
  const page = await ctx.newPage()

  console.log(`打开 H5 供应商端：${URL}`)
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })

  // 等首屏真正渲染出内容（而不是只等 domcontentloaded）
  try {
    await page.waitForFunction(() => (document.body.innerText || '').trim().length > 20, null, {
      timeout: 25000
    })
  } catch {
    console.log('⚠️ 首屏 25s 内未渲染出文本，可能还在编译（vite 冷启动首转较慢）')
  }
  console.log('URL:', page.url())
  console.log('窗口保持打开，关闭窗口或 Ctrl+C 即结束。')

  await new Promise((resolve) => {
    browser.on('disconnected', resolve)
    process.on('SIGINT', () => {
      browser.close().finally(resolve)
    })
  })
}

main().catch((e) => {
  console.error('打开失败:', e.message)
  process.exit(1)
})
