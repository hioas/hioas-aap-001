/**
 * 供应商管理页（设计真源 page-4-pc）的行级展示逻辑 —— 纯函数，便于单测。
 *
 * 诚实边界（PRD 13 §0 / 设计源 skill）：
 *   - 设计稿「接入线路」列（如「3 条」）在 `ProviderProfileResponse` 里**没有对应字段**，
 *     管理端也没有线路/凭证计数接口 → 渲染成「—」，并在页面上可见地说明原因，**不用 0 冒充**。
 *   - 设计稿操作列还有「催办 / 催签 / 看报告」：后端无管理端对应接口（催办=站内信由服务端发、
 *     报告接口仅供应商本人可见 RPT-01…04）→ 本轮不渲染这两个动作，登记为缺口。
 */
import { INDUSTRY_CATEGORY, PROVIDER_STATUS } from '@/api/admin/providers';

/** 「—」= 未知/取不到；绝不写 0（0 是数据，未知不是） */
export const UNKNOWN = '—';

/** 设计稿「最近更新」列格式：06-14 16:20 */
export function fmtShortDate(iso: string | null | undefined): string {
  if (!iso) return UNKNOWN;
  const s = String(iso).replace('T', ' ');
  // 2026-06-14 16:20:31Z → 06-14 16:20
  const m = /^(\d{4})-(\d{2})-(\d{2})[ ](\d{2}):(\d{2})/.exec(s);
  return m ? `${m[2]}-${m[3]} ${m[4]}:${m[5]}` : s.slice(0, 16);
}

/** 完整时间（抽屉里用） */
export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return UNKNOWN;
  return String(iso).replace('T', ' ').replace(/Z$/, '').slice(0, 19);
}

/**
 * 档案完整度配色（按设计帧实测：100%/86% 绿、72% 橙、48% 红）。
 * 阈值：≥80 绿 / ≥60 橙 / <60 红；取不到 → 灰。
 */
export function completenessTone(v: number | null | undefined): 'success' | 'warn' | 'danger' | 'muted' {
  if (v == null || !Number.isFinite(v)) return 'muted';
  if (v >= 80) return 'success';
  if (v >= 60) return 'warn';
  return 'danger';
}

export const completenessText = (v: number | null | undefined): string =>
  v == null || !Number.isFinite(v) ? UNKNOWN : `${Math.round(v)}%`;

export const industryLabel = (v: string | null | undefined): string =>
  v ? INDUSTRY_CATEGORY[v]?.label ?? v : UNKNOWN;

export const industryTone = (v: string | null | undefined): 'info' | 'warn' | 'success' | 'muted' =>
  (v ? INDUSTRY_CATEGORY[v]?.tone : undefined) ?? 'muted';

export const statusLabel = (s: string | null | undefined): string =>
  s ? PROVIDER_STATUS[s]?.label ?? s : UNKNOWN;

export const statusTone = (s: string | null | undefined): 'info' | 'warn' | 'success' | 'danger' | 'muted' =>
  (s ? PROVIDER_STATUS[s]?.tone : undefined) ?? 'muted';

/** 暂停态判定：只有暂停态能「恢复」，非暂停态能「停用」（后端 409 E-1601 是最终裁判） */
export const isSuspended = (status: string | null | undefined): boolean => status === 'SUSPENDED';

/** 接入线路：后端无字段 → 恒为未知，页面必须显式说明（不是「0 条」） */
export const accessLines = (_row: unknown): string => UNKNOWN;

/** 设计稿有、后端无的管理端动作（用于页面可见缺口清单） */
export const DESIGN_ONLY_ACTIONS = ['催办', '催签', '看报告'] as const;

export const MISSING_ACTIONS_NOTE =
  `设计稿操作列还有「${DESIGN_ONLY_ACTIONS.join(' / ')}」：后端**没有**管理端对应接口` +
  '（催办/催签需站内信发送接口、看报告的报告接口仅供应商本人可见 RPT-01…04）→ 本轮不渲染，' +
  '避免给出点了没反应的假按钮。';

/** 类型筛选：ADM-P01 无类型查询参数 → 只能对当前页做前端过滤（跨页筛选需后端补参数） */
export const CATEGORY_FILTER_NOTE =
  '类型筛选：ADM-P01 没有类型查询参数 → 仅对当前页做前端过滤（跨页筛选需后端补 `industryCategory` 参数）。';

/** 分页文案（设计稿：「共 128 条，每页 20 条」） */
export const pageSummary = (total: number, pageSize: number): string =>
  `共 ${total} 条，每页 ${pageSize} 条`;
