import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router';
import { tokenStore } from '@/api/http';

/**
 * hash 路由：管理端可能被部署到任意子路径，hash 免去服务端 rewrite 配置。
 * 后台页一律 lazy import，首屏只付登录页的代价。
 */
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'login', component: () => import('@/views/login/index.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/dashboard/index.vue'), meta: { title: '进件状态看板' } },
      { path: 'usage', name: 'usage', component: () => import('@/views/usage/index.vue'), meta: { title: '用量统计' } },
      { path: 'models', name: 'models', component: () => import('@/views/models/index.vue'), meta: { title: '模型管理' } },
      { path: 'providers', name: 'providers', component: () => import('@/views/providers/index.vue'), meta: { title: '供应商管理' } },
      { path: 'detection', name: 'detection', component: () => import('@/views/detection/index.vue'), meta: { title: '检测中心' } },
      { path: 'reviews', name: 'reviews', component: () => import('@/views/reviews/index.vue'), meta: { title: '报价审核' } },
      { path: 'contracts', name: 'contracts', component: () => import('@/views/contracts/index.vue'), meta: { title: '合同与结算' } },
      { path: 'compilation', name: 'compilation', component: () => import('@/views/compilation/index.vue'), meta: { title: '编译确认台' } },
      { path: 'sync', name: 'sync', component: () => import('@/views/sync/index.vue'), meta: { title: 'new-api 同步' } }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
];

export const router = createRouter({ history: createWebHashHistory(), routes });

router.beforeEach((to) => {
  const isPublic = to.meta.public === true;
  if (!isPublic && !tokenStore.get()) return { path: '/login', query: { redirect: to.fullPath } };
  if (isPublic && tokenStore.get() && to.path === '/login') return { path: '/dashboard' };
  return true;
});

export default router;
