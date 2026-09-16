<template>
  <view class="quotes">
    <!-- 顶部导航：design id=6870f5e0（padding 48/16/12/16 · 白底 · 标题左 / 新建报价右） -->
    <view class="quotes__topbar">
      <text class="quotes__title">{{ PAGE_TITLE }}</text>
      <view class="quotes__spacer" />
      <view class="quotes__new" data-testid="new-quote" @tap="goNewQuote">
        <view class="glyph glyph--plus" aria-hidden="true" />
        <text class="quotes__new-text">{{ NEW_QUOTE_TEXT }}</text>
      </view>
    </view>

    <!-- 筛选行：design id=e3a29c25（padding 12/16 · chip 高 30 r10 间距 9） -->
    <view class="quotes__filters">
      <view
        v-for="f in model.filters"
        :key="f.key"
        class="filter-chip"
        :class="{ 'filter-chip--active': f.key === active }"
        :data-testid="`filter-${f.key}`"
        @tap="onFilter(f.key)"
      >
        <text class="filter-chip__label">{{ f.label }}</text>
      </view>
    </view>

    <!-- 列表区：design id=14f06409（padding 12/16 · 卡间距 12 · 卡 178 高） -->
    <view class="quotes__list">
      <view v-for="row in model.rows" :key="row.id" class="quote-card" data-testid="quote-card">
        <!-- 顶行：标题 15px SemiBold + 状态胶囊（22 高 r11） -->
        <view class="quote-card__top">
          <text class="quote-card__title">{{ row.title }}</text>
          <view class="quote-card__spacer" />
          <view class="quote-card__status" :style="{ background: row.statusBg }" data-testid="status-chip">
            <view class="quote-card__status-dot" :style="{ background: row.statusDot }" />
            <text class="quote-card__status-text" :style="{ color: row.statusText }">{{ row.statusLabel }}</text>
          </view>
        </view>

        <!-- 报价单号行：design id=6b807739（上间距 16；标签 13px + 单号 10px） -->
        <view class="quote-card__no">
          <view class="quote-card__no-row">
            <text class="quote-card__no-label">{{ QUOTE_NO_LABEL }}</text>
            <text class="quote-card__no-value">{{ row.quoteNo }}</text>
          </view>
        </view>

        <!-- 元信息行：design ecd135b9（上间距 12）+ 559e490e（5 个节点，节点之间 8px 间距） -->
        <view class="quote-card__meta">
          <view class="quote-card__meta-row">
            <text
              v-for="(part, i) in metaParts(row.metaText)"
              :key="i"
              class="quote-card__meta-part"
              :class="part === META_SEPARATOR ? 'quote-card__meta-sep' : 'quote-card__meta-text'"
            >{{ part }}</text>
          </view>
        </view>

        <!-- 操作行：design id=4ddbda42（358×60 · padding 16/0 · 链接 40 高 · 间距 12 · 左对齐） -->
        <view class="quote-card__actions">
          <view
            v-for="a in row.actions"
            :key="a.key"
            class="quote-action"
            :data-testid="`action-${a.key}-${row.id}`"
            @tap="onAction(row, a)"
          >
            <view class="glyph" :class="`glyph--${a.key}`" aria-hidden="true" />
            <text class="quote-action__label">{{ a.label }}</text>
          </view>
        </view>
      </view>

      <!-- 空态：设计稿无空态稿 → 文案为占位（已记台账待确认） -->
      <view v-if="model.rows.length === 0" class="quotes__empty" data-testid="quotes-empty">
        <text class="quotes__empty-text">{{ model.emptyText }}</text>
      </view>
    </view>

    <!-- 底部 TabBar：design id=c958806f（padding 8/0/24 · 4 项各 104 宽，报价高亮） -->
    <view class="tabbar">
      <view
        v-for="tab in tabs"
        :key="tab.label"
        class="tabbar__item"
        :data-testid="`tab-${tab.label}`"
        @tap="onTab(tab)"
      >
        <view class="tabbar__icon">
          <view class="tabbar__glyph" :class="{ 'tabbar__glyph--active': tab.label === ACTIVE_TAB }" aria-hidden="true" />
        </view>
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
 * 页面 8【报价管理】报价单列表（序号 8 / page-8-2）
 * 设计真源：.calicat/raw/pages/page-8-2/design.tree.json（430 宽 · 设计总高 1206）
 * 接口真源：GET /api/v1/quotes（列表）· DELETE /api/v1/quotes/{quoteId}（删除）— 18-API「Quote」Tag
 * 交互分类见 .agents/state/aap-feature-status.csv 序号 8 行：
 *   新建报价 = navigation(/pages/quote-models/index，画布 9 模型报价设置-列表，用户拍板对齐原型 page-9)
 *   筛选 chip = api（GET /quotes?status=，参数名/取值集合为推断 → missing-prd）
 *   报价 = navigation(/pages/quote-form/index?quoteId=) · 预览 = navigation(/pages/quote-preview/index?quoteId=，画布 12)
 *   签署 / 合同 = navigation(/pages/contract/index?contractId=，画布 15) · 删除 = api(DELETE /quotes/{id}，二次确认后刷新)
 *   TabBar = navigation（报价 = 本页不跳）
 */
import { computed, onMounted, ref } from 'vue'
import { quoteApi } from '@/api/quote'
import {
  META_SEPARATOR,
  NEW_QUOTE_TEXT,
  PAGE_SIZE,
  PAGE_TITLE,
  QUOTE_NO_LABEL,
  buildQuotesModel,
  metaParts,
  type QuoteAction,
  type QuoteFilterKey,
  type QuoteListRaw,
  type QuoteRow
} from '@/utils/quotes-model'

const WORKBENCH_PAGE = '/pages/workbench/index'
const REPORT_PAGE = '/pages/report/index'
const MINE_PAGE = '/pages/mine/index'
const ACTIVE_TAB = '报价'

/** 删除二次确认文案：设计稿无弹窗稿 → 占位（已记台账待确认，不臆造业务规则） */
const DELETE_MODAL_TITLE = '删除报价单'
const DELETE_MODAL_CONTENT = '确认删除该报价单？删除后不可恢复。'

const raw = ref<QuoteListRaw | null>(null)
const active = ref<QuoteFilterKey>('all')
const model = computed(() => buildQuotesModel(raw.value, active.value))

const tabs = [
  { label: '工作台', url: WORKBENCH_PAGE },
  { label: '报告', url: REPORT_PAGE },
  { label: '报价', url: '' },
  { label: '我的', url: MINE_PAGE }
]

async function load() {
  try {
    raw.value =
      (await quoteApi.list({ page: 1, pageSize: PAGE_SIZE, status: model.value.activeStatusQuery })) ?? null
  } catch {
    raw.value = null
    uni.showToast({ title: '数据加载失败，请稍后重试', icon: 'none' })
  }
}

function onFilter(key: QuoteFilterKey) {
  if (key === active.value) return // 重复点同一个 chip 不重复请求
  active.value = key
  load()
}

function goNewQuote() {
  uni.navigateTo({ url: '/pages/quote-models/index' })
}

function onAction(row: QuoteRow, action: QuoteAction) {
  if (action.kind === 'navigation') {
    if (action.url) uni.navigateTo({ url: action.url })
    return
  }
  if (action.api === 'deleteQuote') confirmDelete(row)
}

/** 删除：二次确认 → DELETE → 重新拉当前筛选的列表（失败只提示，不动列表） */
function confirmDelete(row: QuoteRow) {
  uni.showModal({
    title: DELETE_MODAL_TITLE,
    content: DELETE_MODAL_CONTENT,
    confirmText: '删除',
    cancelText: '取消',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await quoteApi.remove(row.id)
        uni.showToast({ title: '已删除', icon: 'none' })
        await load()
      } catch {
        uni.showToast({ title: '删除失败，请稍后重试', icon: 'none' })
      }
    }
  })
}

function onTab(tab: { label: string; url: string }) {
  if (tab.label === ACTIVE_TAB || !tab.url) return
  uni.navigateTo({ url: tab.url })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.quotes {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部导航（design 6870f5e0） */
.quotes__topbar {
  background: $color-bg-card;
  /* --status-bar-height 由 uni-app 提供（H5 = 0）：设计帧未含状态栏偏移，此处补平台安全区 */
  padding: calc(48px + var(--status-bar-height, 0px)) 16px 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.quotes__title {
  font-size: $font-2xl;
  font-weight: 700; /* design 91be2734 SourceHanSans-Bold */
  color: $color-text-primary;
  line-height: 24px; /* 设计 91be2734 fs20 Bold · lineHeight 1.2 → 24（文本行盒 = 字号×1.2；×1.5 只用于图标字形层） */
  flex: none;
}

.quotes__spacer {
  flex: 1;
}

/* 新建报价按钮（design 7ccb56ba：当前画布 width 100 · 30 高 · r10 · #2563EB · padding 0/12）
   设计里按钮 x343..443 越出 430 画布（自身不自洽）→ 按设计声明宽度 100 实现，位置右对齐 16 保证零溢出 */
.quotes__new {
  width: 100px;
  height: 30px;
  padding: 0 12px;
  border-radius: $radius-md;
  background: $color-primary;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  box-sizing: border-box;
  flex: none;
}

.quotes__new-text {
  font-size: $font-xs;
  font-weight: 500; /* design 8b0d35de SourceHanSans-Medium */
  color: #ffffff;
  line-height: 16px; /* design 显式 height=16 */
}

/* 加号图标（design 47594508：16px remixicon 行框 18 × 24；PRD08 禁 emoji → CSS 形状占位，决策 D5） */
.glyph--plus {
  width: 18px;
  height: 24px;
  position: relative;
  flex: none;
}

.glyph--plus::before,
.glyph--plus::after {
  content: '';
  position: absolute;
  background: #ffffff;
}

.glyph--plus::before {
  left: 1px;
  top: 11px;
  width: 16px;
  height: 2px;
}

.glyph--plus::after {
  left: 8px;
  top: 4px;
  width: 2px;
  height: 16px;
}

/* 筛选行（design e3a29c25） */
.quotes__filters {
  background: $color-bg-card;
  padding: 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 9px;
  box-sizing: border-box;
}

.filter-chip {
  height: 30px;
  padding: 0 12px;
  border-radius: $radius-md;
  background: $color-bg-subtle;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  flex: none;
}

.filter-chip--active {
  background: $color-primary;
}

.filter-chip__label {
  font-size: $font-xs;
  font-weight: 500;
  color: $color-text-muted;
  line-height: 1.2;
}

.filter-chip--active .filter-chip__label {
  color: #ffffff;
}

/* 列表区（design 14f06409：list padding 12/16 · 卡间距 12）
   底部留白 112 = 设计里容器 padding-top 16 + TabBar 84（本页 TabBar 为固定底栏、脱离文档流）
   → 整页 docScrollHeight 1206 = 设计帧高（90 + 54 + 962 + 16 + 84） */
.quotes__list {
  padding: 12px 16px 112px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-sizing: border-box;
}

/* 报价卡（design 9057868c：白底 · r16 · 描边 1px #EEF2F7 · padding 16/20） */
.quote-card {
  width: 100%;
  background: $color-bg-card;
  /* design stroke{align:center,thickness:1} → box-shadow（border 占布局：内容宽会被挤成 356，设计是 358） */
  box-shadow: 0 0 0 1px $color-border-chip;
  border-radius: 16px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.quote-card__top {
  width: 100%;
  height: 22px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.quote-card__title {
  font-size: $font-md;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 22.5px; /* 15px 行框 = 15 × 1.5（设计 fit_content） */
  display: block;
}

.quote-card__spacer {
  flex: 1;
}

/* 状态胶囊（design bea2086e 等：22 高 r11 padding 0/8 + dot 8×6 + 11px） */
.quote-card__status {
  height: 22px;
  padding: 0 8px;
  border-radius: 11px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  box-sizing: border-box;
  flex: none;
}

.quote-card__status-dot {
  width: 8px;
  height: 6px;
  border-radius: 4px;
  flex: none;
}

.quote-card__status-text {
  font-size: $font-2xs;
  font-weight: 500;
  line-height: 16px; /* 11px 行框 = 11 × 1.5（设计 fit_content） */
  display: block;
}

/* 报价单号行（design 6b807739：上间距 16） */
.quote-card__no {
  width: 100%;
  padding-top: 16px;
  box-sizing: border-box;
}

.quote-card__no-row {
  width: 100%;
  height: 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.quote-card__no-label {
  font-size: $font-sm;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 19.5px; /* 13px 行框 = 13 × 1.5（设计 fit_content） */
  display: block;
  flex: none;
}

/* 单号：design 里是白底 r10 的内联标（padding 0/8）→ 与「报价单号」间隔 8+8=16，与设计量得一致 */
.quote-card__no-value {
  margin-left: 16px;
  font-size: 10px;
  font-weight: 500;
  color: $color-text-placeholder;
  line-height: 1.2;
  display: block;
  flex: none;
}

/* 元信息行（design ecd135b9：上间距 12；559e490e = 5 个节点、节点之间 8px 间距、行框 16） */
.quote-card__meta {
  width: 100%;
  padding-top: 12px;
  box-sizing: border-box;
}

.quote-card__meta-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px; /* design：每个后续节点的 container padding-left 8 */
}

.quote-card__meta-part {
  font-size: $font-2xs;
  line-height: 16px; /* 11px 行框 = 11 × 1.5（设计 fit_content：元信息盒高 16 → 卡高 178） */
  display: block;
  flex: none;
}

.quote-card__meta-text {
  color: $color-text-placeholder; /* design ac24812b 等 fontFill rgba(148,163,184,1) */
}

/* 分隔点在设计里是**另一套更浅的灰**（design fd63dfdb/9cafcec1 rgba(203,213,225,1)） */
.quote-card__meta-sep {
  color: $color-border-strong;
}

/* 操作行（design 4ddbda42：60 高 · padding 16/0 · 左对齐 · 链接间距 12） */
.quote-card__actions {
  width: 100%;
  height: 60px;
  padding: 16px 0 0 0;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  box-sizing: border-box;
}

/* 操作链接（design 3d09fef9 子项：40 高 · padding 0/8 · 图标 16 + 文字 13px #2563EB） */
.quote-action {
  height: 40px;
  padding: 0 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  box-sizing: border-box;
  flex: none;
}

.quote-action__label {
  font-size: $font-sm;
  font-weight: 500;
  color: $color-primary;
  line-height: 1.2;
  display: block;
}

/* 操作图标（design 各链接内 remixicon 16px → 行框 16 × 24；CSS 形状占位，与序号 1/2/3 一致） */
.glyph--quote,
.glyph--preview,
.glyph--sign,
.glyph--contract,
.glyph--delete {
  width: 16px;
  height: 24px;
  position: relative; /* ::before/::after 是绝对定位的形状 */
  box-sizing: border-box;
  flex: none;
}

/* 报价：钱币轮廓（方框 + 内横线）—— 形状画在 ::before，盒子按设计行框 16×24 */
.glyph--quote::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  width: 16px;
  height: 16px;
  border: 1.5px solid $color-primary;
  border-radius: 3px;
  box-sizing: border-box;
}

.glyph--quote::after {
  content: '';
  position: absolute;
  left: 3px;
  right: 3px;
  top: 11.5px;
  height: 1.5px;
  background: $color-primary;
}

/* 预览：眼睛（圆 + 中心点） */
.glyph--preview::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  width: 16px;
  height: 16px;
  border: 1.5px solid $color-primary;
  border-radius: 50% / 30%;
  box-sizing: border-box;
}

.glyph--preview::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 10px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: $color-primary;
}

/* 签署 / 合同：文档轮廓（左上折角） */
.glyph--sign::before,
.glyph--contract::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  width: 16px;
  height: 16px;
  border: 1.5px solid $color-primary;
  border-radius: 2px;
  box-sizing: border-box;
}

.glyph--sign::after,
.glyph--contract::after {
  content: '';
  position: absolute;
  left: 3px;
  right: 3px;
  top: 10.5px;
  height: 1.5px;
  background: $color-primary;
}

/* 删除：叉（两条对角线用旋转方块近似） */
.glyph--delete::before,
.glyph--delete::after {
  content: '';
  position: absolute;
  left: 1px;
  top: 12px;
  width: 14px;
  height: 1.5px;
  background: $color-primary;
}

.glyph--delete::before {
  transform: rotate(45deg);
}

.glyph--delete::after {
  transform: rotate(-45deg);
}

.quotes__empty {
  width: 100%;
  padding: 40px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.quotes__empty-text {
  font-size: $font-xs;
  color: $color-text-placeholder;
}

/* 底部 TabBar（design c958806f：padding 8/0/24 · 4 项各 104 宽 · 图标 33 块 + 3 + 文字 16 = 84） */
.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  height: 84px;
  box-sizing: border-box;
  background: $color-bg-card;
  padding: 8px 0 24px 0;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  justify-content: space-between;
}

.tabbar__item {
  width: 104px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tabbar__icon {
  height: 33px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tabbar__glyph {
  width: 22px;
  height: 33px; /* design 22px remixicon 行框 = 22 × 1.5 */
  position: relative;
  box-sizing: border-box;
}

/* 形状画在 ::before（CSS 占位，决策 D5）：18×18 居中于 22×33 行框 */
.tabbar__glyph::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 7.5px;
  width: 18px;
  height: 18px;
  border: 2px solid $color-text-placeholder;
  border-radius: 6px;
  box-sizing: border-box;
}

.tabbar__glyph--active::before {
  border-color: $color-primary;
}

.tabbar__gap {
  height: 3px;
}

.tabbar__label {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  line-height: 16px;
}

.tabbar__label--active {
  color: $color-primary;
  font-weight: 600;
}
</style>
