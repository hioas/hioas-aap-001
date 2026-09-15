/**
 * 页面 1 — 短信验证码 60s 频控（R-02 / AC-03）
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createCooldown } from '@/utils/cooldown'

describe('createCooldown：60 秒频控', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('初始未激活，remaining=0', () => {
    const cd = createCooldown(60)
    expect(cd.active.value).toBe(false)
    expect(cd.remaining.value).toBe(0)
  })

  it('start 后 active=true，remaining=60，按钮文案应为「60s 后重发」', () => {
    const cd = createCooldown(60)
    cd.start()
    expect(cd.active.value).toBe(true)
    expect(cd.remaining.value).toBe(60)
    expect(cd.label('获取验证码')).toBe('60s 后重发')
  })

  it('1 秒后 remaining=59', () => {
    const cd = createCooldown(60)
    cd.start()
    vi.advanceTimersByTime(1000)
    expect(cd.remaining.value).toBe(59)
  })

  it('60 秒后自动解除，label 回到默认文案', () => {
    const cd = createCooldown(60)
    cd.start()
    vi.advanceTimersByTime(60_000)
    expect(cd.remaining.value).toBe(0)
    expect(cd.active.value).toBe(false)
    expect(cd.label('获取验证码')).toBe('获取验证码')
  })

  it('冷却期内再次 start 不重置计时（防连点绕过频控）', () => {
    const cd = createCooldown(60)
    cd.start()
    vi.advanceTimersByTime(30_000)
    cd.start()
    expect(cd.remaining.value).toBe(30)
  })

  it('stop 清理定时器，不残留 timer', () => {
    const cd = createCooldown(60)
    cd.start()
    cd.stop()
    expect(vi.getTimerCount()).toBe(0)
  })
})
