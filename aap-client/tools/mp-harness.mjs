/**
 * 小程序联调 harness —— 加载 mp-weixin 编译产物 + 忠实实现微信端语义的 uni 运行时桩
 *
 * 被 tools/check-mp-api-base.mjs（构建门禁）与 tools/mp-e2e*.mjs（联调）共用。
 *
 * 桩的忠实性要求（不得放水，否则联调脚本会自己掩盖缺陷）：
 *   1. `wx.request` 只接受绝对 URL，相对 URL 一律 fail（微信端真实行为）
 *   2. GET/DELETE 把 data 拼进 query，其余方法发 JSON body（wx.request 语义）
 *   3. `uni` 在产物里**不是全局**，是 `require("../common/vendor.js").index`
 *      → 桩必须按 `{ index: {...} }` 的形状提供，否则产物 MODULE_NOT_FOUND
 */
import { mkdirSync, cpSync, writeFileSync, rmSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
export const DIST_API = resolve(here, '../dist/build/mp-weixin/api')

/**
 * 建一个跑小程序产物的沙箱运行时。
 * @param {{ apiBase?: string, sandboxName?: string }} opts
 * @returns {{ mods: Record<string, any>, storage: Map<string,string>, traffic: Array, uniStub: object, cleanup: () => void }}
 */
export function createMpRuntime(opts = {}) {
  const apiBase = opts.apiBase || process.env.AAP_API_BASE || 'http://127.0.0.1:8084/api/v1'
  const sandbox = resolve(here, `../.${opts.sandboxName || 'mp-harness-sandbox'}`)

  rmSync(sandbox, { recursive: true, force: true })
  mkdirSync(join(sandbox, 'common'), { recursive: true })
  cpSync(DIST_API, join(sandbox, 'api'), { recursive: true })

  const storage = new Map()
  const traffic = []

  async function realRequest(options) {
    const rawUrl = String(options.url ?? '')
    if (!/^https?:\/\//.test(rawUrl)) {
      const err = { errMsg: `request:fail invalid url "${rawUrl}"` }
      traffic.push({ url: rawUrl, method: options.method || 'GET', status: 'INVALID_URL' })
      return { fail: err }
    }
    const method = String(options.method ?? 'GET').toUpperCase()
    let url = rawUrl
    const data = options.data
    const init = { method, headers: { ...(options.header || {}) } }

    if (method === 'GET' || method === 'DELETE') {
      if (data && typeof data === 'object') {
        const qs = new URLSearchParams()
        for (const [k, v] of Object.entries(data)) {
          if (v !== undefined && v !== null) qs.append(k, String(v))
        }
        const q = qs.toString()
        if (q) url += (url.includes('?') ? '&' : '?') + q
      }
    } else if (data !== undefined) {
      init.body = JSON.stringify(data)
      init.headers['Content-Type'] = init.headers['Content-Type'] || 'application/json'
    }

    let res
    try {
      res = await fetch(url, init)
    } catch (e) {
      traffic.push({ url, method, status: 'NETWORK_ERROR' })
      return { fail: { errMsg: `request:fail ${e.message}` } }
    }
    const text = await res.text()
    let body
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
    traffic.push({ url, method, status: res.status, code: body && body.code })
    return {
      ok: { statusCode: res.status, data: body, header: Object.fromEntries(res.headers), cookies: [] }
    }
  }

  const uniStub = {
    getSystemInfoSync: () => ({ uniPlatform: 'mp-weixin', platform: 'devtools' }),
    request(options) {
      realRequest(options)
        .then((r) => {
          if (r.fail) options.fail?.(r.fail)
          else options.success?.(r.ok)
          options.complete?.(r.ok ?? r.fail)
        })
        .catch((e) => options.fail?.({ errMsg: `request:fail ${e.message}` }))
      return { abort() {} }
    },
    getStorageSync: (k) => storage.get(k) ?? '',
    setStorageSync: (k, v) => storage.set(k, v),
    removeStorageSync: (k) => storage.delete(k),
    showToast: () => {},
    hideToast: () => {},
    showLoading: () => {},
    hideLoading: () => {},
    showModal: () => ({ abort() {} }),
    setClipboardData: () => {},
    downloadFile: () => ({ abort() {} }),
    openDocument: () => {},
    navigateTo: () => {},
    redirectTo: () => {},
    switchTab: () => {},
    navigateBack: () => {},
    reLaunch: () => {}
  }

  writeFileSync(join(sandbox, 'common', 'vendor.js'), `module.exports = { index: globalThis.__uniStub__ };\n`)
  globalThis.__uniStub__ = uniStub

  const require_ = createRequire(pathToFileURL(join(sandbox, 'api', 'http.js')))
  const mods = {}
  for (const f of ['http', 'auth', 'usage', 'provider', 'credential', 'detection', 'report', 'quote', 'contract', 'notification', 'payment', 'access-application']) {
    try {
      Object.assign(mods, { [f]: require_(join(sandbox, 'api', `${f}.js`)) })
    } catch (e) {
      mods[f] = { __error: e.message }
    }
  }

  return {
    mods,
    storage,
    traffic,
    uniStub,
    apiBase,
    cleanup: () => rmSync(sandbox, { recursive: true, force: true })
  }
}
