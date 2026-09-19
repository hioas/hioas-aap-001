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
import { request, type PageResult } from '@/api/http';

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

/** 合同状态 → 徽章（PRD 13 §3 五色） */
export const CONTRACT_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  PENDING: { label: '待签署', tone: 'warn' },
  PENDING_SIGN: { label: '待签署', tone: 'warn' },
  SIGNED: { label: '已签署', tone: 'success' },
  ARCHIVED: { label: '已归档', tone: 'muted' },
  VOID: { label: '已作废', tone: 'danger' },
  VOIDED: { label: '已作废', tone: 'danger' }
};

/** 打款状态（后端三态） */
export const PAYMENT_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  PENDING: { label: '待打款', tone: 'warn' },
  PAID: { label: '已打款', tone: 'info' },
  CONFIRMED: { label: '已确认', tone: 'success' }
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
  }
};
