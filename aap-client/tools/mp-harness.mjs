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
import { tmpdir } from 'node:os'

const here = dirname(fileURLToPath(import.meta.url))
export const DIST_API = resolve(here, '../dist/build/mp-weixin/api')

/**
 * 基址归一化：确保以 `/api/v1` 结尾。
 * 为什么要：产物里的 API_BASE 由**构建期** `VITE_API_BASE` 决定，而联调常临时换后端
 * （如换到带本地修复的 8086）。调用方写 `http://host:port` 是自然写法，但直连请求
 * 会因此丢掉 `/api/v1` 前缀（实测：POST /credentials → E-1406 假失败）。
 */
function normalizeApiBase(raw) {
  const u = new URL(String(raw));
  const p = u.pathname.replace(/\/+$/, '');
  return `${u.origin}${p && p !== '/' ? p : '/api/v1'}`.replace(/\/+$/, '');
}

/**
 * 沙箱根目录：**必须放在项目外**。
 * 放在项目内会被 vite dev server 的文件监听捕获，创建/删除时把 dev server 直接打崩
 * （实测：`EBUSY` → dev server 退出，5173 拒绝连接）。放 tmpdir 就彻底不在监听范围内。
 */
const SANDBOX_ROOT = join(tmpdir(), 'aap-mp-sandboxes')

/**
 * 建一个跑小程序产物的沙箱运行时。
 * @param {{ apiBase?: string, sandboxName?: string }} opts
 * @returns {{ mods: Record<string, any>, storage: Map<string,string>, traffic: Array, uniStub: object, cleanup: () => void }}
 */
export function createMpRuntime(opts = {}) {
  // 基址归一化：AAP_API_BASE 常被写成 `http://127.0.0.1:8086`（漏 /api/v1）→ 直连 raw() 会打到
  // 不存在的路径（实测 POST /credentials 得 E-1406）。这里统一补全，客户端请求与直连请求用同一个基址。
  const apiBase = normalizeApiBase(
    opts.apiBase || process.env.AAP_API_BASE || 'http://127.0.0.1:8084/api/v1'
  )
  /** 是否显式指定了后端（用于判断要不要改写产物里的构建期基址） */
  const targetBase = process.env.AAP_API_BASE ? apiBase : ''
  const redirects = []
  const sandbox = join(SANDBOX_ROOT, `${opts.sandboxName || 'mp-harness'}-${process.pid}`)

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
    // 基址重定向（**仅当显式设置 AAP_API_BASE**）：产物里的 API_BASE 是构建期常量，
    // 而联调常要换后端（例如换到带本地修复的 8086）。这里只改 origin + /api/v1 前缀，
    // 路径与 query 原样保留；每次改写都记一条 redirects，避免"悄悄打到别的后端"掩盖问题。
    if (targetBase) {
      try {
        const u = new URL(rawUrl)
        const tb = new URL(targetBase)
        const path = u.pathname.replace(/^\/api\/v1/, '') || '/'
        const to = `${tb.origin}${tb.pathname.replace(/\/+$/, '')}${path}${u.search}`
        if (to !== rawUrl) {
          redirects.push({ from: rawUrl, to })
          url = to
        }
      } catch { /* 非法 URL → 交给下面 fail 分支 */ }
    }
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
    /** 构建期基址被改写为 AAP_API_BASE 的记录（非空即说明本次跑的不是产物里的默认后端） */
    redirects,
    cleanup: () => rmSync(sandbox, { recursive: true, force: true })
  }
}
