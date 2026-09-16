<template>
  <!--
    序号 22【工作台与我的】我的与用量概览（page-22-2 / /pages/usage/index）
    设计真源：.calicat/raw/pages/page-22-2/design.tree.json（430 宽 · 设计总高 1138 · **无 TabBar**）
      顶部导航 0..96 · 12 · 本月汇总卡 108..336(228) · 12 · 近 7 日用量趋势卡 348..570(222) ·
      12 · 模型用量分布卡 582..766(184) · 12 · 成本构成卡 778..985(207) · 12 · 明细入口卡 997..1057(60) ·
      底部说明 1057..1138（padding 24/0/24/0）
    checks 复核轮（载体页 __measure-usage.html · 267 条设计期望值 checks · 红 8 → 绿 0）修 5 类偏差：
      汇总卡 padding 20 → 20/16（宫格 36..175 → 32..178.5）· 补设计 effects drop_shadow(0,6,20,.06) ·
      月份日历字形盒 17×15 → 17×22.5 · 下箭头字形盒 18×15 → 18×24（并去掉形状的 margin-bottom 3 让墨迹居中）·
      月份文字行盒 18 → 14.4（设计 lineHeight 1.2）
  -->
  <view class="usage">
    <!-- 顶部导航（design 30e7ff99：白底 padding 48/16/12/16 · 内容行 36 = 24px 图标 × 1.5） -->
    <view class="nav">
      <view class="nav__back" data-testid="usage-back" @tap="onBack">
        <view class="glyph glyph--back" aria-hidden="true" />
      </view>
      <view class="nav__title-wrap">
        <text class="nav__title" data-testid="usage-title">{{ model.navTitle }}</text>
      </view>
      <view class="nav__spacer" />
      <!-- 月份选择（design 6073d689：h30 r10 #F1F5F9 padding 0/12）；原生月份 picker：client-only + 重新取数 -->
      <picker
        mode="date"
        fields="month"
        class="nav__picker"
        data-testid="month-picker"
        :value="month"
        @change="onMonthChange"
      >
        <view class="month">
          <view class="glyph glyph--calendar" aria-hidden="true" />
          <view class="month__text-wrap">
            <text class="month__value" data-testid="month-value">{{ model.month }}</text>
          </view>
          <view class="month__chevron-wrap">
            <view class="glyph glyph--chevron-down" aria-hidden="true" />
          </view>
        </view>
      </picker>
    </view>

    <!-- 本月汇总卡（design 811a53eb：padding 20/16 r18 · 四宫格 72 高 gap 9 / 行距 8） -->
    <view class="card card--summary">
      <text class="card__title" data-testid="summary-title">{{ model.summaryTitle }}</text>
      <view class="tiles tiles--first">
        <view
          v-for="tile in model.tiles.slice(0, 2)"
          :key="tile.key"
          class="tile"
          data-testid="tile"
          :data-key="tile.key"
          :style="{ background: tile.bg }"
        >
          <text class="tile__value" data-testid="tile-value" :style="{ color: tile.color }">{{ tile.value }}</text>
          <text class="tile__label" data-testid="tile-label">{{ tile.label }}</text>
        </view>
      </view>
      <view class="tiles tiles--second">
        <view
          v-for="tile in model.tiles.slice(2)"
          :key="tile.key"
          class="tile"
          data-testid="tile"
          :data-key="tile.key"
          :style="{ background: tile.bg }"
        >
          <text class="tile__value" data-testid="tile-value" :style="{ color: tile.color }">{{ tile.value }}</text>
          <text class="tile__label" data-testid="tile-label">{{ tile.label }}</text>
        </view>
      </view>
    </view>

    <!-- 近 7 日用量趋势卡（design 0baed36c：padding 20 r18 描边 #EEF2F7 · 标题行 20 + 12 + 图 150） -->
    <view class="card card--trend">
      <view class="card__head">
        <text class="card__title" data-testid="trend-title">{{ model.trendTitle }}</text>
        <view class="card__spacer" />
        <view class="legend">
          <view class="legend__dot" aria-hidden="true" />
          <view class="legend__text-wrap">
            <text class="legend__text" data-testid="trend-legend">{{ model.trendLegend }}</text>
          </view>
        </view>
      </view>
      <view class="trend">
        <!-- 折线用 SVG base64 data-URI（mp-weixin 不能渲染内联 svg，同序号 6 雷达图） -->
        <image class="trend__img" data-testid="trend-chart" :src="model.trend.dataUri" mode="widthFix" />
        <text
          v-for="(label, index) in model.trend.labels"
          :key="`${label}-${index}`"
          class="trend__label"
          data-testid="trend-label"
          :style="labelStyle(index)"
          >{{ label }}</text
        >
        <text v-if="!model.trend.hasData" class="trend__empty" data-testid="trend-empty">—</text>
      </view>
    </view>

    <!-- 模型用量分布卡（design 4a6aa3b5：padding 20 r18 · 4 行 h18 行距 12） -->
    <view class="card card--models">
      <text class="card__title" data-testid="model-title">{{ model.modelTitle }}</text>
      <view v-for="(row, index) in model.modelRows" :key="row.name" class="mrow" :class="{ 'mrow--first': index === 0 }">
        <text class="mrow__name" data-testid="model-name">{{ row.name }}</text>
        <view class="mrow__track">
          <view
            class="mrow__fill"
            data-testid="model-bar-fill"
            :style="{ width: `${row.barPercent}%`, background: row.barColor }"
          />
        </view>
        <view class="mrow__pct-wrap">
          <text class="mrow__pct" data-testid="model-percent">{{ row.percent }}</text>
        </view>
      </view>
    </view>

    <!-- 成本构成卡（design a9b6fb23：padding 20 r18 · 3 行 h18 + 合计行 padding 10 r10 #F8FAFC） -->
    <view class="card card--cost">
      <text class="card__title" data-testid="cost-title">{{ model.costTitle }}</text>
      <view v-for="(row, index) in model.costRows" :key="row.label" class="crow" :class="{ 'crow--first': index === 0 }">
        <text class="crow__label" data-testid="cost-label">{{ row.label }}</text>
        <view class="card__spacer" />
        <text class="crow__value" data-testid="cost-value">{{ row.value }}</text>
      </view>
      <view class="cost-total">
        <text class="cost-total__label" data-testid="cost-total-label">{{ model.costTotal.label }}</text>
        <view class="card__spacer" />
        <text class="cost-total__value" data-testid="cost-total-value">{{ model.costTotal.value }}</text>
      </view>
    </view>

    <!-- 明细入口卡（design 88ce181b：padding 16/20 r18 · 图标 20 宽 27 行盒 + chevron 22 宽 28 行盒） -->
    <view class="card card--detail" data-testid="detail-entry" @tap="onDetailEntry">
      <view class="detail__icon-wrap">
        <view class="glyph glyph--list" aria-hidden="true" />
      </view>
      <view class="detail__text-wrap">
        <text class="detail__text">{{ model.detailText }}</text>
      </view>
      <view class="card__spacer" />
      <view class="detail__chevron-wrap">
        <view class="glyph glyph--chevron-right" aria-hidden="true" />
      </view>
    </view>

    <!-- 底部说明（design 5fe4c752：padding 24/0/24/0 居中两行 11px） -->
    <view class="footer">
      <text class="footer__note" data-testid="footer-note">{{ model.footerNote }}</text>
      <text class="footer__updated" data-testid="footer-updated">{{ model.updatedText }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 22【工作台与我的】我的与用量概览（page-22-2 / /pages/usage/index）
 *
 * 设计真源：.calicat/raw/pages/page-22-2/design.tree.json
 *   （430 宽 · 设计总高 1138 · 导航 96 · 卡片 228/222/184/207/60 · 底部说明 81 · **无 TabBar**）
 * 接口真源：18-API设计OpenAPI.md「Usage」Tag（前缀 /api/v1）
 *   GET /usage/summary（本页唯一读接口，月份维度 month 为 REST 推断）
 *   GET /usage/hourly 仅作「查看逐日 / 逐模型明细」的数据源（画布无明细页 → 本页不调用）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 18-API + 设计稿控件语义；分类见台账序号 22：
 *   返回 = navigation（navigateBack）· 月份选择 = client-only（原生月份 picker → 重新取数）
 *   明细入口 = navigation **无落点**（画布 30 页无明细页 → 不跳转、不臆造路由，台账待拍板）
 *
 * ⚠️ 缺口（全部记台账序号 22，不臆造）：
 *   1. /usage/summary 响应字段级 schema 未定义 → 逐日 / 模型占比 / 成本构成字段名为推断，缺字段渲染「—」；
 *   2. 「较上月节省」「平台服务费（8%）」在 22 份 PRD 零命中 → 服务端优先，费率缺省用设计常量 8%；
 *   3. 占比条填充宽度：设计帧填充 = 百分比 × 卡片外层宽 398（轨道实际 192）→ 设计自身不自洽，
 *      实现按「百分比 × 轨道宽」（语义正确），像素差异已登记；
 *   4. 纵轴刻度 PRD 无定义 → 按峰值取 {1,2,2.5,5,10}×10^n 的上限线性映射（设计帧 1.92 亿 → 上限 2）。
 */
import { computed, onMounted, ref } from 'vue'
import { usageApi } from '@/api/usage'
import {
  LOAD_FAIL_TEXT,
  TREND_GEOMETRY,
  buildUsageOverview,
  currentMonth,
  type UsageOverviewRaw
} from '@/utils/usage-model'

/** 横轴标签盒宽（设计帧 paragraph 宽 20.12） */
const LABEL_WIDTH = 20.12

const raw = ref<UsageOverviewRaw | null>(null)
const month = ref(currentMonth())

const model = computed(() => buildUsageOverview(raw.value ?? {}))

/** 标签定位：x 取设计帧数据点横坐标（图内坐标），纵向取设计帧 y=122.95 */
function labelStyle(index: number): Record<string, string> {
  const point = model.value.trend.points[index]
  const x = point ? point.x : TREND_GEOMETRY.left
  return {
    left: `${x - LABEL_WIDTH / 2}px`,
    width: `${LABEL_WIDTH}px`
  }
}

async function load() {
  try {
    const res = await usageApi.overview({ month: month.value })
    raw.value = (res as UsageOverviewRaw) ?? null
    /* 月份以服务端为准（设计帧 pill 显示的是「数据所属月份」），失败时保持用户选择 */
    month.value = model.value.month
  } catch {
    raw.value = null
    uni.showToast({ title: LOAD_FAIL_TEXT, icon: 'none' })
  }
}

/** 返回：navigation（画布无 TabBar，本页由「我的 → 用量与对账」navigateTo 进入） */
function onBack() {
  uni.navigateBack({ delta: 1 })
}

/** 原生月份 picker：client-only —— 选中后按新月份重新取数 */
async function onMonthChange(event: { detail?: { value?: unknown } } | undefined) {
  const value = event?.detail?.value
  if (typeof value !== 'string' || !/^\d{4}-\d{1,2}$/.test(value)) return
  month.value = value
  await load()
}

/**
 * 「查看逐日 / 逐模型明细」：画布 30 页**无**明细页，18-API 亦只有 /usage/hourly 数据接口而无页面 → 无落点。
 * 按「不臆造路由」原则本轮不跳转、不弹占位 toast（台账序号 22 已登记待拍板）。
 */
function onDetailEntry() {
  /* no-op：等待人类拍板是否新增「逐日 / 逐模型明细」页 */
}

onMounted(load)
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.usage {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  box-sizing: border-box;
  background: $color-bg-page;
}

/* ============================== 顶部导航 ============================== */

.nav {
  height: 96px;
  box-sizing: border-box;
  padding: 48px 16px 12px 16px;
  background: $color-bg-card;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.nav__back {
  width: 26px;
  height: 36px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav__title-wrap {
  padding-left: 12px;
  flex: none;
  display: flex;
  align-items: center;
}

.nav__title {
  display: block;
  font-size: 17px;
  font-weight: 700;
  line-height: 25.5px;
  color: $color-text-primary;
}

.nav__spacer {
  flex: 1;
  min-width: 0;
}

.nav__picker {
  flex: none;
}

.month {
  height: 30px;
  box-sizing: border-box;
  padding: 0 12px;
  border-radius: $radius-md;
  background: $color-bg-subtle;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.month__text-wrap {
  padding-left: 5px;
  display: flex;
  align-items: center;
}

.month__value {
  display: block;
  font-size: $font-xs;
  font-weight: 500;
  line-height: 14.4px; /* 设计 lineHeight 1.2 × 12 */
  color: $color-text-secondary;
}

.month__chevron-wrap {
  padding-left: 4px;
  display: flex;
  align-items: center;
}

/* 图标占位（设计用 remixicon 字形，仓库无图标资源；R-26 禁 emoji）—— 外盒取设计声明宽，内层形状贴墨迹 */
.glyph {
  display: block;
  position: relative;
}

/* 设计声明宽 26 / 墨迹 16×16（remixicon 24px） */
.glyph--back {
  width: 16px;
  height: 16px;

  &::before {
    content: '';
    position: absolute;
    left: 2px;
    top: 2px;
    width: 11px;
    height: 11px;
    border-left: 2px solid $color-text-secondary-2;
    border-bottom: 2px solid $color-text-secondary-2;
    transform: rotate(45deg);
  }
}

/* 设计声明宽 17（remixicon 15px）→ 外盒 17×22.5（= 字号 × 1.5 字形行盒），内层形状 12×12 贴墨迹 14×13 */
.glyph--calendar {
  width: 17px;
  height: 22.5px;
  display: flex;
  align-items: center;
  justify-content: center;

  &::after {
    content: '';
    width: 12px;
    height: 12px;
    border-radius: 3px;
    border: 1.4px solid $color-text-muted;
    box-sizing: border-box;
  }
}

/* 设计声明宽 18（remixicon 16px）→ 外盒 18×24（= 字号 × 1.5 字形行盒），内层形状 8×8 */
.glyph--chevron-down {
  width: 18px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;

  &::after {
    content: '';
    width: 8px;
    height: 8px;
    border-right: 1.5px solid $color-text-placeholder;
    border-bottom: 1.5px solid $color-text-placeholder;
    transform: rotate(45deg);
  }
}

.glyph--chevron-right {
  width: 8px;
  height: 8px;
  border-top: 1.5px solid $color-border-strong;
  border-right: 1.5px solid $color-border-strong;
  transform: rotate(45deg);
}

.glyph--list {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: $color-primary;
}

/* ============================== 卡片通用 ============================== */

.card {
  margin: 12px 16px 0 16px;
  padding: 20px;
  box-sizing: border-box;
  border-radius: $radius-xl;
  background: $color-bg-card;
}

/* 趋势 / 模型 / 成本 / 明细入口四卡在设计帧里有 1px 描边（#EEF2F7）→ 用 ring（不占布局，SKILL §4.8） */
.card--trend,
.card--models,
.card--cost,
.card--detail {
  box-shadow: 0 0 0 1px $color-border-chip;
}

/* 本月汇总卡（design 811a53eb）：padding 20/16（左右 16 → 宫格 32..398 宽 178.5）、
   只有 effects drop_shadow(0,6,20,rgba(15,23,42,.06))、无 stroke → 与其余四卡相反，逐帧按设计走 */
.card--summary {
  padding: 20px 16px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

.card__title {
  display: block;
  font-size: $font-base;
  font-weight: 600;
  line-height: 20px;
  color: $color-text-primary;
}

.card__spacer {
  flex: 1;
  min-width: 0;
}

.card__head {
  height: 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

/* ============================== 本月汇总卡 ============================== */

.tiles {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.tiles--first {
  padding-top: 16px;
}

.tiles--second {
  padding-top: 8px;
}

.tile {
  flex: 1;
  min-width: 0;
  height: 72px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.tile + .tile {
  margin-left: 9px;
}

.tile__value {
  display: block;
  font-size: 17px;
  font-weight: 700;
  line-height: 26px;
}

.tile__label {
  display: block;
  font-size: 10px;
  line-height: 16px;
  color: $color-text-muted;
}

/* ============================== 近 7 日用量趋势卡 ============================== */

.legend {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.legend__dot {
  width: 9px;
  height: 8px;
  flex: none;
  border-radius: 4px;
  background: $color-primary;
}

.legend__text-wrap {
  padding-left: 4px;
}

.legend__text {
  display: block;
  font-size: 10px;
  line-height: 15px;
  color: $color-text-placeholder;
}

.trend {
  position: relative;
  margin-top: 12px;
  height: 150px;
}

.trend__img {
  display: block;
  width: 100%;
  height: 150px;
}

.trend__label {
  position: absolute;
  top: 122.95px;
  font-size: 10px;
  line-height: 13.2px;
  text-align: center;
  color: $color-text-placeholder;
}

.trend__empty {
  position: absolute;
  left: 0;
  top: 60px;
  width: 100%;
  text-align: center;
  font-size: $font-xs;
  line-height: 18px;
  color: $color-text-placeholder;
}

/* ============================== 模型用量分布卡 ============================== */

.mrow {
  height: 18px;
  padding-top: 12px;
  box-sizing: content-box;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.mrow--first {
  padding-top: 16px;
}

.mrow__name {
  display: block;
  width: 131px;
  flex: none;
  font-size: $font-xs;
  line-height: 18px;
  color: $color-text-tertiary;
}

.mrow__track {
  flex: 1;
  min-width: 0;
  height: 10px;
  border-radius: 5px;
  background: $color-bg-subtle;
  overflow: hidden;
}

.mrow__fill {
  height: 10px;
  border-radius: 5px;
}

.mrow__pct-wrap {
  padding-left: 8px;
  flex: none;
}

.mrow__pct {
  display: block;
  font-size: $font-xs;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-primary;
}

/* ============================== 成本构成卡 ============================== */

.crow {
  height: 18px;
  padding-top: 12px;
  box-sizing: content-box;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.crow--first {
  padding-top: 16px;
}

.crow__label {
  display: block;
  width: 131px;
  flex: none;
  font-size: $font-xs;
  line-height: 18px;
  color: $color-text-tertiary;
}

.crow__value {
  display: block;
  font-size: $font-xs;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-primary;
}

.cost-total {
  margin-top: 12px;
  padding: 10px;
  box-sizing: border-box;
  border-radius: $radius-md;
  background: $color-bg-page;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.cost-total__label {
  display: block;
  font-size: $font-xs;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-secondary-2;
}

/* 合计值 14px ExtraBold（设计帧 fontFamily=SourceHanSans-ExtraBold，行盒 21 = 14×1.5） */
.cost-total__value {
  display: block;
  font-size: $font-base;
  font-weight: 800;
  line-height: 21px;
  color: $color-brand;
}

/* ============================== 明细入口卡 ============================== */

.card--detail {
  padding: 16px 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.detail__icon-wrap {
  width: 20px;
  height: 27px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail__text-wrap {
  padding-left: 8px;
  flex: none;
}

.detail__text {
  display: block;
  font-size: $font-sm;
  font-weight: 500;
  line-height: 19.5px;
  color: $color-text-primary;
}

.detail__chevron-wrap {
  width: 22px;
  height: 28px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ============================== 底部说明 ============================== */

.footer {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.footer__note {
  display: block;
  font-size: $font-2xs;
  line-height: 16px;
  color: $color-text-placeholder;
}

.footer__updated {
  display: block;
  font-size: $font-2xs;
  line-height: 16px;
  color: $color-border-strong;
}
</style>
