<template>
  <div class="layout">
    <!-- 左侧导航 240px 深色（设计稿实测：fill rgba(15,23,42,1)，导航项高 42） -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand__logo">云</div>
        <div class="brand__text">
          <div class="brand__name">云算接入</div>
          <div class="brand__sub">运营管理端</div>
        </div>
      </div>

      <nav class="nav">
        <div v-for="group in visibleGroups" :key="group.key" class="nav__group">
          <div class="nav__group-label">{{ group.label }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.key"
            class="nav__item"
            :class="{ 'nav__item--active': isActive(item.route) }"
            :to="item.route"
            :data-testid="`nav-${item.key}`"
          >
            <span class="nav__icon" v-html="ICONS[item.icon]" />
            <span class="nav__label">{{ item.label }}</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar__foot">
        <div class="user-card">
          <div class="user-card__avatar">{{ userInitial }}</div>
          <div class="user-card__text">
            <div class="user-card__name">{{ userName }}</div>
            <div class="user-card__role">{{ roleLabel }}</div>
          </div>
          <button class="user-card__out" data-testid="logout" title="退出登录" @click="onLogout">⎋</button>
        </div>
      </div>
    </aside>

    <main class="main">
      <!-- 顶部栏：页面标题块（设计稿 144 宽）+ 右侧操作插槽 -->
      <header class="topbar">
        <div class="topbar__title-block">
          <h1 class="topbar__title">{{ pageTitle }}</h1>
          <p class="topbar__sub">{{ pageSubtitle }}</p>
        </div>
        <div class="topbar__spacer" />
        <slot name="actions" />
      </header>
      <div class="content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NAV_GROUPS, can, ROLE_LABEL, type AdminRole } from '@/config/nav';
import { tokenStore } from '@/api/http';
import { ICONS } from '@/components/icons';
import { useSession } from '@/composables/useSession';

const route = useRoute();
const router = useRouter();
const { userName, role } = useSession();

const roleLabel = computed(() => ROLE_LABEL[role.value]);
const userInitial = computed(() => (userName.value || '运').slice(0, 1));

/**
 * 菜单按权限点过滤（PRD 13 §2）。
 * ⚠️ 这只是**渲染过滤**，不是安全边界：后端对每个接口都二次校验（PRD 13 §1/§11）。
 */
const visibleGroups = computed(() =>
  NAV_GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((it) => (it.permission ? can(role.value as AdminRole, it.permission) : true))
  })).filter((g) => g.items.length > 0)
);

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/');

const pageTitle = computed(() => (route.meta.title as string) || '');
const pageSubtitle = computed(() => (route.meta.subtitle as string) || '');

function onLogout() {
  tokenStore.clear();
  router.push('/login');
}
</script>

<style scoped>
.layout { display: flex; height: 100vh; overflow: hidden; }

/* ── 侧栏 ─────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-w);
  flex: 0 0 var(--sidebar-w);
  background: var(--c-sidebar);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 18px 16px 14px; }
.brand__logo {
  width: 36px; height: 36px; border-radius: var(--r-lg);
  background: var(--c-primary); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 600;
}
.brand__name { font-size: var(--fs-xl); font-weight: 600; color: #fff; line-height: 1.2; }
.brand__sub { font-size: var(--fs-xs); color: var(--c-text-sub); margin-top: 2px; }

.nav { flex: 1; padding: 6px 12px 12px; }
.nav__group { margin-bottom: 10px; }
.nav__group-label {
  font-size: var(--fs-sm); color: var(--c-nav-group);
  padding: 8px 8px 6px; letter-spacing: 0.4px;
}
.nav__item {
  display: flex; align-items: center; gap: 10px;
  height: var(--nav-item-h); padding: 0 10px; margin-bottom: 2px;
  border-radius: var(--r-lg); text-decoration: none;
  color: var(--c-nav-text); font-size: var(--fs-md);
  transition: background 0.15s, color 0.15s;
}
.nav__item:hover { background: rgba(30, 41, 59, 0.7); color: #fff; }
.nav__item--active { background: var(--c-primary-strong); color: #fff; font-weight: 500; }
.nav__icon { width: 20px; display: inline-flex; justify-content: center; }

.sidebar__foot { padding: 12px; }
.user-card {
  display: flex; align-items: center; gap: 10px;
  background: var(--c-sidebar-card); border-radius: var(--r-xl); padding: 10px;
}
.user-card__avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--c-primary); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: var(--fs-md);
}
.user-card__text { flex: 1; min-width: 0; }
.user-card__name { font-size: var(--fs-base); color: rgba(226, 232, 240, 1); }
.user-card__role { font-size: var(--fs-xs); color: var(--c-text-sub); margin-top: 2px; }
.user-card__out {
  background: transparent; border: 0; color: var(--c-text-muted);
  cursor: pointer; font-size: var(--fs-xl); padding: 2px 4px; border-radius: var(--r-sm);
}
.user-card__out:hover { color: #fff; background: rgba(255, 255, 255, 0.08); }

/* ── 主区 ─────────────────────────────────────────────── */
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; background: var(--c-surface-alt); }
.topbar {
  height: var(--topbar-h); flex: 0 0 var(--topbar-h);
  background: var(--c-surface); border-bottom: 1px solid var(--c-border);
  display: flex; align-items: center; gap: 12px; padding: 0 var(--content-pad);
}
.topbar__title { font-size: var(--fs-2xl); font-weight: 600; margin: 0; color: var(--c-text); }
.topbar__sub { font-size: var(--fs-base); color: var(--c-text-muted); margin: 2px 0 0; }
.topbar__spacer { flex: 1; }
.content { flex: 1; overflow-y: auto; padding: var(--content-pad); }
</style>
