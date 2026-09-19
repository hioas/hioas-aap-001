import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  detectionApi, JOB_STATUS, JOB_RESULT, CONFIG_STATUS, PROBE_NAMES,
  DEFAULT_TIMEOUT_SECONDS, LONG_TIMEOUT_CODES, LONG_TIMEOUT_SECONDS
} from '@/api/admin/detection';

function mockFetch(status: number, body: unknown) {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body)
  } as unknown as Response));
}

describe('aap-admin · 检测中心契约对齐后端', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('人工放行走 DET-06，请求体字段是 override_reason（判据落在请求体上）', async () => {
    const f = mockFetch(200, { code: '0', data: { id: '1', status: 'COMPLETED', result: 'PASS' } });
    vi.stubGlobal('fetch', f);
    await detectionApi.release('458857864461266944', '人工核验通过');
    const [url, init] = (f.mock.calls as unknown as [string, RequestInit][])[0];
    expect(url).toContain('/detection-jobs/458857864461266944/release');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual({ override_reason: '人工核验通过' });
  });

  it('检测配置列表用 pageSize（不是 page_size）', async () => {
    const f = mockFetch(200, { code: '0', data: { total: 0, items: [] } });
    vi.stubGlobal('fetch', f);
    await detectionApi.listConfigs('DRAFT', 1, 50);
    const url = String((f.mock.calls as unknown as string[][])[0][0]);
    expect(url).toContain('pageSize=50');
    expect(url).toContain('status=DRAFT');
    expect(url).not.toContain('page_size');
  });

  it('新建/修改配置打到 ADM-CFG02/04 的正确方法与路径', async () => {
    const f = mockFetch(200, { code: '0', data: { id: '9' } });
    vi.stubGlobal('fetch', f);
    const body = { name: '默认配置', pass_score: 60, probes: [{ probe_code: 'D1', enabled: true, weight: 1, timeout_seconds: 180 }] };
    await detectionApi.createConfig(body);
    await detectionApi.updateConfig('9', body);
    await detectionApi.publishConfig('9');
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls[0][0]).toContain('/admin/detection-configs');
    expect(calls[0][1].method).toBe('POST');
    expect(calls[1][0]).toContain('/admin/detection-configs/9');
    expect(calls[1][1].method).toBe('PUT');
    expect(calls[2][0]).toContain('/admin/detection-configs/9/publish');
    expect(calls[2][1].method).toBe('POST');
  });

  it('检测项字典逐字等于后端 ProbeScoring.PROBE_NAMES（只允许 D1–D8）', () => {
    expect(Object.keys(PROBE_NAMES)).toEqual(['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8']);
    expect(PROBE_NAMES).toEqual({
      D1: 'TTFT', D2: 'P50 延迟', D3: '一致性', D4: 'RPM',
      D5: 'TPM', D6: '缓存命中', D7: '模型指纹', D8: '真实源'
    });
  });

  it('默认超时按 ER：D4/D5 = 600s，其余 180s', () => {
    expect(LONG_TIMEOUT_CODES).toEqual(['D4', 'D5']);
    expect(LONG_TIMEOUT_SECONDS).toBe(600);
    expect(DEFAULT_TIMEOUT_SECONDS).toBe(180);
  });

  it('任务状态与配置状态覆盖后端实际取值', () => {
    expect(Object.keys(JOB_STATUS)).toEqual(
      expect.arrayContaining(['QUEUED', 'RUNNING', 'PARTIAL_DONE', 'COMPLETED', 'FAILED', 'CANCELLED'])
    );
    // 设计稿措辞：运行中 / 排队中 / 已完成 / 失败
    expect(JOB_STATUS.RUNNING.label).toBe('运行中');
    expect(JOB_STATUS.QUEUED.label).toBe('排队中');
    expect(JOB_STATUS.COMPLETED.label).toBe('已完成');
    expect(JOB_STATUS.FAILED.label).toBe('失败');
    expect(Object.keys(CONFIG_STATUS)).toEqual(['DRAFT', 'PUBLISHED', 'SUPERSEDED']);
    expect(JOB_RESULT.PASS.label).toBe('通过');
    expect(JOB_RESULT.MANUAL_REVIEW.tone).toBe('warn');
  });
});
