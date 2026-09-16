<template>
  <view class="report-page">
    <!-- 顶部导航：design id=b362b5a2（白底 · padding 48/16/12/16 · 「检测报告」17px Bold #0F172A · 报告编号 11px #94A3B8） -->
    <view class="report-page__topbar">
      <view class="report-page__icon-btn" data-testid="back-btn" @tap="goBack">
        <view class="glyph glyph--back" aria-hidden="true" />
      </view>
      <text class="report-page__title" data-testid="title">{{ PAGE_TITLE }}</text>
      <view class="report-page__spacer" />
      <text class="report-page__no" data-testid="report-no">{{ model.reportNo }}</text>
    </view>

    <view class="report-page__body">
      <!-- 结论封面卡：design id=4e855266（白 · r18 · padding 20） -->
      <view class="block">
        <view class="card card--cover">
          <view class="card__title-row">
            <view class="card__mark"><view class="glyph glyph--doc" aria-hidden="true" /></view>
            <text class="card__title card__title--cover" data-testid="verdict-title">{{ model.verdictTitle }}</text>
            <view class="card__spacer" />
            <text class="card__sub" data-testid="channel">{{ model.channelText }}</text>
          </view>

          <!-- 综合分块：design id=6f989737（40px 综合分 + 分数说明 + 结论标签 #F0FDF4 r14 h28） -->
          <view class="score-row">
            <text class="score" :class="`score--${model.resultTone}`" data-testid="score">{{ model.scoreText }}</text>
            <view class="score__meta">
              <text class="score__meta-text">{{ model.scoreSectionLabel }}</text>
              <text class="score__meta-text">{{ model.scoreMaxLabel }}</text>
            </view>
            <view class="card__spacer" />
            <view class="result-chip" :class="`result-chip--${model.resultTone}`" data-testid="result-chip">
              <view class="glyph glyph--check" aria-hidden="true" />
              <text class="result-chip__text">{{ model.resultLabel }}</text>
            </view>
          </view>

          <!-- 分隔线：design 377c9abc（1px #EEF2F7，位于综合分块与状态四格之间，间距 16） -->
          <view class="card__divider" />

          <!-- 状态四格：design id=950cbd49（值 15px · 标签 10px #94A3B8） -->
          <view class="status-grid">
            <view v-for="(cell, index) in model.statusCells" :key="index" class="status-cell">
              <text
                class="status-cell__value"
                :class="`status-cell__value--${cell.tone}`"
                data-testid="status-value"
                >{{ cell.value }}</text
              >
              <text class="status-cell__label" data-testid="status-label">{{ cell.label }}</text>
            </view>
          </view>

          <!-- 结论措辞盒：design id=bc2f3eaa（#F8FAFC · r12 · padding 12） -->
          <view class="verdict-box">
            <view class="glyph glyph--check-strong" aria-hidden="true" />
            <text class="verdict-box__text" data-testid="verdict-text">{{ model.verdict }}</text>
          </view>

          <!-- 信息清单：design id=95371b7c（标签 64 宽 11px #94A3B8 · 值 11.5px #475569 · 行 padding 5/0） -->
          <view class="info-list">
            <view
              v-for="(row, index) in model.infoRows"
              :key="row.label"
              class="info-row"
              :class="{ 'info-row--gap': index > 0 }"
            >
              <text class="info-row__label" data-testid="info-label">{{ row.label }}</text>
              <text class="info-row__value" data-testid="info-value">{{ row.value }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 关键指标卡：design id=c13761bd（白 · r18 · padding 20；子卡 #F8FAFC r12 padding 12，2 列） -->
      <view class="block">
        <view class="card">
          <view class="card__title-row">
            <view class="card__bar" />
            <text class="card__title" data-testid="metrics-title">{{ KEY_METRICS_TITLE }}</text>
            <view class="card__spacer" />
            <text class="card__sub">{{ KEY_METRICS_SUB }}</text>
          </view>
          <view class="metrics">
            <view v-for="metric in model.metrics" :key="metric.label" class="metric">
              <text class="metric__label" data-testid="metric-label">{{ metric.label }}</text>
              <view class="metric__value-row">
                <text class="metric__value" data-testid="metric-value">{{ metric.value }}</text>
                <text class="metric__unit">{{ metric.unit }}</text>
              </view>
              <text class="metric__sub" :class="`metric__sub--${metric.subTone}`" data-testid="metric-sub">{{
                metric.sub
              }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 维度总览卡：design id=7530b31a（雷达图区 6cf10c3b 高 258 / 均分行 33713878 / 图例 7a5c9636） -->
      <view class="block">
        <view class="card">
          <view class="card__title-row">
            <text class="card__title" data-testid="dims-title">{{ DIM_TITLE }}</text>
            <view class="card__spacer" />
            <text class="card__sub">{{ DIM_SUB }}</text>
          </view>
          <view class="radar">
            <view class="radar__canvas">
              <image class="radar__img" data-testid="radar" :src="radarUri" mode="widthFix" />
              <!-- 轴标签：design 6cf10c3b 六个 paragraph（11px #64748B，位置按设计稿坐标） -->
              <text
                v-for="(label, index) in model.radar.labels"
                :key="label"
                class="radar__label"
                :class="`radar__label--${index}`"
                data-testid="radar-label"
                >{{ label }}</text
              >
            </view>
          </view>
          <view class="dims">
            <view
              v-for="(dim, index) in model.dims"
              :key="dim.code"
              class="dim"
              :class="{ 'dim--gap': index > 0 }"
            >
              <view class="dim__name">
                <view class="dim__dot" :style="{ background: dim.color }" />
                <text class="dim__text" data-testid="dim-name">{{ dim.name }}</text>
              </view>
              <view class="dim__bar">
                <view class="dim__fill" :style="{ width: `${dim.barPercent}%`, background: dim.color }" />
              </view>
              <text class="dim__score" data-testid="dim-score">{{ dim.scoreText }}</text>
            </view>
          </view>
          <view class="legend">
            <view
              v-for="(item, index) in LEGEND_ITEMS"
              :key="item.text"
              class="legend__item"
              :class="{ 'legend__item--gap': index > 0 }"
            >
              <view class="legend__dot" :style="{ background: item.color }" />
              <text class="legend__text" data-testid="legend-text">{{ item.text }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 全维度明细卡：design id=7806d174（说明行 8485b93b / 分组 A–G / 权重说明盒 104230be） -->
      <view class="block">
        <view class="card">
          <view class="card__title-row">
            <text class="card__title" data-testid="detail-title">{{ DETAIL_TITLE }}</text>
            <view class="card__spacer" />
            <text class="card__sub" data-testid="item-count">{{ model.itemCountText }}</text>
          </view>
          <text class="detail-summary" data-testid="detail-summary">{{ model.detailSummary }}</text>

          <view v-for="section in model.sections" :key="section.code" class="group">
            <view class="group__head">
              <view class="group__bar" :style="{ background: section.color }" />
              <text class="group__title" data-testid="section-title">{{ section.title }}</text>
              <view class="card__spacer" />
              <text class="group__meta">{{ section.meta }}</text>
            </view>

            <view v-if="section.note" class="group__note">{{ section.note }}</view>

            <view
              v-for="row in section.items"
              :key="row.code"
              class="item"
              data-testid="section-item"
              :class="{ 'item--gap': section.items.length > 1 }"
            >
              <view class="item__name">
                <text class="item__label" data-testid="item-label">{{ row.label }}</text>
                <text class="item__metric" data-testid="item-metric">{{ row.metric }}</text>
              </view>
              <view v-if="row.statusKey === 'scored'" class="item__bar">
                <view class="item__fill" :style="{ width: `${row.barPercent}%`, background: row.color }" />
              </view>
              <view v-else class="item__holder" />
              <view v-if="row.statusKey === 'scored'" class="item__score">
                <text class="item__score-text" data-testid="item-score">{{ row.scoreText }}</text>
              </view>
              <view v-else class="item__pill" :class="`item__pill--${row.statusKey}`">
                <text class="item__pill-text" data-testid="item-status">{{ row.scoreText }}</text>
              </view>
            </view>
          </view>

          <view class="note-box">{{ model.weightNote }}</view>
        </view>
      </view>

      <!-- 风险发现卡：design id=658a45d1（4 条：padding 12 r12，底色 #F0FDF4 / #FFFBEB / #FFFBEB / #F1F5F9） -->
      <view class="block">
        <view class="card">
          <view class="card__title-row">
            <text class="card__title" data-testid="risk-title">{{ RISK_TITLE }}</text>
            <view class="card__spacer" />
            <text class="card__sub">{{ model.findings.length }} 条</text>
          </view>
          <view
            v-for="(finding, index) in model.findings"
            :key="finding.title"
            class="finding"
            :class="[`finding--${finding.tone}`, { 'finding--gap': index > 0 }]"
          >
            <view class="glyph" :class="`glyph--finding-${finding.tone}`" aria-hidden="true" />
            <view class="finding__text">
              <text class="finding__title" data-testid="finding-title">{{ finding.title }}</text>
              <text class="finding__body" data-testid="finding-body">{{ finding.body }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 原始证据卡：design id=9844215a（键 88 宽 11px #0F172A · 值 11px #64748B · 行距 padding-top 16/10） -->
      <view class="block">
        <view class="card">
          <view class="card__title-row">
            <text class="card__title" data-testid="evidence-title">{{ EVIDENCE_TITLE }}</text>
            <view class="card__spacer" />
            <text class="card__sub" data-testid="evidence-sub">{{ EVIDENCE_SUB }}</text>
          </view>
          <view
            v-for="(row, index) in model.evidenceRows"
            :key="row.key"
            class="evidence-row"
            :class="{ 'evidence-row--first': index === 0, 'evidence-row--gap': index > 0 }"
          >
            <text class="evidence-row__key" data-testid="evidence-key">{{ row.key }}</text>
            <text class="evidence-row__value" data-testid="evidence-value">{{ row.value }}</text>
          </view>
        </view>
      </view>

      <!-- 免责声明卡：design id=30918987（标题 12px + 正文 11px） -->
      <view class="block">
        <view class="card">
          <view class="disclaimer">
            <view class="glyph glyph--info" aria-hidden="true" />
            <view class="disclaimer__text">
              <text class="disclaimer__title" data-testid="disclaimer-title">{{ DISCLAIMER_TITLE }}</text>
              <text class="disclaimer__body" data-testid="disclaimer-text">{{ model.disclaimer }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部操作条：design id=e096bd63（白 · padding 12 r18；导出 126×48 白底描边；填写报价 #2563EB h48） -->
    <view class="action">
      <view class="action__bar">
        <view class="action__ghost" data-testid="export-btn" @tap="onExport">
          <view class="glyph glyph--download" aria-hidden="true" />
          <text class="action__ghost-text">{{ EXPORT_TEXT }}</text>
        </view>
        <view class="action__primary" data-testid="quote-btn" @tap="onQuote">
          <view class="glyph glyph--edit" aria-hidden="true" />
          <text class="action__primary-text">{{ QUOTE_TEXT }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 页面 6【检测验真】大模型检测报告 · 多维度专业版（序号 6 / page-6）
 * 设计真源：.calicat/raw/pages/page-6/design.tree.json（430 宽）
 * 接口：18-API Report Tag → GET /api/v1/reports/{reportId}、GET /api/v1/reports/{reportId}/export
 *   ⚠️ 18-API 只列路径未列方法 → GET 为 REST 语义推断，已记台账待确认。
 * 交互分类（台账序号 6 行）：
 *   返回 = navigation(navigateBack 1)
 *   导出 PDF = api(GET /reports/{reportId}/export)；小程序内不做文件落地，成功即提示（响应体字段 missing-prd）
 *   填写报价 = navigation(navigateTo /pages/quote-models/index，用户拍板对齐原型 page-9)
 *   评分 / 维度 / 明细 / 风险 / 证据 / 免责 = client-only（渲染态，无点击）
 * 入参：reportId 取页面 query（?reportId=），无 query 时退 storage 键 aap_report_id。
 */
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/api/http'
import { reportApi } from '@/api/report'
import {
  DETAIL_TITLE,
  DIM_SUB,
  DIM_TITLE,
  DISCLAIMER_TITLE,
  EVIDENCE_SUB,
  EVIDENCE_TITLE,
  EXPORT_READY_TOAST,
  EXPORT_TEXT,
  KEY_METRICS_SUB,
  KEY_METRICS_TITLE,
  LEGEND_ITEMS,
  LOAD_FAIL_TOAST,
  MISSING_REPORT_TOAST,
  PAGE_TITLE,
  QUOTE_ROUTE,
  QUOTE_TEXT,
  REPORT_ID_KEY,
  RISK_TITLE,
  buildReportModel,
  radarDataUri,
  type ReportRaw
} from '@/utils/report-model'

const report = ref<ReportRaw | null>(null)

const model = computed(() => buildReportModel(report.value))
const radarUri = computed(() => radarDataUri(model.value.radar.geometry))

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

/** 页面入参：优先页面栈 query，其次 storage（单测/无 query 场景） */
function resolveReportId(): string {
  try {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
    const current = pages[pages.length - 1] as
      | { options?: Record<string, string>; $page?: { options?: Record<string, string> } }
      | undefined
    const query = current?.options ?? current?.$page?.options ?? {}
    if (query.reportId) {
      const fromQuery = String(query.reportId)
      try {
        uni.setStorageSync(REPORT_ID_KEY, fromQuery)
      } catch {
        /* storage 写入失败不影响本次展示 */
      }
      return fromQuery
    }
  } catch {
    /* 无页面栈时忽略，走 storage 兜底 */
  }
  try {
    return String(uni.getStorageSync(REPORT_ID_KEY) || '')
  } catch {
    return ''
  }
}

let reportId = ''

async function load() {
  try {
    report.value = (await reportApi.detail(reportId)) ?? null
  } catch (err) {
    toast(err instanceof ApiError ? err.message : LOAD_FAIL_TOAST)
  }
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** 导出 PDF：18-API Report Tag /reports/{reportId}/export；小程序内不做文件落地，只提示 */
async function onExport() {
  if (!reportId) {
    toast(MISSING_REPORT_TOAST)
    return
  }
  try {
    await reportApi.exportFile(reportId)
    toast(EXPORT_READY_TOAST)
  } catch (err) {
    toast(err instanceof ApiError ? err.message : LOAD_FAIL_TOAST)
  }
}

/** 填写报价：跳用户拍板对齐的原型 page-9「模型报价设置-列表」（不臆造带参路由） */
function onQuote() {
  uni.navigateTo({ url: QUOTE_ROUTE })
}

onMounted(async () => {
  reportId = resolveReportId()
  if (!reportId) {
    toast(MISSING_REPORT_TOAST)
    return
  }
  await load()
})
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.report-page {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部导航（design b362b5a2） */
.report-page__topbar {
  background: $color-bg-card;
  padding: calc(48px + var(--status-bar-height, 0px)) 16px 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.report-page__icon-btn {
  width: 24px;
  height: 33px; /* design 59b830bc：remixicon 22px 行框 = 22×1.5 = 33（顶部栏内容高，撑起 48+33+12=93） */
  display: flex;
  align-items: center;
  justify-content: center;
}

.report-page__title {
  margin-left: 12px;
  font-size: 17px;
  font-weight: 700; /* design eb6fd4b5 fontFamily=SourceHanSans-Bold */
  color: $color-text-primary;
  line-height: 1.2;
}

.report-page__spacer {
  flex: 1;
}

.report-page__no {
  font-size: 11px;
  color: $color-text-placeholder;
  /* design 5d860a4b「报告编号」frame：h=16（叶子 202cd360 height=fill_container）→ 行框取显式 height 16，
     不是 lineHeight 1.2 × 11 = 13.2（同族口径：显式 height 优先）。设计 PNG 顶部栏右侧墨迹 y60..69、
     中心 64.5 = 内容行 48..81 的中心，正是「16 高盒在 33 高行里居中」的结果。
     文案口径：本页设计原文**无**「报告编号」前缀（叶子 content = 'DR-20240613-0758'，
     设计 PNG 墨迹宽 95 = 15 字符）；序号 7 的跨页断言「序号 6 也缺前缀」为误判 —— 见
     .agents/state/evidence/序号6-报告编号前缀核定.txt。 */
  line-height: 16px;
}

.report-page__body {
  display: flex;
  flex-direction: column;
}

/* 区块：design padding [12,16,0,16] */
.block {
  padding: 12px 16px 0 16px;
  box-sizing: border-box;
}

.card {
  background: $color-bg-card;
  border-radius: 18px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  /* design c13761bd 等：stroke{align:center,thickness:0.8} → Figma 中心描边不占布局，用 box-shadow 表达
     （用 border 会把内容宽从 358 挤成 356） */
  box-shadow: 0 0 0 0.8px $color-border-chip;
}

/* design 4e855266：结论封面卡带 drop_shadow(0,6,20,rgba(15,23,42,0.06))，无描边 */
.card--cover {
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

/* design 377c9abc：综合分块与状态四格之间的 1px 分隔线（间距 16） */
.card__divider {
  margin-top: 16px;
  height: 1px;
  width: 100%;
  background: $color-border-chip;
}

/* design 86cbfb7a 等：卡片标题前的 5×14 r2 色条（关键指标卡 8cbfb7a / 各卡同族） */
.card__bar {
  width: 5px;
  height: 14px;
  border-radius: 2px;
  background: $color-primary;
  margin-right: 8px;
  flex-shrink: 0;
}

.card__title-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
  min-height: 20px; /* design：标题行高 20（15px Bold 行框） */
}

.card__mark {
  width: 18px;
  height: 24px; /* design 89db7d78：remixicon 16px 行框 = 24 */
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 5px;
  flex-shrink: 0;
}

.card__title {
  font-size: 15px;
  font-weight: 700; /* design fontFamily=SourceHanSans-Bold */
  color: $color-text-primary;
  line-height: 20px;
}

/* design 625f2248：结论封面卡的标题是 12px Medium #64748B（与其余卡片的 15px Bold 不同） */
.card__title--cover {
  font-size: 12px;
  font-weight: 500;
  color: $color-text-muted;
  line-height: 18px;
}

.card__spacer {
  flex: 1;
}

.card__sub {
  font-size: 11px;
  color: $color-text-placeholder;
}

/* 综合分块（design 6f989737） */
.score-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding-top: 16px;
  width: 100%;
}

.score {
  font-size: 40px;
  font-weight: 900; /* design f717621c fontFamily=SourceHanSans-Black */
  line-height: 44px; /* design：综合分行框 44（PNG 实测 ink 172..203） */
  color: $color-text-primary;
}

.score--success {
  color: $color-success;
}

.score--danger {
  color: $color-danger;
}

.score--warning {
  color: $color-warning-text;
}

.score__meta {
  margin-left: 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.score__meta-text {
  font-size: 12px;
  color: $color-text-placeholder;
  line-height: 17px;
}

.result-chip {
  height: 28px;
  border-radius: 14px;
  padding: 0 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
  background: $color-success-weak-2;
}

.result-chip--danger {
  background: $color-danger-weak;
}

.result-chip--warning {
  background: $color-warning-weak-2;
}

.result-chip--muted {
  background: $color-bg-subtle;
}

.result-chip__text {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 700; /* design c2e5f1be fontFamily=SourceHanSans-Bold */
  color: $color-success-text;
}

.result-chip--danger .result-chip__text {
  color: $color-danger;
}

.result-chip--warning .result-chip__text {
  color: $color-warning-text-2;
}

.result-chip--muted .result-chip__text {
  color: $color-text-muted;
}

/* 状态四格（design 950cbd49） */
.status-grid {
  display: flex;
  flex-direction: row;
  padding-top: 16px;
  width: 100%;
}

.status-cell {
  width: 90px;
  display: flex;
  flex-direction: column;
}

.status-cell__value {
  font-size: 15px;
  font-weight: 700; /* design 173538c1 fontFamily=SourceHanSans-Bold */
  color: $color-text-primary;
  line-height: 20px;
}

.status-cell__value--success {
  color: $color-success;
}

.status-cell__value--danger {
  color: $color-danger;
}

.status-cell__label {
  font-size: 10px;
  color: $color-text-placeholder;
  line-height: 15px;
}

/* 结论措辞盒（design bc2f3eaa） */
.verdict-box {
  margin-top: 16px;
  padding: 12px;
  border-radius: 12px;
  background: $color-bg-page;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  box-sizing: border-box;
}

.verdict-box__text {
  flex: 1;
  margin-left: 8px;
  font-size: 12px;
  color: $color-text-secondary;
  line-height: 19px;
}

/* 信息清单（design 95371b7c） */
.info-list {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  width: 100%;
}

.info-row {
  display: flex;
  flex-direction: row;
  padding: 5px 0;
  width: 100%;
}

.info-row__label {
  width: 64px;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 16px;
}

.info-row__value {
  flex: 1;
  font-size: 11.5px;
  color: $color-text-tertiary;
  line-height: 16px;
}

/* 关键指标卡（design c13761bd：2 列 174 宽，间距 10） */
.metrics {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: stretch;
  row-gap: 10px; /* design：指标行距 95 = 子卡 85 + 10（末行不留间距 → 卡高 351） */
  padding-top: 16px;
  width: 100%;
}

.metric {
  width: 174px;
  padding: 12px;
  border-radius: 12px;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.metric__label {
  font-size: 10.5px;
  color: $color-text-placeholder;
  line-height: 15px;
}

.metric__value-row {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  padding-top: 4px;
  height: 28px; /* design：值行 = padding-top 4 + 值行框 24（子卡高 85 = 12+15+28+18+12） */
  box-sizing: border-box;
}

.metric__value {
  font-size: 19px;
  font-weight: 800; /* design 27855b9c fontFamily=SourceHanSans-ExtraBold */
  color: $color-text-primary;
  line-height: 24px;
}

.metric__unit {
  margin-left: 4px;
  font-size: 11px;
  color: $color-text-muted;
}

.metric__sub {
  padding-top: 4px;
  font-size: 10px;
  line-height: 14px;
}

.metric__sub--success {
  color: $color-success-text;
}

.metric__sub--muted {
  color: $color-text-muted;
}

/* 维度总览（design 6cf10c3b / 33713878 / 7a5c9636） */
.radar {
  height: 258px;
  padding-top: 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

/* 雷达画布：244×250（设计稿 6cf10c3b 内的坐标原点），图与轴标签按设计坐标绝对定位 */
.radar__canvas {
  position: relative;
  width: 244px;
  height: 250px;
}

.radar__img {
  position: absolute;
  left: 34px;
  top: 31px;
  width: 176px;
  height: 176px;
}

.radar__label {
  position: absolute;
  font-size: 11px;
  line-height: 1.31;
  color: $color-text-muted;
}

.radar__label--0 {
  left: 114px;
  top: 16px;
}

.radar__label--1 {
  left: 204px;
  top: 68px;
}

.radar__label--2 {
  left: 198px;
  top: 168px;
}

.radar__label--3 {
  left: 114px;
  top: 223px;
}

.radar__label--4 {
  left: 24px;
  top: 168px;
}

.radar__label--5 {
  left: 24px;
  top: 68px;
}

.dims {
  display: flex;
  flex-direction: column;
  padding-top: 12px;
  width: 100%;
}

.dim {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.dim--gap {
  margin-top: 12px;
}

.dim__name {
  width: 110px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.dim__dot {
  width: 9px;
  height: 8px;
  border-radius: 4px;
}

.dim__text {
  margin-left: 6px;
  font-size: 12px;
  line-height: 16px; /* design：均分行高 16（PNG 实测行距 28 = 16 + 12） */
  color: $color-text-secondary-2;
}

.dim__bar {
  width: 200px;
  height: 6px;
  border-radius: 3px;
  background: $color-border;
  overflow: hidden;
  margin-left: 8px;
}

.dim__fill {
  height: 6px;
  border-radius: 3px;
}

.dim__score {
  width: 32px; /* design 33713878「分」= 32 宽、右对齐（名 110 + 条 200 + 分 32 + 间距 16 = 358） */
  text-align: right;
  margin-left: 8px;
  font-size: 12px;
  line-height: 16px;
  color: $color-text-primary;
}

.legend {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding-top: 16px;
  width: 100%;
}

.legend__item {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.legend__item--gap {
  margin-left: 16px;
}

.legend__dot {
  width: 9px;
  height: 8px;
  border-radius: 4px;
}

.legend__text {
  margin-left: 5px;
  font-size: 10.5px;
  color: $color-text-placeholder;
}

/* 全维度明细（design 7806d174） */
.detail-summary {
  padding-top: 8px;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 24px;
}

.group {
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  width: 100%;
}

/* design：分组之间（以及最后一个分组与权重说明盒之间）有 16 高间隔条
   （design.tree.json 的 spacer 8a882495 = 357×16；PNG 实测组标题 ink 间距 A→B = 437 与 421+16 自洽） */
.group + .group {
  margin-top: 16px;
}

.group__head {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.group__bar {
  width: 5px;
  height: 14px;
  border-radius: 2px;
}

.group__title {
  margin-left: 8px;
  font-size: 13px;
  font-weight: 700; /* design 772db2b3 fontFamily=SourceHanSans-Bold */
  line-height: 18px; /* design：组标题行高 18（PNG 实测色条中心 1514、行高 18） */
  color: $color-text-primary;
}

/* design 分组A：组标题行 → 列表 间隔 14（PNG：标题 ink → 首行 ink = 32 / 92 条数据行距 43 = 29+14） */
.group__head + .item {
  margin-top: 14px;
}

.group__meta {
  font-size: 11px;
  color: $color-text-placeholder;
}

/* design 指纹提示（分组D，id=239a99e9）：位于两条 14 间隔条之间（标题行 →14→ 提示盒 →14→ 列表），
   行框 16（design 文本图层 height=48 = 3 行 × 16） */
.group__head + .group__note {
  margin-top: 14px;
}

.group__note {
  margin-top: 14px;
  padding: 12px;
  border-radius: 12px;
  background: $color-violet-weak;
  font-size: 10.5px;
  color: $color-violet;
  line-height: 16px;
  box-sizing: border-box;
}

.group__note + .item {
  margin-top: 14px;
}

.item {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
}

.item--gap {
  margin-top: 14px; /* design：明细行距 43 = 行高 29 + 间隔 14（PNG x=200 条形实测 1549→1592） */
}

.item__name {
  width: 150px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.item__label {
  font-size: 12px;
  font-weight: 500; /* design 64a9c7b4 fontFamily=SourceHanSans-Medium */
  color: $color-text-secondary-2;
  line-height: 16px;
}

.item__metric {
  font-size: 10px;
  color: $color-text-placeholder;
  line-height: 13px;
}

.item__bar {
  width: 162px;
  flex-shrink: 0;
  height: 6px;
  border-radius: 3px;
  background: $color-border;
  overflow: hidden;
  margin-left: 8px;
}

.item__fill {
  height: 6px;
  border-radius: 3px;
}

/* 未计分行的占位条：设计稿写死 163 宽（150+8+163+8+62 = 391 > 卡片内宽 358，设计自身不自洽）
   → 这里让占位条自适应剩余宽度，保证不横向溢出（已记台账序号 6 备注） */
.item__holder {
  flex: 1;
  min-width: 0;
  height: 6px;
  border-radius: 3px;
  background: $color-bg-subtle;
  margin-left: 8px;
}

.item__score {
  width: 30px;
  flex-shrink: 0;
  margin-left: 8px;
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
}

.item__score-text {
  font-size: 12px;
  font-weight: 700; /* design：明细分值与「分」列同为 Bold */
  color: $color-text-primary;
}

.item__pill {
  flex-shrink: 0;
  margin-left: 8px;
  min-width: 62px;
  height: 18px;
  border-radius: 9px;
  padding: 0 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  background: $color-bg-subtle;
}

.item__pill--evidence .item__pill-text {
  color: $color-text-muted;
}

.item__pill--not_declared,
.item__pill--not_measurable {
  background: $color-warning-weak-2;
}

.item__pill--not_declared .item__pill-text,
.item__pill--not_measurable .item__pill-text {
  color: $color-warning-text-3;
}

.item__pill-text {
  font-size: 10px;
  color: $color-text-muted;
}

.note-box {
  margin-top: 16px; /* design：权重说明盒前的 spacer 8a882495 = 357×16 */
  padding: 12px;
  border-radius: 12px;
  background: $color-bg-page;
  font-size: 10.5px;
  color: $color-text-muted;
  line-height: 16px; /* design 104230be 文本图层 height=48 = 3 行 × 16 */
  box-sizing: border-box;
}

/* 风险发现（design 658a45d1） */
/* design：标题行 → 首条发现 间距 16（PNG：标题行 4421..4441 → 发现1 4457） */
.card__title-row + .finding {
  margin-top: 16px;
}

.finding {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  padding: 12px;
  border-radius: 12px;
  box-sizing: border-box;
  width: 100%;
}

.finding--gap {
  margin-top: 10px;
}

.finding--success {
  background: $color-wechat-weak;
}

.finding--warning {
  background: $color-warning-weak-2;
}

.finding--info {
  background: $color-bg-subtle;
}

.finding__text {
  flex: 1;
  margin-left: 8px;
  display: flex;
  flex-direction: column;
}

.finding__title {
  font-size: 12px;
  font-weight: 700; /* design：发现标题 Bold */
  color: $color-text-primary;
  line-height: 18px;
}

.finding__body {
  font-size: 11px;
  color: $color-text-muted;
  line-height: 17px;
}

/* 原始证据（design 9844215a） */
.evidence-row {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  width: 100%;
}

.evidence-row--first {
  padding-top: 16px;
}

.evidence-row--gap {
  padding-top: 10px;
}

.evidence-row__key {
  width: 88px;
  font-size: 11px;
  color: $color-text-primary;
  line-height: 16px;
}

.evidence-row__value {
  flex: 1;
  font-size: 11px;
  color: $color-text-muted;
  line-height: 16px;
}

/* 免责声明（design 30918987） */
.disclaimer {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  width: 100%;
}

.disclaimer__text {
  flex: 1;
  margin-left: 8px;
  display: flex;
  flex-direction: column;
}

.disclaimer__title {
  font-size: 12px;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 18px;
}

.disclaimer__body {
  font-size: 11px;
  color: $color-text-muted;
  line-height: 17px;
}

/* 底部操作条（design e096bd63） */
.action {
  padding: 16px 16px 24px 16px;
  box-sizing: border-box;
}

.action__bar {
  background: $color-bg-card;
  border-radius: 18px;
  padding: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.action__ghost {
  width: 126px;
  height: 48px;
  border-radius: 12px;
  background: $color-bg-card;
  /* design 导出PDF按钮 stroke{align:center,thickness:0.8,#CBD5E1} → box-shadow（border 会占布局） */
  box-shadow: 0 0 0 0.8px $color-border-strong;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.action__ghost-text {
  margin-left: 6px;
  font-size: 14px;
  color: $color-text-secondary-2;
}

.action__primary {
  flex: 1;
  height: 48px;
  margin-left: 10px;
  border-radius: 12px;
  background: $color-primary;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.action__primary-text {
  margin-left: 6px;
  font-size: 15px;
  font-weight: 700; /* design：填写报价按钮文字 Bold */
  color: $color-bg-card;
}

/* 图标：设计为矢量图标，PRD 08 禁 emoji → CSS 形状占位（同序号 1/2/3/5 做法） */
.glyph {
  width: 16px;
  height: 16px;
  box-sizing: border-box;
}

.glyph--back {
  width: 10px;
  height: 10px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
}

.glyph--doc {
  width: 14px;
  height: 16px;
  border: 1.5px solid $color-primary;
  border-radius: 2px;
}

.glyph--check {
  width: 12px;
  height: 12px;
  border-left: 2px solid $color-success;
  border-bottom: 2px solid $color-success;
  transform: rotate(-45deg);
}

.glyph--check-strong {
  /* design 5c0c5ff2：remixicon 18px 行框 = 20×27（形状画在 ::before） */
  width: 20px;
  height: 27px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.glyph--check-strong::before {
  content: '';
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: $color-success;
}

.glyph--download {
  width: 14px;
  height: 14px;
  border-bottom: 2px solid $color-text-muted;
  border-left: 2px solid $color-text-muted;
  border-right: 2px solid $color-text-muted;
  border-radius: 0 0 2px 2px;
}

.glyph--edit {
  width: 14px;
  height: 14px;
  border: 2px solid $color-bg-card;
  border-radius: 2px;
}

.glyph--info {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid $color-text-placeholder;
}

.glyph--finding-success {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: $color-success;
  margin-top: 3px;
}

.glyph--finding-warning {
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 11px solid $color-warning-text;
  margin-top: 3px;
}

.glyph--finding-info {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid $color-text-muted;
  margin-top: 3px;
}
</style>
