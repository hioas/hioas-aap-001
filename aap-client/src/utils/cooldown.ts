import { getCurrentInstance, onUnmounted, ref, type Ref } from 'vue'

export interface Cooldown {
  active: Ref<boolean>
  remaining: Ref<number>
  start: () => void
  stop: () => void
  /** 冷却中显示「<n>s 后重发」，否则显示默认文案 */
  label: (defaultLabel: string) => string
}

/**
 * 通用倒计时（R-02 60s 频控 / 短信重发）
 * 关键：冷却期内重复 start 不重置计时，避免连点绕过频控。
 */
export function createCooldown(seconds = 60, autoDispose = true): Cooldown {
  const active = ref(false)
  const remaining = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null

  function stop() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
    remaining.value = 0
    active.value = false
  }

  function start() {
    if (active.value) return
    active.value = true
    remaining.value = seconds
    timer = setInterval(() => {
      remaining.value -= 1
      if (remaining.value <= 0) stop()
    }, 1000)
  }

  // 只在组件内注册自动清理，页面外调用（脚本/测试）不产生 Vue warn
  if (autoDispose && getCurrentInstance()) onUnmounted(stop)

  return {
    active,
    remaining,
    start,
    stop,
    label: (defaultLabel: string) => (active.value ? `${remaining.value}s 后重发` : defaultLabel)
  }
}
