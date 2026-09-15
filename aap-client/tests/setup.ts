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
  storage.clear()
}

export const storage = new Map<string, string>()

export function getCalls(api?: string): UniCall[] {
  return api ? calls.filter((c) => c.api === api) : calls.slice()
}

const uniStub = {
  request(options: Record<string, unknown>) {
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
