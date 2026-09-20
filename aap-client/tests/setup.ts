/**
 * vitest 全局环境：为 uni-app 专有全局对象打桩。
 * 每个用例都能通过 globalThis.__uniCalls 断言"页面到底调了哪些 uni API"。
 */
import { beforeEach, vi } from 'vitest'

export interface UniCall {
  api: string
  args: unknown[]
}

const calls: UniCall[] = []

function record(api: string, args: unknown[]) {
  calls.push({ api, args })
}

/** 可编程的 uni.request 响应 */
export interface MockResponse {
  statusCode: number
  data: unknown
  fail?: boolean
}

let queue: MockResponse[] = []
let last: MockResponse = { statusCode: 200, data: { code: '0', message: 'ok', data: {} } }

/** uni.showModal 的「确认/取消」答案（页面类交互会用，如序号 8 删除二次确认） */
let modalAnswer = true

export function setModalAnswer(confirm: boolean) {
  modalAnswer = confirm
}

export function pushResponse(r: MockResponse) {
  queue.push(r)
}

export function setNextResponse(r: MockResponse) {
  last = r
}

export function resetUniMock() {
  calls.length = 0
  queue = []
  last = { statusCode: 200, data: { code: '0', message: 'ok', data: {} } }
  modalAnswer = true
  storage.clear()
}

export const storage = new Map<string, string>()

export function getCalls(api?: string): UniCall[] {
  return api ? calls.filter((c) => c.api === api) : calls.slice()
}

/**
 * 「可用模型目录」(`GET /catalog/models`) —— 凭证页会**并行**取它作为候选模型
 * （管理端维护的目录；见 src/api/catalog.ts）。
 *
 * ⚠️ 底座处理方式，以及为什么：
 *   1. **给空数据**：既有用例的详情 fixture 自带 model_catalog，页面对「详情已有目录」
 *      走详情那条路；若底座塞真数据会多渲染厂商组，把设计稿断言的渲染结果改掉。
 *   2. **不 record 调用**：这个请求是**基础设施**，不是被测行为；若记录，
 *      所有 `getCalls('request')` 的条数断言都要跟着 +1 平白改动。
 *   两条合起来 → 既有用例一字不改即可继续通过。
 *   **专测这条接线的用例**请用 vi.mock('@/api/catalog')（见
 *   tests/pages/credential-catalog-wiring.spec.ts），而不是依赖底座。
 */
const CATALOG_URL_MARK = '/catalog/models'

const uniStub = {
  request(options: Record<string, unknown>) {
    const url = String((options as { url?: string }).url ?? '')
    if (url.includes(CATALOG_URL_MARK)) {
      // 目录：空数据 + 不 record（理由见上方注释）
      const complete = options.complete as ((r: unknown) => void) | undefined
      const success = options.success as ((r: unknown) => void) | undefined
      const payload = { statusCode: 200, data: { code: '0', message: 'ok', data: [] }, header: {}, cookies: [] }
      Promise.resolve().then(() => {
        success?.(payload)
        complete?.(payload)
      })
      return { abort: vi.fn() }
    }
    record('request', [options])
    const resp = queue.length ? (queue.shift() as MockResponse) : last
    const complete = options.complete as ((r: unknown) => void) | undefined
    const success = options.success as ((r: unknown) => void) | undefined
    const fail = options.fail as ((r: unknown) => void) | undefined
    const payload = { statusCode: resp.statusCode, data: resp.data, header: {}, cookies: [] }
    // uni.request 是异步的：这里用微任务模拟，避免同步回调让测试失去意义
    Promise.resolve().then(() => {
      if (resp.fail) {
        fail?.({ errMsg: 'request:fail' })
      } else {
        success?.(payload)
      }
      complete?.(payload)
    })
    return { abort: vi.fn() }
  },
  showToast(options: Record<string, unknown>) {
    record('showToast', [options])
  },
  hideToast(options: Record<string, unknown> = {}) {
    record('hideToast', [options])
  },
  showLoading(options: Record<string, unknown>) {
    record('showLoading', [options])
  },
  hideLoading(options: Record<string, unknown> = {}) {
    record('hideLoading', [options])
  },
  navigateTo(options: Record<string, unknown>) {
    record('navigateTo', [options])
  },
  redirectTo(options: Record<string, unknown>) {
    record('redirectTo', [options])
  },
  switchTab(options: Record<string, unknown>) {
    record('switchTab', [options])
  },
  navigateBack(options: Record<string, unknown> = {}) {
    record('navigateBack', [options])
  },
  // 序号 12-v3（保存成功页）：关闭 / 返回报价单列表用 reLaunch 清栈
  reLaunch(options: Record<string, unknown>) {
    record('reLaunch', [options])
  },
  // 序号 12-v3：复制报价单号
  setClipboardData(options: Record<string, unknown>) {
    record('setClipboardData', [options])
    const success = options.success as ((r: unknown) => void) | undefined
    // uni.setClipboardData 是异步的：用微任务模拟（与 request/showModal 一致）
    Promise.resolve().then(() => success?.({ errMsg: 'setClipboardData:ok' }))
  },
  // 序号 15（合同签署）：PDF 下载 → downloadFile + openDocument
  downloadFile(options: Record<string, unknown>) {
    record('downloadFile', [options])
    const success = options.success as ((r: unknown) => void) | undefined
    Promise.resolve().then(() =>
      success?.({ statusCode: 200, tempFilePath: '/tmp/x.pdf', errMsg: 'downloadFile:ok' })
    )
    return { abort: vi.fn() }
  },
  openDocument(options: Record<string, unknown>) {
    record('openDocument', [options])
    const success = options.success as ((r: unknown) => void) | undefined
    Promise.resolve().then(() => success?.({ errMsg: 'openDocument:ok' }))
    return { abort: vi.fn() }
  },
  showModal(options: Record<string, unknown>) {
    record('showModal', [options])
    const success = options.success as ((r: unknown) => void) | undefined
    // uni.showModal 是异步的：用微任务模拟（与 request 一致）
    Promise.resolve().then(() => success?.({ confirm: modalAnswer, cancel: !modalAnswer }))
    return { abort: vi.fn() }
  },
  setStorageSync(key: string, value: string) {
    record('setStorageSync', [key, value])
    storage.set(key, value)
  },
  getStorageSync(key: string) {
    record('getStorageSync', [key])
    return storage.get(key) ?? ''
  },
  removeStorageSync(key: string) {
    record('removeStorageSync', [key])
    storage.delete(key)
  },
  login(options: Record<string, unknown>) {
    record('login', [options])
    const success = options.success as ((r: unknown) => void) | undefined
    Promise.resolve().then(() =>
      success?.({ code: 'wx-code-from-stub', errMsg: 'login:ok' })
    )
  },
  getSystemInfoSync() {
    return { platform: 'devtools', statusBarHeight: 20, windowWidth: 375, windowHeight: 812 }
  }
}

// @ts-expect-error 测试环境注入
globalThis.uni = uniStub
// @ts-expect-error 测试环境注入
globalThis.wx = { login: uniStub.login }

beforeEach(() => {
  resetUniMock()
})
