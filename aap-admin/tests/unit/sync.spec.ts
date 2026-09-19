import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  syncApi, SYNC_TASK_STATUS, BINDING_STATUS, SWITCHABLE_BINDING_STATUS, RETRYABLE_TASK_STATUS
} from '@/api/admin/sync';

function mockFetch(status: number, body: unknown) {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body)
  } as unknown as Response));
}

describe('aap-admin · new-api 同步契约对齐后端', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('任务列表用 pageSize（不是 page_size）+ status/bindingId 透传', async () => {
    const f = mockFetch(200, { code: '0', data: { total: 0, items: [] } });
    vi.stubGlobal('fetch', f);
    await syncApi.listTasks({ page: 1, pageSize: 50, status: 'FAILED', bindingId: '123' });
    const url = String((f.mock.calls as unknown as string[][])[0][0]);
    expect(url).toContain('pageSize=50');
    expect(url).toContain('status=FAILED');
    expect(url).toContain('bindingId=123');
    expect(url).not.toContain('page_size');
  });

  it('渠道启停走 ADM-S05，请求体字段是 target_status（不是 status）', async () => {
    const f = mockFetch(200, { code: '0', data: { id: '1', status: 'DISABLED' } });
    vi.stubGlobal('fetch', f);
    await syncApi.changeBindingStatus('77', 'DISABLED');
    const [url, init] = (f.mock.calls as unknown as [string, RequestInit][])[0];
    expect(url).toContain('/admin/channel-bindings/77/status');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual({ target_status: 'DISABLED' });
  });

  it('任务重试走 ADM-S03（POST /sync/tasks/{id}/retry）', async () => {
    const f = mockFetch(200, { code: '0', data: { id: '5', status: 'PENDING' } });
    vi.stubGlobal('fetch', f);
    await syncApi.retry('5');
    const [url, init] = (f.mock.calls as unknown as [string, RequestInit][])[0];
    expect(url).toContain('/admin/sync/tasks/5/retry');
    expect(init.method).toBe('POST');
  });

  it('状态机集合逐字对齐后端常量（SWITCHABLE / RETRYABLE）', () => {
    expect(SWITCHABLE_BINDING_STATUS).toEqual(['SYNCED', 'ENABLED', 'DISABLED']);
    expect(RETRYABLE_TASK_STATUS).toEqual(['FAILED', 'MANUAL']);
  });

  it('状态文案覆盖后端实际取值（设计稿：已同步 / 待同步 / 失败）', () => {
    expect(Object.keys(SYNC_TASK_STATUS)).toEqual(['PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'MANUAL']);
    expect(SYNC_TASK_STATUS.SUCCESS.label).toBe('已同步');
    expect(SYNC_TASK_STATUS.PENDING.label).toBe('待同步');
    expect(SYNC_TASK_STATUS.FAILED.label).toBe('失败');
    expect(BINDING_STATUS.SYNCED.label).toBe('已同步');
    expect(BINDING_STATUS.ENABLED.tone).toBe('success');
    expect(BINDING_STATUS.DISABLED.tone).toBe('muted');
  });
});
