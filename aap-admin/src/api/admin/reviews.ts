/**
 * 报价审核（M8）· 真源：AdminReviewController + ReviewService.REASON_CODES
 *
 *   GET  /admin/reviews?status=&page=&pageSize=   待审报价池（ADM-R01）
 *   POST /admin/reviews/{id}/claim                领取（并发失败拿 E-1601）（ADM-R02）
 *   POST /admin/reviews/{id}/approve  {comment}   通过 → 自动生成合同（ADM-R03）
 *   POST /admin/reviews/{id}/reject   {reason_code, reason_text}  驳回（ADM-R04）
 *   GET  /admin/reviews/records?quote_id=         审核记录时间线（ADM-R05）
 */
import { request, type PageResult } from '@/api/http';

export interface ReviewTask {
  id: string;
  review_id?: string;
  quote_id: string;
  quote_no: string | null;
  provider_id: string | null;
  provider_name: string | null;
  status: string;
  claimed_by: string | null;
  claimed_at: string | null;
  review_comment: string | null;
  reject_reason_code: string | null;
  tech_metrics_snapshot: unknown;
  created_at: string | null;
  updated_at: string | null;
}

export interface ReviewRecord {
  id: string;
  quote_id: string;
  task_id: string;
  action: string;
  operator_id: string | null;
  operator_name: string | null;
  before_status: string | null;
  after_status: string | null;
  comment: string | null;
  created_at: string | null;
}

/**
 * 驳回原因码（**逐字取自后端 ReviewService.REASON_CODES**，不是自己编的）。
 * 后端对非法码直接 E-1001 字段级报错，所以前端必须用同一套枚举。
 */
export const REJECT_REASON_CODES = [
  { code: 'PRICE_TOO_HIGH', label: '价格过高' },
  { code: 'PRICE_STRUCTURE_INVALID', label: '价格结构不合法' },
  { code: 'CACHE_PRICE_MISSING', label: '缓存价缺失' },
  { code: 'TECH_RISK', label: '技术风险' },
  { code: 'VALIDITY_ISSUE', label: '有效期问题' },
  { code: 'MISSING_INFO', label: '信息缺失' },
  { code: 'OTHER', label: '其他' }
] as const;

export type RejectReasonCode = (typeof REJECT_REASON_CODES)[number]['code'];

/** 待审池状态（后端 REVIEWABLE = PENDING / CLAIMED） */
export const REVIEW_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  PENDING: { label: '待审核', tone: 'warn' },
  CLAIMED: { label: '待复核', tone: 'info' },
  APPROVED: { label: '已通过', tone: 'success' },
  REJECTED: { label: '已驳回', tone: 'danger' }
};

export const reviewApi = {
  list(status?: string, page = 1, pageSize = 20) {
    return request<PageResult<ReviewTask>>('/admin/reviews', { query: { status, page, page_size: pageSize } });
  },
  claim(id: string) {
    return request<ReviewTask>(`/admin/reviews/${id}/claim`, { method: 'POST' });
  },
  approve(id: string, comment?: string) {
    return request<ReviewTask>(`/admin/reviews/${id}/approve`, { method: 'POST', body: { comment: comment ?? '' } });
  },
  reject(id: string, reasonCode: RejectReasonCode, reasonText?: string) {
    // reason_code 必填且必须命中枚举；后端会二次校验
    return request<ReviewTask>(`/admin/reviews/${id}/reject`, {
      method: 'POST',
      body: { reason_code: reasonCode, reason_text: reasonText ?? '' }
    });
  },
  records(quoteId: string) {
    return request<PageResult<ReviewRecord>>('/admin/reviews/records', { query: { quote_id: quoteId } });
  }
};
