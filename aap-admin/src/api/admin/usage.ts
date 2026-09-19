/**
 * 用量统计（M12）· 真源：AdminUsageController
 *
 *   GET  /admin/usage/hourly?from=&to=&providerId=&channelId=&model=&page=&pageSize=  ADM-U01
 *   POST /admin/usage/refresh  {from,to}  聚合刷新（幂等 UPSERT；仅 TECH_OPS/SUPER_ADMIN）ADM-U02
 *
 * ⚠️ 诚实边界（PRD 13 §9）：设计稿的「综合毛利 / 毛利 / 环比 / 供应商消耗排行」等维度，
 *    后端 Bucket 里**没有毛利字段**（有 quota_raw / cost_usd，可算成本但无售价口径）。
 *    因此页面只渲染后端**真实有**的维度，取不到的显式标「未采集」，不用假数字填充。
 *    时间参数必须 RFC3339 UTC（后端对缺失/格式错会 E-1001 字段级报错）。
 */
import { request, type PageResult } from '@/api/http';

export interface UsageBucket {
  stat_hour: string | null;
  channel_id: string | null;
  channel_name: string | null;
  provider_id: string | null;
  model_name: string | null;
  group_name: string | null;
  request_count: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  cache_read_tokens: number | null;
  cache_write_tokens: number | null;
  cache_write_1h_tokens: number | null;
  image_input_tokens: number | null;
  audio_input_tokens: number | null;
  video_input_tokens: number | null;
  quota_raw: number | null;
  cost_usd: number | null;
  /** OK / NO_CACHE_FIELD —— NO_CACHE_FIELD 表示该桶无缓存字段（PRD 13 §9 要求标注「未采集」） */
  cache_parse_status: string | null;
  source: string | null;
  tier_distribution: Record<string, unknown> | null;
  collected_at: string | null;
}

export interface RefreshResult {
  batch_id: string | null;
  [k: string]: unknown;
}

/** RFC3339 UTC：后端要求的时间格式（本地时间直接发会被拒） */
export function toRfc3339Utc(d: Date): string {
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

export const usageApi = {
  hourly(params: { from?: string; to?: string; providerId?: string; channelId?: string; model?: string; page?: number; pageSize?: number } = {}) {
    return request<PageResult<UsageBucket>>('/admin/usage/hourly', {
      query: {
        from: params.from,
        to: params.to,
        providerId: params.providerId,
        channelId: params.channelId,
        model: params.model,
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 200
      }
    });
  },
  refresh(from: string, to: string) {
    return request<RefreshResult>('/admin/usage/refresh', { method: 'POST', body: { from, to } });
  }
};

/** 大数可读化：18.42M / 6.24B（设计稿用 M/B 口径） */
export function humanCount(n: number | null | undefined): string {
  if (n == null) return '—';
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(2)}K`;
  return String(n);
}

export function money(v: number | null | undefined, currency = '¥'): string {
  if (v == null) return '—';
  return `${currency}${Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
