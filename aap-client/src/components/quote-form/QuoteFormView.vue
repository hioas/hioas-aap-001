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
      <!-- 步骤卡（7acff570；本帧有 / page-apikey 帧无 → 见 variantFlags）-->
      <view v-if="flags.showSteps" class="step-card">
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
          <view v-if="flags.showRequired" class="required" data-testid="chip-required">
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
          <view v-if="flags.showQuoteNoHint" class="hint">
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
            <view
              class="select"
              :class="{ 'select--open': credOpen }"
              data-testid="cred-select"
              :data-open="credOpen ? 'true' : 'false'"
              @tap="toggleCredPanel"
            >
              <view class="select__left">
                <view class="select__keybox">
                  <view class="ic ic-key" />
                </view>
                <text class="select__value" data-testid="cred-value">{{ credValue }}</text>
              </view>
              <view class="ic ic-chevron" :class="{ 'ic-chevron--up': credOpen }" />
            </view>
            <!-- 下拉面板（设计 566c12d1：紧贴选择框下沿 · padding 6 · r[0,0,12,12] · 描边 0.8 #2563EB） -->
            <view v-if="credOpen" class="panel" data-testid="cred-panel">
              <view
                v-for="cred in credentials"
                :key="cred.id"
                class="panel__row"
                :class="{ 'panel__row--on': cred.id === credentialId }"
                :data-testid="`cred-option-${cred.id}`"
                :data-selected="cred.id === credentialId ? 'true' : 'false'"
                @tap="pickCredential(cred.id)"
              >
                <view class="panel__left">
                  <view class="panel__icon" :class="{ 'panel__icon--on': cred.id === credentialId }">
                    <view class="ic ic-key-sm" :class="{ 'ic-key-sm--on': cred.id === credentialId }" />
                  </view>
                  <view class="panel__info">
                    <view class="panel__name-row">
                      <text class="panel__title">{{ cred.alias }}</text>
                      <view v-if="cred.recommended" class="rec-tag" :data-testid="`cred-recommended-${cred.id}`">
                        <text class="rec-tag__text" :style="{ lineHeight: iconLineBox(9) + 'px' }">{{ CRED_RECOMMENDED }}</text>
                      </view>
                    </view>
                    <text
                      v-if="cred.subText"
                      class="panel__sub"
                      :data-testid="`cred-sub-${cred.id}`"
                      :style="{ lineHeight: textLineBox(11) + 'px' }"
                      >{{ cred.subText }}</text
                    >
                  </view>
                </view>
                <!-- 选中态：对勾（本帧面板首项画的就是这个态；未选凭证时不出现，见台账帧内矛盾说明） -->
                <view v-if="cred.id === credentialId" class="ic ic-picked" :data-testid="`cred-check-${cred.id}`" />
                <view v-else-if="cred.envTag" class="env-tag" :data-testid="`cred-tag-${cred.id}`">
                  <text class="env-tag__text" :style="{ lineHeight: textLineBox(10) + 'px' }">{{ cred.envTag }}</text>
                </view>
              </view>

              <view class="panel__divider-wrap">
                <view class="panel__divider" />
              </view>
              <view class="panel__action-wrap">
                <view class="panel__action" data-testid="cred-create" @tap="onCreateCredential">
                  <view class="icon-line" :style="{ height: iconLineBox(15) + 'px' }">
                    <view class="ic ic-plus" />
                  </view>
                  <text class="panel__action-text" data-testid="cred-create-text">{{ CRED_CREATE_ACTION }}</text>
                </view>
              </view>
            </view>
          </view>
          <view class="hint" :style="{ paddingTop: flags.credHintGap + 'px' }">
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
            <view class="empty__desc-wrap" :style="{ paddingTop: flags.emptyDescGap + 'px' }">
              <text
                class="empty__desc"
                data-testid="model-empty-desc"
                :style="{ lineHeight: textLineBox(12) + 'px' }"
                >{{ flags.emptyDesc }}</text
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

        <view v-if="flags.showEmptyTip" class="block-gap-sm">
          <view class="tip">
            <view class="ic ic-tip" />
            <text class="tip__text" data-testid="model-empty-tip" :style="{ lineHeight: textLineBox(11) + 'px' }">{{
              MODEL_EMPTY_TIP
            }}</text>
          </view>
        </view>
      </view>

      <!-- 填写须知卡（f4fab5a4；本帧有 / page-apikey 帧无 → 见 variantFlags）-->
      <view v-if="flags.showNotice" class="card" data-testid="card-notice">
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
 * 序号 12-v1 / 12-v2【报价管理】新增报价单（同页两帧的共用视图）
 *   12-v1 → /pages/quote-form/index   （page-26：初始态，面板收起，有步骤卡与空态提示卡）
 *   12-v2 → /pages/quote-form/apikey  （page-apikey：凭证下拉展开态，无步骤卡/无提示卡，面板紧贴选择框）
 * 设计真源：.calicat/raw/pages/{page-26,page-apikey}/design.tree.json
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 * 文案/校验/请求体的逐条说明与缺口见 src/utils/quote-form-model.ts 顶部注释（不臆造字段与文案）。
 */
import { computed, onMounted, ref } from 'vue'
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
  CRED_CREATE_ACTION,
  CRED_HINT,
  CRED_LABEL,
  CRED_PLACEHOLDER,
  CRED_RECOMMENDED,
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
  SETTINGS_PAGE,
  VARIANT_INITIAL,
  buildCredOptions,
  buildFormPayload,
  buildQuoteNoBox,
  iconLineBox,
  modelChipText,
  nameCountText,
  stepsFor,
  textLineBox,
  validateForSave,
  variantFlags,
  type CredOption,
  type QuoteFormVariant
} from '@/utils/quote-form-model'
import {
  MODEL_STATUS_OPTIONAL,
  MODEL_STATUS_SELECTED,
  buildModelRows,
  toggleModel,
  type QuoteModelRow
} from '@/utils/quote-setup-model'

const props = withDefaults(defineProps<{ variant?: QuoteFormVariant }>(), { variant: VARIANT_INITIAL })

/** 同页两帧的差异开关（纯函数，见 quote-form-model.ts） */
const flags = variantFlags(props.variant)

/** toast 占位文案（设计稿无 toast 稿，22 份 PRD 亦无 → missing-prd） */
const TOAST_DRAFT = '已存为草稿'
const TOAST_SAVED = '保存成功'
const TOAST_FAIL = '保存失败，请稍后重试'

const name = ref('')
const credentialId = ref('')
const quoteNo = ref('')
const credAlias = ref('')
const credOpen = ref(flags.panelOpen)
const credentials = ref<CredOption[]>([])
const rows = ref<QuoteModelRow[]>([])
const saving = ref(false)

const steps = stepsFor(1)
const quoteNoBox = computed(() => buildQuoteNoBox(quoteNo.value))
const countTextValue = computed(() => nameCountText(name.value))
const modelChip = computed(() => modelChipText(credentialId.value, rows.value))
const credValue = computed(() => credAlias.value || CRED_PLACEHOLDER)

/** 展开态帧（page-apikey）进页面即展开面板 → 首屏就要候选项 */
onMounted(() => {
  if (credOpen.value) void loadCredentials()
})

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** 拉候选项（api：GET /credentials，18-API Credential Tag） */
async function loadCredentials() {
  try {
    const raw = await credentialApi.list({ page: 1, pageSize: 20 })
    credentials.value = buildCredOptions(raw?.items)
  } catch (e) {
    credentials.value = []
    uni.showToast({ title: toastMessage(e), icon: 'none' })
  }
}

/** 凭证选择：展开面板并按需拉取列表（api：GET /credentials） */
async function toggleCredPanel() {
  credOpen.value = !credOpen.value
  if (!credOpen.value || credentials.value.length) return
  await loadCredentials()
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

/** 面板底部操作「前往「我的设置」新建凭证」→ 画布第 23 页「我的设置」（台账序号 23，尚未实现） */
function onCreateCredential() {
  uni.navigateTo({ url: SETTINGS_PAGE })
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

/* 凭证选择框（展开态：上圆角 + 主色描边 → 与面板拼成一个连续盒子） */
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
.select--open {
  border-radius: 12px 12px 0 0;
  border-color: $color-primary;
}
.select--open .select__keybox {
  background: $color-primary-weak;
}
.select--open .ic-key {
  border-color: $color-primary;
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

/* 下拉面板（设计 566c12d1：紧贴选择框下沿 · padding 6 · r[0,0,12,12] · 描边 0.8 #2563EB）
   注：上边框去掉 —— 与选择框下边框拼成 1 条连续描边（设计稿为一个连续盒子） */
.panel {
  width: 100%;
  box-sizing: border-box;
  padding: 6px;
  border-radius: 0 0 12px 12px;
  background: $color-bg-card;
  border: 0.8px solid $color-primary;
  border-top: 0;
}
/* 选项行（padding[10,12,10,12] · r10 · 选中底 #EFF6FF） */
.panel__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 10px;
}
.panel__row--on {
  background: $color-primary-weak;
}
.panel__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.panel__icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.panel__icon--on {
  background: $color-primary;
}
.panel__info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}
.panel__name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel__title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 16.8px; /* 设计 lineHeight 1.2（见 textLineBox(14)） */
  white-space: nowrap;
}
/* 推荐标「常用」（设计：h16 r8 #2563EB · 9px SemiBold 白字） */
.rec-tag {
  height: 16px;
  padding: 0 6px;
  border-radius: 8px;
  background: $color-primary;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.rec-tag__text {
  display: block;
  font-size: 9px;
  font-weight: 600;
  color: #ffffff;
}
/* 副行「sk-prod-••••••••2f9a · 12 个模型」（设计 11px #94A3B8 h16） */
.panel__sub {
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 13.2px; /* 设计 lineHeight 1.2（见 textLineBox(11)） */
  white-space: nowrap;
}
/* 环境标「沙箱 / 专用」（设计：h20 r10 #F1F5F9 · 10px Medium #64748B） */
.env-tag {
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.env-tag__text {
  display: block;
  font-size: 10px;
  font-weight: 500;
  color: $color-text-muted;
}
.panel__divider-wrap {
  width: 100%;
  padding-top: 4px;
}
.panel__divider {
  height: 1px;
  background: $color-bg-subtle;
}
.panel__action-wrap {
  width: 100%;
  padding-top: 4px;
}
/* 面板底部操作（padding[8,12,8,12] 居中 gap8） */
.panel__action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 12px;
}
.panel__action-text {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: $color-primary;
  line-height: 14.4px; /* 设计 lineHeight 1.2（见 textLineBox(12)） */
}
/* 图标行盒 = 字号 × 1.5（dev SKILL §4.9/§4.12）：面板底部操作图标 15 → 22.5 */
.icon-line {
  display: flex;
  align-items: center;
  flex-shrink: 0;
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
  /* 设计 stroke align=center（不参与布局）→ 用 ring，避免盒高 +2（page-26 164 / page-apikey 158，见 dev SKILL §4.8） */
  box-shadow: 0 0 0 0.8px $color-border;
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
/* 展开态：箭头朝上 + 主色（设计 566c12d1 的 chevron #2563EB） */
.ic-chevron--up {
  border-color: $color-primary;
  transform: rotate(-135deg);
}
/* 面板候选项图标（设计 34×34 底内的 17px 字形 → CSS 形状占位；选中为白）
   注：用「实心圆」而不是描边方块 —— 描边方块在 430 宽截图里会被误读成复选框（vision 实测），
   设计稿此处是钥匙/文档类字形，圆头更接近钥匙语义且不会与勾选框混淆。 */
.ic-key-sm {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: $color-text-muted;
}
.ic-key-sm--on {
  background: #ffffff;
}
/* 已选对勾（设计 566c12d1 首选项右侧 18px #2563EB） */
.ic-picked {
  width: 12px;
  height: 7px;
  border-left: 2px solid $color-primary;
  border-bottom: 2px solid $color-primary;
  transform: rotate(-45deg);
}
/* 面板底部操作「+」图标（设计 \\uea11，15px #2563EB 圆形加号） */
.ic-plus {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 1.5px solid $color-primary;
  box-sizing: border-box;
  position: relative;
}
.ic-plus::before,
.ic-plus::after {
  content: '';
  position: absolute;
  background: $color-primary;
}
.ic-plus::before {
  left: 50%;
  top: 50%;
  width: 7px;
  height: 1.5px;
  transform: translate(-50%, -50%);
}
.ic-plus::after {
  left: 50%;
  top: 50%;
  width: 1.5px;
  height: 7px;
  transform: translate(-50%, -50%);
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
