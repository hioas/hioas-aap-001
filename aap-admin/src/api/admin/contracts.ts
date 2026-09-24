/**
 * 合同与结算（M9）· 真源：AdminContractController + AdminPaymentController
 *
 *   GET  /admin/contracts?status=&page=&pageSize=     合同列表
 *   POST /admin/contracts/{id}/issue                  发起（生成合同文件）
 *   POST /admin/contracts/{id}/confirm-sign           签署确认
 *   GET  /admin/payments?status=&page=&pageSize=      打款记录
 *   POST /admin/payments/{id}/confirm                 确认打款
 *   GET  /admin/settlements?page=&pageSize=           结算台账（按供应商聚合）
 *   POST /admin/settlements                           生成结算单（ADM-PAY06，口径 D-SETTLE-02）
 *   GET  /admin/settlements/{id}                      结算单详情（ADM-PAY07）
 *   POST /admin/settlements/{id}/confirm              确认出账（ADM-PAY08）
 *   POST /admin/settlements/{id}/void                 作废结算单（ADM-PAY09）
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
  provider_name?: string | null;
  period_from: string | null;
  period_to: string | null;
  total_amount: number | null;
  platform_fee: number | null;
  net_amount?: number | null;
  currency?: string | null;
  status: string;
  created_at: string | null;
}

/** 结算明细行（维度：渠道 × 模型；字段与 aap_settlement_line 表列一一对应）。 */
export interface StatementLine {
  id: string;
  statement_id: string;
  channel_id: string | null;
  model_name: string | null;
  total_tokens: number | null;
  quota_raw: number | null;
  amount: number | null;
}

/** 结算单详情（ADM-PAY07 / SET-02）：主行 + 明细行 + 已关联打款。 */
export interface StatementDetail extends StatementRow {
  lines: StatementLine[];
  payments: PaymentRow[];
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

/**
 * 结算单状态（SettlementService 状态机）：DRAFT --确认--> CONFIRMED（终态）、DRAFT --作废--> VOID
 * （作废后可重新生成，历史单保留，不物理删除）。
 *
 * ⚠️ 表格此前复用 PAYMENT_STATUS 渲染结算状态 → DRAFT 无键、直接显示原始码。
 *    结算与打款是两套状态机，映射必须分开（2026-09-25 修正）。
 */
export const STATEMENT_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  DRAFT: { label: '草稿', tone: 'warn' },
  CONFIRMED: { label: '已出账', tone: 'success' },
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
   * ADM-PAY06 生成结算单。口径（后端 D-SETTLE-02）：
   * 周期=自然月 UTC；金额基数=`aap_usage_hourly.cost_usd` 合计；平台费=合同 `platform_fee_rate` × 基数；
   * 明细维度=渠道 × 模型；门槛=合同 `min_settlement_amount`。
   * 无 SIGNED 合同 → 409 E-1701；周期内无用量或低于门槛 → 409 E-1601（**不生成 0 元单**）；
   * 同周期重复生成 → 幂等返回既有单。
   */
  generateStatement(payload: { provider_id: string; month: string }) {
    return request<StatementDetail>('/admin/settlements', { method: 'POST', body: payload });
  },
  /** ADM-PAY07 结算单详情（含明细行与已关联打款）。 */
  statementDetail(id: string) {
    return request<StatementDetail>(`/admin/settlements/${id}`);
  },
  /** ADM-PAY08 确认出账：DRAFT → CONFIRMED（终态，确认后不可作废）。 */
  confirmStatement(id: string) {
    return request<StatementDetail>(`/admin/settlements/${id}/confirm`, { method: 'POST' });
  },
  /** ADM-PAY09 作废结算单：DRAFT → VOID（理由必填，落审计；作废后可重新生成）。 */
  voidStatement(id: string, reason: string) {
    return request<StatementDetail>(`/admin/settlements/${id}/void`, { method: 'POST', body: { reason } });
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
