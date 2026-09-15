/**
 * 序号 8【报价管理】报价单列表（page-8-2）设计稿文案逐字抄录（真源）
 * 来源：.calicat/raw/pages/page-8-2/design.tree.json（430 宽；页面总高 1206，已用像素色带量得：
 *   顶部导航 0..89 · 筛选行 90..143 · 列表 144..1105（卡高 178 · 卡间距 12）· 底部 TabBar 1122..1205）
 * 用途：实现后用它做文案一致性断言（缺字/改字会被钉死）。
 */

export const DESIGN_TITLE = '报价单'

/** 顶部导航右侧按钮（design id=7ccb56ba，97×30 · r10 · #2563EB） */
export const DESIGN_NEW_QUOTE = '新建报价'

/** 筛选行 6 个 chip 文案（design id=0bf46fd6 / 33be05d4 / d4c61d43 / cf22a9a9 / ba2b8609 / 10b7c5cc） */
export const DESIGN_FILTERS = ['全部', '草稿', '已提交', '已驳回', '待签署', '已完成']

/** 卡片标题（design id=930bc97e，15px SemiBold #0F172A） */
export const DESIGN_CARD_TITLE = '2024Q3 主线路报价'

/** 单号行（design id=70696608 + f057dca5） */
export const DESIGN_QUOTE_NO_LABEL = '报价单号'
export const DESIGN_QUOTE_NO = 'QT-20240615-0007'

/** 元信息行（design id=ac24812b / fd63dfdb / 06eb7078 / 9cafcec1 / 10b7127f） */
export const DESIGN_META = '2 个模型 · CNY · 更新于 06-14 15:20'

/** 操作行文案（design id=0ac90e56 / b350b307 / 453c280c / c4645581 / 4e8134ef） */
export const DESIGN_ACTIONS = ['报价', '预览', '签署', '合同', '删除']

/** 底部 TabBar 4 项（design id=e5b5a912 / c25edea4 / 6beac6f6 / 7479f598） */
export const DESIGN_TABS = ['工作台', '报告', '报价', '我的']

/** 5 张卡的状态胶囊文案（自上而下，design id=5c7b2f20 / 274472d8 / 29c0f0a7 / 3a47d6c3 / 6f03e4ed） */
export const DESIGN_CARD_STATUSES = ['草稿', '已提交', '已驳回', '待签署', '已完成']

/** 逐卡操作（design 报价卡1 / 卡1_3 / 卡3 / 已完成 / 已完成2 的操作行 kids 数） */
export const DESIGN_CARD_ACTIONS: string[][] = [
  ['报价', '预览', '删除'],
  ['报价', '预览', '删除'],
  ['报价', '预览', '删除'],
  ['报价', '预览', '签署', '删除'],
  ['报价', '预览', '合同', '删除']
]
