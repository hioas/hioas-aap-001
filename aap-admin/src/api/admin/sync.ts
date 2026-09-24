/**
 * new-api 同步（page-8-pc）· 真源：`AdminSyncController`（ADM-S01…06）
 *
 *   GET  /admin/sync/tasks?page=&pageSize=&status=&bindingId=   同步任务（ADM-S01，含 operations 明细）
 *   GET  /admin/sync/tasks/{taskId}                             任务详情（ADM-S02）
 *   POST /admin/sync/tasks/{taskId}/retry                       重试（ADM-S03，仅 FAILED / MANUAL）
 *   GET  /admin/channel-bindings?page=&pageSize=                渠道绑定（ADM-S04）
 *   POST /admin/channel-bindings/{id}/status  {target_status}   启停（ADM-S05，仅 SYNCED/ENABLED/DISABLED）
 *   GET  /admin/sync/models/upstream                            上游模型清单（ADM-S06，未配 ACTIVE 端点 → E-1501）
 *
 *   POST /admin/newapi-endpoints  {name,base_url,api_key,readonly}   登记同步端点（ADM-S07，仅 SUPER_ADMIN）
 *   POST /admin/sync/tasks  {provider_id,compilation_id?,channel_name?,mode?}  发起上架同步（ADM-S08）
 *   POST /admin/sync/tasks/{taskId}/execute  {dry_run?}              执行上架（ADM-S09，读前写后三段式）
 *
 * ⚠️ 诚实边界：
 *   - 「立即同步单个渠道」没有对应端点：上架是**按任务**推进的（ADM-S08 建任务 → ADM-S09 执行），
 *     不是「按渠道点一下」；设计稿的「自动同步 / 下次同步 / 同步间隔」仍无配置端点（登记 D-ADM-6）。
 *   - ADM-S08 要求该供应商存在 gate_status=CONFIRMED 的编译产物，否则 409 E-1407（闸门③）——
 *     前端把该错误如实透出，不做「先建任务再补编译」这类绕闸门的动作。
 *   - ADM-S07 的 api_key **只进不出**：响应只回 api_key_mask，页面永不回显明文。
 */
import { request, type PageResult } from '@/api/http';

export interface SyncOperation {
  id: string;
  operation: string | null;
  request_payload: unknown;
  response_payload: unknown;
  result: string | null;
  readback_equal: boolean | null;
  attempt_no: number | null;
  error: string | null;
  created_at: string | null;
}

export interface SyncTask {
  id: string;
  task_id: string;
  task_no: string | null;
  binding_id: string | null;
  provider_id: string | null;
  compilation_id: string | null;
  task_type: string | null;
  status: string;
  payload?: unknown;
  idempotency_key: string | null;
  attempt_count: number | null;
  next_retry_at: string | null;
  last_error: string | null;
  readback_equal: boolean | null;
  operations?: SyncOperation[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ChannelBinding {
  id: string;
  binding_id: string;
  provider_id: string | null;
  credential_id: string | null;
  endpoint_id: string | null;
  channel_id: number | null;
  channel_name: string | null;
  tag: string | null;
  group_name: string | null;
  priority: number | null;
  weight: number | null;
  models: string[] | null;
  status: string;
  last_synced_at: string | null;
  last_readback_hash: string | null;
}

export interface UpstreamModel {
  model_name: string;
  vendor: string | null;
  owned_by: string | null;
  enabled: boolean | null;
}

/**
 * ADM-S07 响应：new-api 同步端点。
 * 注意字段只有 `api_key_mask`（形如 `sk-****abcd`）——**没有**明文 `api_key` 字段，
 * 与契约一致（服务端加密落库，掩码是唯一出口）。
 */
export interface NewApiEndpoint {
  id: string;
  name: string;
  base_url: string;
  readonly: boolean | null;
  status: string | null;
  api_key_mask: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** 同步任务状态（`SyncAdminService.RETRYABLE` 等口径：PENDING/RUNNING/SUCCESS/FAILED/MANUAL） */
export const SYNC_TASK_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  PENDING: { label: '待同步', tone: 'warn' },
  RUNNING: { label: '同步中', tone: 'info' },
  SUCCESS: { label: '已同步', tone: 'success' },
  FAILED: { label: '失败', tone: 'danger' },
  MANUAL: { label: '待人工介入', tone: 'warn' }
};

/** 渠道绑定状态机（PRD §3：SYNCED → ENABLED ⇄ DISABLED） */
export const BINDING_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  SYNCED: { label: '已同步', tone: 'success' },
  ENABLED: { label: '已启用', tone: 'success' },
  DISABLED: { label: '已停用', tone: 'muted' },
  PENDING: { label: '待同步', tone: 'warn' },
  FAILED: { label: '失败', tone: 'danger' }
};

/** 允许启停的渠道状态（后端 SWITCHABLE：SYNCED / ENABLED / DISABLED） */
export const SWITCHABLE_BINDING_STATUS = ['SYNCED', 'ENABLED', 'DISABLED'];

/** 允许重试的任务状态（后端 RETRYABLE：FAILED / MANUAL） */
export const RETRYABLE_TASK_STATUS = ['FAILED', 'MANUAL'];

export const syncApi = {
  listTasks(params: { page?: number; pageSize?: number; status?: string; bindingId?: string } = {}) {
    return request<PageResult<SyncTask>>('/admin/sync/tasks', {
      query: {
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        status: params.status || undefined,
        bindingId: params.bindingId || undefined
      }
    });
  },
  taskDetail(taskId: string) {
    return request<SyncTask>(`/admin/sync/tasks/${taskId}`);
  },
  retry(taskId: string) {
    return request<SyncTask>(`/admin/sync/tasks/${taskId}/retry`, { method: 'POST' });
  },
  listBindings(page = 1, pageSize = 20) {
    return request<PageResult<ChannelBinding>>('/admin/channel-bindings', { query: { page, pageSize } });
  },
  changeBindingStatus(bindingId: string, targetStatus: 'ENABLED' | 'DISABLED') {
    return request<ChannelBinding>(`/admin/channel-bindings/${bindingId}/status`, {
      method: 'POST',
      body: { target_status: targetStatus }
    });
  },
  upstreamModels() {
    return request<{ models: UpstreamModel[] }>('/admin/sync/models/upstream');
  },
  /**
   * ADM-S07 登记 new-api 端点（仅 SUPER_ADMIN）。
   * `api_key` 只进不出：服务端加密落 `api_key_cipher`，响应只回掩码。
   */
  registerEndpoint(body: { name: string; base_url: string; api_key: string; readonly?: boolean }) {
    return request<NewApiEndpoint>('/admin/newapi-endpoints', { method: 'POST', body });
  },
  /**
   * ADM-S08 发起上架同步（建渠道 + 写价）。
   * 闸门③：该供应商需有 `CONFIRMED` 编译产物，否则 409 `E-1407`；
   * 幂等键 `sha256(provider_id|ADD_CHANNEL|channel_name)` —— 重复发起返回**同一**任务。
   */
  createTask(body: {
    provider_id: string;
    compilation_id?: string;
    channel_name?: string;
    mode?: 'REVIEW_THEN_APPLY' | 'DRY_RUN';
  }) {
    return request<SyncTask>('/admin/sync/tasks', { method: 'POST', body });
  },
  /** ADM-S09 执行上架（读前写后三段式 + 回读一致）；`dryRun=true` 只回预演，零上游写零库写。 */
  executeTask(taskId: string, dryRun = false) {
    return request<SyncTask>(`/admin/sync/tasks/${taskId}/execute`, { method: 'POST', body: { dry_run: dryRun } });
  }
};
