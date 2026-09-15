<template>
  <view class="setup">
    <!-- 顶部导航（设计 3a66a8bd padding[48,16,12,16]）-->
    <view class="setup__nav">
      <view class="nav__back" data-testid="back" @tap="goBack">
        <view class="ic ic-back" />
      </view>
      <view class="nav__titles">
        <text class="setup__title">{{ PAGE_TITLE }}</text>
        <text class="setup__subtitle">{{ PAGE_SUBTITLE }}</text>
      </view>
      <view class="nav__help">
        <view class="ic ic-help" />
      </view>
    </view>

    <view class="setup__body">
      <!-- 卡1 报价主体（5e64dc90）-->
      <view class="card">
        <view class="card__head">
          <view class="card__bar" />
          <text class="card__title">{{ CARD_SUBJECT }}</text>
          <view class="card__spacer" />
          <view class="chip chip--neutral" data-testid="chip-add-company" @tap="goAddCompany">
            <view class="ic ic-plus" />
            <text class="chip__label chip__label--green">{{ CHIP_GO_ADD }}</text>
          </view>
        </view>
        <view class="field field--gap16">
          <!-- 设计 5f243d40：选择框前还有一层 padding-top 8 的容器（共 16+8） -->
          <view class="field__inner">
            <view class="select select--active" data-testid="subject-select" @tap="toggleSubject">
              <view class="select__left">
                <view class="select__keybox">
                  <view class="ic ic-company" />
                </view>
                <view class="select__info">
                  <text class="select__name" data-testid="subject-value">{{ subjectName }}</text>
                  <text v-if="subjectCode" class="select__sub">{{ subjectCode }}</text>
                </view>
              </view>
              <view class="ic ic-chevron" />
            </view>
            <view v-if="subjectOpen" class="panel" data-testid="subject-panel">
              <view
                v-for="opt in subjectOptions"
                :key="opt.id"
                class="panel__row"
                :data-testid="`subject-option-${opt.id}`"
                @tap="pickSubject(opt.id)"
              >
                <text class="panel__title">{{ opt.name }}</text>
                <text class="panel__sub">{{ opt.code }}</text>
              </view>
            </view>
          </view>
          <view class="hint" data-testid="subject-hint">
            <text class="hint__star">*</text>
            <text class="hint__text">{{ SUBJECT_HINT }}</text>
          </view>
        </view>
      </view>

      <!-- 卡2 基本信息（0b5dd403）-->
      <view class="card">
        <view class="card__head">
          <view class="card__bar" />
          <text class="card__title">{{ CARD_BASIC }}</text>
          <view class="card__spacer" />
          <view class="chip chip--success" data-testid="chip-basic-done">
            <view class="ic ic-check" />
            <text class="chip__label chip__label--success">{{ CHIP_DONE }}</text>
          </view>
        </view>

        <view class="field field--gap16">
          <view class="label">
            <text class="label__text">{{ NAME_LABEL }}</text>
            <text class="label__star">*</text>
          </view>
          <view class="input-box">
            <input
              v-model="name"
              class="input-box__input"
              data-testid="name-input"
              placeholder="请输入报价单名称"
              placeholder-class="input-box__placeholder"
              :maxlength="NAME_MAX"
            />
            <view v-if="name" class="ic ic-clear" @tap="name = ''" />
          </view>
          <view class="counter">
            <text class="counter__text" data-testid="name-count">{{ nameCount }}</text>
          </view>
        </view>

        <view class="field field--gap16">
          <view class="label">
            <text class="label__text">{{ CRED_LABEL }}</text>
            <text class="label__star">*</text>
          </view>
          <view class="select select--active" data-testid="cred-select" @tap="toggleCredPanel">
            <view class="select__left">
              <view class="select__keybox">
                <view class="ic ic-key" />
              </view>
              <view class="select__info">
                <text class="select__name" data-testid="cred-value">{{ credAlias || CRED_PLACEHOLDER }}</text>
                <text v-if="credMask" class="select__sub">{{ credMask }}</text>
              </view>
            </view>
            <view class="ic ic-chevron" />
          </view>
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
          <view v-if="credAlias" class="hint hint--success" data-testid="cred-hint">
            <view class="ic ic-check-circle" />
            <text class="hint__text hint__text--success">{{ credHint }}</text>
          </view>
        </view>
      </view>

      <!-- 卡3 模型列表（ec8f4041）-->
      <view class="card">
        <view class="card__head">
          <view class="card__bar" />
          <text class="card__title">{{ CARD_MODELS }}</text>
          <view class="card__spacer" />
          <view class="chip chip--info" data-testid="chip-model-count">
            <text class="chip__label chip__label--info">{{ countLabel }}</text>
          </view>
        </view>

        <view class="field field--gap12">
          <view class="toolbar">
            <view class="toolbar__all" data-testid="select-all" @tap="onToggleAll">
              <view class="ic" :class="allChecked ? 'ic-check-circle' : 'ic-circle'" />
              <text class="toolbar__all-text">{{ SELECT_ALL_TEXT }}</text>
            </view>
            <view class="toolbar__source" data-testid="source-hint">
              <view class="ic ic-info" />
              <text class="toolbar__source-text">{{ SOURCE_HINT }}</text>
            </view>
          </view>

          <view class="models">
            <view
              v-for="row in rows"
              :key="row.key"
              class="model"
              :data-testid="`model-row-${row.name}`"
              @tap="onToggleRow(row.key)"
            >
              <view class="ic" :class="row.selected ? 'ic-check-circle' : 'ic-circle'" />
              <view class="model__info">
                <view class="model__name-row">
                  <text class="model__name">{{ row.name }}</text>
                  <view v-if="row.vendor" class="model__vendor">
                    <text class="model__vendor-text">{{ row.vendor }}</text>
                  </view>
                </view>
                <text v-if="row.priceText" class="model__price">{{ row.priceText }}</text>
              </view>
              <view class="chip chip--pill" :class="row.selected ? 'chip--pill-on' : 'chip--pill-off'">
                <text
                  class="model__status"
                  :class="row.selected ? 'model__status--on' : 'model__status--off'"
                  >{{ row.selected ? MODEL_STATUS_SELECTED : MODEL_STATUS_OPTIONAL }}</text
                >
              </view>
              <view class="ic ic-chevron-sm" />
            </view>
          </view>

          <view class="model-note" data-testid="model-note">
            <view class="ic ic-light" />
            <text class="model-note__text">{{ MODEL_LIST_NOTE }}</text>
          </view>
        </view>
      </view>

      <!-- 卡4 联动提示（6e6629c0）-->
      <view class="tip">
        <view class="ic ic-tip" />
        <text class="tip__text" data-testid="tip-text">{{ TIP_TEXT }}</text>
      </view>
    </view>

    <!-- 底部操作条（c0413210 padding[12,16,28,16]）-->
    <view class="setup__bar">
      <view class="setup__bar-inner">
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
 * 序号 9【报价管理】模型报价设置（page-9）— 报价单新建/设置页
 * 设计真源：.calicat/raw/pages/page-9/design.tree.json（430 宽 · 设计总高 1211 · 无 TabBar）
 * 接口真源：18-API「Provider」/provider/profile · 「Credential」/credentials、/credentials/{id}
 *          · 「Quote」POST /quotes、POST /quotes/{quoteId}/items（前缀 /api/v1；方法/字段级 schema 为推断）
 * 交互分类（写进 .agents/state/aap-feature-status.csv 序号 9）：
 *   返回 = navigation(navigateBack) · 去新增 = navigation(/pages/profile-edit/index)
 *   主体/凭证选择 = api（GET /provider/profile、GET /credentials、GET /credentials/{id}）
 *   勾选/全选/字数 = client-only · 存为草稿 = api(POST /quotes) · 保存 = api(POST /quotes + /{id}/items) → navigation(/pages/model-pricing/index)
 *   帮助按钮 = client-only（设计有图标、PRD 无对应说明页 → 不臆造动作）
 * 细节与缺口见 src/utils/quote-setup-model.ts 顶部说明（不臆造字段/文案）。
 */
import { computed, onMounted, ref } from 'vue'
import { credentialApi } from '@/api/credential'
import { providerApi } from '@/api/provider'
import { quoteApi } from '@/api/quote'
import { ApiError } from '@/api/http'
import {
  BTN_DRAFT,
  BTN_SAVE,
  CARD_BASIC,
  CARD_MODELS,
  CARD_SUBJECT,
  CHIP_DONE,
  CHIP_GO_ADD,
  CRED_LABEL,
  CRED_PLACEHOLDER,
  MODEL_LIST_NOTE,
  MODEL_PRICING_PAGE,
  MODEL_STATUS_OPTIONAL,
  MODEL_STATUS_SELECTED,
  NAME_LABEL,
  NAME_MAX,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  PROFILE_EDIT_PAGE,
  SELECT_ALL_TEXT,
  SOURCE_HINT,
  SUBJECT_HINT,
  SUBJECT_PLACEHOLDER,
  TIP_TEXT,
  allSelected,
  buildItemsPayload,
  buildModelRows,
  buildQuotePayload,
  countText,
  credentialHintText,
  nameCountText,
  selectedCount,
  setAllSelected,
  toggleModel,
  validateForDraft,
  validateForSave,
  type QuoteModelRow
} from '@/utils/quote-setup-model'

/** toast 占位文案（设计稿无 toast 稿 → 记 missing-prd） */
const TOAST_DRAFT = '已存为草稿'
const TOAST_SAVED = '保存成功'
const TOAST_FAIL = '保存失败，请稍后重试'

interface SubjectOption {
  id: string
  name: string
  code: string
}

interface CredOption {
  id: string
  alias: string
}

const profile = ref<Record<string, unknown> | null>(null)
const credentials = ref<CredOption[]>([])
const rows = ref<QuoteModelRow[]>([])
const name = ref('')
const providerId = ref('')
const credentialId = ref('')
const credAlias = ref('')
const credMask = ref('')
const subjectOpen = ref(false)
const credOpen = ref(false)
const saving = ref(false)

const subjectOptions = computed<SubjectOption[]>(() => {
  const p = profile.value
  if (!p) return []
  const id = String(p.id ?? p.provider_id ?? '').trim()
  const company = String(p.company_name ?? p.companyName ?? '').trim()
  if (!id || !company) return []
  return [
    {
      id,
      name: company,
      code: String(p.unified_social_credit_code ?? p.unifiedSocialCreditCode ?? '').trim()
    }
  ]
})

const subjectName = computed(() => {
  const hit = subjectOptions.value.find((o) => o.id === providerId.value)
  return hit ? hit.name : SUBJECT_PLACEHOLDER
})
const subjectCode = computed(() => {
  const hit = subjectOptions.value.find((o) => o.id === providerId.value)
  return hit ? hit.code : ''
})
const nameCount = computed(() => nameCountText(name.value))
const countLabel = computed(() => countText(rows.value))
const credHint = computed(() => credentialHintText(rows.value.length))
const allChecked = computed(() => allSelected(rows.value))

onMounted(async () => {
  const [p, list] = await Promise.all([loadProfile(), loadCredentials()])
  profile.value = p
  credentials.value = list
  // 设计稿是「已选主体」态；主体唯一来源是档案（18-API 无公司列表接口）→ 有档案即视为已选
  if (!providerId.value && subjectOptions.value.length === 1) providerId.value = subjectOptions.value[0].id
})

async function loadProfile(): Promise<Record<string, unknown> | null> {
  try {
    return ((await providerApi.profile()) as unknown as Record<string, unknown>) ?? null
  } catch {
    return null
  }
}

async function loadCredentials(): Promise<CredOption[]> {
  try {
    const raw = await credentialApi.list({ page: 1, pageSize: 20 })
    const items = Array.isArray(raw?.items) ? raw.items : []
    return items
      .filter((it) => it.id)
      .map((it) => ({ id: String(it.id), alias: String(it.alias ?? it.id) }))
  } catch {
    return []
  }
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

function goAddCompany() {
  uni.navigateTo({ url: PROFILE_EDIT_PAGE })
}

function toggleSubject() {
  subjectOpen.value = !subjectOpen.value
  if (subjectOpen.value) credOpen.value = false
}

function pickSubject(id: string) {
  providerId.value = id
  subjectOpen.value = false
}

function toggleCredPanel() {
  credOpen.value = !credOpen.value
  if (credOpen.value) subjectOpen.value = false
}

/** 选凭证：拉详情 → 重建模型行（切换凭证自然重置勾选，设计原文如此） */
async function pickCredential(id: string) {
  credOpen.value = false
  credentialId.value = id
  const picked = credentials.value.find((c) => c.id === id)
  credAlias.value = picked?.alias ?? ''
  credMask.value = ''
  try {
    const detail = await credentialApi.detail(id)
    credAlias.value = String(detail?.alias ?? credAlias.value)
    credMask.value = String(detail?.api_key_mask ?? '')
    rows.value = buildModelRows(detail?.model_list)
  } catch (e) {
    rows.value = []
    uni.showToast({ title: toastMessage(e), icon: 'none' })
  }
}

function onToggleRow(key: string) {
  rows.value = toggleModel(rows.value, key)
}

function onToggleAll() {
  rows.value = setAllSelected(rows.value, !allSelected(rows.value))
}

function toastMessage(e: unknown): string {
  if (e instanceof ApiError && e.message) return e.message
  return TOAST_FAIL
}

function currentState() {
  return { name: name.value, providerId: providerId.value, credentialId: credentialId.value, rows: rows.value }
}

function onDraft() {
  if (saving.value) return
  const errors = validateForDraft(currentState())
  if (errors.length) {
    uni.showToast({ title: errors[0], icon: 'none' })
    return
  }
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
    const created = await quoteApi.create(buildQuotePayload(currentState()))
    const quoteId = String(created?.quote_id ?? created?.quoteId ?? created?.id ?? '')
    const items = buildItemsPayload(rows.value).items
    if (quoteId && items.length) await quoteApi.setItems(quoteId, { items })
    uni.showToast({ title: advance ? TOAST_SAVED : TOAST_DRAFT, icon: 'none' })
    if (advance) {
      uni.navigateTo({
        url: quoteId ? `${MODEL_PRICING_PAGE}?quoteId=${quoteId}` : MODEL_PRICING_PAGE
      })
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

.setup {
  min-height: 100vh;
  background: $color-bg-page-2;
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
.setup__nav {
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
.setup__title {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 24px;
}
.setup__subtitle {
  display: block;
  font-size: 12px;
  color: $color-text-placeholder;
  line-height: 18px;
}

/* 内容区 */
.setup__body {
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
.card__spacer {
  flex: 1;
}

/* 标签 chip */
.chip {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  flex-shrink: 0;
}
.chip--neutral {
  background: $color-chip-neutral;
}
.chip--success {
  background: $color-success-weak;
}
.chip--info {
  background: $color-primary-weak;
}
.chip__label {
  font-size: 10px;
  font-weight: 600;
}
.chip__label--green {
  color: $color-success-text-2;
}
.chip__label--success {
  color: $color-success;
}
.chip__label--info {
  font-size: 11px;
  color: $color-primary;
}

/* 字段块（设计 padding-top 16 / 12） */
.field {
  width: 100%;
  display: flex;
  flex-direction: column;
}
.field--gap16 {
  padding-top: 16px;
}
.field--gap12 {
  padding-top: 12px;
}
/* 设计 5f243d40：选择框前额外一层 padding-top 8（卡1 无字段标签行，故单独补） */
.field__inner {
  padding-top: 8px;
}
.label {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-bottom: 8px;
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

/* 选择框 / 输入框 */
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
.select--active {
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
  background: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.select__info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.select__name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: $color-text-primary;
  line-height: 17px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.select__sub {
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 15px;
}
.input-box {
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
.input-box__input {
  flex: 1;
  min-width: 0;
  height: 20px;
  font-size: 14px;
  font-weight: 500;
  color: $color-text-primary;
}
.counter {
  display: flex;
  justify-content: flex-end;
  padding-top: 6px;
}
.counter__text {
  font-size: 11px;
  color: $color-text-placeholder;
}

/* 下拉面板（设计无展开稿 → 复用设计的选择框风格，记 missing-prd） */
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
.panel__sub {
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 15px;
}

/* 说明行 */
.hint {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding-top: 6px;
}
.hint--success {
  align-items: center;
}
.hint__star {
  font-size: 13px;
  font-weight: 600;
  color: $color-danger;
  line-height: 18px;
}
.hint__text {
  font-size: 11px;
  color: $color-text-hint;
  line-height: 16px;
}
.hint__text--success {
  color: $color-success;
}

/* 模型列表工具栏 */
.toolbar {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 10px;
  background: $color-bg-page;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.toolbar__all {
  display: flex;
  align-items: center;
  gap: 8px;
}
.toolbar__all-text {
  font-size: 12px;
  font-weight: 500;
  color: $color-text-secondary-2;
}
.toolbar__source {
  display: flex;
  align-items: center;
  gap: 4px;
}
.toolbar__source-text {
  font-size: 11px;
  color: $color-text-placeholder;
}

/* 模型行 */
.models {
  display: flex;
  flex-direction: column;
  padding-top: 12px;
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
.chip--pill {
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
}
.chip--pill-on {
  background: $color-success-weak;
}
.chip--pill-off {
  background: $color-bg-subtle;
}
.model__status {
  font-size: 10px;
  font-weight: 600;
}
.model__status--on {
  color: $color-success;
}
.model__status--off {
  color: $color-text-placeholder;
}
.model-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding-top: 12px;
}
.model-note__text {
  font-size: 11px;
  color: $color-text-placeholder;
}

/* 联动提示卡 */
.tip {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border-radius: 14px;
  background: $color-primary-weak;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.tip__text {
  font-size: 11px;
  color: $color-brand;
  line-height: 16px;
  white-space: pre-line;
}

/* 底部操作条 */
.setup__bar {
  background: $color-bg-card;
  padding: 12px 16px 28px;
}
.setup__bar-inner {
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

/* 图标（设计稿用 remixicon 字形；小程序/H5 跨端一致性优先 → CSS 形状占位，见台账登记） */
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
}
.ic-chevron {
  width: 8px;
  height: 8px;
  border-right: 2px solid $color-primary;
  border-bottom: 2px solid $color-primary;
  transform: rotate(45deg);
}
.ic-chevron-sm {
  width: 6px;
  height: 6px;
  border-right: 2px solid $color-border-strong;
  border-bottom: 2px solid $color-border-strong;
  transform: rotate(-45deg);
}
.ic-company {
  width: 12px;
  height: 10px;
  background: #ffffff;
  border-radius: 2px;
}
.ic-key {
  width: 12px;
  height: 12px;
  background: #ffffff;
  border-radius: 50%;
}
.ic-plus {
  width: 10px;
  height: 10px;
  background: $color-success-text-2;
  border-radius: 2px;
}
.ic-check {
  width: 11px;
  height: 11px;
  background: $color-success;
  border-radius: 2px;
}
.ic-check-circle {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: $color-primary;
}
.ic-circle {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid $color-border-strong;
  box-sizing: border-box;
}
.ic-clear {
  width: 14px;
  height: 14px;
  background: $color-border-strong;
  border-radius: 50%;
}
.ic-info {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid $color-text-placeholder;
  box-sizing: border-box;
}
.ic-light {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: $color-border-strong;
}
.ic-tip {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: $color-primary;
}
.ic-save {
  width: 14px;
  height: 14px;
  background: #ffffff;
  border-radius: 3px;
}
</style>
