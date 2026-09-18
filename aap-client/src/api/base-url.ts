/**
 * 接口基址解析 —— 小程序前后端联调的关键分歧点
 *
 * 背景（真实缺陷，2026-09-19 联调发现）：
 *   原先 `src/api/http.ts` 把基址硬编码为 `'/api/v1'`（相对路径）。
 *   H5 能跑通，是因为 dev server 的 `server.proxy` 把 `/api` 反代到 aap-server:8084；
 *   小程序里 `uni.request` 直接落到 `wx.request`，**相对 URL 一律失败**（request:fail invalid url），
 *   且小程序运行时不存在 proxy。
 *   → 必须按平台解析：H5 用相对路径（同源 / dev 反代），小程序用绝对 URL。
 *
 * 平台判据：`uni.getSystemInfoSync().uniPlatform`
 *   实测产物取值：H5 = "web"（uni-h5 内联），mp-weixin = "mp-weixin"（dist/build/mp-weixin/common/vendor.js）。
 *   取不到（vitest / 未知平台）按 H5 处理，避免误伤。
 *
 * 优先级：构建期 `VITE_API_BASE` > 平台默认。
 *   - 生产小程序必须显式配 `VITE_API_BASE=https://<已备案域名>/api/v1`（微信要求 https + 域名白名单）；
 *   - 本地联调不配时回落到 `MP_DEV_API_BASE`，需在微信开发者工具里勾「不校验合法域名」。
 */

/** H5 默认：相对路径，交由同源部署或 dev server 反代 */
export const H5_API_BASE = '/api/v1'

/** 小程序本地联调默认：必须是绝对 URL（127.0.0.1 仅开发者工具可用，真机不可达） */
export const MP_DEV_API_BASE = 'http://127.0.0.1:8084/api/v1'

const ABSOLUTE_RE = /^https?:\/\//i

/**
 * 解析接口基址。
 * @param configured 构建期注入的 VITE_API_BASE（可为空）
 * @param uniPlatform uni.getSystemInfoSync().uniPlatform 的取值
 * @throws 小程序平台给了相对基址时抛错（fail fast，防止把 H5 的写法带进小程序）
 */
export function resolveApiBase(
  configured: string | undefined,
  uniPlatform: string | undefined
): string {
  const isWeb = !uniPlatform || uniPlatform === 'web'
  const raw = (configured ?? '').trim() || (isWeb ? H5_API_BASE : MP_DEV_API_BASE)
  const normalized = raw.replace(/\/+$/, '')

  if (!isWeb && !ABSOLUTE_RE.test(normalized)) {
    throw new Error(
      `[api] 小程序平台（uniPlatform=${uniPlatform}）的接口基址必须是绝对 URL，` +
        `当前为 "${normalized}"。小程序运行时没有 proxy，相对路径会被 wx.request 拒绝。`
    )
  }
  return normalized
}

/** 读取当前运行的 uni 平台标识；取不到返回 undefined（调用方按 H5 处理） */
export function currentUniPlatform(): string | undefined {
  try {
    const info = uni.getSystemInfoSync() as { uniPlatform?: string } | undefined
    return info?.uniPlatform
  } catch {
    return undefined
  }
}
