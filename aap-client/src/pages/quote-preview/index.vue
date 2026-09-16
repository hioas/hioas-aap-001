<template>
  <view class="preview">
    <!-- 顶部导航（设计 d02dab76 padding[48,16,12,16]）· 无副标题（设计树只有「报价预览」一个文本层） -->
    <view class="preview__nav">
      <view class="nav__back" data-testid="nav-back" @tap="goBack">
        <view class="ic ic-back" />
      </view>
      <view class="nav__title-wrap">
        <text class="nav__title" data-testid="nav-title">{{ PAGE_TITLE }}</text>
      </view>
    </view>

    <!-- 内容区（设计 5320463d padding[12,16,0,16]，卡间距 12 由包裹层 padding-top 承担） -->
    <view class="preview__body">
      <view v-for="(card, ci) in cards" :key="card.itemId || ci" class="card-wrap">
        <view class="card" :class="ci === 0 ? 'card--lead' : 'card--ring'" data-testid="model-card">
          <!-- 头行（设计 fit_content；卡高反推 26） -->
          <view class="card__head">
            <view class="ic ic-model" />
            <view class="head__name-wrap">
              <text class="head__name" data-testid="model-name">{{ card.modelName }}</text>
            </view>
            <view class="head__spacer" />
            <view
              class="tag"
              :class="`tag--${card.tag.tone}`"
              :data-tone="card.tag.tone"
              data-testid="model-tag"
            >
              <text class="tag__text">{{ card.tag.text }}</text>
            </view>
          </view>

          <!-- 基础价行（设计 基础：wrapper padding-top 12；列 = 标签 12 + 值 22 = 34） -->
          <view class="card__block card__block--first">
            <view class="prices">
              <template v-for="(p, pi) in card.prices" :key="p.label">
                <view v-if="pi > 0" class="prices__spacer" />
                <view class="prices__col">
                  <text class="prices__label" data-testid="price-label">{{ p.label }}</text>
                  <text class="prices__value" data-testid="price-value">{{ p.value }}</text>
                </view>
              </template>
            </view>
          </view>

          <!-- 规则行：首个规则块 padding-top 12、其后 8（设计稿逐块如此）
               行高逐行不同：峰谷/阶梯行 44、请求规则行 40（见 utils/quote-preview-model.ts 注释） -->
          <view
            v-for="(line, li) in card.rules"
            :key="li"
            class="card__block"
            :class="ruleBlockClass(li, card.rules.length)"
          >
            <view class="rule" :class="{ 'rule--compact': line.kind === 'request' }">
              <view class="ic" :class="line.tone === 'amber' ? 'ic-time' : 'ic-rule'" />
              <view class="rule__wrap">
                <text class="rule__text" data-testid="rule-line">{{ line.text }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- 确认提交卡（设计 a059de31 padding20 r16 stroke #EEF2F7） -->
      <view class="card-wrap">
        <view class="card card--ring">
          <view class="confirm" data-testid="confirm-row">
            <view
              class="check"
              :class="{ 'check--on': confirmed }"
              :data-checked="confirmed ? 'true' : 'false'"
              data-testid="confirm-check"
              @tap="toggleConfirm"
            >
              <view v-if="confirmed" class="check__tick" />
            </view>
            <view class="confirm__wrap">
              <text class="confirm__text" data-testid="confirm-text">{{ CONFIRM_TEXT }}</text>
            </view>
          </view>
          <view class="card__block card__block--first">
            <view class="hint">
              <view class="ic ic-hint" />
              <view class="hint__wrap">
                <text class="hint__text" data-testid="submit-hint">{{ HINT_TEXT }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部操作条（设计 8e160a88 padding-top 16 + d7b75749 padding[12,16,24,16]） -->
    <view class="preview__bar-wrap">
      <view class="preview__bar">
        <view class="bar__ghost" data-testid="btn-back-edit" @tap="goBack">{{ BACK_EDIT_TEXT }}</view>
        <view class="bar__main-wrap">
          <view class="bar__main" data-testid="btn-submit" @tap="onSubmit">
            <view class="ic ic-send" />
            <view class="bar__main-text-wrap">
              <text class="bar__main-text">{{ SUBMIT_TEXT }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 12【报价管理】报价预览与提交 2（page-12-2）
 * 设计真源：.calicat/raw/pages/page-12-2/design.tree.json（430 宽 · 设计总高 1027 · 无 TabBar）
 *   几何（设计截图像素量尺 + 卡片整高反推，见 .agents/state/design-shots/page-12-2-design.png）：
 *     顶栏 96 · 内容区 padding 12/16/0/16 · 卡间距 12 · 卡 padding 20 r16（描边 1px #EEF2F7）
 *     卡内：头行 26 · 基础价行 padding-top 12 高 34（标签 12 + 值 22）· 规则行 44（padding 10 + 内容 24），
 *           首个规则块 padding-top 12、其后 8 · 确认卡 127（确认行 22 + 提示条 53）· 底栏 943..1027(84)
 * 接口真源：18-API「Quote」→ GET /quotes/{quoteId} · POST /quotes/{quoteId}/submit（前缀 /api/v1）
 * 交互分类（写进 .agents/state/aap-feature-status.csv 序号 12）：
 *   顶栏返回 / 「返回编辑」 = navigation(navigateBack，不臆造前一页路由)
 *   「提交报价」 = api(POST /quotes/{quoteId}/submit；无请求体 schema → 不发字段)
 *   确认勾选框 = client-only（提交门禁；未勾选或不发请求，见 validateSubmit）
 * 缺口与派生规则见 src/utils/quote-preview-model.ts 顶部说明（不臆造字段/文案）。
 */
import { onMounted, ref } from 'vue'
import { ApiError } from '@/api/http'
import { quoteApi } from '@/api/quote'
import {
  BACK_EDIT_TEXT,
  CONFIRM_TEXT,
  HINT_TEXT,
  PAGE_TITLE,
  QUOTE_ID_KEY,
  QUOTES_LIST_PAGE,
  SUBMIT_TEXT,
  TOAST_FAIL,
  TOAST_MISSING_QUOTE,
  TOAST_SUBMITTED,
  buildPreviewItems,
  buildSubmitPayload,
  readQuoteId,
  ruleBlockClass,
  validateSubmit,
  type PreviewCard
} from '@/utils/quote-preview-model'

const quoteId = ref('')
const cards = ref<PreviewCard[]>([])
/** 设计稿勾选框为蓝底白勾 → 默认已确认 */
const confirmed = ref(true)

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

function toastMessage(e: unknown): string {
  if (e instanceof ApiError && e.message) return e.message
  return TOAST_FAIL
}

function applyDetail(detail: Parameters<typeof buildPreviewItems>[0]) {
  cards.value = buildPreviewItems(detail)
  const id = readQuoteId(detail)
  if (id) quoteId.value = id
}

onMounted(async () => {
  const id = resolveQueryId('quoteId', QUOTE_ID_KEY)
  quoteId.value = id
  if (!id) {
    toast(TOAST_MISSING_QUOTE)
    return
  }
  try {
    applyDetail(await quoteApi.detail(id))
  } catch (e) {
    toast(toastMessage(e))
  }
})

function goBack() {
  uni.navigateBack({ delta: 1 })
}

function toggleConfirm() {
  confirmed.value = !confirmed.value
}

/** 提交：本地只做「有明细 + 已确认」门禁；V1–V17 全量校验由服务端执行（10-PRD §5.1） */
async function onSubmit() {
  const errors = validateSubmit({ confirmed: confirmed.value, itemCount: cards.value.length })
  if (errors.length) {
    toast(errors[0])
    return
  }
  try {
    buildSubmitPayload({ confirmed: confirmed.value, itemCount: cards.value.length })
    await quoteApi.submit(quoteId.value)
    toast(TOAST_SUBMITTED)
    uni.navigateTo({ url: QUOTES_LIST_PAGE })
  } catch (e) {
    toast(toastMessage(e))
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/tokens.scss';

.preview {
  width: 100%;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

/* ---------- 顶栏（96 = 48 + 36 + 12） ---------- */

.preview__nav {
  width: 100%;
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
  display: flex;
  align-items: center;
}

.ic-back {
  width: 10px;
  height: 10px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
}

.nav__title-wrap {
  padding-left: 12px;
  display: flex;
  align-items: center;
}

.nav__title {
  display: block;
  font-size: 17px;
  font-weight: 700;
  line-height: 21px;
  color: $color-text-primary;
}

/* ---------- 内容区 ---------- */

.preview__body {
  box-sizing: border-box;
  padding: 12px 16px 0 16px;
  flex: 1;
}

.card-wrap + .card-wrap {
  padding-top: 12px;
}

.card {
  box-sizing: border-box;
  padding: 20px;
  border-radius: 16px;
  background: $color-bg-card;
}

/* 卡片效果按设计**逐卡不同**（不静默统一，PNG 已佐证）：
   卡1（设计 39fed800）只声明 effects drop_shadow(0,6,20,rgba(15,23,42,.06))，无 stroke
     → PNG：卡1 下方 381..391 有投影染色、x=16 行内无描边像素
   卡2/卡3/确认卡声明 stroke{align:center,thickness:1,#EEF2F7}，无 effects
     → PNG：卡2 上下描边在 y=392 / 612，卡3 624 / 788，确认卡 800 / 926；卡片下方是纯页面底色
   Figma 的 center 描边不占布局 → 用 ring（box-shadow）而非 border（border 会把内容宽挤掉 2px） */
.card--lead {
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

.card--ring {
  box-shadow: 0 0 0 1px $color-border-chip;
}

/* ---------- 卡头行 ---------- */

.card__head {
  height: 26px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.ic-model {
  width: 20px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ic-model::after {
  content: '';
  width: 14px;
  height: 14px;
  border: 2px solid $color-primary;
  border-radius: 4px;
}

.head__name-wrap {
  padding-left: 6px;
  display: flex;
  align-items: center;
}

.head__name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  line-height: 18px;
  color: $color-text-primary;
}

.head__spacer {
  flex: 1;
}

.tag {
  height: 20px;
  box-sizing: border-box;
  padding: 0 8px;
  border-radius: 10px;
  display: flex;
  align-items: center;
}

.tag--primary {
  background: $color-primary-weak;
}

.tag--success {
  background: $color-success-weak;
}

.tag--neutral {
  background: $color-bg-subtle;
}

.tag__text {
  display: block;
  font-size: 10px;
  font-weight: 500;
  line-height: 20px;
}

.tag--primary .tag__text {
  color: $color-primary;
}

.tag--success .tag__text {
  color: $color-success-text;
}

.tag--neutral .tag__text {
  color: $color-text-muted;
}

/* ---------- 卡内块间距（首个块 12，规则块其后 8） ---------- */

.card__block--first {
  padding-top: 12px;
}

.card__block--tight {
  padding-top: 8px;
}

/* ---------- 基础价行（38 = 标签 16 + 值 22，两值均为设计显式 height） ---------- */

.prices {
  height: 38px;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

.prices__col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.prices__spacer {
  width: 9px;
}

.prices__label {
  display: block;
  width: 100%;
  height: 16px;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
  color: $color-text-placeholder;
}

.prices__value {
  display: block;
  width: 100%;
  height: 22px;
  font-size: 14px;
  font-weight: 700;
  line-height: 22px;
  text-align: center;
  color: $color-text-primary;
}

/* ---------- 规则行（峰谷/阶梯 44 = padding 10 + 内容 24 + 10；请求规则 40 = 内容 20） ---------- */

.rule {
  height: 44px;
  box-sizing: border-box;
  padding: 10px;
  border-radius: 10px;
  background: $color-bg-page;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

/* 请求规则行内容高 20（设计该行图标图层 width=fit_content），PNG 实测行高 40 */
.rule--compact {
  height: 40px;
}

.ic-time,
.ic-rule {
  width: 18px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rule--compact .ic-time,
.rule--compact .ic-rule {
  height: 20px;
}

.ic-time::after,
.ic-rule::after {
  content: '';
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 2px solid $color-primary;
}

.ic-time::after {
  border-color: $color-warning-text;
  border-radius: 50%;
}

.rule__wrap {
  padding-left: 6px;
  flex: 1;
  min-width: 0;
  /* 设计里该容器是 alignItems=start 的行 → 文字贴着内容顶（不要 min-height + center，
     那会把 11px 文字的行框在 24 高盒里居中，墨迹整体下沉 3.5px，见 cmp-序号12 像素对账） */
  display: flex;
  align-items: flex-start;
}

.rule__text {
  display: block;
  font-size: 11px;
  /* 行框按设计行**逐行不同**（PNG 墨迹实测，见 .agents/state/evidence/cmp-序号12-*）：
     峰谷/阶梯行（行高 44）文字带在设计里位于行顶 +13 → 行框 18（11 × 1.636）
     请求规则行（行高 40）文字带位于行顶 +11 → 行框 13.2（= 设计声明 lineHeight 1.2） */
  line-height: 18px;
  color: $color-text-secondary;
}

.rule--compact .rule__text {
  line-height: 13.2px;
}

/* ---------- 确认提交卡（127 = 20 + 确认行 19 + 12 + 提示条 56 + 20） ---------- */

.confirm {
  height: 19px; /* = fs12 文本行框 19.2（设计 PNG 确认行 820..838） */
  display: flex;
  flex-direction: row;
  align-items: center;
}

.check {
  width: 18px;
  height: 18px;
  box-sizing: border-box;
  border-radius: 6px;
  border: 1.5px solid $color-border-strong;
  display: flex;
  align-items: center;
  justify-content: center;
}

.check--on {
  background: $color-primary;
  border-color: $color-primary;
}

.check__tick {
  width: 5px;
  height: 9px;
  border-right: 2px solid #ffffff;
  border-bottom: 2px solid #ffffff;
  transform: rotate(45deg) translate(-1px, -1px);
}

.confirm__wrap {
  padding-left: 8px;
  display: flex;
  align-items: center;
}

.confirm__text {
  display: block;
  font-size: 12px;
  line-height: 19px; /* 设计行框 = 12 × 1.6（撑起确认行 19） */
  color: $color-text-secondary;
}

/* ---------- 提示条（56 = padding 10 + 两行 × 18 + padding 10） ---------- */

.hint {
  box-sizing: border-box;
  padding: 10px;
  border-radius: 10px;
  background: $color-warning-weak-2;
  min-height: 56px;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

.ic-hint {
  width: 17px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ic-hint::after {
  content: '';
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid $color-warning-text;
}

.hint__wrap {
  padding-left: 6px;
  flex: 1;
  min-width: 0;
}

.hint__text {
  display: block;
  /* 设计稿该文本层声明宽度 316（卡片内宽 358），按声明宽度换行为两行 —— 与设计截图一致
     设计行框 = 11 × 1.636 ≈ 18 → 提示条 56 = 10 + 2×18 + 10（PNG 实测 851..906） */
  max-width: 316px;
  font-size: 11px;
  line-height: 18px;
  color: $color-warning-text-2;
}

/* ---------- 底部操作条（84 = 12 + 48 + 24，外层 padding-top 16） ---------- */

.preview__bar-wrap {
  padding-top: 16px;
}

.preview__bar {
  box-sizing: border-box;
  padding: 12px 16px 24px 16px;
  background: $color-bg-card;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.bar__ghost {
  width: 156px;
  height: 48px;
  box-sizing: border-box;
  border-radius: 12px;
  border: 1px solid $color-border-strong;
  background: $color-bg-card;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
  color: $color-text-secondary;
}

.bar__main-wrap {
  flex: 1;
  padding-left: 12px;
}

.bar__main {
  height: 48px;
  border-radius: 12px;
  background: $color-primary;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.ic-send {
  width: 20px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ic-send::after {
  content: '';
  width: 0;
  height: 0;
  border-left: 9px solid #ffffff;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
}

.bar__main-text-wrap {
  padding-left: 6px;
  display: flex;
  align-items: center;
}

.bar__main-text {
  display: block;
  font-size: 15px;
  font-weight: 600;
  line-height: 20px;
  color: #ffffff;
}
</style>
