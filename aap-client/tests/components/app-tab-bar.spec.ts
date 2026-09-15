/**
 * 序号 21 新增共享组件 · 底部 TabBar（AppTabBar）— 单测（切片 3）
 *
 * 设计真源：
 *  · page-21-2 `底部TabBar`（design id=9385b03b）：padding 8/0/24 · 4 项各 104 宽 ·
 *    图标 33 块（remixicon 22）+ 3 + 文字 16（11px）= 84 高；高亮「我的」= rgba(37,99,235,1) #2563EB，常规 #94A3B8
 *  · page-20-2 `TabBar`（design id=c02e59d8）：**同一版式**，高亮色 rgba(0,122,255,1) #007AFF →
 *    故抽成共享组件 + activeColor prop（台账记：两帧高亮色不同，逐帧传）。
 *
 * 交互真源：本页 TabBar = navigation（我的 = 当前模块不跳转；目标页未实现时由 uni 侧降级，台账已记）。
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppTabBar from '@/components/app-tab-bar/AppTabBar.vue'
import { ACTIVE_TAB, TAB_ACTIVE_COLOR, TAB_COLOR, TAB_ITEMS } from '@/utils/app-tab-bar-model'
import { getCalls } from '../setup'

const DESIGN_LABELS = ['工作台', '报告', '报价', '我的']

function rgbOf(hex: string): string {
  const v = hex.replace('#', '')
  const n = parseInt(v, 16)
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`
}

function mountBar(props: Record<string, unknown> = {}) {
  return mount(AppTabBar, { props: { active: ACTIVE_TAB, ...props } })
}

async function tap(wrapper: ReturnType<typeof mount>, label: string) {
  await wrapper.find(`[data-testid="tab-${label}"]`).trigger('tap')
}

describe('序号 21 · AppTabBar 结构与设计文案', () => {
  it('4 项，标签与设计逐字一致且顺序不变', () => {
    const wrapper = mountBar()
    const items = wrapper.findAll('[data-testid^="tab-"]')
    expect(items.length).toBe(4)
    expect(items.map((i) => i.find('.tabbar__label').text())).toEqual(DESIGN_LABELS)
  })

  it('默认高亮「我的」（page-21-2 设计帧）', () => {
    const wrapper = mountBar()
    expect(wrapper.find('.tabbar__label--active').text()).toBe(ACTIVE_TAB)
  })

  it('每项 = 图标块 + 3 间隙 + 文字（设计 33 + 3 + 16 = 52）', () => {
    const wrapper = mountBar()
    const first = wrapper.findAll('[data-testid^="tab-"]')[0]
    expect(first.find('.tabbar__icon').exists()).toBe(true)
    expect(first.find('.tabbar__gap').exists()).toBe(true)
    expect(first.find('.tabbar__label').exists()).toBe(true)
  })
})

describe('序号 21 · AppTabBar 逐帧取色', () => {
  it('默认高亮色 = #2563EB（page-21-2），常规 #94A3B8', () => {
    const wrapper = mountBar()
    expect(TAB_ACTIVE_COLOR).toBe('#2563EB')
    expect(TAB_COLOR).toBe('#94A3B8')
    const activeLabel = wrapper.find('.tabbar__label--active')
    expect(activeLabel.attributes('style')).toContain(rgbOf(TAB_ACTIVE_COLOR))
  })

  it('page-20-2 帧传 activeColor=#007AFF → 高亮色随帧变化，常规色不变', () => {
    const wrapper = mountBar({ activeColor: '#007AFF' })
    expect(wrapper.find('.tabbar__label--active').attributes('style')).toContain(rgbOf('#007AFF'))
    const inactive = wrapper.findAll('.tabbar__label').find((l) => !l.classes('tabbar__label--active'))
    expect(inactive?.attributes('style')).toContain(rgbOf(TAB_COLOR))
  })

  it('非高亮项文字不加粗、高亮项加粗（design SourceHanSans-SemiBold）', () => {
    const wrapper = mountBar()
    expect(wrapper.find('.tabbar__label--active').classes()).toContain('tabbar__label--active')
  })
})

describe('序号 21 · AppTabBar 交互（navigation）', () => {
  it('4 项落点与画布一致（工作台 / 报告 / 报价 / 我的）', () => {
    expect(TAB_ITEMS.map((t) => t.label)).toEqual(DESIGN_LABELS)
    expect(TAB_ITEMS.map((t) => t.url)).toEqual([
      '/pages/workbench/index',
      '/pages/report/index',
      '/pages/quotes/index',
      '/pages/mine/index'
    ])
  })

  it('点「工作台」→ navigateTo 到工作台', async () => {
    const wrapper = mountBar()
    await tap(wrapper, '工作台')
    expect((getCalls('navigateTo')[0].args[0] as Record<string, unknown>).url).toBe('/pages/workbench/index')
  })

  it('点「报告」→ navigateTo /pages/report/index（列表页未实现，登记台账）', async () => {
    const wrapper = mountBar()
    await tap(wrapper, '报告')
    expect((getCalls('navigateTo')[0].args[0] as Record<string, unknown>).url).toBe('/pages/report/index')
  })

  it('点「报价」→ navigateTo 报价单列表', async () => {
    const wrapper = mountBar()
    await tap(wrapper, '报价')
    expect((getCalls('navigateTo')[0].args[0] as Record<string, unknown>).url).toBe('/pages/quotes/index')
  })

  it('点当前高亮项「我的」→ 不跳转（本模块）', async () => {
    const wrapper = mountBar()
    await tap(wrapper, '我的')
    expect(getCalls('navigateTo').length).toBe(0)
  })

  it('page-20-2 帧（active=我的）行为一致：点「我的」不跳转', async () => {
    const wrapper = mountBar({ activeColor: '#007AFF' })
    await tap(wrapper, '我的')
    expect(getCalls('navigateTo').length).toBe(0)
  })
})
