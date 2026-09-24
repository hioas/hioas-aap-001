/**
 * 左侧导航配置
 *
 * 分组与文案**逐字取自设计稿**（.calicat-admin/raw/pages/page-1-pc/design.json）：
 *   概览   → 状态看板 / 用量统计 / 模型管理
 *   进件管理 → 供应商管理 / 检测中心 / 报价审核 / 合同与结算
 *   下发与同步 → 编译确认台 / new-api 同步
 *
 * PRD 13 §2 的菜单更全（配置中心 / 系统管理）。差异是**设计稿只画了 9 项**，
 * 已在 .calicat-admin/coverage-gaps.md 记为 missing-design：菜单项不臆造，
 * PRD 有而设计稿没有的先按「本轮不渲染」，等设计补齐或用户裁定。
 *
 * ⚠️ 例外（2026-09-23）：新增「系统管理 → 运营账号」。原因是该能力**有接口无入口** ——
 * ADM-AUTH02…05（账号列表/建号/停用/恢复）后端早已就位，但控制台没有任何页面能到它，
 * 生产上开运营账号只能手写 SQL。为不阻塞运营，先按 PRD 13 §2 的「系统管理」分组渲染这一项，
 * 且**仅 SUPER_ADMIN 可见**（permission: admin.user.manage）。
 * 设计补齐后若与本项冲突，删掉本组 6 行即可回退（不影响其它导航）。
 */
export interface NavItem {
  key: string;
  label: string;
  icon: string;
  route: string;
  /** PRD 13 §2 要求的权限点；缺省=所有角色可见 */
  permission?: string;
}

export interface NavGroup {
  key: string;
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    key: 'overview',
    label: '概览',
    items: [
      { key: 'dashboard', label: '状态看板', icon: 'dashboard', route: '/dashboard' },
      { key: 'usage', label: '用量统计', icon: 'chart', route: '/usage' },
      { key: 'models', label: '模型管理', icon: 'grid', route: '/models' }
    ]
  },
  {
    key: 'intake',
    label: '进件管理',
    items: [
      { key: 'providers', label: '供应商管理', icon: 'office', route: '/providers' },
      { key: 'detection', label: '检测中心', icon: 'shield', route: '/detection' },
      { key: 'reviews', label: '报价审核', icon: 'audit', route: '/reviews' },
      { key: 'contracts', label: '合同与结算', icon: 'contract', route: '/contracts' }
    ]
  },
  {
    key: 'dispatch',
    label: '下发与同步',
    items: [
      { key: 'compilation', label: '编译确认台', icon: 'code', route: '/compilation' },
      { key: 'sync', label: 'new-api 同步', icon: 'sync', route: '/sync' }
    ]
  },
  {
    // 见文件头「例外（2026-09-23）」：PRD 13 §2 有「系统管理」，设计稿未画；为让 ADM-AUTH02…05 有入口而渲染此项
    key: 'system',
    label: '系统管理',
    items: [
      {
        key: 'adminUsers',
        label: '运营账号',
        icon: 'user',
        route: '/admin-users',
        permission: 'admin.user.manage'
      }
    ]
  }
];

/**
 * 角色（PRD 13 §1）。
 * 权限模型 RBAC：**前端只做渲染过滤，后端一律二次校验** —— 前端隐藏不是安全边界。
 */
export type AdminRole = 'BIZ_OPERATOR' | 'TECH_OPS' | 'SUPER_ADMIN';

export const ROLE_LABEL: Record<AdminRole, string> = {
  BIZ_OPERATOR: '运营商务',
  TECH_OPS: '技术运营',
  SUPER_ADMIN: '超级管理员'
};

/**
 * 前端菜单过滤用的权限点（PRD 13 §1 权限总表）。
 * 注意：技术运营看不到合同写操作；运营商务看不到检测配置/报告模板/审计日志/new-api 连接配置。
 */
export function can(role: AdminRole, action: string): boolean {
  const table: Record<string, AdminRole[]> = {
    'detection.config': ['TECH_OPS', 'SUPER_ADMIN'],
    'detection.monitor.all': ['TECH_OPS', 'SUPER_ADMIN'],
    'quote.review': ['BIZ_OPERATOR', 'TECH_OPS', 'SUPER_ADMIN'],
    'quote.approve': ['BIZ_OPERATOR', 'SUPER_ADMIN'],
    'contract.write': ['BIZ_OPERATOR', 'SUPER_ADMIN'],
    'compile.confirm': ['TECH_OPS', 'SUPER_ADMIN'],
    'sync.run': ['BIZ_OPERATOR', 'TECH_OPS', 'SUPER_ADMIN'],
    // ADM-U02 聚合刷新：与后端 @PreAuthorize 一致（技术运营/超管），运营商务不可点
    'usage.refresh': ['TECH_OPS', 'SUPER_ADMIN'],
    'audit.read': ['TECH_OPS', 'SUPER_ADMIN'],
    'apikey.reveal': ['SUPER_ADMIN'],
    'newapi.config': ['SUPER_ADMIN'],
    // 运营账号建号/停用 = 提权操作（ADM-AUTH02…05 后端同为 SUPER_ADMIN 门禁）
    'admin.user.manage': ['SUPER_ADMIN']
  };
  const allowed = table[action];
  if (!allowed) return true; // 未登记权限点的菜单 = 全员可见
  return allowed.includes(role);
}
