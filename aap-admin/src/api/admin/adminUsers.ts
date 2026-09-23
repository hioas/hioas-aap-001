import { request, type PageResult } from '@/api/http';

/**
 * 运营账号管理（ADM-AUTH02…05，2026-09-23 新增）。
 *
 * <p>为什么要页面：`ADM-AUTH01` 打通管理端登录后，**建号仍只能手写 SQL**（生产运维无法自助开通），
 * 后端 4 个端点早就位但控制台没有入口 —— 属于「接口有、界面点不到」那一类缺口。
 *
 * <p>权限：全部限 **SUPER_ADMIN**（建号/停用属提权操作，不下放给运营商务/技术运营）；
 * 前端只做渲染过滤，后端一律二次校验（403 E-1901）。
 * 手机号只出**脱敏值** `phone_masked`（后端不明文返回）。
 */
export interface AdminUserRow {
  id: string;
  admin_user_id: string;
  username: string;
  display_name: string | null;
  role: string;
  status: string;
  phone_masked: string | null;
  last_login_at: string | null;
  created_at: string | null;
}

/** 角色 → 中文（PRD 13 §1 三角色） */
export const ADMIN_ROLE_LABEL: Record<string, string> = {
  BIZ_OPERATOR: '运营商务',
  TECH_OPS: '技术运营',
  SUPER_ADMIN: '超级管理员'
};

/** 账号状态 → 徽章（后端 AdminUserService：ACTIVE / SUSPENDED） */
export const ADMIN_USER_STATUS: Record<string, { label: string; tone: 'success' | 'danger' | 'info' }> = {
  ACTIVE: { label: '启用中', tone: 'success' },
  SUSPENDED: { label: '已停用', tone: 'danger' }
};

export const adminUserApi = {
  /** ADM-AUTH02 运营账号列表（q：page/pageSize/role?/status?/keyword?） */
  list(query: { page?: number; pageSize?: number; role?: string; status?: string; keyword?: string } = {}) {
    return request<PageResult<AdminUserRow>>('/admin/admin-users', { query });
  },
  /** ADM-AUTH03 开账号：手机号即登录名（唯一）；role 白名单 BIZ_OPERATOR/TECH_OPS/SUPER_ADMIN */
  create(payload: { username: string; display_name?: string | null; role: string; phone: string }) {
    return request<AdminUserRow>('/admin/admin-users', { method: 'POST', body: payload });
  },
  /** ADM-AUTH04 停用（理由必填；不可停用自己、不可停用最后一个启用中的超管） */
  suspend(id: string, reason: string) {
    return request<AdminUserRow>(`/admin/admin-users/${encodeURIComponent(id)}/suspend`, {
      method: 'POST',
      body: { reason }
    });
  },
  /** ADM-AUTH05 恢复启用 */
  resume(id: string) {
    return request<AdminUserRow>(`/admin/admin-users/${encodeURIComponent(id)}/resume`, { method: 'POST' });
  }
};
