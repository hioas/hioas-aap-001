/**
 * 内联 SVG 图标集。
 *
 * 设计稿用的是 remixicon 字体图标（fontFamily=remixicon）。这里**不引入整套图标字体**
 * （几百 KB，且管理端只用到导航 9 个 + 若干操作图标），改为等价的内联 SVG，
 * 路径取自 remixicon 同名图标的几何语义（线性 24×24）。视觉等价、零依赖。
 */
export const ICONS: Record<string, string> = {
  user:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/></svg>',
  dashboard:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="11" width="7" height="10" rx="1.5"/><rect x="3" y="15" width="7" height="6" rx="1.5"/></svg>',
  chart:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
  grid:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/></svg>',
  office:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-5h6v5M9 11h.01M15 11h.01"/></svg>',
  shield:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3l7 3v6c0 4.4-3 8.2-7 9-4-0.8-7-4.6-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/></svg>',
  audit:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M9 3h6l4 4v14H5V3h4z"/><path d="M9 3v4h6"/><path d="M8 13h8M8 17h5"/></svg>',
  contract:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><path d="M9 15c1-1.5 2-1.5 3 0s2 1.5 3 0"/></svg>',
  code:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/></svg>',
  sync:
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 11a8 8 0 0 0-14-4M4 13a8 8 0 0 0 14 4"/><path d="M20 5v6h-6M4 19v-6h6"/></svg>',
  refresh:
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 11a8 8 0 0 0-14-4M4 13a8 8 0 0 0 14 4"/><path d="M20 5v6h-6M4 19v-6h6"/></svg>',
  download:
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v12M7 10l5 5 5-5M4 20h16"/></svg>',
  calendar:
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>'
};
