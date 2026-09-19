/**
 * 供应商管理（ADM-P01…03）· 真源：`AdminProviderController` + `ProviderProfileResponse`
 *
 *   GET  /admin/providers?page=&pageSize=&status=&keyword=   供应商列表（ADM-P01）
 *   POST /admin/providers/{id}/suspend  {suspend_reason}     暂停（ADM-P02，原因 2–500 字）
 *   POST /admin/providers/{id}/resume                        恢复（ADM-P03，回到暂停前状态）
 *
 * 字段名逐字取自 `ProviderProfileResponse`（同一字段同时有 snake_case 与 camelCase 两套别名，
 * 这里统一读 snake_case，与决策 D-JSON-01「与数据字典同名」一致）。
 *
 * ⚠️ 管理端**没有**「新建供应商」接口（无 `POST /admin/providers`），
 * 也没有催办 / 催签 / 管理端看报告接口 —— 见 `.agents/state/aap-decisions.md` D-ADM-4。
 */
import { request, type PageResult } from '@/api/http';

/** 供应商档案（ADM-P01 列表项 / ADM-P02·03 响应体） */
export interface ProviderRow {
  id: string;
  provider_id: string;
  provider_no: string | null;
  provider_code: string | null;
  company_name: string | null;
  uscc: string | null;
  industry_category: string | null;
  province: string | null;
  city: string | null;
  address: string | null;
  website: string | null;
  contact_name: string | null;
  contact_title: string | null;
  contact_phone_masked: string | null;
  contact_email: string | null;
  company_intro: string | null;
  /** 档案完整度 0–100（后端 `aap_provider.completeness`） */
  completeness: number;
  qualification_files: ProviderFileAsset[];
  status: string;
  recheck_interval_days: number;
  manual_override: boolean;
  override_reason: string | null;
  account?: { phone_masked: string | null; role: string | null; wx_bound: boolean };
  created_at: string | null;
  updated_at: string | null;
  version: number;
}

export interface ProviderFileAsset {
  file_id: string;
  file_name: string | null;
  size: number | null;
  content_type: string | null;
  uploaded_at: string | null;
  type: string | null;
}

/**
 * 供应商类型（后端 `ProviderController` 的 `@Pattern`：`^(ORIGINAL|RESELLER|AGGREGATOR)$`）。
 *
 * ⚠️ 设计稿内部两处不一致：page-4-pc 列表列写「渠道商 / 原厂 / 中转商」，
 * page-4-1 新增抽屉的类型选项写「官方直连 / 第三方代理 / 自建网关」。
 * 这里以**后端枚举**为准（三个值一一对应），把抽屉侧的措辞差异登记为设计偏差，
 * 不静默二选一。
 */
export const INDUSTRY_CATEGORY: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'muted' }> = {
  ORIGINAL: { label: '原厂', tone: 'info' },
  RESELLER: { label: '渠道商', tone: 'success' },
  AGGREGATOR: { label: '中转商', tone: 'warn' }
};

/** 抽屉（page-4-1）里的类型措辞 —— 与上面同一枚举，只是设计稿的另一种叫法（偏差留痕）。 */
export const INDUSTRY_CATEGORY_DRAWER_LABEL: Record<string, string> = {
  ORIGINAL: '官方直连',
  RESELLER: '第三方代理',
  AGGREGATOR: '自建网关'
};

/**
 * ProviderStatus 12 态（清单 §5 / 17-spec §4，逐字取自
 * `docs/backend/02-API接口模型清单.md` §5 全局枚举字典）。
 */
export const PROVIDER_STATUS: Record<string, { label: string; tone: 'info' | 'warn' | 'success' | 'danger' | 'muted' }> = {
  PENDING_CREDENTIAL: { label: '待接入凭证', tone: 'warn' },
  DETECTING: { label: '检测中', tone: 'info' },
  DETECT_FAILED: { label: '检测未通过', tone: 'danger' },
  DETECT_PASSED: { label: '检测通过', tone: 'success' },
  QUOTING: { label: '报价中', tone: 'info' },
  QUOTE_SUBMITTED: { label: '审核中', tone: 'warn' },
  CONTRACT_PENDING: { label: '待签署', tone: 'warn' },
  SIGNED: { label: '已签署', tone: 'info' },
  PAID: { label: '已打款', tone: 'success' },
  PUBLISHED: { label: '已上架', tone: 'success' },
  SUSPENDED: { label: '已暂停', tone: 'danger' },
  TERMINATED: { label: '已终止', tone: 'muted' }
};

/** 暂停原因（ADM-P02 契约：`suspend_reason` 必填、2–500 字） */
export const SUSPEND_REASON_MIN = 2;
export const SUSPEND_REASON_MAX = 500;

export const providerApi = {
  list(params: { page?: number; pageSize?: number; status?: string; keyword?: string } = {}) {
    return request<PageResult<ProviderRow>>('/admin/providers', {
      query: {
        page: params.page ?? 1,
        pageSize: params.pageSize ?? 20,
        status: params.status || undefined,
        keyword: params.keyword || undefined
      }
    });
  },
  /** ADM-P02：状态非法（如已是暂停态）→ 409 E-1601 */
  suspend(id: string, reason: string) {
    return request<ProviderRow>(`/admin/providers/${id}/suspend`, {
      method: 'POST',
      body: { suspend_reason: reason }
    });
  },
  /** ADM-P03：非暂停态 → 409 E-1601 */
  resume(id: string) {
    return request<ProviderRow>(`/admin/providers/${id}/resume`, { method: 'POST' });
  }
};
