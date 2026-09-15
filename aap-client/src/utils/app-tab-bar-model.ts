/**
 * 底部 TabBar 共享模型（序号 21 抽出）
 *
 * 设计真源（两帧同一版式，仅高亮色不同）：
 *  · page-21-2 `底部TabBar`（id=9385b03b）padding 8/0/24 · 4 项各 104 · 图标 33 + 3 + 文字 16 = 84 高
 *    高亮「我的」= rgba(37,99,235,1) #2563EB · 常规 rgba(148,163,184,1) #94A3B8
 *  · page-20-2 `TabBar`（id=c02e59d8）同版式，高亮色 rgba(0,122,255,1) #007AFF
 *    → 抽成共享组件 + activeColor prop（逐帧传），避免每页各写一套（SKILL §2.6 设计系统复用）
 *
 * 交互真源：TabBar = navigation；当前模块（我的）不跳转；目标页未实现时由 uni 侧降级（台账已记）。
 */
import { MINE_PAGE, QUOTES_PAGE, REPORT_PAGE, WORKBENCH_PAGE } from './routes'

export interface TabItem {
  label: string
  url: string
}

/** 4 项（设计帧顺序：工作台 / 报告 / 报价 / 我的） */
export const TAB_ITEMS: TabItem[] = [
  { label: '工作台', url: WORKBENCH_PAGE },
  { label: '报告', url: REPORT_PAGE },
  { label: '报价', url: QUOTES_PAGE },
  { label: '我的', url: MINE_PAGE }
]

/** 当前模块（两帧都高亮「我的」） */
export const ACTIVE_TAB = '我的'

/** 常规色（两帧一致） */
export const TAB_COLOR = '#94A3B8'
/** 默认高亮色 = page-21-2 帧（page-20-2 传 #007AFF 覆盖） */
export const TAB_ACTIVE_COLOR = '#2563EB'

/** 是否当前模块（不跳转） */
export function isActiveTab(label: string, active: string = ACTIVE_TAB): boolean {
  return label === active
}

/** 图标字形色 */
export function tabGlyphColor(label: string, active: string = ACTIVE_TAB, activeColor: string = TAB_ACTIVE_COLOR): string {
  return isActiveTab(label, active) ? activeColor : TAB_COLOR
}

/** 文字色 */
export function tabLabelColor(label: string, active: string = ACTIVE_TAB, activeColor: string = TAB_ACTIVE_COLOR): string {
  return isActiveTab(label, active) ? activeColor : TAB_COLOR
}

/** 落点：当前模块或空 url → 空串（不跳转） */
export function resolveTabTarget(url: string, label: string, active: string = ACTIVE_TAB): string {
  if (isActiveTab(label, active)) return ''
  return url || ''
}
