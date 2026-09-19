import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ApiError, tokenStore, request, API_BASE } from '@/api/http';

/** 构造一个 fetch 桩：返回指定的 HTTP 状态 + 响应体 */
function mockFetch(status: number, body: unknown, opts: { throwNetwork?: boolean } = {}) {
  return vi.fn(async () => {
    if (opts.throwNetwork) throw new TypeError('Failed to fetch');
    return {
      ok: status >= 200 && status < 300,
      status,
      text: async () => (body === undefined ? '' : JSON.stringify(body))
    } as unknown as Response;
  });
}

describe('aap-admin · http 客户端', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('成功：解析统一响应包并返回 data', async () => {
    vi.stubGlobal('fetch', mockFetch(200, { code: '0', message: 'ok', data: { total: 3, items: [1, 2, 3] } }));
    const r = await request<{ total: number }>('/admin/providers');
    expect(r.total).toBe(3);
  });

  it('基址是相对路径 /api/v1（纯 Web，不需要绝对基址）', () => {
    expect(API_BASE).toBe('/api/v1');
  });

  it('业务码非 0 → 抛 ApiError，且带上 code / message / traceId', async () => {
    vi.stubGlobal('fetch', mockFetch(200, { code: 'E-1601', message: '该报价单已被他人领取', traceId: 'abc123' }));
    await expect(request('/admin/reviews/1/claim', { method: 'POST' })).rejects.toMatchObject({
      name: 'ApiError',
      code: 'E-1601',
      message: '该报价单已被他人领取',
      traceId: 'abc123'
    });
  });

  it('HTTP 401 → 清 token 并抛 E-1902 语义（不静默吞掉）', async () => {
    localStorage.setItem('aap_admin_token', 't');
    vi.stubGlobal('fetch', mockFetch(401, { code: 'E-1902', message: '未认证或登录已过期' }));
    await expect(request('/admin/providers')).rejects.toMatchObject({ code: 'E-1902' });
    expect(tokenStore.get()).toBe(''); // token 被清
  });

  it('业务码 E-1902（HTTP 200）同样触发登出逻辑', async () => {
    localStorage.setItem('aap_admin_token', 't');
    vi.stubGlobal('fetch', mockFetch(200, { code: 'E-1902', message: '未认证或登录已过期' }));
    await expect(request('/admin/providers')).rejects.toMatchObject({ code: 'E-1902' });
    expect(tokenStore.get()).toBe('');
  });

  it('skipAuthRedirect：登录接口自身不清 token（否则登录失败会被当成会话过期）', async () => {
    localStorage.setItem('aap_admin_token', 'keep-me');
    vi.stubGlobal('fetch', mockFetch(401, { code: 'E-1902', message: '未认证' }));
    await expect(request('/auth/sms/login', { method: 'POST', skipAuthRedirect: true })).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBe('keep-me');
  });

  it('网络层失败 → E-NETWORK，与业务失败区分开（否则「后端没起来」会被误报成业务错误）', async () => {
    vi.stubGlobal('fetch', mockFetch(0, undefined, { throwNetwork: true }));
    await expect(request('/admin/providers')).rejects.toMatchObject({ code: 'E-NETWORK' });
  });

  it('响应不是合法 JSON → E-PARSE（带 HTTP 状态）', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, text: async () => '<html>502</html>' } as unknown as Response)));
    await expect(request('/admin/providers')).rejects.toMatchObject({ code: 'E-PARSE', status: 200 });
  });

  it('query 构造：丢弃 undefined/null/空串，数组展开为重复键', async () => {
    const f = mockFetch(200, { code: '0', data: null });
    vi.stubGlobal('fetch', f);
    await request('/admin/reviews', { query: { status: 'PENDING', page: 1, empty: '', nil: null, un: undefined, tags: ['a', 'b'] } });
    const url = String((f.mock.calls as unknown as string[][])[0][0]);
    expect(url).toContain('status=PENDING');
    expect(url).toContain('page=1');
    expect(url).not.toContain('empty=');
    expect(url).not.toContain('nil=');
    expect(url).not.toContain('un=');
    expect(url).toContain('tags=a');
    expect(url).toContain('tags=b');
  });

  it('带 token 时自动附 Authorization；无 token 时不附', async () => {
    const f1 = mockFetch(200, { code: '0', data: null });
    vi.stubGlobal('fetch', f1);
    await request('/admin/providers');
    expect((f1.mock.calls as unknown as [string, RequestInit][])[0][1].headers).not.toHaveProperty('Authorization');

    localStorage.setItem('aap_admin_token', 'tok-1');
    const f2 = mockFetch(200, { code: '0', data: null });
    vi.stubGlobal('fetch', f2);
    await request('/admin/providers');
    expect((f2.mock.calls as unknown as [string, RequestInit][])[0][1].headers).toMatchObject({ Authorization: 'Bearer tok-1' });
  });

  it('有 body 时设置 Content-Type: application/json 并序列化', async () => {
    const f = mockFetch(200, { code: '0', data: null });
    vi.stubGlobal('fetch', f);
    await request('/admin/reviews/1/approve', { method: 'POST', body: { comment: '价格合理' } });
    const init = (f.mock.calls as unknown as [string, RequestInit][])[0][1];
    expect(init.headers).toMatchObject({ 'Content-Type': 'application/json' });
    expect(init.body).toBe(JSON.stringify({ comment: '价格合理' }));
    expect(init.method).toBe('POST');
  });

  it('tokenStore 同时保存 token 与 refresh_token，clear 两个都清', () => {
    tokenStore.set('t1', 'r1');
    expect(tokenStore.get()).toBe('t1');
    expect(tokenStore.getRefresh()).toBe('r1');
    tokenStore.clear();
    expect(tokenStore.get()).toBe('');
    expect(tokenStore.getRefresh()).toBe('');
  });
});
