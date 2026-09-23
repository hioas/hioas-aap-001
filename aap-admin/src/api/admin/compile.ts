import { request, type PageResult } from '@/api/http';

/**
 * 编译确认台（ADM-Q01 + ADM-CP01…04，2026-09-23 接线）。
 *
 * <p>后端 `compile/` 早已完整实现（BillingCompiler / BillingExpr / BillingVerifier +
 * CompilationController），但管理端页面一直是「待实现」骨架 → **运营无法从界面触发编译、
 * 看表达式、跑模拟验证、人工确认解锁**，而这是「审核通过 → 下发写入」之间必经的一步
 * （`publish_blocked=true` 期间不允许写入）。属于「有接口无页面」第 3 处。
 *
 * <p>闸门语义（CompilationService 注释）：COMPILED=已编译、写入封锁 → VERIFIED=模拟验证通过、
 * 仍待人工确认 → CONFIRMED=人工确认，`publish_blocked=false` 可进入同步写入；验证不过则 FAILED。
 */
export interface ModelExpr {
  model_name: string | null;
  expr_version: string | null;
  expr: string | null;
  tier_labels: string[] | null;
  rule_hits: string[] | null;
  verified: boolean | null;
  source_hash: string | null;
  inline_expanded: string | null;
}

export interface VerifyCase {
  case_code: string;
  case_name: string | null;
  input: Record<string, unknown> | null;
  expected: number | null;
  actual: number | null;
  passed: boolean | null;
  diff_note: string | null;
}

export interface VerifyReport {
  status: string | null;
  case_total: number | null;
  case_passed: number | null;
  failed_field: string | null;
  cases: VerifyCase[] | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface CompilationResult {
  compilation_id: string;
  id: string;
  quote_id: string | null;
  quote_version: number | null;
  provider_id: string | null;
  status: string | null;
  gate_status: string | null;
  source_hash: string | null;
  compiler_version: string | null;
  publish_blocked: boolean | null;
  previous_expr: Record<string, unknown> | null;
  compiled: ModelExpr[] | null;
  verify_report: VerifyReport | null;
  confirmed_at: string | null;
  created_at: string | null;
}

/** 编译状态 → 徽章（后端只产出这 4 个值） */
export const COMPILATION_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' }> = {
  COMPILED: { label: '已编译 · 写入封锁', tone: 'info' },
  VERIFIED: { label: '已验证 · 待确认', tone: 'warn' },
  CONFIRMED: { label: '已确认 · 已解锁', tone: 'success' },
  FAILED: { label: '验证失败', tone: 'danger' }
};

/** 模拟验证用例（BillingVerifier 的 V1–V6；V3 拆 a/b 两个边界） */
export const VERIFY_CASE_NAMES: Record<string, string> = {
  V1: '基础',
  V2: '缓存命中',
  V3: '阶梯边界',
  V3a: '阶梯·下界',
  V3b: '阶梯·上界',
  V4: '时段边界',
  V5: '组合',
  V6: '多模型独立'
};

export const compileApi = {
  /** ADM-CP01 编译记录列表（q：page/pageSize/status?） */
  list(query: { page?: number; pageSize?: number; status?: string } = {}) {
    return request<PageResult<CompilationResult>>('/admin/compilations', { query });
  },
  /** ADM-CP02 编译详情（含 compiled[] 与 verify_report） */
  detail(id: string) {
    return request<CompilationResult>(`/admin/compilations/${encodeURIComponent(id)}`);
  },
  /** ADM-Q01 发起编译：报价单须审核通过（未通过 E-1601）；仅 TECH_OPS/SUPER_ADMIN */
  compile(quoteId: string) {
    return request<CompilationResult>(`/admin/quotes/${encodeURIComponent(quoteId)}/compile`, { method: 'POST' });
  },
  /** ADM-CP03 重新模拟验证（失败 E-1405，报告仍保留） */
  verify(id: string) {
    return request<VerifyReport>(`/admin/compilations/${encodeURIComponent(id)}/verify`, { method: 'POST' });
  },
  /** ADM-CP04 人工确认（未验证 → E-1407；确认后解除写入封锁） */
  confirm(id: string) {
    return request<CompilationResult>(`/admin/compilations/${encodeURIComponent(id)}/confirm`, { method: 'POST' });
  }
};
