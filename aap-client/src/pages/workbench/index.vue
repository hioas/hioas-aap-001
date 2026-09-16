<template>
  <view class="workbench">
    <!-- 顶部栏：design id=921c92f0-798c-4b03-90ac-4c2982fa3106 -->
    <view class="workbench__topbar">
      <view class="brand">
        <text class="brand__date">{{ headerDate }}</text>
        <text class="brand__company">{{ companyName }}</text>
      </view>
      <view class="topbar__spacer" />
      <view class="icon-btn" data-testid="notice-btn" @tap="openMessages">
        <view class="glyph glyph--bell" aria-hidden="true" />
      </view>
      <view class="topbar__gap" />
      <view class="avatar" data-testid="avatar-btn" @tap="openMine">
        <view class="glyph glyph--user" aria-hidden="true" />
      </view>
    </view>

    <!-- 内容区：design id=8548b4e0 -->
    <view class="workbench__content">
      <!-- 收益总览卡：design id=b1ffcd99 -->
      <view class="card">
        <view class="card__head">
          <text class="card__title-sm">本月词元用量</text>
          <view class="card__head-spacer" />
          <view class="badge">
            <text class="badge__arrow">↑</text>
            <text class="badge__gap" />
            <text class="badge__value">{{ model.momText }}</text>
          </view>
        </view>

        <view class="card__gap-12" />

        <view class="ring-row">
          <view class="ring" :style="{ background: donutBackground }">
            <view class="ring__hole">
              <text class="ring__label">{{ model.centerLabel }}</text>
              <text class="ring__value">{{ model.totalText }}</text>
            </view>
          </view>

          <view class="legend">
            <view v-for="col in legendColumns" :key="col.key" class="legend__col">
              <view v-for="cat in col.items" :key="cat.key" class="legend__item">
                <view class="legend__dot" :style="{ background: cat.color }" />
                <view class="legend__text">
                  <text class="legend__label">{{ cat.label }}</text>
                  <text class="legend__value">{{ cat.text }}</text>
                </view>
              </view>
            </view>
          </view>
        </view>

        <view class="card__gap-16" />
        <view class="divider" />
        <view class="card__gap-16" />

        <view class="metrics">
          <template v-for="(m, i) in model.metrics" :key="m.label">
            <view v-if="i > 0" class="metrics__sep" />
            <view class="metrics__item" :class="`metrics__item--${metricAlign(i)}`">
              <text class="metrics__label">{{ m.label }}</text>
              <text class="metrics__value" :class="{ 'metrics__value--success': m.tone === 'success' }">
                {{ m.value }}
              </text>
            </view>
          </template>
        </view>
      </view>

      <view class="card__gap-12" />

      <!-- 模型调用量卡：design id=a2d9015e -->
      <view class="card">
        <view class="card__head">
          <text class="card__title">模型调用量</text>
          <view class="card__head-spacer" />
          <text class="card__hint">按收入贡献排序</text>
        </view>

        <view class="card__gap-16" />

        <template v-for="(row, i) in model.models" :key="row.rank">
          <view v-if="i > 0" class="card__gap-16" />
          <view class="model" data-testid="model-row">
            <view class="model__rank" :style="{ background: row.badgeBg }">
              <text class="model__rank-text" :style="{ color: row.rankColor }">{{ row.rank }}</text>
            </view>
            <view class="model__gap" />
            <view class="model__mid">
              <view class="model__name-row">
                <text class="model__name">{{ row.name }}</text>
                <view class="model__name-spacer" />
                <text class="model__amount">{{ row.amountText }}</text>
              </view>
              <view class="model__bar-gap" />
              <view class="model__bar-row">
                <view class="model__bar-track">
                  <view
                    class="model__bar-fill"
                    :style="{ width: `${row.barPercent}%`, background: row.barColor }"
                    data-testid="model-bar"
                  />
                </view>
                <view class="model__bar-gap-inline" />
                <text class="model__calls">{{ row.callsText }}</text>
              </view>
            </view>
          </view>
        </template>

        <view v-if="model.models.length === 0" class="model__empty" data-testid="model-empty">
          <text class="model__empty-text">暂无模型调用数据</text>
        </view>

        <view class="card__gap-16" />

        <view class="card__head">
          <text class="model__footer">{{ model.footerText }}</text>
          <view class="card__head-spacer" />
          <text class="link" data-testid="model-detail" @tap="goto(USAGE_PAGE)">明细</text>
          <view class="model__chevron" aria-hidden="true" />
        </view>
      </view>

      <view class="card__gap-12" />

      <!-- 快捷入口卡：design id=0b333dd0 -->
      <view class="card card--quick">
        <view class="quick">
          <view
            v-for="q in quickEntries"
            :key="q.label"
            class="quick__item"
            :data-testid="`quick-${q.label}`"
            @tap="onQuick(q)"
          >
            <view class="quick__icon" :style="{ background: q.iconBg }">
              <view class="quick__glyph" :style="{ borderColor: q.iconColor }" aria-hidden="true" />
            </view>
            <view class="quick__gap" />
            <text class="quick__label">{{ q.label }}</text>
          </view>
        </view>
      </view>

      <view class="card__gap-12" />

      <!-- 待办卡：design id=82951b52 -->
      <view class="card card--todo">
        <view class="card__head">
          <text class="card__title">待处理</text>
          <view class="card__head-spacer" />
          <text class="link" data-testid="todo-all" @tap="goto(MESSAGES_PAGE)">全部</text>
        </view>

        <view class="card__gap-16" />

        <template v-for="(t, i) in todos" :key="t.text">
          <view v-if="i > 0" class="todo__divider" />
          <view class="todo" :data-testid="`todo-${t.text}`" @tap="onTodo(t)">
            <view class="todo__icon" :style="{ background: t.iconBg }">
              <view class="todo__glyph" :style="{ background: t.iconColor }" aria-hidden="true" />
            </view>
            <view class="todo__gap" />
            <text class="todo__text">{{ t.text }}</text>
            <view class="card__head-spacer" />
            <view class="todo__chevron" aria-hidden="true" />
          </view>
        </template>
      </view>

      <view class="workbench__bottom" />
    </view>

    <!-- 底部 TabBar：design id=eac7d9ba -->
    <view class="tabbar">
      <view
        v-for="tab in tabs"
        :key="tab.label"
        class="tabbar__item"
        :data-testid="`tab-${tab.label}`"
        :data-active="String(tab.label === ACTIVE_TAB)"
        @tap="onTab(tab)"
      >
        <view class="tabbar__glyph" :class="{ 'tabbar__glyph--active': tab.label === ACTIVE_TAB }" aria-hidden="true" />
        <view class="tabbar__gap" />
        <text class="tabbar__label" :class="{ 'tabbar__label--active': tab.label === ACTIVE_TAB }">
          {{ tab.label }}
        </text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 页面 2【工作台与我的】工作台 · 方案B 数据台（浅色版）
 * 设计真源：.calicat/raw/pages/page-2-b/design.tree.json（430 宽）
 * 接口：GET /api/v1/provider/profile（公司名）、GET /api/v1/usage/summary（用量汇总）
 * 交互分类：见 .agents/state/aap-feature-status.csv 序号 2 行
 */
import { computed, onMounted, ref } from 'vue'
import { providerApi } from '@/api/provider'
import { usageApi } from '@/api/usage'
import { PLACEHOLDER, formatHeaderDate } from '@/utils/format'
import { buildWorkbenchModel, type UsageSummaryRaw } from '@/utils/workbench-model'

const USAGE_PAGE = '/pages/usage/index'
const MESSAGES_PAGE = '/pages/messages/index'
const CONTRACTS_PAGE = '/pages/contract/index'
const QUOTES_PAGE = '/pages/quotes/index'
const REPORT_PAGE = '/pages/report/index'
const MINE_PAGE = '/pages/mine/index'
const CREDENTIALS_PAGE = '/pages/credentials/index'
const ACTIVE_TAB = '工作台'

const summary = ref<UsageSummaryRaw | null>(null)
const companyName = ref(PLACEHOLDER)
const headerDate = formatHeaderDate()

const model = computed(() => buildWorkbenchModel(summary.value ?? {}))

/** 环形图：按设计稿 6 类占比拼 conic-gradient；无数据时退为轨道色 */
const donutBackground = computed(() => {
  const raw = summary.value
  if (!raw || !raw.total_tokens) return '#f1f5f9'
  const parts: Array<{ color: string; value: number | undefined }> = [
    { color: '#1d4ed8', value: raw.prompt_tokens },
    { color: '#3b82f6', value: raw.completion_tokens },
    { color: '#16a34a', value: raw.cache_read_tokens },
    { color: '#5856d6', value: raw.image_input_tokens },
    { color: '#f59e0b', value: raw.audio_input_tokens },
    { color: '#af52de', value: raw.video_input_tokens }
  ]
  const totalPart = parts.reduce((s, p) => s + (p.value ?? 0), 0)
  if (totalPart <= 0) return '#f1f5f9'
  let cursor = 0
  const stops = parts.map((p) => {
    const from = (cursor / totalPart) * 100
    cursor += p.value ?? 0
    const to = (cursor / totalPart) * 100
    return `${p.color} ${from.toFixed(2)}% ${to.toFixed(2)}%`
  })
  const rest = Math.max(0, raw.total_tokens - totalPart)
  if (rest > 0) {
    const from = (totalPart / raw.total_tokens) * 100
    stops.push(`#e2e8f0 ${from.toFixed(2)}% 100%`)
  }
  return `conic-gradient(${stops.join(', ')})`
})

/** 图例两列：设计稿第 1 列 输入/输出/缓存，第 2 列 图片/音频/视频（gap 12） */
const legendColumns = computed(() => {
  const items = model.value.categories
  return [
    { key: 'main', items: items.slice(0, 3) },
    { key: 'minor', items: items.slice(3) }
  ]
})

function metricAlign(i: number) {
  return ['start', 'center', 'end'][i] ?? 'start'
}

/* 快捷入口 4 项：设计画布的「钱包」项按决策 D2（aap-decisions.md，用户 2026-09-16 拍板）整项删除 */
const quickEntries = [
  { label: '评测', iconBg: '#eff6ff', iconColor: '#2563eb', url: CREDENTIALS_PAGE },
  { label: '报价', iconBg: '#ecfdf5', iconColor: '#16a34a', url: QUOTES_PAGE },
  { label: '合同', iconBg: '#fff7ed', iconColor: '#d97706', url: CONTRACTS_PAGE },
  { label: '明细', iconBg: '#f1f5f9', iconColor: '#64748b', url: USAGE_PAGE }
]

const todos = [
  { text: '合同待签署（06-20 前）', iconBg: '#fff7ed', iconColor: '#f59e0b', url: CONTRACTS_PAGE },
  { text: '1 条报价单被驳回', iconBg: '#fef2f2', iconColor: '#ef4444', url: QUOTES_PAGE }
]

const tabs = [
  { label: '工作台', url: '' },
  { label: '报告', url: REPORT_PAGE },
  { label: '报价', url: QUOTES_PAGE },
  { label: '我的', url: MINE_PAGE }
]

function goto(url: string) {
  if (!url) return
  uni.navigateTo({ url })
}

function openMessages() {
  goto(MESSAGES_PAGE)
}

function openMine() {
  goto(MINE_PAGE)
}

function onQuick(q: { url: string }) {
  goto(q.url)
}

function onTodo(t: { url: string }) {
  goto(t.url)
}

function onTab(tab: { label: string; url: string }) {
  if (tab.label === ACTIVE_TAB) return
  goto(tab.url)
}

onMounted(async () => {
  const [profile, usage] = await Promise.allSettled([providerApi.profile(), usageApi.summary()])
  if (profile.status === 'fulfilled') {
    companyName.value = profile.value?.companyName || PLACEHOLDER
  }
  if (usage.status === 'fulfilled') {
    summary.value = usage.value ?? {}
  } else {
    uni.showToast({ title: '数据加载失败，请稍后重试', icon: 'none' })
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.workbench {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部栏 */
.workbench__topbar {
  background: $color-bg-card;
  padding: 48px 16px 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.brand {
  width: 160px;
  display: flex;
  flex-direction: column;
}

.brand__date {
  font-size: $font-xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

.brand__company {
  font-size: $font-2xl;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.3;
}

.topbar__spacer {
  flex: 1;
}

.topbar__gap {
  width: 9px;
}

.icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 21px;
  background: #dbeafe;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 图标占位（设计稿为 remixicon 矢量图标；PRD08 禁 emoji，先用 CSS 形状占位） */
.glyph {
  width: 14px;
  height: 14px;
}

.glyph--bell {
  border: 2px solid $color-text-muted;
  border-radius: 5px 5px 2px 2px;
}

.glyph--user {
  border: 2px solid $color-primary;
  border-radius: 50%;
}

/* 内容区 */
.workbench__content {
  padding: 12px 16px 96px 16px; /* 底部留白 = 固定 TabBar 高度，避免最后一张卡被遮盖 */
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.card {
  background: $color-bg-card;
  border-radius: $radius-xl;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  width: 100%;
}

.card--quick {
  padding: 16px 20px;
}

.card--todo {
  padding: 16px 20px;
}

.card__head {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.card__head-spacer {
  flex: 1;
}

.card__title {
  font-size: $font-md;
  font-weight: 600;
  color: $color-text-primary;
}

.card__title-sm {
  font-size: $font-xs;
  font-weight: 500;
  color: $color-text-muted;
}

.card__hint {
  font-size: $font-xs;
  color: $color-text-placeholder;
}

.card__gap-12 {
  height: 12px;
}

.card__gap-16 {
  height: 16px;
}

.divider {
  height: 1px;
  width: 100%;
  background: $color-bg-subtle;
}

/* 环比标 */
.badge {
  height: 26px;
  border-radius: 13px;
  background: $color-success-weak;
  padding: 0 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.badge__arrow {
  font-size: $font-base;
  color: $color-success;
}

.badge__gap {
  width: 2px;
}

.badge__value {
  font-size: $font-xs;
  font-weight: 600;
  color: $color-success;
}

/* 环形图 + 图例 */
.ring-row {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.ring {
  width: 104px;
  height: 104px;
  border-radius: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.ring__hole {
  width: 70px;
  height: 70px;
  border-radius: 35px;
  background: $color-bg-card;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring__label {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  line-height: 1.31;
}

.ring__value {
  font-size: 19px;
  color: $color-text-primary;
  line-height: 1.31;
}

.legend {
  flex: 1;
  display: flex;
  flex-direction: row;
  gap: 24px;
  margin-left: 28px;
}

.legend__col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.legend__item {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
}

.legend__dot {
  width: 10px;
  height: 9px;
  border-radius: 5px;
  margin-top: 4px;
  flex: none;
}

.legend__text {
  display: flex;
  flex-direction: column;
}

.legend__label {
  font-size: $font-xs;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 1.2;
}

.legend__value {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  line-height: 1.3;
}

/* 底行三指标 */
.metrics {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.metrics__sep {
  width: 2px;
  height: 30px;
  background: $color-border;
}

.metrics__item {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.metrics__item--start {
  align-items: flex-start;
}

.metrics__item--center {
  align-items: center;
}

.metrics__item--end {
  align-items: flex-end;
}

.metrics__label {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

.metrics__value {
  font-size: $font-md;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.4;
}

.metrics__value--success {
  color: $color-success;
}

/* 模型调用量 */
.model {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.model__rank {
  width: 26px;
  height: 26px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.model__rank-text {
  font-size: $font-xs;
  font-weight: 700;
  /* 颜色由 row.rankColor 行内给（设计 模型1~4序号 fontFill 逐行不同） */
}

.model__gap {
  width: 12px;
  flex: none;
}

.model__mid {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.model__name-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.model__name-spacer {
  flex: 1;
}

.model__name {
  font-size: $font-xs;
  font-weight: 600;
  color: $color-text-primary;
}

.model__amount {
  font-size: $font-xs;
  font-weight: 700;
  color: $color-text-primary;
}

.model__bar-gap {
  height: 8px;
}

.model__bar-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.model__bar-track {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: $color-bg-subtle;
  overflow: hidden;
}

.model__bar-fill {
  height: 6px;
  border-radius: 3px;
}

.model__bar-gap-inline {
  width: 8px;
  flex: none;
}

.model__calls {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  width: 70px;
  text-align: right;
}

.model__empty {
  padding: 12px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.model__empty-text {
  font-size: $font-xs;
  color: $color-text-placeholder;
}

.model__footer {
  font-size: $font-2xs;
  color: $color-text-placeholder;
}

.model__chevron {
  width: 7px;
  height: 7px;
  border-top: 2px solid $color-primary;
  border-right: 2px solid $color-primary;
  transform: rotate(45deg);
  margin-left: 6px;
}

.link {
  font-size: $font-xs;
  font-weight: 500;
  color: $color-primary;
  padding: 8px 0;
}

/* 快捷入口 */
.quick {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.quick__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 0;
}

.quick__icon {
  width: 40px;
  height: 40px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.quick__glyph {
  width: 16px;
  height: 16px;
  border: 2px solid;
  border-radius: 5px;
}

.quick__gap {
  height: 6px;
}

.quick__label {
  font-size: 10px;
  font-weight: 500;
  color: $color-text-secondary;
}

/* 待办 */
.todo {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
  padding: 4px 0;
}

.todo__divider {
  height: 1px;
  width: 100%;
  background: $color-bg-subtle;
  margin: 12px 0;
}

.todo__icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.todo__glyph {
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.todo__gap {
  width: 10px;
  flex: none;
}

.todo__text {
  font-size: $font-xs;
  font-weight: 500;
  color: $color-text-secondary-2;
}

.todo__chevron {
  width: 7px;
  height: 7px;
  border-top: 2px solid #cbd5e1;
  border-right: 2px solid #cbd5e1;
  transform: rotate(45deg);
}

.workbench__bottom {
  height: 16px;
}

/* 底部 TabBar：固定在视口底部（设计稿为独立底部栏；DOM 实测要求 tabbar.bottom == innerHeight） */
.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  box-sizing: border-box;
  background: $color-bg-card;
  padding: 8px 0 24px 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.tabbar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tabbar__glyph {
  width: 18px;
  height: 18px;
  border: 2px solid $color-text-placeholder;
  border-radius: 6px;
}

.tabbar__glyph--active {
  border-color: $color-primary;
}

.tabbar__gap {
  height: 8px;
}

.tabbar__label {
  font-size: $font-2xs;
  color: $color-text-placeholder;
}

.tabbar__label--active {
  color: $color-primary;
  font-weight: 600;
}
</style>
