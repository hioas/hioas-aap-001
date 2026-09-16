<template>
  <!-- 序号 12-v3【报价管理】新增报价单-保存成功（page-29）· /pages/quote-form/success -->
  <view class="qs">
    <!-- 顶部导航（48 + 标题块 42 + 12 = 102） -->
    <view class="qs__nav">
      <view class="nav__left">
        <view class="nav__btn" data-testid="back" @tap="onBack">
          <view class="ic-back" />
        </view>
        <view class="nav__titles">
          <text class="nav__title" data-testid="nav-title">{{ PAGE_TITLE }}</text>
          <text class="nav__subtitle" data-testid="nav-subtitle">{{ PAGE_SUBTITLE }}</text>
        </view>
      </view>
      <view class="nav__btn" data-testid="close" @tap="onClose">
        <view class="ic-close" />
      </view>
    </view>

    <!-- 内容区（padding 16/16/20/16 · gap 16） -->
    <view class="qs__body">
      <!-- 1) 成功头部卡（28 + 图标 64 + 14 + 标题 24 + 副标题 18 + 18 + 单号条 62 + 28 = 256） -->
      <view class="card succ" data-testid="success-card">
        <view class="succ__icon"><view class="ic-check-big" /></view>
        <view class="succ__title-wrap">
          <text class="succ__title" data-testid="success-title">{{ SUCCESS_TITLE }}</text>
        </view>
        <text class="succ__desc" data-testid="success-desc">{{ SUCCESS_DESC }}</text>
        <view class="succ__bar-wrap">
          <view class="no-bar" data-testid="quote-no-bar">
            <view class="no-bar__info">
              <text class="no-bar__label" data-testid="quote-no-label">{{ QUOTE_NO_LABEL }}</text>
              <text class="no-bar__value" data-testid="quote-no-value">{{ view.quoteNo }}</text>
            </view>
            <view class="no-bar__copy" data-testid="copy" @tap="onCopy">
              <view class="ic-copy" />
              <text class="no-bar__copy-text">{{ COPY_TEXT }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 2) 结果摘要卡（16 + 头 20 + 14 + 38×3 + 39.5 + 30 + 16 = 249.5） -->
      <view class="card" data-testid="summary-card">
        <view class="card__head">
          <view class="head__bar" />
          <text class="card__title" data-testid="summary-title">{{ SUMMARY_TITLE }}</text>
        </view>
        <view class="sum__first">
          <view class="srow" data-testid="row-name">
            <text class="srow__label">{{ ROW_NAME }}</text>
            <text class="srow__value">{{ view.quoteName }}</text>
          </view>
        </view>
        <view class="srow" data-testid="row-cred">
          <text class="srow__label">{{ ROW_CRED }}</text>
          <view class="srow__value-group">
            <view v-if="view.credEnvTag" class="env-chip">
              <text class="env-chip__text" data-testid="cred-env-tag">{{ view.credEnvTag }}</text>
            </view>
            <text v-if="view.credMask" class="srow__value" data-testid="cred-mask">{{ view.credMask }}</text>
            <!-- 脱敏 key 缺失时才退退回别名（设计帧该行只有「环境小标 + 脱敏 key」，别名不单独渲染） -->
            <text v-else class="srow__value" data-testid="cred-fallback">{{ view.credAlias }}</text>
          </view>
        </view>
        <view class="srow" data-testid="row-models">
          <text class="srow__label">{{ ROW_MODELS }}</text>
          <view class="count-chip">
            <text class="count-chip__text">{{ view.selectedCountText }}</text>
          </view>
        </view>
        <view class="srow srow--no" data-testid="row-no">
          <text class="srow__label">{{ QUOTE_NO_LABEL }}</text>
          <view class="srow__value-group srow__value-group--no">
            <view class="icon-line icon-line--13"><view class="ic-check-sm" /></view>
            <text class="srow__value srow__value--primary">{{ view.quoteNo }}</text>
          </view>
        </view>
        <view class="srow srow--last" data-testid="row-status">
          <text class="srow__label">{{ ROW_STATUS }}</text>
          <view class="status-chip" :style="{ backgroundColor: view.status.bg }">
            <view class="status-chip__dot" :style="{ backgroundColor: view.status.dot }" />
            <text class="status-chip__text" :style="{ color: view.status.text }" data-testid="status-chip">
              {{ view.status.label }}
            </text>
          </view>
        </view>
      </view>

      <!-- 3) 已带出模型卡（16 + 头 24 + 12 + 28 + 8 + 28 + 16 = 132） -->
      <view class="card" data-testid="models-card">
        <view class="card__head card__head--icon">
          <view class="icon-line icon-line--16"><view class="ic-models" /></view>
          <text class="card__title card__title--sm" data-testid="model-card-title">{{ CARD_MODELS }}</text>
          <view class="head__spacer" />
          <text class="head__count" data-testid="model-count">{{ view.modelTotalText }}</text>
        </view>
        <view v-if="selectedTags.length" class="tags__wrap">
          <view class="tags">
            <view
              v-for="t in selectedTags"
              :key="t.key"
              class="tag tag--on"
              :data-testid="`model-tag-${t.key}`"
              data-selected="true"
            >
              <text class="tag__text">{{ t.name }}</text>
            </view>
          </view>
        </view>
        <view v-if="unselectedTags.length" class="tags__wrap tags__wrap--2">
          <view class="tags">
            <view
              v-for="t in unselectedTags"
              :key="t.key"
              class="tag tag--off"
              :data-testid="`model-tag-${t.key}`"
              data-selected="false"
            >
              <text class="tag__text">{{ t.name }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 4) 下一步提示卡（12 + 图标行盒 24（= 字号16×1.5）+ 12 = 48；文案单行 13.2，卡高由图标行盒决定） -->
      <view class="tip" data-testid="tip-card">
        <view class="icon-line icon-line--16"><view class="ic-info" /></view>
        <text class="tip__text" data-testid="tip">{{ TIP_TEXT }}</text>
      </view>
    </view>

    <!-- 底部操作条（12 + 48 + 10 + 48 + 28 = 146） -->
    <view class="qs__bar">
      <view class="btn btn--primary" data-testid="btn-primary" @tap="onPrimary">
        <view class="icon-line icon-line--18 icon-line--light"><view class="ic-shield" /></view>
        <text class="btn__text btn__text--light">{{ BTN_PRIMARY }}</text>
      </view>
      <view class="btn-wrap">
        <view class="btn btn--ghost" data-testid="btn-secondary" @tap="onSecondary">
          <text class="btn__text">{{ BTN_SECONDARY }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 12-v3 · /pages/quote-form/success（page-29：新增报价单-保存成功）
 *
 * 设计与缺口真源：src/utils/quote-success-model.ts 顶部注释 + .calicat/raw/pages/page-29/design.tree.json
 * 页面入参：quoteId 优先页面栈 query（?quoteId=），其次 storage 键 aap_quote_id；
 *   凭证 id 同族取 aap_credential_id（报价单响应自带 credential_id 时优先）。
 * 取数：GET /quotes/{quoteId}（报价单详情 + 明细行）→ 有凭证 id 时再 GET /credentials/{id}（model_list）；
 *   两个端点均取 18-API「Quote」/「Credential」Tag 的真实路径（前缀 /api/v1），方法为 REST 语义推断（missing-prd）。
 */
import { computed, onMounted, ref } from 'vue'
import { quoteApi } from '@/api/quote'
import { credentialApi } from '@/api/credential'
import {
  BTN_PRIMARY,
  BTN_SECONDARY,
  CARD_MODELS,
  COPY_TEXT,
  CREDENTIAL_ID_KEY,
  MODEL_PRICING_PAGE,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  QUOTES_LIST_PAGE,
  QUOTE_ID_KEY,
  QUOTE_NO_LABEL,
  ROW_CRED,
  ROW_MODELS,
  ROW_NAME,
  ROW_STATUS,
  SUCCESS_DESC,
  SUCCESS_TITLE,
  SUMMARY_TITLE,
  TIP_TEXT,
  TOAST_COPIED,
  TOAST_FAIL,
  TOAST_NO_QUOTE_NO,
  buildSuccessView,
  resolveCredentialId,
  type CredentialSuccessRaw,
  type QuoteSuccessRaw,
  type QuoteSuccessView
} from '@/utils/quote-success-model'

const view = ref<QuoteSuccessView>(buildSuccessView({}))

const selectedTags = computed(() => view.value.models.filter((m) => m.selected))
const unselectedTags = computed(() => view.value.models.filter((m) => !m.selected))

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

/** 页面入参：优先页面栈 query，其次 storage（单测/无 query 场景；与序号 11/5 同口径） */
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

function errorText(e: unknown): string {
  const message = (e as { message?: string } | undefined)?.message
  return message ? String(message) : TOAST_FAIL
}

let quoteId = ''

async function load() {
  quoteId = resolveQueryId('quoteId', QUOTE_ID_KEY)
  if (!quoteId) return
  const hintCredId = resolveQueryId('credentialId', CREDENTIAL_ID_KEY)
  let quote: QuoteSuccessRaw | null = null
  let credential: CredentialSuccessRaw | null = null
  try {
    quote = (await quoteApi.detail(quoteId)) as unknown as QuoteSuccessRaw
  } catch (e) {
    view.value = buildSuccessView({ quote: null, credential: null })
    toast(errorText(e))
    return
  }
  const credId = resolveCredentialId(quote, hintCredId)
  if (credId) {
    try {
      credential = (await credentialApi.detail(credId)) as unknown as CredentialSuccessRaw
    } catch (e) {
      // 凭证侧取不到 → 摘要仍用报价单侧数据，环境标/脱敏/模型清单不渲染（不猜）
      toast(errorText(e))
    }
  }
  view.value = buildSuccessView({ quote, credential, fallbackCredentialId: credId })
}

onMounted(() => {
  void load()
})

function onBack() {
  uni.navigateBack({ delta: 1 })
}

/** 关闭与「返回报价单列表」同落报价单列表：reLaunch 清栈，避免回到已提交的表单页（设计无交互数据 → 推断） */
function onClose() {
  uni.reLaunch({ url: QUOTES_LIST_PAGE })
}

function onCopy() {
  if (!view.value.hasQuoteNo) {
    toast(TOAST_NO_QUOTE_NO)
    return
  }
  uni.setClipboardData({
    data: view.value.quoteNo,
    success: () => toast(TOAST_COPIED)
  })
}

function onPrimary() {
  uni.navigateTo({ url: quoteId ? `${MODEL_PRICING_PAGE}?quoteId=${quoteId}` : MODEL_PRICING_PAGE })
}

function onSecondary() {
  uni.reLaunch({ url: QUOTES_LIST_PAGE })
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.qs {
  min-height: 100vh;
  background: $color-bg-page-2;
  display: flex;
  flex-direction: column;
}

/* ---------- 顶部导航（48 + 42 + 12 = 102） ---------- */
.qs__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 48px 16px 12px;
  background: $color-bg-card;
}
.nav__left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.nav__btn {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nav__titles {
  display: flex;
  flex-direction: column;
}
.nav__title {
  font-size: 18px;
  font-weight: 700;
  line-height: 24px;
  color: $color-text-primary;
}
.nav__subtitle {
  font-size: 12px;
  line-height: 18px;
  color: $color-text-placeholder;
}

/* ---------- 内容区 ---------- */
.qs__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 16px 20px;
}
.card {
  background: $color-bg-card;
  border-radius: 16px;
  /* 卡片内边距 16（page-29 结果摘要卡 / 带出模型卡；成功头部卡用 .succ 覆盖为 28/16） */
  padding: 16px;
  /* design f5d8ac7d / 7ce5a3a9 / cec63018 effects drop_shadow(0,4,16,rgba(15,23,42,0.06))：三张卡逐卡同值，
     且三卡都**没有** stroke → 只能用 box-shadow（不得用 ring 顶替） */
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
}

/* ---------- 1) 成功头部卡（28+64+14+24+18+18+62+28 = 256） ---------- */
.succ {
  padding: 28px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  box-sizing: border-box;
}
.succ__icon {
  width: 64px;
  height: 64px;
  border-radius: 32px;
  background: $color-success-weak;
  display: flex;
  align-items: center;
  justify-content: center;
}
.succ__title-wrap {
  padding-top: 14px;
  display: flex;
  justify-content: center;
  width: 100%;
}
.succ__title {
  font-size: 18px;
  font-weight: 700;
  line-height: 24px;
  color: $color-text-primary;
  text-align: center;
}
.succ__desc {
  font-size: 12px;
  line-height: 18px;
  color: $color-text-placeholder;
  text-align: center;
}
.succ__bar-wrap {
  padding-top: 18px;
  width: 100%;
}
/* 单号展示条：padding 12/14 · r12 · bg #F8FAFC · 描边 0.8 #BFDBFE（描边在盒外 → ring） */
.no-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 12px;
  background: $color-bg-page;
  box-shadow: 0 0 0 0.8px $color-primary-border-2;
  box-sizing: border-box;
}
.no-bar__info {
  width: 155px;
  display: flex;
  flex-direction: column;
}
.no-bar__label {
  font-size: 11px;
  font-weight: 500;
  line-height: 15px;
  color: $color-text-placeholder;
}
.no-bar__value {
  font-size: 17px;
  font-weight: 700;
  line-height: 23px;
  color: $color-primary;
  /* 设计帧里单号信息固定 155 宽会被折行；实现按单行渲染（挂台账：设计帧自相矛盾） */
  white-space: nowrap;
}
.no-bar__copy {
  height: 32px;
  padding: 0 12px;
  border-radius: 10px;
  background: $color-primary-weak;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.no-bar__copy-text {
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
  color: $color-primary;
}

/* ---------- 2) 结果摘要卡 ---------- */
.card__head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card__head--icon {
  min-height: 24px;
}
.head__bar {
  width: 5px;
  height: 16px;
  border-radius: 2px;
  background: $color-primary;
  flex-shrink: 0;
}
.card__title {
  font-size: 15px;
  font-weight: 700;
  line-height: 20px;
  color: $color-text-primary;
}
.card__title--sm {
  font-size: 14px;
  line-height: 18px;
  font-weight: 600;
}
.head__spacer {
  flex: 1;
}
.head__count {
  font-size: 11px;
  line-height: 13.2px;
  color: $color-text-placeholder;
}
.sum__first {
  padding-top: 14px;
}
.srow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
}
.srow--no {
  /* 单号行含 13px remixicon 绿勾 → 行盒 = 13 × 1.5 = 19.5（图标行盒规则） */
  padding: 10px 0;
}
.srow--last {
  padding: 10px 0 0;
}
.srow__label {
  font-size: 13px;
  line-height: 18px;
  color: $color-text-placeholder;
}
.srow__value {
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-primary;
}
.srow__value--primary {
  color: $color-primary;
}
.srow__value-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
/* 单号行右侧组：设计 55b312e3 gap=4（与密钥行的密钥信息 e86268ab gap=8 不是同一个间距） */
.srow__value-group--no {
  gap: 4px;
}
.env-chip {
  height: 18px;
  padding: 0 8px;
  border-radius: 9px;
  background: $color-primary-weak;
  display: flex;
  align-items: center;
}
.env-chip__text {
  font-size: 10px;
  font-weight: 600;
  line-height: 18px;
  color: $color-primary;
}
.count-chip {
  height: 18px;
  padding: 0 8px;
  border-radius: 9px;
  background: $color-success-weak;
  display: flex;
  align-items: center;
}
.count-chip__text {
  font-size: 10px;
  font-weight: 600;
  line-height: 18px;
  color: $color-wechat;
}
.status-chip {
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.status-chip__dot {
  width: 7px;
  height: 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.status-chip__text {
  font-size: 11px;
  font-weight: 600;
  line-height: 20px;
}

/* ---------- 3) 已带出模型卡 ---------- */
.tags__wrap {
  padding-top: 12px;
}
.tags__wrap--2 {
  padding-top: 8px;
}
.tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.tag {
  height: 28px;
  padding: 0 12px;
  border-radius: 14px;
  display: flex;
  align-items: center;
}
.tag--on {
  background: $color-primary-weak;
}
.tag--on .tag__text {
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
  color: $color-primary;
}
.tag--off {
  background: $color-bg-page;
  box-shadow: 0 0 0 0.8px $color-bg-subtle;
}
.tag--off .tag__text {
  font-size: 12px;
  font-weight: 500;
  line-height: 16px;
  color: $color-text-placeholder;
}

/* ---------- 4) 提示卡（12 + 行盒 24 / 文案 + 12） ---------- */
.tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 14px;
  background: $color-primary-weak;
}
.tip__text {
  font-size: 11px;
  line-height: 13.2px;
  color: $color-brand;
  flex: 1;
  min-width: 0;
}

/* ---------- 底部操作条（12 + 48 + 10 + 48 + 28 = 146） ---------- */
.qs__bar {
  padding: 12px 16px 28px;
  background: $color-bg-card;
  /* design a17976f7 effects drop_shadow(0,-4,16,rgba(15,23,42,0.05)) */
  box-shadow: 0 -4px 16px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
}
.btn {
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
}
.btn--primary {
  background: $color-primary;
  /* design e607246e effects drop_shadow(0,6,16,rgba(37,99,235,0.28)) */
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
}
.btn--ghost {
  background: $color-bg-card;
  /* 描边在盒外（同页-10-2 规则）→ ring，保持固定高度 48 */
  box-shadow: 0 0 0 0.8px $color-border;
}
.btn-wrap {
  padding-top: 10px;
}
.btn__text {
  font-size: 14px;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-muted;
}
.btn__text--light {
  font-size: 15px;
  color: #ffffff;
}

/* 图标行盒包裹层（设计里 remixicon 段落按 字号 × 1.5 撑行 → 见 utils/quote-form-model.iconLineBox） */
.icon-line {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.icon-line--13 {
  height: 19.5px;
}
.icon-line--16 {
  height: 24px;
}
.icon-line--18 {
  height: 27px;
}

/* 图标占位盒（design 每个 remixicon 字号层一个）：盒 = 设计图层声明宽 × 字号×1.5 行盒，
   形状画在 ::before（决策 D5：不引入图标字体库 → CSS 形状占位）。page-29 定标：fs18→27 · fs16→24 · fs14→21 · fs13→19.5 */
.ic-back {
  width: 20px;
  height: 27px;
  position: relative;
  flex-shrink: 0;
}
.ic-back::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 9px;
  height: 9px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: translate(-50%, -50%) rotate(45deg);
}
.ic-close {
  width: 20px;
  height: 27px;
  position: relative;
  flex-shrink: 0;
}
.ic-close::before,
.ic-close::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 14px;
  height: 2px;
  background: $color-text-muted;
  border-radius: 1px;
}
.ic-close::before {
  transform: translate(-50%, -50%) rotate(45deg);
}
.ic-close::after {
  transform: translate(-50%, -50%) rotate(-45deg);
}
.ic-check-big {
  width: 41px;
  height: 57px;
  position: relative;
  flex-shrink: 0;
}
.ic-check-big::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 22px;
  height: 11px;
  border-left: 4px solid $color-wechat;
  border-bottom: 4px solid $color-wechat;
  transform: translate(-50%, -50%) rotate(-45deg) translate(2px, -2px);
}
.ic-check-sm {
  width: 15px;
  height: 19.5px;
  position: relative;
  flex-shrink: 0;
}
.ic-check-sm::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 7px;
  border-left: 2px solid $color-wechat;
  border-bottom: 2px solid $color-wechat;
  transform: translate(-50%, -50%) rotate(-45deg);
}
.ic-copy {
  width: 16px;
  height: 21px;
  position: relative;
  flex-shrink: 0;
}
.ic-copy::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  border: 2px solid $color-primary;
  border-radius: 2px;
  box-sizing: border-box;
  transform: translate(-50%, -50%);
}
.ic-copy::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 10px;
  height: 10px;
  border: 2px solid $color-primary;
  border-radius: 2px;
  background: $color-primary-weak;
  box-sizing: border-box;
  transform: translate(calc(-50% + 3px), calc(-50% - 4px));
}
.ic-models {
  width: 18px;
  height: 24px;
  position: relative;
  flex-shrink: 0;
}
.ic-models::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: $color-primary;
  transform: translate(-50%, -50%);
}
.ic-info {
  width: 18px;
  height: 24px;
  position: relative;
  flex-shrink: 0;
}
.ic-info::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid $color-primary;
  box-sizing: border-box;
  transform: translate(-50%, -50%);
}
.ic-shield {
  width: 20px;
  height: 27px;
  position: relative;
  flex-shrink: 0;
}
.ic-shield::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 14px;
  height: 16px;
  border: 2px solid #ffffff;
  border-radius: 3px 3px 7px 7px;
  box-sizing: border-box;
  transform: translate(-50%, -50%);
}
</style>
