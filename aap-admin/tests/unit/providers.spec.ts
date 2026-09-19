import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  providerApi, PROVIDER_STATUS, INDUSTRY_CATEGORY, INDUSTRY_CATEGORY_DRAWER_LABEL, SUSPEND_REASON_MAX
} from '@/api/admin/providers';
import {
  fmtShortDate, fmtDateTime, completenessTone, completenessText, industryLabel, industryTone,
  statusLabel, statusTone, isSuspended, pageSummary, UNKNOWN, MISSING_ACTIONS_NOTE, CATEGORY_FILTER_NOTE
} from '@/views/providers/model';
import {
  emptyVendorForm, validateVendorForm, vendorErrorSummary, vendorFooterHint, VENDOR_CODE_PATTERN,
  CATEGORY_OPTIONS, REGION_OPTIONS, CURRENCY_OPTIONS, NO_CREATE_API_NOTICE, NO_TEST_CONN_API_NOTICE
} from '@/views/providers/form';

function mockFetch(status: number, body: unknown) {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body)
  } as unknown as Response));
}

describe('aap-admin · 供应商管理（page-4-pc）契约对齐后端', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  /**
   * 缺陷8 回归：请求侧分页参数名必须是**驼峰 pageSize**。
   * 曾经发 page_size → 后端 @RequestParam Integer pageSize 绑不上 → 静默用默认 20 条/页
   * （请求 100 条也只回 20 条）。这条断言就是防它复发。
   */
  it('分页参数名是 pageSize（不是 page_size）', async () => {
    const f = mockFetch(200, { code: '0', data: { total: 0, items: [], page: 1, pageSize: 20 } });
    vi.stubGlobal('fetch', f);
    await providerApi.list({ page: 1, pageSize: 50 });
    const url = String((f.mock.calls as unknown as string[][])[0][0]);
    expect(url).toContain('pageSize=50');
    expect(url).not.toContain('page_size');
  });

  it('列表把 status / keyword 透传（空值不发，避免发出空条件）', async () => {
    const f = mockFetch(200, { code: '0', data: { total: 0, items: [] } });
    vi.stubGlobal('fetch', f);
    await providerApi.list({ page: 2, pageSize: 20, status: 'SUSPENDED', keyword: '云智' });
    const url = decodeURIComponent(String((f.mock.calls as unknown as string[][])[0][0]));
    expect(url).toContain('status=SUSPENDED');
    expect(url).toContain('keyword=云智');
    expect(url).toContain('page=2');

    const f2 = mockFetch(200, { code: '0', data: { total: 0, items: [] } });
    vi.stubGlobal('fetch', f2);
    await providerApi.list({ status: '', keyword: '' });
    const url2 = String((f2.mock.calls as unknown as string[][])[0][0]);
    expect(url2).not.toContain('status=');
    expect(url2).not.toContain('keyword=');
  });

  it('停用走 ADM-P02 且请求体字段是 suspend_reason（判据落在请求体上）', async () => {
    const f = mockFetch(200, { code: '0', data: { id: '1', status: 'SUSPENDED' } });
    vi.stubGlobal('fetch', f);
    await providerApi.suspend('123', '资质过期');
    const [url, init] = (f.mock.calls as unknown as [string, RequestInit][])[0];
    expect(url).toContain('/admin/providers/123/suspend');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual({ suspend_reason: '资质过期' });
    expect(SUSPEND_REASON_MAX).toBe(500);
  });

  it('恢复走 ADM-P03（POST，无请求体）', async () => {
    const f = mockFetch(200, { code: '0', data: { id: '1', status: 'PUBLISHED' } });
    vi.stubGlobal('fetch', f);
    await providerApi.resume('123');
    const [url, init] = (f.mock.calls as unknown as [string, RequestInit][])[0];
    expect(url).toContain('/admin/providers/123/resume');
    expect(init.method).toBe('POST');
  });

  it('ProviderStatus 12 态逐字取自清单 §5（不自己编枚举）', () => {
    expect(Object.keys(PROVIDER_STATUS)).toEqual([
      'PENDING_CREDENTIAL', 'DETECTING', 'DETECT_FAILED', 'DETECT_PASSED', 'QUOTING', 'QUOTE_SUBMITTED',
      'CONTRACT_PENDING', 'SIGNED', 'PAID', 'PUBLISHED', 'SUSPENDED', 'TERMINATED'
    ]);
    // 设计稿四态措辞与后端枚举的对应（已上架/审核中/检测未通过/待签署）
    expect(PROVIDER_STATUS.PUBLISHED.label).toBe('已上架');
    expect(PROVIDER_STATUS.QUOTE_SUBMITTED.label).toBe('审核中');
    expect(PROVIDER_STATUS.DETECT_FAILED.label).toBe('检测未通过');
    expect(PROVIDER_STATUS.CONTRACT_PENDING.label).toBe('待签署');
  });

  it('供应商类型 = 后端 @Pattern 的三个值（ORIGINAL|RESELLER|AGGREGATOR）', () => {
    expect(Object.keys(INDUSTRY_CATEGORY)).toEqual(['ORIGINAL', 'RESELLER', 'AGGREGATOR']);
    expect(Object.keys(INDUSTRY_CATEGORY_DRAWER_LABEL)).toEqual(['ORIGINAL', 'RESELLER', 'AGGREGATOR']);
    // 设计稿同一组枚举两处措辞不一致 → 两个映射都要有，偏差登记在页面可见文案里
    expect(CATEGORY_OPTIONS.map((c) => c.label)).toEqual(['官方直连', '第三方代理', '自建网关']);
  });
});

describe('aap-admin · 供应商管理页展示逻辑（诚实边界）', () => {
  it('时间格式：设计稿「最近更新」是 06-14 16:20；取不到就是「—」而不是空串', () => {
    expect(fmtShortDate('2026-06-14T16:20:31Z')).toBe('06-14 16:20');
    expect(fmtShortDate(null)).toBe(UNKNOWN);
    expect(fmtShortDate(undefined)).toBe(UNKNOWN);
    expect(fmtDateTime('2026-06-14T16:20:31Z')).toBe('2026-06-14 16:20:31');
    expect(fmtDateTime(null)).toBe(UNKNOWN);
  });

  it('档案完整度配色按设计帧阈值：≥80 绿 / ≥60 橙 / <60 红；取不到灰（未知≠0）', () => {
    expect(completenessTone(100)).toBe('success');
    expect(completenessTone(86)).toBe('success');
    expect(completenessTone(72)).toBe('warn');
    expect(completenessTone(48)).toBe('danger');
    expect(completenessTone(null)).toBe('muted');
    expect(completenessText(null)).toBe(UNKNOWN);
    expect(completenessText(72.4)).toBe('72%');
  });

  it('枚举取不到时回「—」/ 灰，不猜也不留空', () => {
    expect(industryLabel('RESELLER')).toBe('渠道商');
    expect(industryLabel(null)).toBe(UNKNOWN);
    expect(industryTone(null)).toBe('muted');
    expect(statusLabel('PUBLISHED')).toBe('已上架');
    expect(statusLabel('WHAT_EVER')).toBe('WHAT_EVER'); // 后端新增态也要显示出来，不吞
    expect(statusTone(null)).toBe('muted');
  });

  it('只有暂停态给「恢复」，其余给「停用」（后端 409 E-1601 是最终裁判）', () => {
    expect(isSuspended('SUSPENDED')).toBe(true);
    expect(isSuspended('PUBLISHED')).toBe(false);
    expect(isSuspended(null)).toBe(false);
  });

  it('分页文案照设计稿：「共 N 条，每页 20 条」', () => {
    expect(pageSummary(128, 20)).toBe('共 128 条，每页 20 条');
  });

  it('缺口文案必须说清「后端没有」与「未渲染假按钮」，不能只在注释里', () => {
    expect(MISSING_ACTIONS_NOTE).toContain('催办');
    expect(MISSING_ACTIONS_NOTE).toContain('后端');
    expect(MISSING_ACTIONS_NOTE).toContain('不渲染');
    expect(CATEGORY_FILTER_NOTE).toContain('当前页');
  });
});

describe('aap-admin · 新增供应商抽屉（page-4-1）表单校验', () => {
  it('空表单 → 5 项错误，汇总/底部文案按设计稿句式带真实数量', () => {
    const errors = validateVendorForm(emptyVendorForm());
    expect(Object.keys(errors).sort()).toEqual(['apiKey', 'baseUrl', 'category', 'code', 'name']);
    expect(errors.name).toBe('供应商名称不能为空');
    expect(errors.baseUrl).toBe('地址格式不正确，需以 http:// 或 https:// 开头');
    expect(errors.apiKey).toBe('请填写 API Key，或点击「测试连通」完成校验');
    expect(vendorErrorSummary(errors)).toBe('有 5 项内容需要修正，修正后才能保存供应商');
    expect(vendorFooterHint(errors)).toBe('5 项未通过校验，暂不可保存');
  });

  it('合法表单 → 0 项错误（校验不是永远失败的空转）', () => {
    const f = emptyVendorForm();
    Object.assign(f, {
      name: 'Mistral AI', code: 'mistral', category: 'ORIGINAL',
      baseUrl: 'https://api.mistral.ai/v1', apiKey: 'sk-test'
    });
    expect(validateVendorForm(f)).toEqual({});
    expect(vendorErrorSummary(validateVendorForm(f))).toBe('有 0 项内容需要修正，修正后才能保存供应商');
  });

  it('API Base URL 必须带协议头（设计稿原文：需以 http:// 或 https:// 开头）', () => {
    const f = emptyVendorForm();
    Object.assign(f, { name: 'x', code: 'x', category: 'RESELLER', apiKey: 'k' });
    f.baseUrl = 'api.mistral.ai/v1';
    expect(validateVendorForm(f).baseUrl).toBe('地址格式不正确，需以 http:// 或 https:// 开头');
    f.baseUrl = 'http://api.mistral.ai/v1';
    expect(validateVendorForm(f).baseUrl).toBeUndefined();
  });

  it('供应商标识：小写字母开头（设计稿「英文小写，用于路由与日志标识」）', () => {
    expect(VENDOR_CODE_PATTERN.test('mistral')).toBe(true);
    expect(VENDOR_CODE_PATTERN.test('mistral-ai-2')).toBe(true);
    expect(VENDOR_CODE_PATTERN.test('Mistral')).toBe(false);
    expect(VENDOR_CODE_PATTERN.test('2mistral')).toBe(false);
    expect(VENDOR_CODE_PATTERN.test('_mistral')).toBe(false);
  });

  it('选项集合照设计稿：地区 4 个、币种 2 个', () => {
    expect([...REGION_OPTIONS]).toEqual(['中国', '美国', '欧洲', '其他']);
    expect([...CURRENCY_OPTIONS]).toEqual(['CNY', 'USD']);
  });

  it('能力缺口提示必须写明「未发出任何请求」（不得假装保存成功）', () => {
    expect(NO_CREATE_API_NOTICE).toContain('未发出任何请求');
    expect(NO_CREATE_API_NOTICE).toContain('POST /admin/providers');
    expect(NO_TEST_CONN_API_NOTICE).toContain('未发出任何请求');
  });
});
