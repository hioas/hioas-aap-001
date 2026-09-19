/**
 * 进件状态看板的数据组装。
 *
 * 数据真源：后端 admin 接口（不臆造字段）。
 *   GET /admin/providers                  → 供应商列表（进件主体）
 *   GET /admin/reviews                    → 待审报价池
 *   GET /admin/contracts                  → 合同（待签）
 *   GET /admin/payments                   → 打款记录（待打款）
 *   GET /admin/sync/tasks                 → 同步任务（异常告警）
 *   GET /admin/usage/hourly               → 近 24h 用量
 *
 * ⚠️ 诚实边界（PRD 13 §0）：后端目前**没有**看板聚合接口，KPI 与漏斗是
 * 由上述列表接口**如实统计**得出；取不到的维度一律显式标注「未采集」，
 * 不编造数字（设计稿的 128/36/19/73/200 是示意值，不能当真实数据渲染）。
 */
import { request, type PageResult } from '@/api/http';

export interface KpiCard {
  key: string;
  label: string;
  value: number | null;
  unit?: string;
  /** 环比：设计稿显示「↑ 12.5%」；后端没有历史快照时显式标记不可比 */
  delta?: { text: string; direction: 'up' | 'down' | 'flat' } | null;
  /** 环比不可比的原因（诚实边界） */
  deltaNote?: string;
  tone?: 'default' | 'warn' | 'danger';
}

export interface FunnelStage {
  label: string;
  value: number | null;
}

export interface ProviderRow {
  id: string;
  intakeNo: string;
  provider: string;
  stage: string;
  status: string;
  statusTone: 'info' | 'warn' | 'success' | 'danger' | 'muted';
  updatedAt: string;
  owner: string;
  action: { label: string; route: string };
}

export interface DashboardData {
  kpis: KpiCard[];
  funnel: FunnelStage[];
  funnelNote: string | null;
  providers: ProviderRow[];
  total: number;
  /** 各数据源取数失败时的显式说明（不静默吞） */
  warnings: string[];
  fetchedAt: string;
}

/** 后端供应商状态 → 看板环节 + 徽章色（PRD 13 §3 五色映射） */
const STAGE_MAP: Record<string, { stage: string; status: string; tone: ProviderRow['statusTone']; action: ProviderRow['action'] }> = {
  PENDING_PRECHECK: { stage: '凭证提交', status: '待检测', tone: 'warn', action: { label: '查看', route: '/providers' } },
  PENDING_DETECTION: { stage: '检测验真', status: '待检测', tone: 'warn', action: { label: '查看', route: '/detection' } },
  DETECTING: { stage: '检测验真', status: '进行中', tone: 'info', action: { label: '查看', route: '/detection' } },
  ACTIVE: { stage: '报价审核', status: '供货中', tone: 'success', action: { label: '查看', route: '/providers' } },
  SUSPENDED: { stage: '已停用', status: '已停用', tone: 'danger', action: { label: '查看', route: '/providers' } },
  DETECT_FAILED: { stage: '检测验真', status: '未通过', tone: 'danger', action: { label: '查看报告', route: '/detection' } },
  REJECTED: { stage: '凭证提交', status: '已驳回', tone: 'danger', action: { label: '查看', route: '/providers' } }
};

function mapProvider(p: Record<string, any>): ProviderRow {
  const raw = String(p.status ?? '');
  const m = STAGE_MAP[raw] ?? { stage: '凭证提交', status: raw || '未知', tone: 'muted' as const, action: { label: '查看', route: '/providers' } };
  return {
    id: String(p.id ?? ''),
    intakeNo: String(p.code ?? p.provider_no ?? p.id ?? ''),
    provider: String(p.name ?? p.company_name ?? ''),
    stage: m.stage,
    status: m.status,
    statusTone: m.tone,
    updatedAt: String(p.updated_at ?? p.created_at ?? ''),
    owner: String(p.owner_name ?? p.owner ?? '未分配'),
    action: m.action
  };
}

/** 安全取列表：任一数据源失败不阻断整页，但必须记进 warnings */
async function safeList(path: string, query?: Record<string, unknown>): Promise<{ items: any[]; total: number; error?: string }> {
  try {
    const r = await request<PageResult<any>>(path, { query });
    return { items: r?.items ?? [], total: r?.total ?? (r?.items?.length ?? 0) };
  } catch (e) {
    return { items: [], total: 0, error: `${path} → ${(e as Error).message}` };
  }
}

export async function loadDashboard(): Promise<DashboardData> {
  const warnings: string[] = [];
  const [providers, reviews, contracts, payments, syncTasks] = await Promise.all([
    safeList('/admin/providers', { page: 1, pageSize: 100 }),
    safeList('/admin/reviews', { page: 1, pageSize: 100 }),
    safeList('/admin/contracts', { page: 1, pageSize: 100 }),
    safeList('/admin/payments', { page: 1, pageSize: 100 }),
    safeList('/admin/sync/tasks', { page: 1, pageSize: 100 })
  ]);
  for (const [name, r] of [['供应商', providers], ['待审报价', reviews], ['合同', contracts], ['打款', payments], ['同步任务', syncTasks]] as const) {
    if (r.error) warnings.push(`${name}：${r.error}`);
  }

  const rows = providers.items.map(mapProvider);

  // 阶段计数（真实统计；取不到即 null，由页面渲染为「—」，不写 0 冒充）
  const countBy = (pred: (r: ProviderRow) => boolean) => (providers.error ? null : rows.filter(pred).length);
  const inIntake = countBy((r) => r.stage === '凭证提交');
  const inDetection = countBy((r) => r.stage === '检测验真');
  const supplying = countBy((r) => r.stage === '报价审核');

  // 待打款：后端 settlement_status 未打款
  const pendingPay = payments.error
    ? null
    : payments.items.filter((p) => String(p.settlement_status ?? p.status ?? '').includes('未打款') || String(p.status ?? '') === 'PENDING').length;
  // 待签合同
  const pendingSign = contracts.error
    ? null
    : contracts.items.filter((c) => String(c.status ?? '') === 'PENDING' || String(c.status ?? '') === '待签').length;
  // 异常告警：同步失败
  const syncFailed = syncTasks.error
    ? null
    : syncTasks.items.filter((t) => ['FAILED', 'PARTIAL_FAILED'].includes(String(t.status ?? ''))).length;

  const kpis: KpiCard[] = [
    {
      key: 'intake',
      label: '进件总数',
      value: providers.error ? null : providers.total,
      delta: null,
      deltaNote: '后端无历史快照，环比不可比'
    },
    {
      key: 'pending_detect',
      label: '待检测任务',
      value: inDetection,
      delta: null,
      deltaNote: '后端无历史快照，环比不可比',
      tone: 'warn'
    },
    { key: 'pending_review', label: '待审核报价单', value: reviews.error ? null : reviews.total, delta: null, deltaNote: '后端无历史快照，环比不可比', tone: 'warn' },
    { key: 'pending_sign', label: '待签合同', value: pendingSign, delta: null, deltaNote: '后端无历史快照，环比不可比' },
    { key: 'pending_pay', label: '待打款', value: pendingPay, delta: null, deltaNote: '后端无历史快照，环比不可比', tone: 'danger' },
    { key: 'sync_failed', label: '同步异常', value: syncFailed, delta: null, deltaNote: '后端无历史快照，环比不可比', tone: 'danger' }
  ];

  // 漏斗（设计稿 4 段：已注册 → 已提交凭证 → 检测通过 → 报价已上架）
  const funnel: FunnelStage[] = [
    { label: '已注册', value: providers.error ? null : providers.total },
    { label: '已提交凭证', value: inIntake === null || inDetection === null ? null : (providers.total - inIntake) },
    { label: '检测通过', value: inDetection },
    { label: '报价已上架', value: supplying }
  ];

  return {
    kpis,
    funnel,
    funnelNote: warnings.length ? null : '转化率由上方阶段计数实时计算（后端无漏斗接口，未编造）',
    providers: rows.slice(0, 20),
    total: providers.total,
    warnings,
    fetchedAt: new Date().toISOString()
  };
}
