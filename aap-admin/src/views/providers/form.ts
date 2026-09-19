/**
 * 「新增供应商」抽屉（设计真源：Calicat page-4-1 `4.1新增供应商 · 右侧抽屉（校验错误态）`）的
 * 表单模型与校验 —— 纯函数，不依赖 DOM，便于单测。
 *
 * ⚠️ 后端能力边界（不得假装成功）：
 *   管理端**没有** `POST /admin/providers`（无创建供应商接口），也没有「测试连通」接口。
 *   因此本表单的所有提交动作都必须显式告知「未发出任何请求」，不得伪造成功。
 *   登记见 `.agents/state/aap-decisions.md` D-ADM-4。
 *
 * 设计稿文案逐字取自 page-4-1：
 *   - 字段：供应商名称* / 供应商标识*（英文小写，用于路由与日志标识）/ 供应商类型* /
 *     所属地区 / API Base URL* / 默认 API Key*（含「测试连通」）/ 请求超时（ms）60000 /
 *     失败重试次数 2 / 结算币种 CNY·USD / 默认并发限流（QPS）50 / 启用该供应商
 *   - 错误汇总条：「有 N 项内容需要修正，修正后才能保存供应商」
 *   - 底部提示：「N 项未通过校验，暂不可保存」
 *   - 逐字段错误文案：「供应商名称不能为空」「地址格式不正确，需以 http:// 或 https:// 开头」
 *     「请填写 API Key，或点击「测试连通」完成校验」
 */
import { INDUSTRY_CATEGORY_DRAWER_LABEL } from '@/api/admin/providers';

export interface VendorForm {
  /** 供应商名称（必填） */
  name: string;
  /** 供应商标识：英文小写，用于路由与日志标识（必填） */
  code: string;
  /** 供应商类型（必填）—— 后端枚举 ORIGINAL / RESELLER / AGGREGATOR */
  category: '' | 'ORIGINAL' | 'RESELLER' | 'AGGREGATOR';
  /** 所属地区：设计稿给的四个选项；后端无对应字段（client-only） */
  region: string;
  /** API Base URL（必填，须以 http:// 或 https:// 开头） */
  baseUrl: string;
  /** 默认 API Key（必填） */
  apiKey: string;
  /** 请求超时（ms） */
  timeoutMs: number;
  /** 失败重试次数 */
  retries: number;
  /** 结算币种 */
  currency: 'CNY' | 'USD';
  /** 默认并发限流（QPS） */
  qps: number;
  /** 启用该供应商 */
  enabled: boolean;
}

/** 设计稿的四个地区选项（顺序照搬） */
export const REGION_OPTIONS = ['中国', '美国', '欧洲', '其他'] as const;

/** 设计稿的币种选项（USD 为设计稿选中态） */
export const CURRENCY_OPTIONS = ['CNY', 'USD'] as const;

/** 供应商类型的抽屉措辞（设计稿叫法；值仍是后端枚举） */
export const CATEGORY_OPTIONS = (['ORIGINAL', 'RESELLER', 'AGGREGATOR'] as const).map((value) => ({
  value,
  label: INDUSTRY_CATEGORY_DRAWER_LABEL[value]
}));

export function emptyVendorForm(): VendorForm {
  return {
    name: '',
    code: '',
    category: '',
    region: '欧洲', // 设计帧的选中态
    baseUrl: '',
    apiKey: '',
    timeoutMs: 60000,
    retries: 2,
    currency: 'USD', // 设计帧的选中态
    qps: 50,
    enabled: true // 设计帧的开关为开
  };
}

export type VendorFormErrors = Partial<Record<keyof VendorForm, string>>;

/** 供应商标识：英文小写，用于路由与日志标识 → 小写字母开头，后接小写字母/数字/连字符 */
export const VENDOR_CODE_PATTERN = /^[a-z][a-z0-9-]*$/;

/** 设计稿原文：「英文小写，用于路由与日志标识」 */
export const VENDOR_CODE_HINT = '英文小写，用于路由与日志标识';

export function validateVendorForm(form: VendorForm): VendorFormErrors {
  const errors: VendorFormErrors = {};
  if (!form.name.trim()) errors.name = '供应商名称不能为空';

  if (!form.code.trim()) errors.code = '供应商标识不能为空';
  else if (!VENDOR_CODE_PATTERN.test(form.code.trim())) errors.code = '供应商标识只能用小写字母、数字与连字符，且以字母开头';

  if (!form.category) errors.category = '请选择供应商类型';

  const url = form.baseUrl.trim();
  if (!url) errors.baseUrl = '地址格式不正确，需以 http:// 或 https:// 开头';
  else if (!/^https?:\/\/.+/.test(url)) errors.baseUrl = '地址格式不正确，需以 http:// 或 https:// 开头';

  if (!form.apiKey.trim()) errors.apiKey = '请填写 API Key，或点击「测试连通」完成校验';

  if (!Number.isFinite(form.timeoutMs) || form.timeoutMs <= 0) errors.timeoutMs = '请求超时需为正整数（ms）';
  if (!Number.isFinite(form.retries) || form.retries < 0) errors.retries = '失败重试次数不能为负';
  if (!Number.isFinite(form.qps) || form.qps <= 0) errors.qps = '并发限流需为正整数（QPS）';

  return errors;
}

export const VENDOR_ERROR_COUNT = (errors: VendorFormErrors): number => Object.keys(errors).length;

/** 错误汇总条文案（设计稿：「有 3 项内容需要修正，修正后才能保存供应商」） */
export const vendorErrorSummary = (errors: VendorFormErrors): string =>
  `有 ${VENDOR_ERROR_COUNT(errors)} 项内容需要修正，修正后才能保存供应商`;

/** 底部提示文案（设计稿：「3 项未通过校验，暂不可保存」） */
export const vendorFooterHint = (errors: VendorFormErrors): string =>
  `${VENDOR_ERROR_COUNT(errors)} 项未通过校验，暂不可保存`;

/**
 * 后端能力缺口说明（**必须**在页面上可见，不能只在注释里）。
 * 保存/保存草稿/测试连通三个动作都指向这一句。
 */
export const NO_CREATE_API_NOTICE =
  '后端未提供「创建供应商」接口（全仓无 POST /admin/providers）→ 本次未发出任何请求，也未写入任何数据。' +
  '已登记为能力缺口（D-ADM-4），待拍板：补后端接口 / 降级为只读 / 暂缓。';

/** 测试连通：后端同样无接口（供应商侧只有 credentials/{id}/precheck，属供应商本人） */
export const NO_TEST_CONN_API_NOTICE =
  '后端未提供管理端「测试连通」接口 → 本次未发出任何请求。';
