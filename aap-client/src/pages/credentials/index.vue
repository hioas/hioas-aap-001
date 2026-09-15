<template>
  <view class="cred">
    <!-- 顶部栏：design id=69130ec6（white · padding 16/20 · 底部 1px #F1F5F9 分隔） -->
    <view class="cred__topbar">
      <view class="cred__icon-btn" data-testid="back-btn" @tap="goBack">
        <view class="glyph glyph--back" aria-hidden="true" />
      </view>
      <!-- 标题块：design id=fdab1cad（w=120 · 垂直） -->
      <view class="cred__title-block">
        <text class="cred__title">凭证列表</text>
        <text class="cred__subtitle">统一管理客户检测凭证</text>
      </view>
      <view class="cred__icon-btn" data-testid="help-btn" @tap="openHelp">
        <text class="glyph--help" aria-hidden="true">?</text>
      </view>
    </view>

    <!-- 内容区：design id=827a9db0（padding 16/20 · 垂直 gap 16） -->
    <view class="cred__content">
      <!-- 接入凭证按钮：design id=ddcec724（48 高 · r12 · #2563EB · gap 6） -->
      <view class="cred__submit" data-testid="submit-btn" @tap="goSubmit">
        <view class="glyph glyph--plus" aria-hidden="true" />
        <text class="cred__submit-text">接入凭证</text>
      </view>

      <!-- 列表标题行：design id=f89b39ae -->
      <view class="cred__list-head">
        <text class="cred__list-title">凭证列表</text>
        <text class="cred__list-total" data-testid="list-total">{{ model.totalText }}</text>
      </view>

      <!-- 状态统计行：design id=9da021fa（gap 8；chip r10 padding 6/10 描边 #EEF2F7） -->
      <view class="cred__stats">
        <view v-for="chip in model.chips" :key="chip.key" class="chip" :data-testid="`chip-${chip.key}`">
          <view class="chip__dot" :style="{ background: chip.color }" />
          <text class="chip__label">{{ chip.label }}</text>
          <text class="chip__count">{{ chip.count }}</text>
        </view>
      </view>

      <!-- 凭证列表卡：design id=cb9ceb72（white · r16 · padding 2/16） -->
      <view class="cred-card">
        <!-- 表头：design id=c1940840（高 44；列宽 226/48/42/42） -->
        <view class="cred-card__head">
          <text class="cred-card__th cred-card__th--name">凭证名称</text>
          <text class="cred-card__th cred-card__th--models">模型数</text>
          <text class="cred-card__th cred-card__th--status">状态</text>
          <text class="cred-card__th cred-card__th--view">查看</text>
        </view>

        <!-- 数据行：design id=02850966（padding 12/0） -->
        <view v-for="(row, i) in model.rows" :key="row.id" class="cred-row" data-testid="cred-row">
          <view class="cred-row__name-col">
            <text class="cred-row__alias">{{ row.alias }}</text>
            <text class="cred-row__time">{{ row.timeText }}</text>
          </view>
          <text class="cred-row__models">{{ row.modelCountText }}</text>
          <view class="cred-row__status">
            <view class="cred-row__dot" :style="{ background: row.statusColor }" />
          </view>
          <view class="cred-row__view">
            <text
              v-if="row.reportText"
              class="cred-row__report"
              :data-testid="`row-report-${i}`"
              @tap="openReport(row)"
            >
              {{ row.reportText }}
            </text>
          </view>
        </view>

        <!-- 空态：设计稿只给了「有数据」变体（画布无空态稿）→ 文案为占位，已记台账待确认 -->
        <view v-if="model.rows.length === 0" class="cred-card__empty" data-testid="cred-empty">
          <text class="cred-card__empty-text">暂无接入凭证</text>
        </view>

        <!-- 列表底部说明：design id=3bf43b00 -->
        <view class="cred-card__footer">
          <view class="glyph glyph--info" aria-hidden="true" />
          <text class="cred-card__footer-text">{{ model.footerText }}</text>
        </view>
      </view>
    </view>

    <!-- 底部 TabBar：design id=f084a5c4（padding 10/16/14/16） -->
    <view class="tabbar">
      <view
        v-for="tab in tabs"
        :key="tab.label"
        class="tabbar__item"
        :data-testid="`tab-${tab.label}`"
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
 * 页面 3【工作台与我的】凭证列表-有数据（序号 3 / page-3）
 * 设计真源：.calicat/raw/pages/page-3/design.tree.json（430 宽）
 * 接口：GET /api/v1/credentials（18-API Credential Tag；page/pageSize 约定）
 * 交互分类见 .agents/state/aap-feature-status.csv 序号 3 行：
 *   返回 = navigation(navigateBack) · 帮助 = client-only（画布无帮助页） ·
 *   接入凭证 = navigation(/pages/credential-submit/index) ·
 *   报告 = navigation（通过→/pages/report/index · 不通过→/pages/report-failed/index） ·
 *   状态统计 chip = client-only（设计稿无选中态、列表已含全部 4 态，不做筛选） · TabBar = navigation
 */
import { computed, onMounted, ref } from 'vue'
import { credentialApi } from '@/api/credential'
import { PAGE_SIZE, buildCredentialsModel, type CredentialListRaw, type CredentialRow } from '@/utils/credentials-model'

const CREDENTIAL_SUBMIT_PAGE = '/pages/credential-submit/index'
const REPORT_PAGE = '/pages/report/index'
const REPORT_FAILED_PAGE = '/pages/report-failed/index'
const QUOTES_PAGE = '/pages/quotes/index'
const MINE_PAGE = '/pages/mine/index'
const ACTIVE_TAB = '工作台'

const raw = ref<CredentialListRaw | null>(null)
const model = computed(() => buildCredentialsModel(raw.value))

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

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** 帮助：设计画布无帮助页（.calicat/inventory.json 30 页中无）→ client-only，不臆造路由 */
function openHelp() {
  uni.showToast({ title: '帮助功能开发中', icon: 'none' })
}

function goSubmit() {
  goto(CREDENTIAL_SUBMIT_PAGE)
}

/** 报告：不通过走序号 7「检测未通过报告」页，通过走序号 6「大模型检测报告」页（映射记台账待确认） */
function openReport(row: CredentialRow) {
  if (!row.reportId) return
  const page = row.statusKey === 'rejected' ? REPORT_FAILED_PAGE : REPORT_PAGE
  uni.navigateTo({ url: `${page}?reportId=${row.reportId}` })
}

function onTab(tab: { label: string; url: string }) {
  if (tab.label === ACTIVE_TAB) return
  goto(tab.url)
}

onMounted(async () => {
  try {
    raw.value = (await credentialApi.list({ page: 1, pageSize: PAGE_SIZE })) ?? null
  } catch {
    raw.value = null
    uni.showToast({ title: '数据加载失败，请稍后重试', icon: 'none' })
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.cred {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page-2;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部栏（design 69130ec6） */
.cred__topbar {
  background: $color-bg-card;
  /* --status-bar-height 由 uni-app 提供（H5 = 0，小程序为状态栏高度）：设计帧未含状态栏偏移，此处补平台安全区 */
  padding: calc(16px + var(--status-bar-height, 0px)) 20px 16px 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid $color-bg-subtle;
  box-sizing: border-box;
}

.cred__icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.cred__title-block {
  width: 120px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.cred__title {
  font-size: $font-xl;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 1.2;
}

.cred__subtitle {
  font-size: $font-xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

/* 图标占位（设计稿为矢量图标，PRD08 禁 emoji → CSS 形状占位，与序号 1/2 一致） */
.glyph--back {
  width: 9px;
  height: 9px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
  margin-left: 3px;
}

.glyph--help {
  font-size: $font-xl;
  color: $color-text-muted;
  line-height: 1.2;
}

.glyph--plus {
  width: 14px;
  height: 14px;
  position: relative;
}

.glyph--plus::before,
.glyph--plus::after {
  content: '';
  position: absolute;
  background: #ffffff;
}

.glyph--plus::before {
  left: 0;
  top: 6px;
  width: 14px;
  height: 2px;
}

.glyph--plus::after {
  left: 6px;
  top: 0;
  width: 2px;
  height: 14px;
}

.glyph--info {
  width: 12px;
  height: 12px;
  border: 1.5px solid $color-text-placeholder;
  border-radius: 50%;
  box-sizing: border-box;
  flex: none;
}

/* 内容区（design 827a9db0） */
.cred__content {
  padding: 16px 20px 96px 20px; /* 底部留白 = 固定 TabBar 高度 */
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-sizing: border-box;
}

.cred__submit {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  background: $color-primary;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.cred__submit-text {
  font-size: $font-md;
  color: #ffffff;
  line-height: 1.2;
}

.cred__list-head {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.cred__list-title {
  font-size: $font-md;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 1.2;
}

.cred__list-total {
  font-size: $font-xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

.cred__stats {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.chip {
  background: $color-bg-card;
  border: 0.8px solid $color-border-chip;
  border-radius: $radius-md;
  padding: 6px 10px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.chip__dot {
  width: 9px;
  height: 8px;
  border-radius: 4px;
  flex: none;
}

.chip__label {
  font-size: $font-xs;
  color: $color-text-tertiary;
  line-height: 1.2;
}

.chip__count {
  font-size: $font-xs;
  color: $color-text-primary;
  line-height: 1.2;
}

/* 凭证列表卡（design cb9ceb72） */
.cred-card {
  width: 100%;
  background: $color-bg-card;
  border-radius: 16px;
  padding: 2px 16px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.cred-card__head {
  width: 100%;
  height: 44px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.cred-card__th {
  font-size: $font-xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

.cred-card__th--name {
  width: 226px;
  flex: none;
}

.cred-card__th--models {
  width: 48px;
  flex: none;
}

.cred-card__th--status {
  width: 42px;
  flex: none;
}

.cred-card__th--view {
  width: 42px;
  flex: none;
}

.cred-row {
  width: 100%;
  padding: 12px 0;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.cred-row__name-col {
  width: 226px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
}

.cred-row__alias {
  font-size: $font-sm;
  color: $color-text-primary;
  line-height: 1.2;
}

.cred-row__time {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

.cred-row__models {
  width: 48px;
  flex: none;
  font-size: $font-sm;
  color: $color-text-primary;
  line-height: 1.2;
}

.cred-row__status {
  width: 42px;
  flex: none;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.cred-row__dot {
  width: 9px;
  height: 8px;
  border-radius: 4px;
  flex: none;
}

.cred-row__view {
  width: 42px;
  flex: none;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.cred-row__report {
  font-size: $font-sm;
  color: $color-primary;
  line-height: 1.2;
  padding: 8px 0;
}

.cred-card__empty {
  width: 100%;
  padding: 24px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cred-card__empty-text {
  font-size: $font-xs;
  color: $color-text-placeholder;
}

/* 列表底部说明（design 3bf43b00） */
.cred-card__footer {
  width: 100%;
  padding: 4px 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.cred-card__footer-text {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

/* 底部 TabBar（design f084a5c4） */
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
  padding: 10px 16px 14px 16px;
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
