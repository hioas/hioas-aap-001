/**
 * 管理端 HTTP 客户端
 *
 * 约定（与后端统一响应包一致）：
 *   - 业务码在 body.code：'0' 成功；非 '0' 抛 ApiError（含 code/message/traceId）
 *   - HTTP 401 / body.code = E-1902 → 清 token 并跳登录（不静默吞掉）
 *   - 基址用**相对路径** /api/v1：dev 由 vite proxy 转发到 127.0.0.1:8084，
 *     生产同源部署。管理端是纯 Web，不存在小程序那种「相对 URL 不可用」的约束。
 */
import { ElMessage } from 'element-plus';

export const API_BASE = '/api/v1';

const TOKEN_KEY = 'aap_admin_token';
const REFRESH_KEY = 'aap_admin_refresh_token';

export class ApiError extends Error {
  code: string;
  traceId?: string;
  status?: number;
  constructor(code: string, message: string, opts: { traceId?: string; status?: number } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.traceId = opts.traceId;
    this.status = opts.status;
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY) || '',
  getRefresh: () => localStorage.getItem(REFRESH_KEY) || '',
  set(token: string, refresh?: string) {
    localStorage.setItem(TOKEN_KEY, token);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }
};

export interface ApiEnvelope<T> {
  code: string;
  message?: string;
  data?: T;
  /**
   * 追踪号。⚠️ 后端统一响应包用的是**驼峰 `traceId`**（实测
   * `{"code":"E-1001","message":"参数校验失败","data":null,"traceId":"776b0abc..."}`），
   * 不是 snake_case。两种都声明并容错，避免排障时拿不到追踪号。
   */
  traceId?: string;
  trace_id?: string;
  details?: unknown;
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  /** query 参数；undefined/null/'' 的键会被丢弃（避免发出空条件） */
  query?: Record<string, unknown>;
  body?: unknown;
  /** 跳过 401 自动登出（登录接口自身用） */
  skipAuthRedirect?: boolean;
  signal?: AbortSignal;
}

function buildQuery(query?: Record<string, unknown>): string {
  if (!query) return '';
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue;
    if (Array.isArray(v)) {
      for (const item of v) if (item !== undefined && item !== null && item !== '') usp.append(k, String(item));
    } else {
      usp.append(k, String(v));
    }
  }
  const s = usp.toString();
  return s ? `?${s}` : '';
}

/** 一次真实的 fetch；把「网络层失败」和「业务码非 0」区分开 */
export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE}${path}${buildQuery(opts.query)}`;
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let bodyInit: BodyInit | undefined;
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    bodyInit = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(url, { method: opts.method ?? 'GET', headers, body: bodyInit, signal: opts.signal });
  } catch (e) {
    // 网络层失败必须与业务失败区分：否则会把「后端没起来」误报成业务错误
    throw new ApiError('E-NETWORK', `无法连接后端（${url}）：${(e as Error).message}`, { status: 0 });
  }

  let env: ApiEnvelope<T> | null = null;
  const text = await res.text();
  if (text) {
    try {
      env = JSON.parse(text) as ApiEnvelope<T>;
    } catch {
      throw new ApiError('E-PARSE', `响应不是合法 JSON（HTTP ${res.status}）：${text.slice(0, 200)}`, { status: res.status });
    }
  }

  const code = env?.code ?? (res.ok ? '0' : `HTTP_${res.status}`);
  if (res.status === 401 || code === 'E-1902') {
    if (!opts.skipAuthRedirect) {
      tokenStore.clear();
      ElMessage.error('登录已过期，请重新登录');
      if (typeof location !== 'undefined' && !location.hash.startsWith('#/login')) location.hash = '#/login';
    }
    throw new ApiError(code, env?.message ?? '未认证或登录已过期', { traceId: env?.traceId ?? env?.trace_id, status: res.status });
  }

  if (!res.ok || code !== '0') {
    throw new ApiError(code, env?.message ?? `请求失败（HTTP ${res.status}）`, {
      // 后端用驼峰 traceId；旧代码只读 trace_id，追踪号永远拿不到（新写的测试抓到）
      traceId: env?.traceId ?? env?.trace_id,
      status: res.status
    });
  }
  return (env?.data ?? (null as unknown as T)) as T;
}

/** 分页响应的统一形状（后端列表接口） */
export interface PageResult<T> {
  total: number;
  items: T[];
  page?: number;
  page_size?: number;
}
