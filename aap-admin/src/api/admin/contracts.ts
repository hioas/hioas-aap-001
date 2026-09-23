/**
 * 合同与结算（M9）· 真源：AdminContractController + AdminPaymentController
 *
 *   GET  /admin/contracts?status=&page=&pageSize=     合同列表
 *   POST /admin/contracts/{id}/issue                  发起（生成合同文件）
 *   POST /admin/contracts/{id}/confirm-sign           签署确认
 *   GET  /admin/payments?status=&page=&pageSize=      打款记录
 *   POST /admin/payments/{id}/confirm                 确认打款
 *   GET  /admin/settlements?page=&pageSize=           结算台账（按供应商聚合）
 *
 * ⚠️ PRD 13 §6：「**不做资金流转，仅记录**」。所以这里的「打款」只是记录状态，
 *    前端不得出现任何「转账/支付」措辞或跳转。
 */
import { request, tokenStore, ApiError, API_BASE, type PageResult } from '@/api/http';

export interface ContractRow {
  id: string;
  contract_id?: string;
  contract_no: string | null;
  quote_id: string | null;
  quote_no: string | null;
  provider_id: string | null;
  title?: string | null;
  name?: string | null;
  contract_name?: string | null;
  status: string;
  sign_channel?: string | null;
  cooperation_mode: string | null;
  valid_from: string | null;
  valid_to: string | null;
  settlement_cycle?: string | null;
  platform_fee_rate?: number | null;
  currency?: string | null;
  min_settlement_amount?: number | null;
  sign_deadline?: string | null;
  supplier_name: string | null;
  signer_name?: string | null;
  signer_phone_masked?: string | null;
  sign_method?: string | null;
  terms?: string[] | null;
  records?: unknown[] | null;
  file_id?: string | null;
  file_name?: string | null;
  signed_at: string | null;
  archived_at?: string | null;
  created_at: string | null;
}

export interface PaymentRow {
  id: string;
  payment_id?: string;
  provider_id: string | null;
  contract_id: string | null;
  contract_no: string | null;
  statement_id?: string | null;
  amount: number | null;
  currency: string | null;
  status: string;
  voucher_file_id: string | null;
  paid_at: string | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  remark?: string | null;
  created_at: string | null;
}

export interface StatementRow {
  id: string;
  statement_no: string | null;
  provider_id: string | null;
  period_from: string | null;
  period_to: string | null;
  total_amount: number | null;
  platform_fee: number | null;
  status: string;
  created_at: string | null;
}

/**
 * 合同状态 → 徽章（PRD 13 §3 五色）。
 *
 * ⚠️ 键必须覆盖**后端真实状态**（ContractService 状态机）：
 *   CREATED --issue--> PENDING_SIGN --供应商签署--> SUPPLIER_SIGNED --平台确认--> SIGNED --归档--> ARCHIVED
 * 此前这里只有 PENDING/PENDING_SIGN/SIGNED/ARCHIVED/VOID，缺 CREATED 与 SUPPLIER_SIGNED
 * → 管理端合同列表里这两种状态显示成原始码（2026-09-23 修正）。
 */
export const CONTRACT_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  CREATED: { label: '待发起', tone: 'warn' },
  PENDING: { label: '待签署', tone: 'warn' }, // 兼容旧值
  PENDING_SIGN: { label: '待签署', tone: 'warn' },
  SUPPLIER_SIGNED: { label: '供应商已签', tone: 'info' },
  SIGNED: { label: '已签署', tone: 'success' },
  ARCHIVED: { label: '已归档', tone: 'muted' },
  VOID: { label: '已作废', tone: 'danger' },
  VOIDED: { label: '已作废', tone: 'danger' }
};

/**
 * 打款状态（后端四态，PaymentRecordEntity）。
 *
 * ⚠️ 后端真实取值是 UNSETTLED / PAYMENT_RECORDED / CONFIRMED / VOID（PRD 10 §4.3）；
 * 此前这里写的是 PENDING / PAID —— 与后端**一个都对不上**，于是「待打款批次」永远为空、
 * 打款记录在管理端根本看不到（2026-09-23 修正）。PENDING/PAID 仅作别名保留。
 */
export const PAYMENT_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  UNSETTLED: { label: '待打款', tone: 'warn' },
  PENDING: { label: '待打款', tone: 'warn' }, // 兼容旧值
  PAYMENT_RECORDED: { label: '已打款待确认', tone: 'info' },
  PAID: { label: '已打款待确认', tone: 'info' }, // 兼容旧值
  CONFIRMED: { label: '已确认', tone: 'success' },
  VOID: { label: '已作废', tone: 'danger' }
};

export const contractApi = {
  list(status?: string, page = 1, pageSize = 20) {
    return request<PageResult<ContractRow>>('/admin/contracts', { query: { status, page, pageSize } });
  },
  issue(id: string) {
    return request<ContractRow>(`/admin/contracts/${id}/issue`, { method: 'POST' });
  },
  confirmSign(id: string) {
    return request<ContractRow>(`/admin/contracts/${id}/confirm-sign`, { method: 'POST' });
  },
  payments(status?: string, page = 1, pageSize = 20) {
    return request<PageResult<PaymentRow>>('/admin/payments', { query: { status, page, pageSize } });
  },
  confirmPayment(id: string) {
    return request<PaymentRow>(`/admin/payments/${id}/confirm`, { method: 'POST' });
  },
  statements(page = 1, pageSize = 20) {
    return request<PageResult<StatementRow>>('/admin/settlements', { query: { page, pageSize } });
  },
  /**
   * 记录打款（ADM-PAY04，2026-09-23 新增）。运营线下打款后录入：合同须 SIGNED，
   * 金额>0 且币种与合同一致（C4），凭证必填（C5）。**仅记录，不产生资金流转**（PRD 10 R-42）。
   */
  recordPayment(payload: {
    contract_id: string;
    amount: number;
    currency?: string | null;
    voucher_file_id: string;
    paid_at?: string | null;
    remark?: string | null;
  }) {
    return request<PaymentRow>('/admin/payments', { method: 'POST', body: payload });
  },
  /** 作废打款（ADM-PAY05）：PAYMENT_RECORDED/CONFIRMED → VOID，必填理由，作废后可重录。 */
  voidPayment(id: string, reason: string) {
    return request<PaymentRow>(`/admin/payments/${id}/void`, { method: 'POST', body: { reason } });
  }
};

/**
 * 上传打款凭证（`POST /files`，multipart）。
 *
 * <p>为什么单独实现而不走 {@link request}：该封装固定 `Content-Type: application/json`，
 * 传 FormData 必须让浏览器自己带 multipart boundary。
 * 返回 `file_id`（后端响应字段），供 {@link contractApi.recordPayment} 的 `voucher_file_id` 使用。
 */
export async function uploadVoucher(file: File): Promise<string> {
  const form = new FormData();
  form.append('biz_type', 'PAYMENT_VOUCHER');
  form.append('file', file);
  const token = tokenStore.get();
  const res = await fetch(`${API_BASE}/files`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form
  });
  const body = (await res.json()) as { code?: string; message?: string; data?: { file_id?: string; id?: string } };
  if (!res.ok || (body.code && body.code !== '0')) {
    throw new ApiError(body.code ?? String(res.status), body.message ?? '凭证上传失败');
  }
  const id = body.data?.file_id ?? body.data?.id;
  if (!id) throw new ApiError('E-2001', '凭证上传失败：响应缺少 file_id');
  return id;
}
