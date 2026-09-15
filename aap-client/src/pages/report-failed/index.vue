<template>
  <view class="rf-page">
    <!-- 顶部导航：design id=5cd2c5ba（白底 · padding 48/16/12/16 · 返回 26 宽 · 报告编号 11px #94A3B8） -->
    <view class="rf-page__topbar">
      <view class="rf-page__icon-btn" data-testid="back-btn" @tap="goBack">
        <view class="glyph glyph--back" aria-hidden="true" />
      </view>
      <text class="rf-page__title" data-testid="title">{{ PAGE_TITLE }}</text>
      <view class="rf-page__spacer" />
      <text class="rf-page__no" data-testid="report-no">{{ REPORT_NO_PREFIX }}{{ model.reportNo }}</text>
    </view>

    <view class="rf-page__body">
      <!-- 未通过封面卡：design id=07b82bea（白 r18 padding 20） -->
      <view class="block">
        <view class="card">
          <view class="card__title-row">
            <text class="card__label" data-testid="verdict-title">{{ VERDICT_TITLE }}</text>
            <view class="card__spacer" />
            <text class="card__sub" data-testid="channel">{{ model.channel }}</text>
          </view>

          <!-- 综合分块：design id=9cb5cda0（38px 综合分 + 分数说明 + 结论标签 #FEF2F2 r14 h28） -->
          <view class="score-row">
            <text class="score" data-testid="score">{{ model.scoreText }}</text>
            <view class="score__meta">
              <text class="score__meta-text" data-testid="score-label">{{ SCORE_LABEL }}</text>
              <text class="score__meta-text" data-testid="score-max">{{ SCORE_MAX_LABEL }}</text>
            </view>
            <view class="card__spacer" />
            <view class="result-chip" data-testid="result-chip">
              <view class="glyph glyph--chip" aria-hidden="true" />
              <text class="result-chip__text">{{ model.resultLabel }}</text>
            </view>
          </view>

          <!-- 一票否决条：design id=c93a930a（#FEF2F2 r12 padding 12 · 文案 12px #B91C1C） -->
          <view v-if="model.vetoVisible" class="veto-row">
            <view class="veto-box">
              <view class="glyph glyph--alert" aria-hidden="true" />
              <text class="veto-box__text" data-testid="veto-text">{{ model.vetoText }}</text>
            </view>
          </view>

          <!-- 结论措辞：design id=d5ad8ecf（图标 + 12px #475569） -->
          <view class="verdict-row">
            <view class="glyph glyph--red-dot" aria-hidden="true" />
            <text class="verdict-row__text" data-testid="verdict-text">{{ model.verdictText }}</text>
          </view>
        </view>
      </view>

      <!-- 分项评分总览卡：design id=35a1df87（白 r18 padding 20 · 1px #EEF2F7） -->
      <view class="block">
        <view class="card card--outlined">
          <text class="card__title" data-testid="dim-title">{{ DIM_TITLE }}</text>

          <view
            v-for="(dim, index) in model.dims"
            :key="dim.code || index"
            class="dim-row"
            :class="{ 'dim-row--first': index === 0 }"
            data-testid="dim-row"
          >
            <text class="dim__label" data-testid="dim-label">{{ dim.label }}</text>
            <view class="dim__track">
              <view
                class="dim__fill"
                data-testid="dim-fill"
                :style="{ width: `${dim.barPercent}%`, background: dim.color }"
              />
            </view>
            <view class="dim__score-box">
              <text class="dim__score" :style="{ color: dim.color }" data-testid="dim-score">{{ dim.scoreText }}</text>
            </view>
          </view>

          <view class="weight-row">
            <view class="weight-box">
              <text class="weight-box__text" data-testid="weight-note">{{ model.weightNote }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- D2 详情卡：design id=09ddc4ca（白 r18 padding 20 · 1px #FECACA） -->
      <view v-if="model.detail.visible" class="block">
        <view class="card card--danger" data-testid="detail-card">
          <view class="detail__head">
            <text class="detail__title" data-testid="detail-title">{{ model.detail.title }}</text>
            <view class="card__spacer" />
            <text class="detail__score" data-testid="detail-score">{{ model.detail.scoreText }}</text>
          </view>
          <view
            v-for="(line, index) in model.detail.lines"
            :key="index"
            class="detail__line-row"
            :class="{ 'detail__line-row--first': index === 0 }"
          >
            <text class="detail__line" data-testid="detail-line">{{ line }}</text>
          </view>
        </view>
      </view>

      <!-- 免责声明卡：design id=1b0391c3（白 r18 padding 16/20 · 1px #EEF2F7） -->
      <view class="block">
        <view class="card card--outlined card--disclaimer">
          <view class="glyph glyph--info" aria-hidden="true" />
          <view class="disclaimer__textbox">
            <text class="disclaimer__title" data-testid="disclaimer-title">{{ model.disclaimerTitle }}</text>
            <text class="disclaimer__text" data-testid="disclaimer-text">{{ model.disclaimerText }}</text>
          </view>
        </view>
      </view>

      <!-- 底部操作：design id=e60b6a5c（白底 padding 12/16/24/16 · 非圆角、随文档流） -->
      <view class="action">
        <view class="action__inner">
          <view class="action__ghost" data-testid="export-btn" @tap="onExport">
            <view class="glyph glyph--download" aria-hidden="true" />
            <text class="action__ghost-text">{{ EXPORT_TEXT }}</text>
          </view>
          <view class="action__primary" data-testid="resubmit-btn" @tap="onResubmit">
            <text class="action__primary-text">{{ RESUBMIT_TEXT }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 页面 7【检测验真】检测未通过报告 2（序号 7 / page-7-2）
 * 设计真源：.calicat/raw/pages/page-7-2/design.tree.json（430 宽）
 * 接口：18-API Report Tag → GET /api/v1/reports/{reportId}、GET /api/v1/reports/{reportId}/export；
 *       Detection Tag → POST /api/v1/detection-jobs（重测）
 *   ⚠️ 18-API 只列路径未列方法 → 方法均为 REST 语义推断，已记台账序号 7 待确认。
 * 交互分类（台账序号 7 行）：
 *   返回 = navigation(navigateBack 1)
 *   导出 PDF = api(GET /reports/{reportId}/export)；小程序内不做文件落地，成功即提示
 *   重新提交检测 = api(POST /detection-jobs，09-PRD §5 重测（人工点击）) → 成功后跳检测进行中页带 jobId
 *   评分 / 分项 / 详情 / 免责 = client-only（渲染态，无点击）
 * 入参：reportId 取页面 query（?reportId=），无 query 时退 storage 键 aap_report_id；
 *   credentialId 优先取报告体 credential_id，其次 storage 键 aap_credential_id（与提交页同一键）。
 */
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/api/http'
import { reportApi } from '@/api/report'
import { detectionApi } from '@/api/detection'
import {
  CREDENTIAL_ID_KEY,
  DETECTING_PAGE,
  EXPORT_READY_TOAST,
  EXPORT_TEXT,
  LOAD_FAIL_TOAST,
  MISSING_CREDENTIAL_TOAST,
  MISSING_REPORT_TOAST,
  PAGE_TITLE,
  REPORT_ID_KEY,
  REPORT_NO_PREFIX,
  RESUBMIT_READY_TOAST,
  RESUBMIT_TEXT,
  SCORE_LABEL,
  SCORE_MAX_LABEL,
  VERDICT_TITLE,
  DIM_TITLE,
  buildReportFailedModel,
  type ReportFailedRaw
} from '@/utils/report-failed-model'

const report = ref<ReportFailedRaw | null>(null)

const model = computed(() => buildReportFailedModel(report.value))

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

/** 页面入参：优先页面栈 query，其次 storage（单测/无 query 场景） */
function resolveQueryId(key: string, storageKey: string): string {
  try {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
    const current = pages[pages.length - 1] as
      | { options?: Record<string, string>; $page?: { options?: Record<string, string> } }
      | undefined
    const query = current?.options ?? current?.$page?.options ?? {}
    const fromQuery = query[key] ? String(query[key]) : ''
    if (fromQuery) {
      try {
        uni.setStorageSync(storageKey, fromQuery)
      } catch {
        /* storage 写入失败不影响本次展示 */
      }
      return fromQuery
    }
  } catch {
    /* 无页面栈时忽略，走 storage 兜底 */
  }
  try {
    return String(uni.getStorageSync(storageKey) || '')
  } catch {
    return ''
  }
}

let reportId = ''

function readStorage(key: string): string {
  try {
    return String(uni.getStorageSync(key) || '')
  } catch {
    return ''
  }
}

async function load() {
  try {
    report.value = (await reportApi.detail<ReportFailedRaw>(reportId)) ?? null
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

/**
 * 重新提交检测：09-PRD §5 重测（人工点击）→ POST /detection-jobs（请求体只带 credential_id）。
 * 成功后跳检测进行中页并带 jobId（与提交接入凭证页同一跳转口径）；失败（如 E-1301 互斥 / 日配额）只提示服务端文案。
 */
async function onResubmit() {
  const credentialId = report.value?.credential_id ? String(report.value.credential_id) : readStorage(CREDENTIAL_ID_KEY)
  if (!credentialId) {
    toast(MISSING_CREDENTIAL_TOAST)
    return
  }
  try {
    const res = await detectionApi.create({ credential_id: credentialId })
    const jobId = res?.job_id ?? res?.jobId ?? res?.id ?? ''
    if (jobId) {
      try {
        uni.setStorageSync('aap_detection_job_id', String(jobId))
      } catch {
        /* storage 写入失败不阻断跳转 */
      }
    }
    toast(RESUBMIT_READY_TOAST)
    uni.navigateTo({
      url: jobId ? `${DETECTING_PAGE}?jobId=${encodeURIComponent(String(jobId))}` : DETECTING_PAGE
    })
  } catch (err) {
    toast(err instanceof ApiError ? err.message : LOAD_FAIL_TOAST)
  }
}

onMounted(async () => {
  reportId = resolveQueryId('reportId', REPORT_ID_KEY)
  if (!reportId) {
    toast(MISSING_REPORT_TOAST)
    return
  }
  await load()
})
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.rf-page {
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部导航（design 5cd2c5ba） */
.rf-page__topbar {
  background: $color-bg-card;
  padding: calc(48px + var(--status-bar-height, 0px)) 16px 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.rf-page__icon-btn {
  /* 设计稿返回图标段落 26×28.8（24px 字号 × lineHeight 1.2）→ 顶栏总高 48+29+12=89 */
  width: 26px;
  height: 29px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rf-page__title {
  margin-left: 12px;
  font-size: 17px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
}

.rf-page__spacer {
  flex: 1;
}

.rf-page__no {
  font-size: 11px;
  color: $color-text-placeholder;
}

.rf-page__body {
  display: flex;
  flex-direction: column;
}

/* 区块：design padding 12/16/0/16 */
.block {
  padding: 12px 16px 0 16px;
  box-sizing: border-box;
}

.card {
  background: $color-bg-card;
  border-radius: $radius-xl;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.card--outlined {
  border: 1px solid $color-border-chip;
}

.card--danger {
  border: 1px solid $color-danger-border;
}

.card__title-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.card__spacer {
  flex: 1;
}

.card__label {
  font-size: 12px;
  font-weight: 500;
  color: $color-text-muted;
  line-height: 1.2;
}

.card__sub {
  font-size: 12px;
  color: $color-text-placeholder;
  line-height: 1.2;
}

.card__title {
  font-size: 15px;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 22px;
}

/* 综合分块（design 9cb5cda0） */
.score-row {
  margin-top: 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.score {
  font-size: 38px;
  font-weight: 800;
  color: $color-danger-strong;
  line-height: 1.2;
}

.score__meta {
  margin-left: 12px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.score__meta-text {
  font-size: 12px;
  color: $color-text-placeholder;
  line-height: 1.2;
}

/* 结论标签（design 16f0f3cf：h28 r14 #FEF2F2） */
.result-chip {
  height: 28px;
  padding: 0 12px;
  border-radius: 14px;
  background: $color-danger-weak;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.result-chip__text {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 600;
  color: $color-danger-text;
  line-height: 1.2;
}

/* 一票否决条（design c93a930a） */
.veto-row {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
}

.veto-box {
  padding: 12px;
  border-radius: 12px;
  background: $color-danger-weak;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  box-sizing: border-box;
}

.veto-box__text {
  margin-left: 8px;
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: $color-danger-text;
  line-height: 1.5;
}

/* 结论措辞（design d5ad8ecf） */
.verdict-row {
  margin-top: 12px;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  box-sizing: border-box;
}

.verdict-row__text {
  margin-left: 8px;
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: $color-text-secondary;
  line-height: 1.5;
}

/* 分项总览 8 行（design 8d9285cb 等；首行 padding-top 16、其余 12） */
.dim-row {
  margin-top: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.dim-row--first {
  margin-top: 16px;
}

.dim__label {
  width: 101px;
  flex-shrink: 0;
  font-size: 12px;
  color: $color-text-tertiary;
  line-height: 1.2;
}

.dim__track {
  flex: 1;
  min-width: 0;
  height: 8px;
  border-radius: 4px;
  background: $color-border;
  overflow: hidden;
}

/* D8 分值为 0 时设计稿仍画 4px 红色残段（最小可视宽度），按设计还原 */
.dim__fill {
  height: 8px;
  border-radius: 4px;
  min-width: 4px;
}

.dim__score-box {
  padding-left: 10px;
  flex-shrink: 0;
}

.dim__score {
  /* uni-app H5 里 <text> 默认是 inline，父级 UNI-VIEW 继承 16px 字号 → 行盒被撑到 24px（设计行高 14.4） */
  display: block;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

/* 权重说明盒（design def3b414） */
.weight-row {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
}

.weight-box {
  padding: 12px;
  border-radius: 12px;
  background: $color-bg-page;
  box-sizing: border-box;
}

.weight-box__text {
  /* uni-app H5 把 <text> 渲染成 inline 的 UNI-TEXT：不设 block 时行盒按父级 line-height 撑高，
     实测文本块 40px（设计 36px）、说明盒 72px（设计 60px）→ 显示为块级后与设计一致 */
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 18px;
}

/* D2 详情卡（design b2bba46b / 四行解释） */
.detail__head {
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.detail__title {
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 1.2;
}

.detail__score {
  font-size: 14px;
  font-weight: 700;
  color: $color-danger-strong;
  line-height: 1.2;
}

.detail__line-row {
  margin-top: 6px;
}

.detail__line-row--first {
  margin-top: 8px;
}

.detail__line {
  /* 同上：<text> 在非 flex 容器里是 inline → 行盒被父级撑高（实测行高 24 vs 设计 20） */
  display: block;
  font-size: 12px;
  color: $color-text-muted;
  line-height: 20px;
}

/* 免责声明卡（design 1b0391c3：padding 16/20） */
.card--disclaimer {
  padding: 16px 20px;
  flex-direction: row;
  align-items: flex-start;
}

.disclaimer__textbox {
  margin-left: 12px;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.disclaimer__title {
  font-size: 12px;
  font-weight: 500;
  color: $color-text-muted;
  line-height: 18px;
}

.disclaimer__text {
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 18px;
}

/* 底部操作（design e60b6a5c：白底 padding 12/16/24/16，随文档流） */
.action {
  margin-top: 16px;
  background: $color-bg-card;
  box-sizing: border-box;
}

.action__inner {
  padding: 12px 16px 24px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.action__ghost {
  width: 193px;
  height: 44px;
  border-radius: 12px;
  background: $color-bg-card;
  border: 1px solid $color-border-strong;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.action__ghost-text {
  margin-left: 6px;
  font-size: 14px;
  font-weight: 500;
  color: $color-text-tertiary;
}

.action__primary {
  flex: 1;
  min-width: 0;
  height: 44px;
  margin-left: 12px;
  border-radius: 12px;
  background: $color-primary;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.action__primary-text {
  font-size: 14px;
  font-weight: 600;
  color: $color-bg-card;
}

/* 图标：设计为矢量图标，PRD 08 禁 emoji → CSS 形状占位（同序号 1/2/3/5/6 做法） */
.glyph {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  box-sizing: border-box;
}

.glyph--back {
  width: 10px;
  height: 10px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
}

.glyph--chip {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: $color-danger-strong;
}

.glyph--alert {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: $color-danger-strong;
}

.glyph--red-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid $color-danger-strong;
  margin-top: 2px;
}

.glyph--info {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid $color-text-placeholder;
}

.glyph--download {
  width: 14px;
  height: 14px;
  border-bottom: 2px solid $color-text-muted;
  border-left: 2px solid $color-text-muted;
  border-right: 2px solid $color-text-muted;
  border-radius: 0 0 2px 2px;
}
</style>
