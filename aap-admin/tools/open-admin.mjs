#!/usr/bin/env node
/**
 * 打开管理端并**保持浏览器不关闭**（供人工查看）。
 *
 * 用法：node tools/open-admin.mjs [baseUrl] [phone]
 *   默认 baseUrl = http://127.0.0.1:5174，phone = 13900000001（超管）
 *
 * 行为：启动本地 Chrome（有头）→ 自动登录 → 停在状态看板 → 进程常驻不退出，
 * 关闭窗口或 Ctrl+C 才结束。之所以不自动 close：这个脚本的用途就是「打开给人看」。
 */
import { chromium } from 'playwright';

const BASE = process.argv[2] || 'http://127.0.0.1:5174';
const PHONE = process.argv[3] || '13900000001';

const main = async () => {
  const browser = await chromium.launch({
    channel: 'chrome',
    headless: false,
    args: ['--start-maximized']
  });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, locale: 'zh-CN' });
  const page = await ctx.newPage();

  console.log(`打开管理端：${BASE}（账号 ${PHONE}）`);
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.locator('[data-testid="phone"]').waitFor({ state: 'visible', timeout: 25000 });

  const captcha = (await page.locator('[data-testid="captcha-text"]').innerText()).trim();
  await page.locator('[data-testid="phone"]').fill(PHONE);
  await page.locator('[data-testid="captcha"]').fill(captcha);

  await page.locator('[data-testid="sms-btn"]').click();
  await page.locator('[data-testid="dev-code"]').waitFor({ state: 'visible', timeout: 12000 });
  const code = (await page.locator('[data-testid="dev-code"]').innerText()).replace(/\D/g, '');
  await page.locator('[data-testid="sms-code"]').fill(code);
  await page.locator('[data-testid="submit"]').click();

  await page.waitForFunction(() => !!localStorage.getItem('aap_admin_token'), null, { timeout: 15000 });
  await page.goto(`${BASE}/#/dashboard`, { waitUntil: 'domcontentloaded' });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  console.log('已登录并停在「进件状态看板」。浏览器保持打开，关闭窗口即结束。');
  // 常驻：等浏览器被关掉
  await new Promise((resolve) => {
    browser.on('disconnected', resolve);
    process.on('SIGINT', () => {
      browser.close().finally(resolve);
    });
  });
  console.log('浏览器已关闭。');
};

main().catch((e) => {
  console.error('打开失败:', e.message);
  process.exit(2);
});
