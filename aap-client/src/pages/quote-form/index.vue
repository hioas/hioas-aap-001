<template>
  <view class="qf">
    <!-- 顶部导航（设计 c36637be padding[48,16,12,16]）-->
    <view class="qf__nav">
      <view class="nav__back" data-testid="back" @tap="goBack">
        <view class="ic ic-back" />
      </view>
      <view class="nav__titles">
        <text class="nav__title" data-testid="nav-title">{{ PAGE_TITLE }}</text>
        <text class="nav__subtitle" data-testid="nav-subtitle">{{ PAGE_SUBTITLE }}</text>
      </view>
      <view class="nav__help" data-testid="help">
        <view class="ic ic-help" />
      </view>
    </view>

    <view class="qf__body">
      <!-- 步骤卡（7acff570）-->
      <view class="step-card">
        <view
          v-for="step in steps"
          :key="step.no"
          class="step"
          :class="{ 'step--active': step.active }"
          :data-testid="`step-${step.no}`"
          :data-active="step.active ? 'true' : 'false'"
        >
          <view class="step__dot">
            <text class="step__no">{{ step.no }}</text>
          </view>
          <view class="step__texts">
            <text class="step__title">{{ step.title }}</text>
            <text class="step__desc">{{ step.desc }}</text>
          </view>
        </view>
        <view class="step-line" />
      </view>

      <!-- 基本信息卡（82bbea2b）-->
      <view class="card" data-testid="card-basic">
        <view class="card__head">
          <view class="card__bar" />
          <text class="card__title" data-testid="card-basic-title">{{ CARD_BASIC }}</text>
          <view class="card__spacer" />
          <view class="required" data-testid="chip-required">
            <view class="ic ic-required" />
            <text class="required__text">{{ REQUIRED_HINT }}</text>
          </view>
        </view>

        <!-- 字段：报价单名称 -->
        <view class="field">
          <view class="label">
            <text class="label__text" data-testid="name-label">{{ NAME_LABEL }}</text>
            <text class="label__star" data-testid="name-star">*</text>
          </view>
          <view class="field__inner">
            <view class="input-box">
              <input
                v-model="name"
                class="input-box__input"
                data-testid="name-input"
                :placeholder="NAME_PLACEHOLDER"
                placeholder-class="input-box__placeholder"
                :maxlength="NAME_MAX"
              />
              <view v-if="name" class="ic ic-clear" data-testid="name-clear" @tap="name = ''" />
            </view>
          </view>
          <view class="counter">
            <text class="counter__text" data-testid="name-count">{{ countTextValue }}</text>
          </view>
        </view>

        <view class="divider-wrap">
          <view class="divider" />
        </view>

        <!-- 字段：报价单号（系统生成，只读）-->
        <view class="field">
          <view class="label label--gap8">
            <text class="label__text" data-testid="quote-no-label">{{ QUOTE_NO_LABEL }}</text>
            <view class="tag tag--blue" data-testid="quote-no-tag">
              <text class="tag__text">{{ QUOTE_NO_TAG }}</text>
            </view>
          </view>
          <view class="field__inner">
            <view class="readonly-box" data-testid="quote-no-box">
              <view class="readonly-box__left">
                <view class="ic ic-doc" />
                <text class="readonly-box__text" data-testid="quote-no-text">{{ quoteNoBox.text }}</text>
              </view>
              <view class="sample-pill">
                <text class="sample-pill__text" data-testid="quote-no-sample">{{ quoteNoBox.sample }}</text>
              </view>
            </view>
          </view>
          <view class="hint">
            <view class="ic ic-info-sm" />
            <text class="hint__text" data-testid="quote-no-hint">{{ QUOTE_NO_HINT }}</text>
          </view>
        </view>

        <view class="divider-wrap">
          <view class="divider" />
        </view>

        <!-- 字段：凭证名称 -->
        <view class="field">
          <view class="label">
            <text class="label__text" data-testid="cred-label">{{ CRED_LABEL }}</text>
            <text class="label__star" data-testid="cred-star">*</text>
          </view>
          <view class="field__inner">
            <view class="select" data-testid="cred-select" @tap="toggleCredPanel">
              <view class="select__left">
                <view class="select__keybox">
                  <view class="ic ic-key" />
                </view>
                <text class="select__value" data-testid="cred-value">{{ credValue }}</text>
              </view>
              <view class="ic ic-chevron" />
            </view>
            <!-- 下拉面板（设计无展开稿 → 复用设计的选择框风格，记 missing-prd；台账 12-v2 为展开态帧） -->
            <view v-if="credOpen" class="panel" data-testid="cred-panel">
              <view
                v-for="cred in credentials"
                :key="cred.id"
                class="panel__row"
                :data-testid="`cred-option-${cred.id}`"
                @tap="pickCredential(cred.id)"
              >
                <text class="panel__title">{{ cred.alias }}</text>
              </view>
            </view>
          </view>
          <view class="hint">
            <view class="ic ic-info-blue" />
            <text class="hint__text hint__text--blue" data-testid="cred-hint">{{ CRED_HINT }}</text>
          </view>
        </view>
      </view>

      <!-- 模型列表卡（9fabffe3）-->
      <view class="card" data-testid="card-models">
        <view class="card__head">
          <view class="card__bar" />
          <text class="card__title" data-testid="card-models-title">{{ CARD_MODELS }}</text>
          <view class="card__spacer" />
          <view class="tag" data-testid="chip-model">
            <text class="tag__text tag__text--muted">{{ modelChip }}</text>
          </view>
        </view>

        <view class="block-gap">
          <!-- 空态（设计 dbdd7d3d：仅未选凭证时）-->
          <view v-if="!rows.length" class="empty" data-testid="model-empty">
            <view class="empty__icon">
              <view class="ic ic-empty" />
            </view>
            <view class="empty__title-wrap">
              <text class="empty__title" data-testid="model-empty-title">{{ MODEL_EMPTY_TITLE }}</text>
            </view>
            <view class="empty__desc-wrap">
              <text
                class="empty__desc"
                data-testid="model-empty-desc"
                :style="{ lineHeight: textLineBox(12) + 'px' }"
                >{{ MODEL_EMPTY_DESC }}</text
              >
            </view>
          </view>
          <!-- 已带出态：本帧设计稿无该态 → 复用序号 9 同族帧（page-9）的模型行设计 -->
          <view v-else class="models">
            <view
              v-for="row in rows"
              :key="row.key"
              class="model"
              :data-testid="`model-row-${row.name}`"
              @tap="onToggleRow(row.key)"
            >
              <view class="ic" :class="row.selected ? 'ic-check-on' : 'ic-check-off'" />
              <view class="model__info">
                <view class="model__name-row">
                  <text class="model__name">{{ row.name }}</text>
                  <view v-if="row.vendor" class="model__vendor">
                    <text class="model__vendor-text">{{ row.vendor }}</text>
                  </view>
                </view>
                <text v-if="row.priceText" class="model__price">{{ row.priceText }}</text>
              </view>
              <view class="tag tag--pill" :class="row.selected ? 'tag--pill-on' : 'tag--pill-off'">
                <text
                  class="tag__text"
                  :class="row.selected ? 'tag__text--on' : 'tag__text--muted'"
                  >{{ row.selected ? MODEL_STATUS_SELECTED : MODEL_STATUS_OPTIONAL }}</text
                >
              </view>
            </view>
          </view>
        </view>

        <view class="block-gap-sm">
          <view class="tip">
            <view class="ic ic-tip" />
            <text class="tip__text" data-testid="model-empty-tip" :style="{ lineHeight: textLineBox(11) + 'px' }">{{
              MODEL_EMPTY_TIP
            }}</text>
          </view>
        </view>
      </view>

      <!-- 填写须知卡（f4fab5a4）-->
      <view class="card" data-testid="card-notice">
        <view class="card__head">
          <view class="head-icon" :style="{ height: iconLineBox(18) + 'px' }">
            <view class="ic ic-notice" />
          </view>
          <text class="card__title card__title--sm" data-testid="card-notice-title">{{ CARD_NOTICE }}</text>
        </view>
        <view
          v-for="(item, i) in NOTICES"
          :key="i"
          class="notice-wrap"
          :class="{ 'notice-wrap--first': i === 0 }"
        >
          <view class="notice">
            <view class="notice__dot">
              <text class="notice__no" data-testid="notice-index">{{ i + 1 }}</text>
            </view>
            <text class="notice__text" data-testid="notice-text" :style="{ lineHeight: textLineBox(12) + 'px' }">{{
              item
            }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部操作条（0bf8e01d padding[12,16,28,16]）-->
    <view class="qf__bar">
      <view class="bar__hint">
        <view class="hint-icon" :style="{ height: iconLineBox(13) + 'px' }">
          <view class="ic ic-save-info" />
        </view>
        <text class="bar__hint-text" data-testid="bar-hint">{{ BAR_HINT }}</text>
      </view>
      <view class="bar__row">
        <view class="btn btn--ghost" data-testid="btn-draft" @tap="onDraft">{{ BTN_DRAFT }}</view>
        <view class="btn btn--primary" data-testid="btn-save" @tap="onSave">
          <view class="ic ic-save" />
          <text class="btn__text">{{ BTN_SAVE }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 12-v1【报价管理】新增报价单-初始态（page-26）— /pages/quote-form/index
 * 设计真源：.calicat/raw/pages/page-26/design.tree.json（430 宽 · 设计总高 1238 · 无 TabBar）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 * 文案/校验/请求体的逐条说明与缺口见 src/utils/quote-form-model.ts 顶部注释（不臆造字段与文案）。
 */
import { computed, ref } from 'vue'
import { ApiError } from '@/api/http'
import { credentialApi } from '@/api/credential'
import { quoteApi } from '@/api/quote'
import {
  BAR_HINT,
  BTN_DRAFT,
  BTN_SAVE,
  CARD_BASIC,
  CARD_MODELS,
  CARD_NOTICE,
  CRED_HINT,
  CRED_LABEL,
  CRED_PLACEHOLDER,
  MODEL_EMPTY_DESC,
  MODEL_EMPTY_TIP,
  MODEL_EMPTY_TITLE,
  MODEL_PRICING_PAGE,
  NAME_LABEL,
  NAME_MAX,
  NAME_PLACEHOLDER,
  NOTICES,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  QUOTE_NO_HINT,
  QUOTE_NO_LABEL,
  QUOTE_NO_TAG,
  REQUIRED_HINT,
  buildFormPayload,
  buildQuoteNoBox,
  iconLineBox,
  modelChipText,
  nameCountText,
  stepsFor,
  textLineBox,
  validateForSave
} from '@/utils/quote-form-model'
import {
  MODEL_STATUS_OPTIONAL,
  MODEL_STATUS_SELECTED,
  buildModelRows,
  toggleModel,
  type QuoteModelRow
} from '@/utils/quote-setup-model'

/** toast 占位文案（设计稿无 toast 稿，22 份 PRD 亦无 → missing-prd） */
const TOAST_DRAFT = '已存为草稿'
const TOAST_SAVED = '保存成功'
const TOAST_FAIL = '保存失败，请稍后重试'

interface CredOption {
  id: string
  alias: string
}

const name = ref('')
const credentialId = ref('')
const quoteNo = ref('')
const credAlias = ref('')
const credOpen = ref(false)
const credentials = ref<CredOption[]>([])
const rows = ref<QuoteModelRow[]>([])
const saving = ref(false)

const steps = stepsFor(1)
const quoteNoBox = computed(() => buildQuoteNoBox(quoteNo.value))
const countTextValue = computed(() => nameCountText(name.value))
const modelChip = computed(() => modelChipText(credentialId.value, rows.value))
const credValue = computed(() => credAlias.value || CRED_PLACEHOLDER)

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** 凭证选择：展开面板并按需拉取列表（api：GET /credentials，18-API Credential Tag） */
async function toggleCredPanel() {
  credOpen.value = !credOpen.value
  if (!credOpen.value || credentials.value.length) return
  try {
    const raw = await credentialApi.list({ page: 1, pageSize: 20 })
    const items = Array.isArray(raw?.items) ? raw.items : []
    credentials.value = items
      .filter((it) => it.id)
      .map((it) => ({ id: String(it.id), alias: String(it.alias ?? it.id) }))
  } catch (e) {
    credentials.value = []
    uni.showToast({ title: toastMessage(e), icon: 'none' })
  }
}

/** 选中凭证 → 拉详情带出模型清单（api：GET /credentials/{id}） */
async function pickCredential(id: string) {
  credOpen.value = false
  credentialId.value = id
  const picked = credentials.value.find((c) => c.id === id)
  credAlias.value = picked?.alias ?? ''
  try {
    const detail = await credentialApi.detail(id)
    credAlias.value = String(detail?.alias ?? credAlias.value)
    rows.value = buildModelRows(detail?.model_list)
  } catch (e) {
    rows.value = []
    uni.showToast({ title: toastMessage(e), icon: 'none' })
  }
}

function onToggleRow(key: string) {
  rows.value = toggleModel(rows.value, key)
}

function toastMessage(e: unknown): string {
  if (e instanceof ApiError && e.message) return e.message
  return TOAST_FAIL
}

function currentState() {
  return { name: name.value, credentialId: credentialId.value, rows: rows.value }
}

/** 存为草稿（A2「草稿无限暂存」→ 不做必填拦截） */
function onDraft() {
  if (saving.value) return
  void submit(false)
}

function onSave() {
  if (saving.value) return
  const errors = validateForSave(currentState())
  if (errors.length) {
    uni.showToast({ title: errors[0], icon: 'none' })
    return
  }
  void submit(true)
}

/** 提交：POST /quotes（主体）→ 有勾选时 POST /quotes/{id}/items（明细行）→ 提示/跳转 */
async function submit(advance: boolean) {
  saving.value = true
  try {
    const created = await quoteApi.create(buildFormPayload(currentState()))
    const quoteId = String(created?.quote_id ?? created?.quoteId ?? created?.id ?? '')
    const items = rows.value.filter((r) => r.selected).map((r) => ({ model_name: r.name }))
    if (quoteId && items.length) await quoteApi.setItems(quoteId, { items })
    uni.showToast({ title: advance ? TOAST_SAVED : TOAST_DRAFT, icon: 'none' })
    if (advance) {
      uni.navigateTo({ url: quoteId ? `${MODEL_PRICING_PAGE}?quoteId=${quoteId}` : MODEL_PRICING_PAGE })
    } else {
      uni.navigateBack({ delta: 1 })
    }
  } catch (e) {
    uni.showToast({ title: toastMessage(e), icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.qf {
  min-height: 100vh;
  background: $color-bg-page-2;
  display: flex;
  flex-direction: column;
}

/* 顶部导航（48 + 标题块 42 + 12 = 102） */
.qf__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 48px 16px 12px;
  background: $color-bg-card;
}
.nav__back,
.nav__help {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nav__titles {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 1;
  margin-left: 12px;
}
.nav__title {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 24px;
}
.nav__subtitle {
  display: block;
  font-size: 12px;
  color: $color-text-placeholder;
  line-height: 18px;
}

/* 内容区（padding[16,16,20,16] gap16） */
.qf__body {
  flex: 1;
  padding: 16px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  width: 100%;
  box-sizing: border-box;
  padding: 16px;
  border-radius: 16px;
  background: $color-bg-card;
  display: flex;
  flex-direction: column;
}
.card__head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card__bar {
  width: 5px;
  height: 16px;
  border-radius: 2px;
  background: $color-primary;
  flex-shrink: 0;
}
.card__title {
  font-size: 15px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 20px;
}
.card__title--sm {
  font-size: 13px;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 18px;
}
.card__spacer {
  flex: 1;
}
/* 图标行盒包裹层（字号 × 1.5，见 utils/quote-form-model.iconLineBox） */
.head-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.hint-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* 步骤卡 */
.step-card {
  width: 100%;
  box-sizing: border-box;
  padding: 16px;
  border-radius: 16px;
  background: $color-bg-card;
  display: flex;
  align-items: center;
}
.step {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.step__dot {
  width: 26px;
  height: 26px;
  border-radius: 13px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step--active .step__dot {
  background: $color-primary;
}
.step__no {
  font-size: 12px;
  font-weight: 700;
  color: $color-text-placeholder;
  line-height: 18px;
}
.step--active .step__no {
  color: #ffffff;
}
.step__texts {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.step__title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: $color-text-placeholder;
  line-height: 18px;
}
.step--active .step__title {
  color: $color-text-primary;
}
.step__desc {
  display: block;
  font-size: 11px;
  color: $color-border-strong;
  line-height: 15px;
}
.step--active .step__desc {
  color: $color-text-placeholder;
}
.step-line {
  flex: 1;
  height: 2px;
  border-radius: 2px;
  background: $color-border;
  margin: 0 12px;
}

/* 必填提示 */
.required {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.required__text {
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 16.5px;
}

/* 字段 */
.field {
  width: 100%;
  display: flex;
  flex-direction: column;
  padding-top: 16px;
}
.label {
  display: flex;
  align-items: center;
  gap: 4px;
}
.label--gap8 {
  gap: 8px;
}
.label__text {
  font-size: 13px;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 18px;
}
.label__star {
  font-size: 13px;
  font-weight: 600;
  color: $color-danger;
  line-height: 18px;
}
.field__inner {
  padding-top: 8px;
}
.divider-wrap {
  padding-top: 16px;
}
.divider {
  width: 100%;
  height: 1px;
  background: $color-bg-subtle;
}

/* 名称输入框 */
.input-box {
  width: 100%;
  height: 48px;
  box-sizing: border-box;
  padding: 0 14px;
  border-radius: 12px;
  background: $color-bg-page;
  border: 0.8px solid $color-border;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.input-box__input {
  flex: 1;
  min-width: 0;
  height: 20px;
  font-size: 14px;
  color: $color-text-primary;
}
.input-box__placeholder {
  font-size: 14px;
  color: $color-border-strong;
}
.counter {
  display: flex;
  justify-content: flex-end;
  padding-top: 6px;
}
.counter__text {
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 16.5px;
}

/* 单号只读框 */
.readonly-box {
  width: 100%;
  height: 48px;
  box-sizing: border-box;
  padding: 0 14px;
  border-radius: 12px;
  background: $color-bg-subtle;
  border: 0.8px solid $color-border-strong;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.readonly-box__left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.readonly-box__text {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: $color-text-placeholder;
  line-height: 21px;
  white-space: nowrap;
}
.sample-pill {
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  background: $color-bg-card;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.sample-pill__text {
  font-size: 10px;
  font-weight: 500;
  color: $color-text-placeholder;
  line-height: 15px;
}

/* 标签胶囊 */
.tag {
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.tag--blue {
  height: 18px;
  border-radius: 9px;
  background: $color-primary-weak;
}
.tag__text {
  font-size: 11px;
  font-weight: 500;
  color: $color-text-placeholder;
  line-height: 16.5px;
}
.tag__text--muted {
  font-size: 11px;
  color: $color-text-placeholder;
}
.tag--blue .tag__text {
  font-size: 10px;
  font-weight: 600;
  color: $color-primary;
  line-height: 15px;
}

/* 凭证选择框 */
.select {
  width: 100%;
  height: 48px;
  box-sizing: border-box;
  padding: 0 14px;
  border-radius: 12px;
  background: $color-bg-card;
  border: 0.8px solid $color-border;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.select__left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.select__keybox {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.select__value {
  display: block;
  font-size: 14px;
  color: $color-border-strong;
  line-height: 21px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 下拉面板（设计无展开稿 → 复用设计的选择框风格；台账 12-v2 为展开态帧） */
.panel {
  margin-top: 8px;
  border-radius: 12px;
  background: $color-bg-card;
  border: 0.8px solid $color-border;
  overflow: hidden;
}
.panel__row {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
}
.panel__title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 18px;
}

/* 模型行（复用序号 9 同族帧 page-9 的行设计） */
.models {
  display: flex;
  flex-direction: column;
}
.model {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}
.model__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.model__name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.model__name {
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 18px;
}
.model__vendor {
  height: 16px;
  padding: 0 6px;
  border-radius: 8px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
}
.model__vendor-text {
  font-size: 9px;
  font-weight: 500;
  color: $color-text-muted;
}
.model__price {
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 16px;
}
.tag--pill {
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
}
.tag--pill-on {
  background: $color-success-weak;
}
.tag--pill-off {
  background: $color-bg-subtle;
}
.tag__text--on {
  font-size: 10px;
  font-weight: 600;
  color: $color-success;
}
.tag__text--muted {
  font-size: 10px;
  font-weight: 600;
  color: $color-text-placeholder;
}

/* 说明行 */
.hint {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding-top: 6px;
}
.hint__text {
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 16.5px;
}
.hint__text--blue {
  color: $color-text-muted;
}

/* 模型列表空态 */
.block-gap {
  padding-top: 16px;
}
.block-gap-sm {
  padding-top: 12px;
}
.empty {
  width: 100%;
  box-sizing: border-box;
  padding: 28px 16px;
  border-radius: 12px;
  background: $color-bg-empty;
  border: 0.8px solid $color-border;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.empty__icon {
  width: 56px;
  height: 56px;
  border-radius: 28px;
  background: $color-primary-weak;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty__title-wrap {
  padding-top: 12px;
}
.empty__title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 20px;
}
.empty__desc-wrap {
  padding-top: 6px;
}
.empty__desc {
  display: block;
  font-size: 12px;
  color: $color-text-placeholder;
  line-height: 14.4px; /* 设计 lineHeight 1.2（见 textLineBox(12)） */
  text-align: center;
}

/* 提示卡 */
.tip {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 10px;
  background: $color-primary-weak;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.tip__text {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  color: $color-brand;
  line-height: 13.2px; /* 设计 lineHeight 1.2（见 textLineBox(11)） */
}

/* 填写须知 */
.notice-wrap {
  padding-top: 8px;
}
.notice-wrap--first {
  padding-top: 12px;
}
.notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.notice__dot {
  width: 18px;
  height: 18px;
  border-radius: 9px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.notice__no {
  font-size: 10px;
  font-weight: 700;
  color: $color-text-muted;
  line-height: 15px;
}
.notice__text {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: $color-text-muted;
  line-height: 14.4px; /* 设计 lineHeight 1.2（见 textLineBox(12)） */
}

/* 底部操作条 */
.qf__bar {
  background: $color-bg-card;
  padding: 12px 16px 28px;
}
.bar__hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.bar__hint-text {
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 16.5px;
}
.bar__row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 10px;
}
.btn {
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn--ghost {
  width: 128px;
  box-sizing: border-box;
  background: $color-bg-card;
  border: 0.8px solid $color-border;
  font-size: 14px;
  font-weight: 600;
  color: $color-text-muted;
  flex-shrink: 0;
}
.btn--primary {
  flex: 1;
  background: $color-primary;
  gap: 8px;
}
.btn__text {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
}

/* 图标（设计稿为 remixicon 字形 → CSS 形状占位，见台账登记） */
.ic {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.ic-back {
  width: 10px;
  height: 10px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
}
.ic-help {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid $color-text-muted;
  box-sizing: border-box;
}
.ic-required {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid $color-danger;
  box-sizing: border-box;
}
.ic-clear {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: $color-border-strong;
}
.ic-doc {
  width: 16px;
  height: 14px;
  border-radius: 2px;
  background: $color-text-placeholder;
}
.ic-info-sm {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid $color-text-placeholder;
  box-sizing: border-box;
}
.ic-info-blue {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid $color-primary;
  box-sizing: border-box;
}
.ic-chevron {
  width: 8px;
  height: 8px;
  border-right: 2px solid $color-text-placeholder;
  border-bottom: 2px solid $color-text-placeholder;
  transform: rotate(45deg);
}
.ic-key {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid $color-text-muted;
  box-sizing: border-box;
}
.ic-check-on {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: $color-primary;
}
.ic-check-off {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid $color-border-strong;
  box-sizing: border-box;
}
.ic-empty {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: $color-primary-border-light;
}
.ic-tip {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid $color-primary;
  box-sizing: border-box;
}
.ic-notice {
  width: 18px;
  height: 18px;
  border-radius: 3px;
  background: $color-text-muted;
}
.ic-save-info {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: $color-border-strong;
}
.ic-save {
  width: 14px;
  height: 14px;
  background: #ffffff;
  border-radius: 3px;
}
</style>
