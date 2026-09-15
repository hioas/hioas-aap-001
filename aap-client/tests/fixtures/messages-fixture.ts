/**
 * 序号 20【合同与通知】站内信列表（page-20-2）— 设计原文夹具
 *
 * 全部文案**逐字**抄自 .calicat/raw/pages/page-20-2/design.tree.json（不得改写，见状态文件 §3.5）。
 * 设计帧：430 宽 · 设计总高 760（1:1 帧图）。
 * 结构锚点（设计截图像素量尺 png-bands，见本轮状态文件小结）：
 *   顶部导航 0..86 · 筛选行 86..140 · 消息列表区 140..676（5 卡 × 92 + 4 间隙 × 12 + 上内边距 12）
 *   · 卡间距容器 padding-top 12 · TabBar 676..760(84)
 */

export const DESIGN_TITLE = '消息'
export const DESIGN_READ_ALL = '全部已读'
export const DESIGN_UNREAD_BADGE = '3 条未读'

/** 筛选 chip 文案（design: 筛选全部/筛选未读/筛选订单/筛选系统） */
export const DESIGN_FILTERS = ['全部', '未读', '订单', '系统']

/** 底部 TabBar 文案（design: Tab工作台/Tab报告 2/Tab报价/Tab我的） */
export const DESIGN_TABS = ['工作台', '报告', '报价', '我的']

/** 高亮 Tab（design: Tab我的 字号 22 填充 rgba(0,122,255,1)） */
export const DESIGN_ACTIVE_TAB = '我的'

/** 设计帧里 5 条站内信的逐字文案（标题 / 摘要 / 时间） */
export const DESIGN_MESSAGES = [
  {
    title: '检测报告已生成（通过）',
    content: '华东主线路综合评分 92 分，可进入报价流程。',
    time: '10 分钟前',
    unread: true,
    iconBg: 'rgba(239,246,255,1)',
    iconColor: 'rgba(37,99,235,1)'
  },
  {
    title: '报价单被驳回，请修改后重提',
    content: '06 月增量报价：输出价高于市场均价 18%。',
    time: '2 小时前',
    unread: true,
    iconBg: 'rgba(255,247,237,1)',
    iconColor: 'rgba(217,119,6,1)'
  },
  {
    title: '合同待签署提醒',
    content: 'API 接入服务合同请在 06-20 前完成签署。',
    time: '昨天 18:20',
    unread: true,
    iconBg: 'rgba(236,253,245,1)',
    iconColor: 'rgba(22,163,74,1)'
  },
  {
    title: '6 月账单已出，结算金额 ¥12,860.00',
    content: '预计 07-15 打款至绑定对公账户。',
    time: '3 天前',
    unread: false,
    iconBg: 'rgba(239,246,255,1)',
    iconColor: 'rgba(37,99,235,1)'
  },
  {
    title: '平台系统升级公告',
    content: '06-16 02:00–04:00 计费系统维护，期间不影响调用。',
    time: '5 天前',
    unread: false,
    iconBg: 'rgba(241,245,249,1)',
    iconColor: 'rgba(100,116,139,1)'
  }
] as const

/** 设计帧里已读 / 未读两态的取色（design.tree.json fontFill） */
export const DESIGN_UNREAD_COLORS = {
  title: '#0F172A',
  content: '#64748B',
  time: '#94A3B8'
}

export const DESIGN_READ_COLORS = {
  title: '#94A3B8',
  content: '#94A3B8',
  time: '#CBD5E1'
}

/** 未读红点（design: 未读点1 width=9 height=8 cornerRadius=4 fills=rgba(239,68,68,1)） */
export const DESIGN_DOT = { width: 9, height: 8, color: '#EF4444' }

/** TabBar 高亮色（design: Tab我的 fills / fontFill = rgba(0,122,255,1)） */
export const DESIGN_TAB_ACTIVE_COLOR = '#007AFF'
export const DESIGN_TAB_COLOR = '#94A3B8'
