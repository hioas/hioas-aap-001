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
 * ⚠️ 后端**没有**「立即触发渠道同步」端点，也没有同步计划（间隔/下次同步）配置端点：
 *   设计稿的「立即同步 / 自动同步 / 下次同步 / 同步间隔」在管理端无对应能力（登记 D-ADM-6）。
 *   真实可用的是：读列表、按任务重试、渠道启停、读上游清单。
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
  }
};
