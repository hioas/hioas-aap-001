/**
 * 序号 20【合同与通知】站内信列表（page-20-2）— 视图模型单测（切片 1）
 *
 * 真源：
 *  - 设计：.calicat/raw/pages/page-20-2/design.tree.json（文案逐字；已读/未读两态取色；图标底色）
 *  - 数据字典：.calicat/prd/15-数据模型ER与数据字典.md §aap_notification
 *      recipient_type/id、channel(SMS/INBOX/BOTH)、event_code、title、content(脱敏)、biz_type/id、read_at、status
 *  - 接口：.calicat/prd/18-API设计OpenAPI.md「Audit/Notification」Tag → /notifications、/notifications/{id}/read
 *  ⚠️ 18-API 卡片只列路径、无查询参数/字段级 schema → 查询参数名、时间格式、图标类型映射均为推断（记 missing-prd）。
 */
import { describe, expect, it } from 'vitest'
import {
  FILTERS,
  MESSAGE_ICON_META,
  PAGE_TITLE,
  READ_ALL_TEXT,
  TABS,
  ACTIVE_TAB,
  buildMessageQuery,
  buildMessageRow,
  buildMessagesModel,
  formatMessageTime,
  isUnread,
  resolveMessageKind,
  resolveMessageTarget,
  unreadBadgeText
} from '@/utils/messages-model'
import { DESIGN_MESSAGES, DESIGN_READ_COLORS, DESIGN_UNREAD_COLORS } from '../fixtures/messages-fixture'

const NOW = '2026-06-16T10:30:00+08:00'

describe('序号 20 · 设计原文常量（文案不得改写）', () => {
  it('页面标题 = 消息（design 顶部导航图层 TEXT=消息 20px Bold）', () => {
    expect(PAGE_TITLE).toBe('消息')
  })

  it('右上按钮 = 全部已读', () => {
    expect(READ_ALL_TEXT).toBe('全部已读')
  })

  it('筛选 4 个 chip，文案与顺序与设计稿一致', () => {
    expect(FILTERS.map((f) => f.label)).toEqual(['全部', '未读', '订单', '系统'])
  })

  it('筛选 key 与设计帧一一对应（all/unread/order/system）', () => {
    expect(FILTERS.map((f) => f.key)).toEqual(['all', 'unread', 'order', 'system'])
  })

  it('TabBar 4 项文案与设计稿一致，高亮项 = 我的（设计帧 Tab我的 为蓝色）', () => {
    expect(TABS.map((t) => t.label)).toEqual(['工作台', '报告', '报价', '我的'])
    expect(ACTIVE_TAB).toBe('我的')
  })
})

describe('序号 20 · isUnread（未读判定）', () => {
  it('read_at 缺省 → 未读', () => {
    expect(isUnread({ id: 'n1' })).toBe(true)
  })

  it('read_at 为 null / 空串 → 未读（数据字典 read_at 为空即未读）', () => {
    expect(isUnread({ id: 'n1', read_at: null })).toBe(true)
    expect(isUnread({ id: 'n1', read_at: '' })).toBe(true)
  })

  it('read_at 有值 → 已读', () => {
    expect(isUnread({ id: 'n1', read_at: '2026-06-16T02:00:00Z' })).toBe(false)
  })

  it('字段级 schema 未定义 → 兼容 readAt / read 两种容错命名', () => {
    expect(isUnread({ id: 'n1', readAt: '2026-06-16T02:00:00Z' })).toBe(false)
    expect(isUnread({ id: 'n1', read: true })).toBe(false)
    expect(isUnread({ id: 'n1', read: false })).toBe(true)
  })
})

describe('序号 20 · resolveMessageKind（图标类型，设计帧 5 种底色）', () => {
  it('event_code 含 DETECTION → detect', () => {
    expect(resolveMessageKind({ event_code: 'DETECTION_PASSED' })).toBe('detect')
  })

  it('biz_type=QUOTE（或 event_code 含 QUOTE/REJECT）→ quote', () => {
    expect(resolveMessageKind({ biz_type: 'QUOTE' })).toBe('quote')
    expect(resolveMessageKind({ event_code: 'QUOTE_REJECTED' })).toBe('quote')
  })

  it('biz_type=CONTRACT（或 event_code 含 CONTRACT/SIGN）→ contract', () => {
    expect(resolveMessageKind({ biz_type: 'CONTRACT' })).toBe('contract')
    expect(resolveMessageKind({ event_code: 'CONTRACT_SIGN_REMINDER' })).toBe('contract')
  })

  it('biz_type=BILL/PAYMENT（或 event_code 含 BILL/SETTLE）→ bill', () => {
    expect(resolveMessageKind({ biz_type: 'BILL' })).toBe('bill')
    expect(resolveMessageKind({ event_code: 'SETTLEMENT_PAID' })).toBe('bill')
  })

  it('无依据（缺字段 / 未知取值）→ system（设计第 5 条灰底公告）', () => {
    expect(resolveMessageKind({})).toBe('system')
    expect(resolveMessageKind({ event_code: 'WHAT_NOTICE' })).toBe('system')
  })

  it('服务端直接给 kind 时优先（容错读取）', () => {
    expect(resolveMessageKind({ kind: 'bill', event_code: 'DETECTION_PASSED' })).toBe('bill')
  })
})

describe('序号 20 · 图标底色与字形色（设计帧逐值）', () => {
  it('detect = 浅蓝底 + 蓝字形（消息1图标）', () => {
    expect(MESSAGE_ICON_META.detect).toEqual({ bg: '#EFF6FF', color: '#2563EB' })
  })

  it('quote = 浅橙底 + 橙字形（消息2图标）', () => {
    expect(MESSAGE_ICON_META.quote).toEqual({ bg: '#FFF7ED', color: '#D97706' })
  })

  it('contract = 浅绿底 + 绿字形（消息3图标）', () => {
    expect(MESSAGE_ICON_META.contract).toEqual({ bg: '#ECFDF5', color: '#16A34A' })
  })

  it('bill = 浅蓝底 + 蓝字形（消息4图标）', () => {
    expect(MESSAGE_ICON_META.bill).toEqual({ bg: '#EFF6FF', color: '#2563EB' })
  })

  it('system = 浅灰底 + 灰字形（消息5图标）', () => {
    expect(MESSAGE_ICON_META.system).toEqual({ bg: '#F1F5F9', color: '#64748B' })
  })
})

describe('序号 20 · formatMessageTime（设计帧 5 种时间写法）', () => {
  it('1 分钟内 → 刚刚', () => {
    expect(formatMessageTime('2026-06-16T10:29:30+08:00', NOW)).toBe('刚刚')
  })

  it('30 分钟 → 10 分钟前（设计第 1 条）', () => {
    expect(formatMessageTime('2026-06-16T10:20:00+08:00', NOW)).toBe('10 分钟前')
  })

  it('2 小时（同日）→ 2 小时前（设计第 2 条）', () => {
    expect(formatMessageTime('2026-06-16T08:30:00+08:00', NOW)).toBe('2 小时前')
  })

  it('昨天 → 昨天 18:20（设计第 3 条，含零补位的 HH:mm）', () => {
    expect(formatMessageTime('2026-06-15T18:20:00+08:00', NOW)).toBe('昨天 18:20')
  })

  it('跨日前 30 小时内但非昨天 → 时间正序仍按小时（不误判成昨天）', () => {
    expect(formatMessageTime('2026-06-16T04:30:00+08:00', NOW)).toBe('6 小时前')
  })

  it('3 天 / 5 天前（设计第 4、5 条）', () => {
    expect(formatMessageTime('2026-06-13T10:30:00+08:00', NOW)).toBe('3 天前')
    expect(formatMessageTime('2026-06-11T10:30:00+08:00', NOW)).toBe('5 天前')
  })

  it('≥7 天 → MM-DD（PRD 无格式定义 → 派生规则，记 missing-prd）', () => {
    expect(formatMessageTime('2026-06-01T10:30:00+08:00', NOW)).toBe('06-01')
  })

  it('时间缺失/非法 → 空串（不臆造时间）', () => {
    expect(formatMessageTime('', NOW)).toBe('')
    expect(formatMessageTime(undefined, NOW)).toBe('')
  })
})

describe('序号 20 · buildMessageQuery（筛选 → 查询参数，参数名为推断）', () => {
  it('全部 → 不传筛选参数', () => {
    expect(buildMessageQuery('all')).toEqual({})
  })

  it('未读 → unread=true（read_at 为空的语义）', () => {
    expect(buildMessageQuery('unread')).toEqual({ unread: 'true' })
  })

  it('订单 → category=ORDER', () => {
    expect(buildMessageQuery('order')).toEqual({ category: 'ORDER' })
  })

  it('系统 → category=SYSTEM', () => {
    expect(buildMessageQuery('system')).toEqual({ category: 'SYSTEM' })
  })
})

describe('序号 20 · buildMessageRow（单条渲染模型）', () => {
  it('未读行：标题/摘要用未读数色，显示红点，时间取设计写法', () => {
    const row = buildMessageRow(
      {
        id: 'n1',
        title: DESIGN_MESSAGES[0].title,
        content: DESIGN_MESSAGES[0].content,
        created_at: '2026-06-16T10:20:00+08:00',
        event_code: 'DETECTION_PASSED'
      },
      NOW
    )
    expect(row.title).toBe('检测报告已生成（通过）')
    expect(row.content).toBe('华东主线路综合评分 92 分，可进入报价流程。')
    expect(row.timeText).toBe('10 分钟前')
    expect(row.unread).toBe(true)
    expect(row.titleColor).toBe(DESIGN_UNREAD_COLORS.title)
    expect(row.contentColor).toBe(DESIGN_UNREAD_COLORS.content)
    expect(row.timeColor).toBe(DESIGN_UNREAD_COLORS.time)
    expect(row.iconBg).toBe('#EFF6FF')
  })

  it('已读行：标题降到浅灰，红点不显示（设计第 4、5 条）', () => {
    const row = buildMessageRow(
      {
        id: 'n4',
        title: DESIGN_MESSAGES[3].title,
        content: DESIGN_MESSAGES[3].content,
        created_at: '2026-06-13T10:30:00+08:00',
        read_at: '2026-06-13T12:00:00+08:00',
        biz_type: 'BILL'
      },
      NOW
    )
    expect(row.unread).toBe(false)
    expect(row.titleColor).toBe(DESIGN_READ_COLORS.title)
    expect(row.contentColor).toBe(DESIGN_READ_COLORS.content)
    expect(row.timeColor).toBe(DESIGN_READ_COLORS.time)
    expect(row.iconBg).toBe('#EFF6FF')
  })

  it('摘要去换行/多空格（列表渲染为单行省略）', () => {
    const row = buildMessageRow({ id: 'n1', title: 'T', content: '  第一行\n  第二行  ' }, NOW)
    expect(row.content).toBe('第一行 第二行')
  })
})

describe('序号 20 · buildMessagesModel（整页模型）', () => {
  const RAW = {
    total: 5,
    items: [
      { id: 'n1', title: DESIGN_MESSAGES[0].title, content: DESIGN_MESSAGES[0].content, created_at: '2026-06-16T10:20:00+08:00', event_code: 'DETECTION_PASSED' },
      { id: 'n2', title: DESIGN_MESSAGES[1].title, content: DESIGN_MESSAGES[1].content, created_at: '2026-06-16T08:30:00+08:00', event_code: 'QUOTE_REJECTED' },
      { id: 'n3', title: DESIGN_MESSAGES[2].title, content: DESIGN_MESSAGES[2].content, created_at: '2026-06-15T18:20:00+08:00', event_code: 'CONTRACT_SIGN_REMINDER' },
      { id: 'n4', title: DESIGN_MESSAGES[3].title, content: DESIGN_MESSAGES[3].content, created_at: '2026-06-13T10:30:00+08:00', read_at: '2026-06-13T12:00:00+08:00', biz_type: 'BILL' },
      { id: 'n5', title: DESIGN_MESSAGES[4].title, content: DESIGN_MESSAGES[4].content, created_at: '2026-06-11T10:30:00+08:00', read_at: '2026-06-11T11:00:00+08:00', event_code: 'SYSTEM_NOTICE' }
    ]
  }

  it('5 条消息逐条对齐设计稿（标题/摘要/时间/未读态/图标底色）', () => {
    const model = buildMessagesModel(RAW, 'all', NOW)
    expect(model.rows).toHaveLength(5)
    DESIGN_MESSAGES.forEach((d, i) => {
      expect(model.rows[i].title).toBe(d.title)
      expect(model.rows[i].content).toBe(d.content)
      expect(model.rows[i].timeText).toBe(d.time)
      expect(model.rows[i].unread).toBe(d.unread)
      expect(model.rows[i].iconBg).toBe(
        { 'rgba(239,246,255,1)': '#EFF6FF', 'rgba(255,247,237,1)': '#FFF7ED', 'rgba(236,253,245,1)': '#ECFDF5', 'rgba(241,245,249,1)': '#F1F5F9' }[
          d.iconBg
        ]
      )
    })
  })

  it('未读计数 3 + 徽标文案「3 条未读」（设计原文）', () => {
    const model = buildMessagesModel(RAW, 'all', NOW)
    expect(model.unreadCount).toBe(3)
    expect(model.badgeText).toBe('3 条未读')
  })

  it('无未读时徽标不渲染（空串）', () => {
    const model = buildMessagesModel(
      { items: [{ id: 'n1', title: 'T', content: 'C', read_at: '2026-06-16T10:00:00+08:00' }] },
      'all',
      NOW
    )
    expect(model.unreadCount).toBe(0)
    expect(model.badgeText).toBe('')
  })

  it('空列表 → empty=true 且 rows 为空（空态不臆造文案）', () => {
    const model = buildMessagesModel({ total: 0, items: [] }, 'all', NOW)
    expect(model.empty).toBe(true)
    expect(model.rows).toEqual([])
  })

  it('响应体缺 items（null/未定义）→ 不崩，按空列表处理', () => {
    expect(buildMessagesModel(null, 'all', NOW).rows).toEqual([])
    expect(buildMessagesModel({ total: 2 }, 'all', NOW).empty).toBe(true)
  })

  it('兼容 items / list / records 三种列表命名（字段级 schema missing-prd）', () => {
    const one = [{ id: 'n1', title: 'T', content: 'C' }]
    expect(buildMessagesModel({ list: one }, 'all', NOW).rows).toHaveLength(1)
    expect(buildMessagesModel({ records: one }, 'all', NOW).rows).toHaveLength(1)
  })
})

describe('序号 20 · resolveMessageTarget（点击落点，biz_type 映射为推断）', () => {
  it('biz_type=CONTRACT + biz_id → 合同详情页并带 contractId', () => {
    expect(resolveMessageTarget({ biz_type: 'CONTRACT', biz_id: 'ct1' })).toBe('/pages/contract/index?contractId=ct1')
  })

  it('biz_type=QUOTE → 报价单列表（该页无 id 入参）', () => {
    expect(resolveMessageTarget({ biz_type: 'QUOTE', biz_id: 'q1' })).toBe('/pages/quotes/index')
  })

  it('biz_type=REPORT/DETECTION + biz_id → 检测报告页并带 reportId', () => {
    expect(resolveMessageTarget({ biz_type: 'REPORT', biz_id: 'r1' })).toBe('/pages/report/index?reportId=r1')
    expect(resolveMessageTarget({ biz_type: 'DETECTION', biz_id: 'j1' })).toBe('/pages/report/index?reportId=j1')
  })

  it('无 biz_type / 未知取值 → 空串（不臆造落点，点击只标记已读）', () => {
    expect(resolveMessageTarget({})).toBe('')
    expect(resolveMessageTarget({ biz_type: 'UNKNOWN', biz_id: 'x' })).toBe('')
  })

  it('biz_id 做 URI 编码', () => {
    expect(resolveMessageTarget({ biz_type: 'CONTRACT', biz_id: 'a b/c' })).toBe('/pages/contract/index?contractId=a%20b%2Fc')
  })
})

describe('序号 20 · unreadBadgeText', () => {
  it('N>0 → 「N 条未读」', () => {
    expect(unreadBadgeText(3)).toBe('3 条未读')
  })

  it('0 → 空串', () => {
    expect(unreadBadgeText(0)).toBe('')
  })
})
