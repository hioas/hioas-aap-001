/**
 * 检测中心（page-5-pc）· 真源：`DetectionController`（DET-06）+ `AdminDetectionConfigController`（ADM-CFG01…05）
 *
 *   POST /detection-jobs/{jobId}/release   {override_reason}   人工放行（DET-06，TECH_OPS/SUPER_ADMIN）
 *   GET  /admin/detection-configs?page=&pageSize=&status=      检测配置列表（ADM-CFG01）
 *   POST /admin/detection-configs          {name,pass_score,veto_rule,probes[]}   新建（ADM-CFG02）
 *   PUT  /admin/detection-configs/{id}     同上（仅 DRAFT）     修改（ADM-CFG04）
 *   POST /admin/detection-configs/{id}/publish                 发布（ADM-CFG05，DRAFT→PUBLISHED）
 *
 * ⚠️ 能力缺口（**必须**在页面可见，不得用 0 或示意数据填充）：
 *   管理端**没有检测任务列表接口**（全仓 admin 侧只有 `POST /detection-jobs/{id}/release` 按 id 放行；
 *   DET-01…05 全部限供应商本人）→ 设计稿 page-5-pc 的「运行中任务 / 排队等待 / 今日已完成 / 失败率」
 *   四个 KPI 与任务表格**无法用真实数据渲染**。登记为 D-ADM-5，等拍板补接口。
 */
import { request, type PageResult } from '@/api/http';

/** 检测任务（DET-02 / DET-06 响应体，`DetectionViews.Job`） */
export interface DetectionJob {
  id: string;
  job_id: string;
  job_no: string | null;
  provider_id: string | null;
  credential_id: string | null;
  status: string;
  trigger_type: string | null;
  started_at: string | null;
  finished_at: string | null;
  total_score: number | null;
  result: string | null;
  confidence: string | null;
  error_code: string | null;
  error_msg: string | null;
  report_id: string | null;
  attempt_count: number | null;
  progress?: { percent: number | null; finished: number | null; total: number | null; eta_minutes: number | null };
  created_at: string | null;
  updated_at: string | null;
  /** ADM-DET01 管理端列表附加（供应商侧为 null）：运营据此辨认是哪个供应商/哪条线路 */
  provider_name?: string | null;
  credential_alias?: string | null;
}

/** 检测任务状态（`DetectionService`：QUEUED / RUNNING / PARTIAL_DONE / COMPLETED / CANCELLED） */
export const JOB_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  QUEUED: { label: '排队中', tone: 'warn' },
  RUNNING: { label: '运行中', tone: 'info' },
  PARTIAL_DONE: { label: '部分完成', tone: 'warn' },
  COMPLETED: { label: '已完成', tone: 'success' },
  FAILED: { label: '失败', tone: 'danger' },
  CANCELLED: { label: '已取消', tone: 'muted' }
};

/** 检测结论（R-25 四分支） */
export const JOB_RESULT: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  PASS: { label: '通过', tone: 'success' },
  FAIL: { label: '不通过', tone: 'danger' },
  MANUAL_REVIEW: { label: '人工复核', tone: 'warn' },
  PARTIAL: { label: '部分通过', tone: 'info' }
};

/** 检测配置状态（ADM-CFG05：DRAFT → PUBLISHED，旧活版置 SUPERSEDED） */
export const CONFIG_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  DRAFT: { label: '草稿', tone: 'warn' },
  PUBLISHED: { label: '已发布', tone: 'success' },
  SUPERSEDED: { label: '已被替代', tone: 'muted' }
};

/**
 * 检测项字典（**逐字取自后端 `ProbeScoring.PROBE_NAMES`**，只允许 D1–D8）。
 * 前端不得自己造检测项；后端对非法/重复 code 直接 E-1001。
 */
export const PROBE_NAMES: Record<string, string> = {
  D1: 'TTFT',
  D2: 'P50 延迟',
  D3: '一致性',
  D4: 'RPM',
  D5: 'TPM',
  D6: '缓存命中',
  D7: '模型指纹',
  D8: '真实源'
};

/** 默认超时（ER §aap_detection_config_probe：D1–D3/D6–D8 = 180s，D4/D5 = 600s） */
export const LONG_TIMEOUT_CODES = ['D4', 'D5'];
export const DEFAULT_TIMEOUT_SECONDS = 180;
export const LONG_TIMEOUT_SECONDS = 600;

export interface DetectionProbe {
  probe_code: string;
  probe_name: string | null;
  enabled: boolean;
  weight: number;
  timeout_seconds: number;
  params?: unknown;
}

export interface DetectionConfig {
  id: string;
  config_id: string;
  version_no: string | null;
  name: string | null;
  pass_score: number | null;
  veto_rule?: unknown;
  status: string;
  probes: DetectionProbe[];
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DetectionConfigSave {
  name: string;
  pass_score: number;
  veto_rule?: unknown;
  probes: Array<{ probe_code: string; enabled: boolean; weight: number; timeout_seconds: number }>;
}

export const detectionApi = {
  /**
   * ADM-DET01 检测任务列表（管理端跨供应商；**2026-09-23 新增**）。
   *
   * <p>此前管理端无任何任务列表端点 → 本页 KPI/表格只能显「未知」，人工放行需手输任务 ID
   * （运营无从得知 ID）→ 放行实际不可用，而它是凭证拿到 PASS（进而报价）的唯一路径。
   */
  jobs(query: { status?: string; credentialId?: string; providerId?: string; page?: number; pageSize?: number } = {}) {
    return request<PageResult<DetectionJob>>('/admin/detection-jobs', { query });
  },
  /** DET-06 人工放行：理由必填（后端 E-1001）；任务不存在 E-1304；已取消 E-1601 */
  release(jobId: string, reason: string) {
    return request<DetectionJob>(`/detection-jobs/${encodeURIComponent(jobId)}/release`, {
      method: 'POST',
      body: { override_reason: reason }
    });
  },
  listConfigs(status?: string, page = 1, pageSize = 20) {
    return request<PageResult<DetectionConfig>>('/admin/detection-configs', {
      query: { status: status || undefined, page, pageSize }
    });
  },
  createConfig(body: DetectionConfigSave) {
    return request<DetectionConfig>('/admin/detection-configs', { method: 'POST', body });
  },
  updateConfig(id: string, body: DetectionConfigSave) {
    return request<DetectionConfig>(`/admin/detection-configs/${id}`, { method: 'PUT', body });
  },
  publishConfig(id: string) {
    return request<DetectionConfig>(`/admin/detection-configs/${id}/publish`, { method: 'POST' });
  }
};
