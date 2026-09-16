/**
 * 页面路由集中定义（设计画布 → uni-app pages.json 的路径）
 *
 * 序号 21（我的页）引入：本页有 9 个入口行 + 4 个 TabBar 项，落点分散在多个模块，
 * 若每个模块各写一份字符串常量必然漂移 → 统一放这里，页面/模型/组件共用。
 *
 * ⚠️ 落点页在 pages.json / src/pages 下的实现状态（2026-09-16 复核：两页均已实现，旧注释「未实现 → 降级」作废）：
 *   序号 22 /pages/usage/index（用量与对账）· 序号 23 /pages/settings/index（账号与设置）。
 */

export const LOGIN_PAGE = '/pages/login/index'
export const WORKBENCH_PAGE = '/pages/workbench/index'
export const REPORT_PAGE = '/pages/report/index'
export const REPORT_FAILED_PAGE = '/pages/report-failed/index'
export const QUOTES_PAGE = '/pages/quotes/index'
export const MESSAGES_PAGE = '/pages/messages/index'
export const CONTRACT_PAGE = '/pages/contract/index'
export const MINE_PAGE = '/pages/mine/index'
export const PROFILE_PAGE = '/pages/profile/index'
export const PROFILE_EDIT_PAGE = '/pages/profile-edit/index'
export const CREDENTIALS_PAGE = '/pages/credentials/index'
/** 序号 22（已实现）：用量与对账 */
export const USAGE_PAGE = '/pages/usage/index'
/** 序号 23（已实现）：我的设置 */
export const SETTINGS_PAGE = '/pages/settings/index'
