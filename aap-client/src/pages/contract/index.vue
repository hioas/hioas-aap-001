<template>
  <!-- 序号 15【合同与通知】合同签署 2（page-15-2）· /pages/contract/index -->
  <view class="ct">
    <!-- 顶部导航（48 + 图标行盒 36 + 12 = 96） -->
    <view class="ct__nav">
      <view class="nav__back" data-testid="back" @tap="onBack">
        <view class="icon-line icon-line--24"><view class="ic-back" /></view>
      </view>
      <text class="nav__title" data-testid="nav-title">{{ PAGE_TITLE }}</text>
      <view class="nav__spacer" />
      <text class="nav__no" data-testid="nav-no">{{ view.navNo }}</text>
    </view>

    <!-- 内容区（padding 12/16/0/16 · 卡间距 12） -->
    <view class="ct__body">
      <!-- 1) 合同状态卡（20 + max(46, 42) + 20 = 86） -->
      <view class="card card--status" data-testid="card-status">
        <view class="status__icon"><view class="ic-contract" /></view>
        <view class="status__content">
          <view class="status__row">
            <text class="status__title" data-testid="status-title">{{ view.title }}</text>
            <view v-if="view.hasStatus" class="status-chip" :style="{ backgroundColor: view.status.bg }">
              <text class="status-chip__text" :style="{ color: view.status.text }" data-testid="status-chip">
                {{ view.status.label }}
              </text>
            </view>
          </view>
          <text v-if="view.deadline" class="status__deadline" data-testid="deadline">{{ view.deadline }}</text>
        </view>
      </view>

      <!-- 2) 电子签提示卡（12 + 图标行盒 27 + 12 = 51） -->
      <view class="card card--tip" data-testid="tip-card">
        <view class="icon-line icon-line--18"><view class="ic-shield" /></view>
        <text class="tip__text" data-testid="tip">{{ TIP_TEXT }}</text>
      </view>

      <!-- 3) 合同基本信息（20 + 20 + 16 + 4×18 + 3×12 + 20 = 184） -->
      <view class="card card--basic" data-testid="card-basic">
        <text class="card__title" data-testid="card-basic-title">{{ CARD_BASIC }}</text>
        <view v-for="(row, i) in view.basicRows" :key="row.key" class="crow" :class="`crow--${i}`">
          <text class="crow__label">{{ row.label }}</text>
          <text class="crow__value">{{ row.value }}</text>
        </view>
      </view>

      <!-- 4) 费用与分成（20 + 20 + 16 + 3×18 + 2×12 + 20 = 154 · 值右对齐） -->
      <view class="card card--fee" data-testid="card-fee">
        <text class="card__title" data-testid="card-fee-title">{{ CARD_FEE }}</text>
        <view v-for="(row, i) in view.feeRows" :key="row.key" class="crow crow--fee" :class="`crow--${i}`">
          <text class="crow__label crow__label--fee">{{ row.label }}</text>
          <view class="crow__spacer" />
          <text class="crow__value crow__value--bold">{{ row.value }}</text>
        </view>
      </view>

      <!-- 5) 关键条款（20 + 20 + 8 + 20 + 3×(6 + 20) + 20 = 166） -->
      <view class="card card--terms" data-testid="card-terms">
        <text class="card__title" data-testid="card-terms-title">{{ CARD_TERMS }}</text>
        <view v-for="(c, i) in view.clauses" :key="`c${i}`" class="clause" :class="`clause--${i}`">
          <text class="clause__text">{{ c }}</text>
        </view>
      </view>

      <!-- 6) 签署信息（20 + 20 + 16 + 3×18 + 2×12 + 20 = 154） -->
      <view class="card card--sign" data-testid="card-sign">
        <text class="card__title" data-testid="card-sign-title">{{ CARD_SIGN }}</text>
        <view v-for="(row, i) in view.signRows" :key="row.key" class="crow" :class="`crow--${i}`">
          <text class="crow__label">{{ row.label }}</text>
          <text class="crow__value">{{ row.value }}</text>
        </view>
      </view>

      <!-- 7) 签署记录（20 + 20 + 16 + 34 + 12 + 34 + 20 = 156） -->
      <view class="card card--records" data-testid="card-records">
        <text class="card__title" data-testid="card-records-title">{{ CARD_RECORDS }}</text>
        <view v-for="(r, i) in view.records" :key="r.key" class="record" :class="`record--${i}`">
          <view class="record__dot" :data-tone="r.tone" :style="{ backgroundColor: r.dot }" />
          <view class="record__body">
            <text class="record__title">{{ r.title }}</text>
            <text v-if="r.time" class="record__time">{{ r.time }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部操作条（16 + 12 + 48 + 24 = 100 → 栏高 84） -->
    <view class="ct__bar-wrap">
      <view class="ct__bar">
        <view class="btn btn--ghost" data-testid="btn-pdf" @tap="onPdf">
          <view class="icon-line icon-line--18"><view class="ic-download" /></view>
          <text class="btn__text">{{ BTN_PDF }}</text>
        </view>
        <view class="btn btn--primary" data-testid="btn-sign" @tap="onSign">
          <view class="icon-line icon-line--18 icon-line--light"><view class="ic-send" /></view>
          <text class="btn__text btn__text--light">{{ BTN_SIGN }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 15 · /pages/contract/index（page-15-2：合同签署 2）
 *
 * 设计与缺口真源：src/utils/contract-model.ts 顶部注释 + .calicat/raw/pages/page-15-2/design.tree.json
 * 页面入参：contractId 优先页面栈 query（?contractId=），其次 storage 键 aap_contract_id。
 * 取数：GET /contracts/{contractId}（18-API「Contract」Tag 的真实路径，前缀 /api/v1；方法为 REST 推断 missing-prd）。
 *
 * ⚠️ 设计帧「电子签章 / 短信验证码签署」与 10-PRD §4.2 / 17-spec R-41「合同线下」冲突 → 按设计稿实现，冲突记台账等拍板。
 */
import { onMounted, ref } from 'vue'
import { contractApi } from '@/api/contract'
import {
  BTN_PDF,
  BTN_SIGN,
  CARD_BASIC,
  CARD_FEE,
  CARD_RECORDS,
  CARD_SIGN,
  CARD_TERMS,
  CONFIRM_SIGN_CONTENT,
  CONFIRM_SIGN_TITLE,
  CONTRACT_ID_KEY,
  PAGE_TITLE,
  TIP_TEXT,
  TOAST_FILE_FAIL,
  TOAST_LOAD_FAIL,
  TOAST_NO_CONTRACT,
  TOAST_NO_FILE,
  TOAST_SIGNED,
  buildContractView,
  type ContractRaw,
  type ContractView
} from '@/utils/contract-model'

const view = ref<ContractView>(buildContractView(null))

function errorText(e: unknown): string {
  const message = (e as { message?: string } | undefined)?.message
  return message ? String(message) : TOAST_LOAD_FAIL
}

/** 页面入参：优先页面栈 query，其次 storage（单测/无 query 场景；与序号 11/12-v3 同口径） */
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

let contractId = ''

async function load() {
  contractId = resolveQueryId('contractId', CONTRACT_ID_KEY)
  if (!contractId) {
    view.value = buildContractView(null)
    return
  }
  try {
    const raw = (await contractApi.detail(contractId)) as ContractRaw
    view.value = buildContractView(raw)
  } catch (e) {
    view.value = buildContractView(null)
    uni.showToast({ title: errorText(e), icon: 'none' })
  }
}

onMounted(() => {
  void load()
})

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

function onBack() {
  uni.navigateBack({ delta: 1 })
}

/**
 * 下载 PDF：先按 18-API「Contract」/contracts/{id}/file 取文件地址，
 * 再走 uni.downloadFile + uni.openDocument（小程序标准链路）；无地址不编造、直接提示。
 */
async function onPdf() {
  if (!contractId) {
    toast(TOAST_NO_FILE)
    return
  }
  try {
    const res = await contractApi.file(contractId)
    const url = String(res?.url || res?.file_url || '')
    if (!url) {
      toast(TOAST_NO_FILE)
      return
    }
    uni.downloadFile({
      url,
      success: (r) => {
        const filePath = String((r as { tempFilePath?: string } | undefined)?.tempFilePath || '')
        if (!filePath) {
          toast(TOAST_FILE_FAIL)
          return
        }
        uni.openDocument({
          filePath,
          fileType: 'pdf',
          fail: () => toast(TOAST_FILE_FAIL)
        })
      },
      fail: () => toast(TOAST_FILE_FAIL)
    })
  } catch (e) {
    toast(errorText(e))
  }
}

/**
 * 去签署：设计帧的「签署方式 = 短信验证码签署」与 10-PRD §4.2 / R-41「合同线下」冲突（已记台账）→
 * 本轮按设计稿发起签署（POST /contracts/{id}/sign，18-API 无请求体 schema → 不带字段），二次确认后执行。
 */
function onSign() {
  if (!contractId) {
    toast(TOAST_NO_CONTRACT)
    return
  }
  uni.showModal({
    title: CONFIRM_SIGN_TITLE,
    content: CONFIRM_SIGN_CONTENT,
    success: (res) => {
      if (res?.confirm) void doSign()
    }
  })
}

async function doSign() {
  try {
    await contractApi.sign(contractId)
    toast(TOAST_SIGNED)
    await load()
  } catch (e) {
    toast(errorText(e))
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.ct {
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
}

/* ---------- 顶部导航（48 + 36 + 12 = 96） ---------- */
.ct__nav {
  display: flex;
  align-items: center;
  padding: 48px 16px 12px;
  background: $color-bg-card;
}
.nav__back {
  width: 26px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.nav__title {
  padding-left: 12px;
  font-size: 17px;
  font-weight: 700;
  line-height: 20.4px;
  color: $color-text-primary;
}
.nav__spacer {
  flex: 1;
}
.nav__no {
  font-size: 11px;
  line-height: 13.2px;
  color: $color-text-placeholder;
  flex-shrink: 0;
}

/* ---------- 内容区（12/16/0/16 · 卡距 12） ---------- */
.ct__body {
  display: flex;
  flex-direction: column;
  padding: 12px 16px 0;
}
.card {
  background: $color-bg-card;
  border-radius: 16px;
  padding: 20px;
  box-sizing: border-box;
  width: 100%;
}
/* 卡间距 12（设计：每个后续卡片外包裹层 padding-top 12） */
.card + .card {
  margin-top: 12px;
}
/* 描边在盒外（§4.8 规则）→ ring，卡片声明高度 = 可见高度 */
.card--tip,
.card--basic,
.card--fee,
.card--terms,
.card--sign,
.card--records {
  box-shadow: 0 0 0 1px $color-border-chip;
}
/* 合同状态卡（设计树无 stroke，截图像素显示其下 12px 间隙有柔和投影 → 近似值，已记台账） */
.card--status {
  padding: 20px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
}
.status__icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: $color-warning-weak-2;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.status__content {
  flex: 1;
  min-width: 0;
  padding-left: 12px;
  display: flex;
  flex-direction: column;
  align-self: center;
}
.status__row {
  display: flex;
  align-items: center;
  min-height: 22px;
}
.status__title {
  font-size: 15px;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-primary;
}
.status-chip {
  height: 22px;
  padding: 0 8px;
  margin-left: 8px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.status-chip__text {
  font-size: 11px;
  font-weight: 500;
  line-height: 22px;
}
.status__deadline {
  padding-top: 4px;
  height: 16px;
  font-size: 11px;
  line-height: 16px;
  color: $color-text-placeholder;
}

/* ---------- 电子签提示卡（12 + 27 + 12 = 51） ---------- */
.card--tip {
  display: flex;
  align-items: flex-start;
  padding: 12px 20px;
}
.tip__text {
  padding-left: 8px;
  width: 276px;
  font-size: 11px;
  line-height: 13.2px;
  color: $color-text-muted;
}

/* ---------- 卡片通用 ---------- */
.card__title {
  display: block;
  height: 20px;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  color: $color-text-primary;
}
.crow {
  display: flex;
  align-items: center;
  height: 18px;
}
/* 首行间距：基本信息/签署信息 16，费用与分成 16；后续行 12 */
.crow--0 {
  margin-top: 16px;
}
.crow--1,
.crow--2,
.crow--3 {
  margin-top: 12px;
}
.crow__label {
  width: 87px;
  font-size: 12px;
  line-height: 18px;
  color: $color-text-placeholder;
  flex-shrink: 0;
}
.crow__value {
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-primary;
}
.crow--fee .crow__label--fee {
  width: auto;
  color: $color-text-muted;
}
.crow__spacer {
  flex: 1;
}
.crow__value--bold {
  font-weight: 700;
}

/* ---------- 关键条款（首条 pt8，其后 pt6，行高 20） ---------- */
.clause {
  height: 20px;
}
.clause__text {
  display: block;
  font-size: 12px;
  line-height: 20px;
  color: $color-text-muted;
}
.clause--0 {
  margin-top: 8px;
}
.clause--1,
.clause--2,
.clause--3 {
  margin-top: 6px;
}

/* ---------- 签署记录（首条 pt16，其后 pt12，单条 34） ---------- */
.record {
  display: flex;
  align-items: flex-start;
}
.record--0 {
  margin-top: 16px;
}
.record--1,
.record--2,
.record--3 {
  margin-top: 12px;
}
.record__dot {
  width: 11px;
  height: 10px;
  border-radius: 5px;
  flex-shrink: 0;
}
.record__body {
  padding-left: 12px;
  display: flex;
  flex-direction: column;
}
.record__title {
  height: 18px;
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-primary;
}
.record__time {
  height: 16px;
  font-size: 11px;
  line-height: 16px;
  color: $color-text-placeholder;
}

/* ---------- 底部操作条（16 + 12 + 48 + 24 = 100 → 栏高 84） ---------- */
.ct__bar-wrap {
  padding-top: 16px;
  margin-top: auto;
}
.ct__bar {
  display: flex;
  align-items: center;
  padding: 12px 16px 24px;
  background: $color-bg-card;
}
.btn {
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}
.btn--ghost {
  width: 126px;
  background: $color-bg-card;
  /* 描边在盒外 → ring，保持固定高 48 */
  box-shadow: 0 0 0 0.8px $color-border-strong;
  flex-shrink: 0;
}
.btn--primary {
  flex: 1;
  min-width: 0;
  margin-left: 12px;
  background: $color-primary;
}
.btn__text {
  padding-left: 5px;
  font-size: 13px;
  font-weight: 500;
  line-height: 18px;
  color: $color-text-secondary;
}
.btn__text--light {
  padding-left: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
}

/* 图标行盒包裹层（设计 remixicon 段落按 字号 × 1.5 撑行 → 见 utils/quote-form-model.iconLineBox） */
.icon-line {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.icon-line--18 {
  height: 27px;
  /* 设计里这三个图标都是 fontSize=18 的 remixicon 段落，声明宽度 20（不是字形宽度）→
     盒子固定 20 宽，否则提示卡文案会左移 6px（实测 x50 vs 设计 x56 盒 / x64 墨迹） */
  width: 20px;
  justify-content: center;
}
.icon-line--24 {
  height: 36px;
  width: 26px;
  justify-content: center;
}
.icon-line--light .ic-send {
  border-left-color: #ffffff;
  border-top-color: #ffffff;
}

/* 图标（设计稿为 remixicon 字形 → CSS 形状占位，已记台账） */
.ic-back {
  width: 10px;
  height: 10px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
}
.ic-contract {
  width: 18px;
  height: 18px;
  border: 2px solid $color-warning-text;
  border-radius: 3px;
  box-sizing: border-box;
}
.ic-shield {
  width: 14px;
  height: 16px;
  border: 2px solid $color-primary;
  border-radius: 3px 3px 7px 7px;
  box-sizing: border-box;
}
.ic-download {
  width: 14px;
  height: 14px;
  border: 2px solid $color-text-secondary;
  border-top: 0;
  border-radius: 0 0 3px 3px;
  box-sizing: border-box;
  position: relative;
}
.ic-download::before {
  content: '';
  position: absolute;
  left: 4px;
  top: -6px;
  width: 2px;
  height: 8px;
  background: $color-text-secondary;
}
.ic-send {
  width: 0;
  height: 0;
  border-left: 8px solid #ffffff;
  border-top: 6px solid #ffffff;
  border-right: 8px solid transparent;
  border-bottom: 6px solid transparent;
}
</style>
