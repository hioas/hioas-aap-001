<template>
  <view class="detecting-page">
    <!-- 顶部导航：design id=c2a2498d（白底 · padding 48/16/12/16 · 返回 24px #334155 · 标题 17px Bold） -->
    <view class="detecting-page__topbar">
      <view class="detecting-page__icon-btn" data-testid="back-btn" @tap="goBack">
        <view class="glyph glyph--back" aria-hidden="true" />
      </view>
      <text class="detecting-page__title">{{ PAGE_TITLE }}</text>
      <view class="detecting-page__spacer" />
      <!-- 状态 chip：design id=70d01d00（#EFF6FF · r12 · h24 · 9×7 蓝点 + 11px #2563EB） -->
      <view v-if="model.chipLabel" class="chip chip--status" data-testid="status-chip">
        <view class="chip__dot" aria-hidden="true" />
        <text class="chip__text">{{ model.chipLabel }}</text>
      </view>
    </view>

    <view class="detecting-page__body">
      <!-- 总进度卡片：design id=88f1ee17（白 · r18 · padding 20 · effects drop_shadow(0,6,blur 20,rgba(15,23,42,0.06))） -->
      <view class="card card--shadow">
        <view class="card__title-row">
          <text class="card__title" data-testid="total-label">{{ TOTAL_LABEL }}</text>
          <view class="card__spacer" />
          <text class="card__percent" data-testid="total-percent">{{ model.percentText }}</text>
        </view>

        <!-- 进度条：design id=61993aa5（轨道高 10 #E2E8F0 r5；填充 #2563EB） -->
        <view class="bar">
          <view class="bar__fill" data-testid="progress-fill" :style="{ width: model.percentText }" />
        </view>

        <!-- 进度元信息行：design id=dac2c177 -->
        <view class="meta">
          <text class="meta__done" data-testid="progress-finished">{{ model.finishedText }}</text>
          <view class="meta__spacer" />
          <text v-if="model.etaText" class="meta__eta" data-testid="eta-text">{{ model.etaText }}</text>
        </view>

        <!-- 成本保护行：design id=257b52bf（#ECFDF5 · r12 · padding 12） -->
        <view class="cost" data-testid="cost-block">
          <view class="glyph glyph--shield" aria-hidden="true" />
          <view class="cost__text">
            <text class="cost__title">{{ COST_TITLE }}</text>
            <text class="cost__sub">{{ COST_SUB }}</text>
          </view>
        </view>
      </view>

      <!-- 分项进度卡片：design id=2138c3d3（白 · r18 · padding 20 · 描边 #EEF2F7） -->
      <view class="card card--stroke card--gap">
        <text class="card__title" data-testid="section-label">{{ SECTION_LABEL }}</text>

        <view class="rows">
          <view
            v-for="(row, index) in model.rows"
            :key="row.code"
            class="probe-row"
            :class="[`probe-row--${row.stateKey}`, { 'probe-row--gap': index > 0 }]"
            data-testid="probe-row"
          >
            <!-- 图标块 32×32 r10：design id=301d0f9a 等 -->
            <view class="probe-row__box">
              <view class="glyph" :class="`glyph--probe-${row.stateKey}`" aria-hidden="true" />
            </view>
            <view class="probe-row__content">
              <text class="probe-row__name" data-testid="probe-name">{{ row.label }}</text>
              <text class="probe-row__detail" data-testid="probe-detail">{{ row.detailText }}</text>
            </view>
            <!-- 状态 chip：design id=d1fa51b9 等（h22 · r11 · padding 0 8px） -->
            <view class="probe-chip" data-testid="probe-chip">
              <text class="probe-chip__text">{{ row.chipText }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 提示卡片：design id=c960eff4（白 · r18 · padding 16/20 · 描边 #EEF2F7 · 图标 #D97706） -->
      <view class="card card--stroke card--gap tip" data-testid="tip-card">
        <view class="glyph glyph--tip" aria-hidden="true" />
        <text class="tip__text">{{ TIP_TEXT }}</text>
      </view>
    </view>

    <!-- 底部操作条：design id=ed66b6f1（白 · padding 12/16/24/16 · 按钮 h48 r12 #F1F5F9） -->
    <view class="history-bar">
      <view class="history-bar__btn" data-testid="history-btn" @tap="onHistory">
        <view class="glyph glyph--history" aria-hidden="true" />
        <text class="history-bar__text">{{ HISTORY_TEXT }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 页面 5【检测验真】检测进行中 2（序号 5 / page-5-2）
 * 设计真源：.calicat/raw/pages/page-5-2/design.tree.json（430 宽，129 图层）
 * 接口：18-API Detection Tag → GET /api/v1/detection-jobs/{jobId}、GET /api/v1/detection-jobs/{jobId}/results
 *   ⚠️ 18-API 只列路径未列方法 → GET 为 REST 语义推断，已记台账待确认。
 * 交互分类（台账序号 5 行）：
 *   返回 = navigation(navigateBack 1)
 *   「查看历史检测报告」= client-only（画布 30 页无「历史检测报告」页；GET /reports 无对应页面设计 → 不臆造路由）
 *   结束后的跳转 = 不做（09-PRD：检测完成后系统自动通知；设计稿无完成/失败态 → 待人类拍板）
 * 入参：jobId 取页面 query（navigateTo 的 ?jobId=），无 query 时退 storage 键 aap_detection_job_id，
 *   从 query 拿到时同时写入 storage，便于 H5 刷新后仍能续看。
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ApiError } from '@/api/http'
import { detectionApi } from '@/api/detection'
import {
  COST_SUB,
  COST_TITLE,
  HISTORY_TEXT,
  HISTORY_TOAST,
  JOB_ID_KEY,
  MISSING_JOB_TOAST,
  PAGE_TITLE,
  POLL_INTERVAL_MS,
  SECTION_LABEL,
  TIP_TEXT,
  TOTAL_LABEL,
  buildDetectingModel,
  shouldPoll,
  type DetectionJobRaw,
  type DetectionResultsRaw
} from '@/utils/detecting-model'

const job = ref<DetectionJobRaw | null>(null)
const results = ref<DetectionResultsRaw | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

const model = computed(() => buildDetectingModel(job.value, results.value))

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

/** 页面入参：优先页面栈 query，其次 storage（单测/无 query 场景） */
function resolveJobId(): string {
  try {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
    const current = pages[pages.length - 1] as
      | { options?: Record<string, string>; $page?: { options?: Record<string, string> } }
      | undefined
    const query = current?.options ?? current?.$page?.options ?? {}
    if (query.jobId) {
      const fromQuery = String(query.jobId)
      try {
        uni.setStorageSync(JOB_ID_KEY, fromQuery)
      } catch {
        /* storage 写入失败不影响本次展示 */
      }
      return fromQuery
    }
  } catch {
    /* 无页面栈时忽略，走 storage 兜底 */
  }
  try {
    return String(uni.getStorageSync(JOB_ID_KEY) || '')
  } catch {
    return ''
  }
}

let jobId = ''

function stopPolling() {
  if (timer !== null) {
    clearInterval(timer)
    timer = null
  }
}

async function load() {
  try {
    const [jobRaw, resultsRaw] = await Promise.all([detectionApi.job(jobId), detectionApi.results(jobId)])
    job.value = jobRaw ?? null
    results.value = resultsRaw ?? null
    if (!shouldPoll(job.value?.status)) stopPolling()
  } catch (err) {
    toast(err instanceof ApiError ? err.message : '加载失败，请稍后重试')
  }
}

function startPolling() {
  stopPolling()
  timer = setInterval(() => {
    // 终态/未知状态不再打接口（clearInterval 已在 load 内按状态触发，这里再兜一层）
    if (!shouldPoll(job.value?.status)) {
      stopPolling()
      return
    }
    void load()
  }, POLL_INTERVAL_MS)
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** 画布无「历史检测报告」页（.calicat/inventory.json 30 页已核对）→ client-only，不臆造路由 */
function onHistory() {
  toast(HISTORY_TOAST)
}

onMounted(async () => {
  jobId = resolveJobId()
  if (!jobId) {
    toast(MISSING_JOB_TOAST)
    return
  }
  await load()
  if (shouldPoll(job.value?.status)) startPolling()
})

onUnmounted(stopPolling)
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.detecting-page {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部导航（design c2a2498d：padding 48/16/12/16 · 白底 · 返回图标层 594997da 宽 26 / fontSize 24 → 行框 36
   → 栏高 96 = 48 + 36 + 12；修前图标盒 24×24 使栏高只有 84、标题/徽章整体上移 6px） */
.detecting-page__topbar {
  background: $color-bg-card;
  /* --status-bar-height 由 uni-app 提供（H5 = 0）：设计帧未含状态栏偏移，此处补平台安全区 */
  padding: calc(48px + var(--status-bar-height, 0px)) 16px 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

/* 返回图标盒 = 设计图层盒（宽 26 × 行框 36；形状画在 ::before 里，D5 仍为 CSS 占位） */
.detecting-page__icon-btn {
  width: 26px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.detecting-page__title {
  margin-left: 12px;
  font-size: 17px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
}

.detecting-page__spacer {
  flex: 1;
}

/* 状态 chip（design 70d01d00） */
.chip--status {
  height: 24px;
  border-radius: 12px;
  padding: 0 8px;
  background: $color-primary-weak;
  display: flex;
  flex-direction: row;
  align-items: center;
  flex: none;
}

.chip__dot {
  width: 9px;
  height: 7px;
  border-radius: 4px;
  background: $color-primary;
  flex: none;
}

.chip__text {
  margin-left: 4px;
  font-size: $font-2xs;
  font-weight: 500;
  color: $color-primary;
  /* 设计 797ccbbc 图层行框 = 11 → 16（文本行框 ≈ 字号度量行框） */
  line-height: 16px;
}

/* 内容区：各区段容器 padding-top 12（design 65309096 / 9c8019ba / 72d58ad4） */
.detecting-page__body {
  padding: 12px 16px 0 16px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.card {
  width: 100%;
  background: $color-bg-card;
  border-radius: $radius-xl;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 卡1 = design 88f1ee17：effects drop_shadow(0,6,blur 20,rgba(15,23,42,0.06))（卡片投影，不占布局） */
.card--shadow {
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

/* 设计 2138c3d3 / c960eff4 的 stroke = Figma **center** 描边 → CSS 必须用 box-shadow：
   用 border 会占掉 1px 布局（内容宽 358 → 356、卡内所有右/下元素各偏 1px） */
.card--stroke {
  box-shadow: 0 0 0 1px $color-border-chip;
}

.card--gap {
  margin-top: 12px;
}

.card__title-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.card__spacer {
  flex: 1;
}

.card__title {
  font-size: $font-md;
  font-weight: 600;
  color: $color-text-primary;
  /* 设计「分项检测」ea3a0a0d 显式 height=22（15px SemiBold 行框）；「总进度」同字号同族 → 同值 */
  line-height: 22px;
}

.card__percent {
  font-size: $font-2xl;
  font-weight: 700;
  color: $color-primary;
  /* 设计 PNG 实测：卡顶 108 + padding 20 + 标题行 26 + gap 16 = 进度条 170 → 行框 = 26（20px Bold） */
  line-height: 26px;
}

/* 进度条（design 61993aa5 / ab1875c5） */
.bar {
  width: 100%;
  height: 10px;
  margin-top: 16px;
  border-radius: 5px;
  background: $color-border;
  overflow: hidden;
}

.bar__fill {
  height: 10px;
  border-radius: 5px;
  background: $color-primary;
}

/* 进度元信息行（design dac2c177） */
.meta {
  width: 100%;
  margin-top: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.meta__done {
  font-size: $font-xs;
  color: $color-text-muted;
  /* 设计 dac2c177 元信息行行框 = 18（设计 PNG：条底 179 + 12 = 192，行高 18，+16 = 成本块 226） */
  line-height: 18px;
}

.meta__spacer {
  flex: 1;
}

.meta__eta {
  font-size: $font-xs;
  color: $color-text-placeholder;
  line-height: 18px;
}

/* 成本保护行（design 257b52bf / ff72fdea / f44b1675） */
.cost {
  width: 100%;
  margin-top: 16px;
  background: $color-success-weak;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  box-sizing: border-box;
}

.cost__text {
  margin-left: 12px;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.cost__title {
  font-size: $font-xs;
  font-weight: 600;
  color: $color-success-text;
  /* 设计 ff72fdea 显式 height=18（12px SemiBold） */
  line-height: 18px;
}

.cost__sub {
  font-size: $font-2xs;
  color: $color-success;
  /* 设计 f44b1675 显式 height=16（11px Regular）→ 成本块内容 34 + padding 24 = 58（设计 PNG 226..283） */
  line-height: 16px;
}

/* 分项检测行（design 073af6ea / 301d0f9a / d1fa51b9 等） */
.rows {
  width: 100%;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
}

.probe-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.probe-row--gap {
  margin-top: 12px;
}

.probe-row__box {
  width: 32px;
  height: 32px;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  box-sizing: border-box;
}

.probe-row__content {
  margin-left: 12px;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.probe-row__name {
  font-size: $font-sm;
  font-weight: 600;
  color: $color-text-primary;
  /* 设计 1fe5e490 等显式 height=18（13px SemiBold） */
  line-height: 18px;
}

.probe-row__detail {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  /* 设计 cc4105a8 等显式 height=16（11px Regular）→ 行内容 34 = 行高（设计 PNG 行距 46 = 34 + 12） */
  line-height: 16px;
}

.probe-chip {
  height: 22px;
  border-radius: 11px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.probe-chip__text {
  font-size: $font-2xs;
  font-weight: 500;
  line-height: 16px;
}

/* 三态配色（design：完成 #ECFDF5/#15803D · 进行中 #EFF6FF/#2563EB · 排队中 #F8FAFC+#F1F5F9/#64748B） */
.probe-row--done .probe-row__box {
  background: $color-success-weak;
}

.probe-row--done .glyph--probe-done::before {
  border-left: 2px solid $color-success;
  border-bottom: 2px solid $color-success;
}

.probe-row--done .probe-chip {
  background: $color-success-weak;
}

.probe-row--done .probe-chip__text {
  color: $color-success-text;
}

.probe-row--running .probe-row__box {
  background: $color-primary-weak;
}

.probe-row--running .glyph--probe-running::before {
  border: 2px solid $color-primary;
  border-top-color: transparent;
  border-radius: 50%;
}

.probe-row--running .probe-chip {
  background: $color-primary-weak;
}

.probe-row--running .probe-chip__text {
  color: $color-primary;
}

.probe-row--queued .probe-row__box {
  background: $color-bg-page;
}

.probe-row--queued .glyph--probe-queued::before {
  border: 1.5px solid $color-text-placeholder;
  border-radius: 50%;
}

.probe-row--queued .probe-row__name {
  color: $color-text-muted;
}

.probe-row--queued .probe-chip {
  background: $color-bg-subtle;
}

.probe-row--queued .probe-chip__text {
  color: $color-text-muted;
}

/* 未覆盖状态（FAILED/SKIPPED/NOT_MEASURABLE…）：中性底，chip 原样直显，不臆造中文 */
.probe-row--other .probe-row__box {
  background: $color-bg-subtle;
}

.probe-row--other .glyph--probe-other::before {
  border: 1.5px solid $color-text-muted;
  border-radius: 3px;
}

.probe-row--other .probe-chip {
  background: $color-bg-subtle;
}

.probe-row--other .probe-chip__text {
  color: $color-text-muted;
}

/* 提示卡片（design c960eff4 / 051f76fc：padding 16/20 · 高 72 = 16 + 内容 40 + 16，设计 PNG 762..833） */
.tip {
  padding: 16px 20px;
  min-height: 72px;
  flex-direction: row;
  align-items: flex-start;
}

.tip__text {
  margin-left: 8px;
  flex: 1;
  min-width: 0;
  font-size: $font-xs;
  color: $color-text-muted;
  /* 设计 PNG 实测行距 16（两行 ink 784..795 / 800..810 → 内容 32） */
  line-height: 16px;
  /* 设计 c960eff4 声明 alignItems=start（图标贴顶 ink 785..802 ✓），但文案 ink 784..810 落在卡的垂直中心
     → 文案自身居中（盒顶 782 = 卡顶 762 + (72-32)/2）；H5 字体行框内的墨迹偏移与设计字体不同，靠这条对齐 ink */
  align-self: center;
}

/* 底部操作条（design ed66b6f1 / 73a98024） */
.history-bar {
  width: 100%;
  margin-top: 16px;
  background: $color-bg-card;
  padding: 12px 16px 24px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.history-bar__btn {
  flex: 1;
  height: 48px;
  background: $color-bg-subtle;
  border-radius: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.history-bar__text {
  margin-left: 6px;
  font-size: $font-base;
  font-weight: 500;
  color: $color-text-secondary;
  /* 设计 85053dbd 图层行框 = 14 → 20 */
  line-height: 20px;
}

/* 图标占位（设计稿为 remixicon 矢量图标，PRD08 禁 emoji → CSS 形状占位，与序号 1/2/3/4 一致）
   ⚠️ 盒子尺寸必须按设计图层：宽 = 该图层 width、高 = 字号×1.5 行框（序号 4 定标），形状一律画进 ::before。
   历史实现把形状直接画在盒子上（如返回 9×9、盾牌 14×14）→ 盒子 ≠ 设计尺寸，栏高/卡高与图标后文本整体偏移。 */
.glyph {
  flex: none;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}

.glyph::before,
.glyph::after {
  box-sizing: border-box;
}

/* 顶部返回（设计 594997da：盒 26×36，字形 24px） */
.glyph--back {
  width: 26px;
  height: 36px;
}

.glyph--back::before {
  content: '';
  width: 12px;
  height: 12px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
  margin-left: 3px;
}

/* 成本保护盾牌（设计 3c6df7a9：盒 22×30，字形 20px） */
.glyph--shield {
  width: 22px;
  height: 30px;
}

.glyph--shield::before {
  content: '';
  width: 14px;
  height: 14px;
  background: $color-success;
  border-radius: 3px 3px 7px 7px;
}

/* 分项图标（设计 9d54ad21 等：盒 20×27，字形 18px）· 三态形状与配色见上方 .probe-row--* 规则 */
.glyph--probe-done,
.glyph--probe-running,
.glyph--probe-queued,
.glyph--probe-other {
  width: 20px;
  height: 27px;
}

.glyph--probe-done::before {
  content: '';
  width: 8px;
  height: 4px;
  transform: rotate(-45deg);
  margin-bottom: 2px;
}

.glyph--probe-running::before {
  content: '';
  width: 13px;
  height: 13px;
}

.glyph--probe-queued,
.glyph--probe-other {
  position: relative;
}

.glyph--probe-queued::before {
  content: '';
  width: 13px;
  height: 13px;
}

.glyph--probe-queued::after {
  content: '';
  position: absolute;
  left: 9px;
  top: 9px;
  width: 1.5px;
  height: 4px;
  background: $color-text-placeholder;
}

.glyph--probe-other::before {
  content: '';
  width: 12px;
  height: 12px;
}

/* 提示三角（设计 05b50545：盒 22×30，字形 20px） */
.glyph--tip {
  width: 22px;
  height: 30px;
}

.glyph--tip::before {
  content: '';
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-bottom: 14px solid $color-warning-text;
}

/* 历史报告表盘（设计 ca7fa21f：盒 22×30，字形 20px） */
.glyph--history {
  width: 22px;
  height: 30px;
  position: relative;
}

.glyph--history::before {
  content: '';
  width: 13px;
  height: 13px;
  border: 1.5px solid $color-text-muted;
  border-radius: 50%;
}

.glyph--history::after {
  content: '';
  position: absolute;
  left: 10px;
  top: 11px;
  width: 1.5px;
  height: 4px;
  background: $color-text-muted;
}
</style>
