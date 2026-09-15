/**
 * 序号 20【合同与通知】站内信列表（page-20-2 / /pages/messages/index）— 视图模型
 *
 * 真源：
 *  - 设计：.calicat/raw/pages/page-20-2/design.tree.json（430 宽 · 设计总高 760 · 文案逐字）
 *  - 数据字典：.calicat/prd/15-数据模型ER与数据字典.md §aap_notification
 *      recipient_type/id、channel(SMS/INBOX/BOTH)、event_code、title、content(脱敏)、biz_type/id、read_at、status
 *  - 接口：.calicat/prd/18-API设计OpenAPI.md「Audit/Notification」Tag → /notifications、/notifications/{id}/read
 *
 * ⚠️ 缺失依据（一律记台账序号 20 备注，不臆造业务规则）：
 *  1. 18-API 只列路径 → GET/POST 方法与查询参数名（unread/category）为 REST 语义推断（missing-prd）；
 *  2. aap_notification 无「分类」列 → 设计「订单/系统」chip 的取值集合为推断（服务端为准）；
 *  3. 18-API 无「全部已读」批量接口 → 页面按列表逐条调用 /notifications/{id}/read（见 src/api/notification.ts）；
 *  4. 时间写法（刚刚 / N 分钟前 / N 小时前 / 昨天 HH:mm / N 天前 / MM-DD）PRD 零定义 → 派生规则；
 *  5. 图标类型（detect/quote/contract/bill/system）由 event_code/biz_type 派生 → 服务端给 kind 时优先；
 *  6. 徽标「N 条未读」计数取自当前列表（接口未定义汇总字段）。
 */

/** 页面标题（design 顶部导航图层 TEXT=消息） */
export const PAGE_TITLE = '消息'

/** 右上按钮（design TEXT=全部已读） */
export const READ_ALL_TEXT = '全部已读'

/** 路由常量（序号 21 起统一由 src/utils/routes.ts 提供，避免每页各写一套） */
import { CONTRACT_PAGE, QUOTES_PAGE, REPORT_PAGE } from './routes'

export {
  CONTRACT_PAGE,
  LOGIN_PAGE,
  MESSAGES_PAGE,
  MINE_PAGE,
  QUOTES_PAGE,
  REPORT_PAGE,
  WORKBENCH_PAGE
} from './routes'

/** 站内信内的单条（字段名容错：18-API 无字段级 schema） */
export interface MessageRaw {
  id?: string
  title?: string
  content?: string
  created_at?: string
  createdTime?: string
  read_at?: string | null
  readAt?: string | null
  read?: boolean
  is_read?: boolean
  event_code?: string
  biz_type?: string
  biz_id?: string
  kind?: string
}

/** 列表响应（兼容 items / list / records） */
export interface MessageListRaw {
  total?: number
  items?: MessageRaw[]
  list?: MessageRaw[]
  records?: MessageRaw[]
}

export type MessageKind = 'detect' | 'quote' | 'contract' | 'bill' | 'system'

export type MessageFilterKey = 'all' | 'unread' | 'order' | 'system'

/** 4 个筛选 chip（design：筛选全部/筛选未读/筛选订单/筛选系统） */
export const FILTERS: { key: MessageFilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'unread', label: '未读' },
  { key: 'order', label: '订单' },
  { key: 'system', label: '系统' }
]

/** 默认选中 chip（design 筛选全部 fills=rgba(37,99,235,1)） */
export const DEFAULT_FILTER: MessageFilterKey = 'all'

/** 底部 TabBar 4 项与高亮项（序号 21 起由共享模型 src/utils/app-tab-bar-model.ts 提供） */
export { ACTIVE_TAB, TAB_ITEMS as TABS } from './app-tab-bar-model'

/** 图标底色 / 字形色（design 5 条消息逐值） */
export const MESSAGE_ICON_META: Record<MessageKind, { bg: string; color: string }> = {
  detect: { bg: '#EFF6FF', color: '#2563EB' },
  quote: { bg: '#FFF7ED', color: '#D97706' },
  contract: { bg: '#ECFDF5', color: '#16A34A' },
  bill: { bg: '#EFF6FF', color: '#2563EB' },
  system: { bg: '#F1F5F9', color: '#64748B' }
}

/** 已读 / 未读两态取色（design fontFill 逐值） */
export const UNREAD_COLORS = { title: '#0F172A', content: '#64748B', time: '#94A3B8' }
export const READ_COLORS = { title: '#94A3B8', content: '#94A3B8', time: '#CBD5E1' }

const KINDS: MessageKind[] = ['detect', 'quote', 'contract', 'bill', 'system']

/** 未读判定：数据字典只有 read_at → 为空即未读（兼容 readAt/read/is_read 容错命名） */
export function isUnread(raw: MessageRaw | null | undefined): boolean {
  if (!raw) return true
  const at = raw.read_at ?? raw.readAt
  if (typeof at === 'string') return at.trim() === ''
  if (typeof raw.read === 'boolean') return !raw.read
  if (typeof raw.is_read === 'boolean') return !raw.is_read
  return true
}

/** 图标类型：服务端给 kind 时优先；否则由 event_code / biz_type 派生（missing-prd） */
export function resolveMessageKind(raw: MessageRaw | null | undefined): MessageKind {
  if (!raw) return 'system'
  const explicit = String(raw.kind || '').trim().toLowerCase() as MessageKind
  if (KINDS.includes(explicit)) return explicit
  const token = `${raw.event_code || ''} ${raw.biz_type || ''}`.toUpperCase()
  if (/DETECT/.test(token)) return 'detect'
  if (/QUOTE|REJECT/.test(token)) return 'quote'
  if (/CONTRACT|SIGN/.test(token)) return 'contract'
  if (/BILL|PAYMENT|SETTLE/.test(token)) return 'bill'
  return 'system'
}

/** 点击落点：biz_type → 目标路由（biz_type 取值集合 PRD 零定义 → 推断；未知一律不跳转） */
export function resolveMessageTarget(raw: MessageRaw | null | undefined): string {
  if (!raw) return ''
  const biz = String(raw.biz_type || '').toUpperCase()
  const id = String(raw.biz_id || '')
  const withId = (page: string, key: string) => (id ? `${page}?${key}=${encodeURIComponent(id)}` : page)
  if (biz === 'CONTRACT') return withId(CONTRACT_PAGE, 'contractId')
  if (biz === 'QUOTE') return QUOTES_PAGE
  if (biz === 'REPORT' || biz === 'DETECTION') return withId(REPORT_PAGE, 'reportId')
  return ''
}

const pad2 = (n: number) => String(n).padStart(2, '0')

const parseTime = (value?: string | null): Date | null => {
  if (!value || typeof value !== 'string') return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()

/**
 * 时间文案（设计帧 5 种写法：10 分钟前 / 2 小时前 / 昨天 18:20 / 3 天前 / 5 天前）。
 * PRD 无格式定义 → 派生规则（记 missing-prd）；时间缺失/非法返回空串。
 */
export function formatMessageTime(created?: string | null, now: string | Date = new Date()): string {
  const t = parseTime(created)
  if (!t) return ''
  const nowDate = now instanceof Date ? now : parseTime(String(now))
  if (!nowDate) return ''
  const diffMin = Math.floor((nowDate.getTime() - t.getTime()) / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const dayDiff = Math.round((startOfDay(nowDate) - startOfDay(t)) / 86400000)
  if (dayDiff === 0) return `${Math.floor(diffMin / 60)} 小时前`
  if (dayDiff === 1) return `昨天 ${pad2(t.getHours())}:${pad2(t.getMinutes())}`
  if (dayDiff > 1 && dayDiff < 7) return `${dayDiff} 天前`
  return `${pad2(t.getMonth() + 1)}-${pad2(t.getDate())}`
}

/** 徽标文案（design 原文「3 条未读」）；无未读不渲染 */
export function unreadBadgeText(count: number): string {
  return count > 0 ? `${count} 条未读` : ''
}

/** 筛选 chip → 查询参数（参数名与取值集合为推断，记 missing-prd） */
export function buildMessageQuery(filter: MessageFilterKey): Record<string, string> {
  if (filter === 'unread') return { unread: 'true' }
  if (filter === 'order') return { category: 'ORDER' }
  if (filter === 'system') return { category: 'SYSTEM' }
  return {}
}

/** 列表字段容错读取（18-API 无字段级 schema） */
export function readMessageItems(raw: MessageListRaw | null | undefined): MessageRaw[] {
  if (!raw) return []
  const list = raw.items ?? raw.list ?? raw.records
  return Array.isArray(list) ? list : []
}

export interface MessageRow {
  id: string
  title: string
  content: string
  timeText: string
  unread: boolean
  kind: MessageKind
  iconBg: string
  iconColor: string
  titleColor: string
  contentColor: string
  timeColor: string
  target: string
}

/** 单行渲染模型（设计：标题 13px SemiBold / 摘要 12px / 时间 11px；已读整体降灰） */
export function buildMessageRow(raw: MessageRaw, now: string | Date = new Date()): MessageRow {
  const unread = isUnread(raw)
  const kind = resolveMessageKind(raw)
  const meta = MESSAGE_ICON_META[kind]
  const colors = unread ? UNREAD_COLORS : READ_COLORS
  return {
    id: String(raw.id ?? ''),
    title: String(raw.title ?? ''),
    content: String(raw.content ?? '').replace(/\s+/g, ' ').trim(),
    timeText: formatMessageTime(raw.created_at ?? raw.createdTime, now),
    unread,
    kind,
    iconBg: meta.bg,
    iconColor: meta.color,
    titleColor: colors.title,
    contentColor: colors.content,
    timeColor: colors.time,
    target: resolveMessageTarget(raw)
  }
}

export interface MessagesModel {
  rows: MessageRow[]
  unreadCount: number
  badgeText: string
  empty: boolean
}

/** 整页模型：行 + 未读计数 + 徽标 + 空态 */
export function buildMessagesModel(
  raw: MessageListRaw | null | undefined,
  _filter: MessageFilterKey = DEFAULT_FILTER,
  now: string | Date = new Date()
): MessagesModel {
  const rows = readMessageItems(raw).map((item) => buildMessageRow(item, now))
  const unreadCount = rows.filter((r) => r.unread).length
  return { rows, unreadCount, badgeText: unreadBadgeText(unreadCount), empty: rows.length === 0 }
}
