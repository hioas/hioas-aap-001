<template>
  <view class="pricing">
    <!-- 顶部导航（设计 5e8ed34f padding[48,16,12,16]）-->
    <view class="pricing__nav">
      <view class="nav__back" data-testid="back" @tap="goBack">
        <view class="ic ic-back" />
      </view>
      <view class="nav__titles">
        <text class="nav__title" data-testid="nav-title">{{ model.modelName }}</text>
        <text class="nav__subtitle" data-testid="nav-subtitle">{{ PAGE_SUBTITLE }}</text>
      </view>
      <view class="nav__spacer" />
      <view class="nav__save" data-testid="save-top" @tap="onSave">{{ NAV_SAVE_TEXT }}</view>
    </view>

    <view class="pricing__body">
      <!-- 卡1 模型信息（ea10ef4e padding[14,16,14,16] gap10 r16）-->
      <view class="card card--info">
        <view class="info__head">
          <view class="info__badge">
            <text class="info__badge-text" data-testid="model-badge">{{ model.badgeNo }}</text>
          </view>
          <text class="info__name" data-testid="model-name">{{ model.modelName }}</text>
          <view class="info__spacer" />
          <view class="ic ic-chevron-up" data-testid="collapse-model" @tap="infoOpen = !infoOpen" />
        </view>
        <text v-if="infoOpen" class="info__summary" data-testid="tier-summary">{{ summary }}</text>
      </view>

      <!-- 卡2 计费方式（7d82920c padding[14,16,14,16] gap12 r16）-->
      <view class="card card--mode">
        <view class="mode__field">
          <text class="field__label" data-testid="tier-label">{{ TIER_LABEL }}</text>
          <view class="box box--input">
            <input
              class="box__input"
              data-testid="tier-input"
              :value="tier"
              @input="onTierInput($event)"
            />
          </view>
        </view>
        <view class="mode__row">
          <view class="box box--select box--grow" data-testid="mode-select" @tap="onPendingOptions">
            <text class="box__text">{{ model.billingMode }}</text>
            <view class="ic ic-caret" />
          </view>
          <view class="box box--branch" data-testid="btn-add-branch" @tap="onPendingOptions">
            <view class="ic ic-plus-blue" />
            <text class="branch__text">{{ ADD_BRANCH_TEXT }}</text>
          </view>
        </view>
      </view>

      <!-- 卡3 Token 价格 + 媒体定价（61e7d071 padding[14,16,14,16] gap14 r16）-->
      <view class="card card--price">
        <view class="price__head">
          <text class="price__title" data-testid="token-card-title">{{ TOKEN_CARD_TITLE }}</text>
          <view class="unit">
            <text class="unit__text" data-testid="unit-label">{{ PRICE_UNIT_LABEL }}</text>
          </view>
        </view>

        <view class="price__rows">
          <view v-for="(row, ri) in tokenRows" :key="ri" class="price__row">
            <view v-for="f in row" :key="f.key" class="price__field">
              <view class="price__label-row">
                <view
                  class="check"
                  :class="{ 'check--on': f.enabled }"
                  :data-testid="`check-${f.key}`"
                  @tap="onTogglePrice(f.key)"
                >
                  <view v-if="f.enabled" class="check__tick" />
                </view>
                <text class="price__label" :data-testid="`price-label-${f.key}`">{{ f.label }}</text>
              </view>
              <view class="box box--input">
                <input
                  class="box__input"
                  :data-testid="`price-${f.key}`"
                  :value="f.value"
                  @input="onPriceInput(f.key, $event)"
                />
              </view>
            </view>
          </view>
        </view>

        <view class="divider" />

        <view class="media__head">
          <text class="media__title" data-testid="media-title">{{ MEDIA_TITLE }}</text>
          <view class="ic ic-chevron-up-sm" data-testid="collapse-media" @tap="mediaOpen = !mediaOpen" />
        </view>
        <view v-if="mediaOpen" class="media__cols">
          <view class="media__col">
            <view v-for="f in mediaColA" :key="f.key" class="price__field">
              <view class="price__label-row">
                <view
                  class="check"
                  :class="{ 'check--on': f.enabled }"
                  :data-testid="`check-${f.key}`"
                  @tap="onTogglePrice(f.key)"
                >
                  <view v-if="f.enabled" class="check__tick" />
                </view>
                <text class="media__label" :data-testid="`media-label-${f.key}`">{{ f.label }}</text>
              </view>
              <view class="box box--input">
                <input
                  class="box__input"
                  :data-testid="`price-${f.key}`"
                  :value="f.value"
                  @input="onPriceInput(f.key, $event)"
                />
              </view>
            </view>
          </view>
          <view class="media__col">
            <view v-for="f in mediaColB" :key="f.key" class="price__field">
              <view class="price__label-row">
                <view
                  class="check"
                  :class="{ 'check--on': f.enabled }"
                  :data-testid="`check-${f.key}`"
                  @tap="onTogglePrice(f.key)"
                >
                  <view v-if="f.enabled" class="check__tick" />
                </view>
                <text class="media__label" :data-testid="`media-label-${f.key}`">{{ f.label }}</text>
              </view>
              <view class="box box--input">
                <input
                  class="box__input"
                  :data-testid="`price-${f.key}`"
                  :value="f.value"
                  @input="onPriceInput(f.key, $event)"
                />
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- 卡4 请求规则计费（53b7d46b padding[14,16,14,16] gap12 r16）-->
      <view class="card card--rule">
        <view class="rule__head">
          <view class="rule__head-left">
            <view class="rule__bar" />
            <text class="rule__title" data-testid="rule-card-title">{{ RULE_CARD_TITLE }}</text>
          </view>
          <view class="ic ic-chevron-up-sm" data-testid="collapse-rule" @tap="ruleOpen = !ruleOpen" />
        </view>
        <text class="rule__note" data-testid="rule-note">{{ RULE_NOTE }}</text>

        <template v-if="ruleOpen">
          <view
            v-for="g in ruleGroups"
            :key="g.no"
            class="rule-group"
            :data-testid="`rule-group-${g.no}`"
          >
            <view class="rule-group__head">
              <text class="rule-group__title" :data-testid="`rule-group-title-${g.no}`">{{ titleOf(g) }}</text>
              <view class="ic ic-trash" :data-testid="`rule-delete-${g.no}`" @tap="onRemoveGroup(g.no)" />
            </view>

            <view class="rule-group__row">
              <view
                class="box box--cond box--grow"
                :data-testid="`rule-field-${g.no}`"
                @tap="onPendingOptions"
              >
                <text class="cond__text">{{ g.field }}</text>
                <view class="ic ic-caret-sm" />
              </view>
              <view
                class="box box--cond box--grow"
                :data-testid="`rule-granularity-${g.no}`"
                @tap="onPendingOptions"
              >
                <text class="cond__text">{{ g.granularity }}</text>
                <view class="ic ic-caret-sm" />
              </view>
            </view>

            <view class="rule-group__row">
              <view class="box box--cond box--grow" :data-testid="`rule-tz-${g.no}`" @tap="onPendingOptions">
                <text class="cond__text">{{ g.tz }}</text>
                <view class="ic ic-caret-sm" />
              </view>
              <view class="box box--cond box--grow" :data-testid="`rule-op-${g.no}`" @tap="onPendingOptions">
                <text class="cond__text">{{ g.op }}</text>
                <view class="ic ic-caret-sm" />
              </view>
            </view>

            <view class="rule-group__row">
              <view class="box box--cond box--input box--grow">
                <input
                  class="cond__input"
                  :data-testid="`rule-value-${g.no}`"
                  :value="g.value"
                  :placeholder="VALUE_PLACEHOLDER"
                  placeholder-class="cond__placeholder"
                  @input="onRuleInput(g.no, 'value', $event)"
                />
              </view>
            </view>

            <view class="rule-group__actions">
              <view class="action" :data-testid="`btn-add-param-${g.no}`" @tap="onPendingOptions">
                <view class="ic ic-plus-sm" />
                <text class="action__text">{{ ADD_PARAM_TEXT }}</text>
              </view>
              <view class="action" :data-testid="`btn-add-time-${g.no}`" @tap="onPendingOptions">
                <view class="ic ic-plus-sm" />
                <text class="action__text">{{ ADD_TIME_TEXT }}</text>
              </view>
            </view>

            <view class="rule-group__row rule-group__row--multi">
              <text class="multiplier__label" :data-testid="`rule-multiplier-label-${g.no}`">{{ MULTIPLIER_LABEL }}</text>
              <view class="box box--cond box--input box--grow">
                <input
                  class="cond__input"
                  :data-testid="`rule-multiplier-${g.no}`"
                  :value="g.multiplier"
                  @input="onRuleInput(g.no, 'multiplier', $event)"
                />
              </view>
            </view>

            <text class="rule-group__note" :data-testid="`rule-group-note-${g.no}`">{{ MULTIPLIER_NOTE }}</text>
          </view>

          <view class="rule__add" data-testid="btn-add-group" @tap="onAddGroup">
            <view class="ic ic-plus-blue" />
            <text class="rule__add-text">{{ ADD_RULE_GROUP_TEXT }}</text>
          </view>
        </template>
        <text v-else class="rule__hint" data-testid="rule-hint">{{ RULE_HINT }}</text>
      </view>
    </view>

    <!-- 底部操作条（69e37d20 padding[12,16,16,16]）-->
    <view class="pricing__bar">
      <view class="pricing__save" data-testid="save-bottom" @tap="onSave">
        <view class="ic ic-check-white" />
        <text class="pricing__save-text">{{ BOTTOM_SAVE_TEXT }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 11【报价管理】模型定价-详情（page-11）
 * 设计真源：.calicat/raw/pages/page-11/design.tree.json（430 宽 · 设计总高 1541 · 无 TabBar）
 * 接口真源：18-API「Quote」→ GET /quotes/items/{itemId} · GET /quotes/{quoteId}/items · PUT /quotes/items/{itemId}
 * 交互分类（写进 .agents/state/aap-feature-status.csv 序号 11）：
 *   返回 = navigation(navigateBack) · 顶栏「保存」/ 底部「保存价格」 = api(PUT /quotes/items/{itemId})
 *   卡1/媒体/规则的折叠箭头、勾选框、档位与价格输入、规则组增删、条件选择框 = client-only
 *   （条件/计价方式的下拉**选项集合**在 22 份 PRD 与 18-API 零命中 → 只回显设计值/服务端值 + 占位提示，不造选项）
 * 细节与缺口见 src/utils/model-pricing-model.ts 顶部说明（不臆造字段/文案）。
 */
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/api/http'
import { quoteApi } from '@/api/quote'
import {
  ADD_BRANCH_TEXT,
  ADD_PARAM_TEXT,
  ADD_RULE_GROUP_TEXT,
  ADD_TIME_TEXT,
  BOTTOM_SAVE_TEXT,
  MEDIA_TITLE,
  MULTIPLIER_LABEL,
  MULTIPLIER_NOTE,
  NAV_SAVE_TEXT,
  PAGE_SUBTITLE,
  PRICE_UNIT_LABEL,
  QUOTE_ID_KEY,
  QUOTE_ITEM_ID_KEY,
  RULE_CARD_TITLE,
  RULE_HINT,
  RULE_NOTE,
  TIER_LABEL,
  TOAST_FAIL,
  TOAST_MISSING_ITEM,
  TOAST_SAVED,
  TOKEN_CARD_TITLE,
  VALUE_PLACEHOLDER,
  addRuleGroup,
  buildItemPayload,
  buildItemViewModel,
  removeRuleGroup,
  ruleGroupTitle,
  setPriceValue,
  setRuleValue,
  tierSummaryText,
  togglePriceField,
  validateItem,
  type PriceField,
  type RequestRuleGroup
} from '@/utils/model-pricing-model'

/** 占位提示（下拉选项集合缺依据 → missing-prd；文案本身为占位，已记台账） */
const OPTIONS_PENDING_TOAST = '选项待服务端下发'

const model = ref(buildItemViewModel(null))
const tier = ref('')
const infoOpen = ref(true)
const mediaOpen = ref(true)
const ruleOpen = ref(true)
const saving = ref(false)

const summary = computed(() => tierSummaryText(model.value.priceFields))
const tokenFields = computed(() => model.value.priceFields.filter((f) => f.group === 'token'))
const mediaFields = computed(() => model.value.priceFields.filter((f) => f.group === 'media'))
const ruleGroups = computed(() => model.value.ruleGroups)

/** Token 价格两列：行1 输入/输出 · 行2 缓存读取/写入 · 行3 1 小时缓存写入（设计稿逐行如此） */
const tokenRows = computed<PriceField[][]>(() => {
  const list = tokenFields.value
  return [list.slice(0, 2), list.slice(2, 4), list.slice(4, 5)]
})
const mediaColA = computed(() => mediaFields.value.slice(0, 3))
const mediaColB = computed(() => mediaFields.value.slice(3, 5))

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

function applyRaw(raw: Record<string, unknown> | null | undefined) {
  model.value = buildItemViewModel(raw)
  tier.value = model.value.tier
}

onMounted(async () => {
  const itemId = resolveQueryId('itemId', QUOTE_ITEM_ID_KEY)
  const quoteId = resolveQueryId('quoteId', QUOTE_ID_KEY)
  try {
    if (itemId) {
      applyRaw(await quoteApi.getItem(itemId))
      return
    }
    if (quoteId) {
      const list = await quoteApi.listItems(quoteId)
      const first = Array.isArray(list?.items) ? list.items[0] : undefined
      if (first) {
        applyRaw(first)
        return
      }
    }
    toast(TOAST_MISSING_ITEM)
  } catch (e) {
    toast(toastMessage(e))
  }
})

function toastMessage(e: unknown): string {
  if (e instanceof ApiError && e.message) return e.message
  return TOAST_FAIL
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** 下拉/新增类控件：选项集合无 PRD 依据 → 只提示，不发请求、不臆造选项 */
function onPendingOptions() {
  toast(OPTIONS_PENDING_TOAST)
}

function onTogglePrice(key: string) {
  model.value.priceFields = togglePriceField(model.value.priceFields, key)
}

function onPriceInput(key: string, e: unknown) {
  model.value.priceFields = setPriceValue(model.value.priceFields, key, inputValue(e))
}

function onTierInput(e: unknown) {
  tier.value = inputValue(e)
}

function onRuleInput(no: number, field: 'value' | 'multiplier', e: unknown) {
  model.value.ruleGroups = setRuleValue(model.value.ruleGroups, no, field, inputValue(e))
}

/** uni-app input 事件：H5/小程序在 detail.value，纯 DOM 在 target.value */
function inputValue(e: unknown): string {
  const ev = e as { detail?: { value?: unknown }; target?: { value?: unknown } } | undefined
  if (ev?.detail && ev.detail.value !== undefined && ev.detail.value !== null) {
    return String(ev.detail.value)
  }
  return ev?.target?.value === undefined || ev.target.value === null ? '' : String(ev.target.value)
}

function onAddGroup() {
  model.value.ruleGroups = addRuleGroup(model.value.ruleGroups)
}

function onRemoveGroup(no: number) {
  model.value.ruleGroups = removeRuleGroup(model.value.ruleGroups, no)
}

function titleOf(g: RequestRuleGroup) {
  return ruleGroupTitle(g)
}

function currentState() {
  return {
    priceFields: model.value.priceFields,
    ruleGroups: model.value.ruleGroups,
    tier: tier.value,
    billingMode: model.value.billingMode
  }
}

async function onSave() {
  if (saving.value) return
  const errors = validateItem(currentState())
  if (errors.length) {
    toast(errors[0])
    return
  }
  if (!model.value.itemId) {
    toast(TOAST_MISSING_ITEM)
    return
  }
  saving.value = true
  try {
    await quoteApi.saveItem(model.value.itemId, buildItemPayload(currentState()))
    toast(TOAST_SAVED)
  } catch (e) {
    toast(toastMessage(e))
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.pricing {
  min-height: 100vh;
  background: $color-bg-page-2;
  display: flex;
  flex-direction: column;
}

/* 顶部导航（设计 5e8ed34f padding[48,16,12,16]） */
.pricing__nav {
  display: flex;
  align-items: center;
  padding: 48px 16px 12px;
  background: $color-bg-card;
}
.nav__back {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex-shrink: 0;
}
.nav__titles {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0 12px;
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
  font-size: 10px;
  color: $color-text-placeholder;
  line-height: 14.4px;
}
.nav__spacer {
  flex: 1;
}
.nav__save {
  font-size: 14px;
  font-weight: 600;
  color: $color-primary;
  line-height: 19.2px;
  flex-shrink: 0;
}

/* 内容区（设计 66b78139 padding16 gap14） */
.pricing__body {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.card {
  width: 100%;
  box-sizing: border-box;
  border-radius: 16px;
  background: $color-bg-card;
  /* design effects：四张卡均声明 drop_shadow(0,4,16,rgba(15,23,42,0.06))（box-shadow 不占布局） */
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
}
.card--info {
  padding: 14px 16px;
  gap: 10px;
}
.card--mode {
  padding: 14px 16px;
  gap: 12px;
}
.card--price {
  padding: 14px 16px;
  gap: 14px;
}
.card--rule {
  padding: 14px 16px;
  gap: 12px;
}

/* 卡1 模型信息 */
.info__head {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 26px;
}
.info__badge {
  width: 26px;
  height: 26px;
  border-radius: 13px;
  background: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.info__badge-text {
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
  line-height: 14.4px;
}
.info__name {
  font-size: 15px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 18px;
}
.info__spacer {
  flex: 1;
}
.info__summary {
  display: block;
  font-size: 11px;
  color: $color-text-muted;
  line-height: 18px;
}

/* 卡2 计费方式 */
.mode__field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.field__label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 18px;
}
.mode__row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.box {
  box-sizing: border-box;
  border-radius: 10px;
  background: $color-bg-page;
  display: flex;
  align-items: center;
  box-shadow: 0 0 0 0.8px $color-border;
}
.box--grow {
  flex: 1;
  min-width: 0;
}
.box--input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
}
.box--select {
  height: 44px;
  padding: 0 12px;
  justify-content: space-between;
}
.box__input {
  width: 100%;
  height: 17px;
  font-size: 13px;
  color: $color-text-primary;
}
.box__text {
  font-size: 13px;
  color: $color-text-primary;
}
.box--branch {
  height: 44px;
  padding: 0 12px;
  gap: 4px;
  background: $color-bg-card;
  box-shadow: 0 0 0 0.8px $color-primary-border-light;
  flex-shrink: 0;
}
.branch__text {
  font-size: 12px;
  font-weight: 600;
  color: $color-primary;
}

/* 卡3 价格 */
.price__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.price__title {
  font-size: 14px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 19.2px;
}
.unit {
  padding: 3px 8px;
  border-radius: 9px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
}
.unit__text {
  font-size: 11px;
  font-weight: 600;
  color: $color-text-muted;
  /* 设计稿「单位标签」= padding 3/8 + 11px 文本行盒 18（设计截图量尺：价格行1 框 top 455 = 卡顶392.4+头24+间距14+标签18+7）
     —— 若按 13.2 行盒写，整卡会矮 5px，卡3 之后的每个元素都会上移（本轮由 DOM 数字抓出的真偏差） */
  line-height: 18px;
}
.price__rows {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.price__row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.price__field {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.price__label-row {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 18px;
}
.price__label {
  font-size: 12px;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 14.4px;
}
.check {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  box-sizing: border-box;
  background: $color-bg-card;
  box-shadow: 0 0 0 0.8px $color-border-strong;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.check--on {
  background: $color-primary;
  box-shadow: none;
}
.check__tick {
  width: 7px;
  height: 4px;
  border-left: 1.6px solid #ffffff;
  border-bottom: 1.6px solid #ffffff;
  transform: rotate(-45deg) translate(0.5px, -1px);
}
.divider {
  width: 100%;
  height: 1px;
  background: $color-bg-subtle;
}
.media__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 19.2px;
}
.media__title {
  font-size: 13px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 15.6px;
}
.media__cols {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.media__col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.media__label {
  font-size: 12px;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 14.4px;
}
/* 设计里媒体列勾选框 stroke thickness = 1（token 列是 0.8）→ 分开声明；:not(--on) 让勾选态仍无描边 */
.media__col .check:not(.check--on) {
  box-shadow: 0 0 0 1px $color-border-strong;
}

/* 卡4 请求规则 */
.rule__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 19.2px;
}
.rule__head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.rule__bar {
  width: 5px;
  height: 16px;
  border-radius: 2px;
  background: $color-primary;
  flex-shrink: 0;
}
.rule__title {
  font-size: 14px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 16.8px;
}
.rule__note {
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 13.2px;
}
.rule__hint {
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 13.2px;
}
.rule-group {
  padding: 12px;
  border-radius: 12px;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rule-group__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 19.2px;
}
.rule-group__title {
  font-size: 12px;
  font-weight: 700;
  color: $color-text-secondary-2;
  line-height: 14.4px;
}
.rule-group__row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.box--cond {
  height: 40px;
  padding: 0 12px;
  border-radius: 9px;
  background: $color-bg-card;
}
.box--cond.box--grow {
  justify-content: space-between;
}
.box--cond.box--input.box--grow {
  justify-content: flex-start;
}
.cond__text {
  font-size: 12px;
  color: $color-text-secondary-2;
}
.cond__input {
  width: 100%;
  height: 16px;
  font-size: 12px;
  color: $color-text-primary;
}
.cond__placeholder {
  color: $color-text-placeholder;
}
.rule-group__actions {
  display: flex;
  align-items: center;
  gap: 18px;
  height: 16.8px;
}
.action {
  display: flex;
  align-items: center;
  gap: 4px;
}
.action__text {
  font-size: 12px;
  font-weight: 600;
  color: $color-primary;
}
.rule-group__row--multi {
  gap: 10px;
}
.multiplier__label {
  font-size: 12px;
  font-weight: 600;
  color: $color-text-secondary-2;
  line-height: 14.4px;
  flex-shrink: 0;
}
.rule-group__note {
  display: block;
  font-size: 11px;
  color: $color-text-placeholder;
  line-height: 13.2px;
}
.rule__add {
  height: 44px;
  border-radius: 10px;
  background: $color-bg-card;
  box-shadow: 0 0 0 0.8px $color-border-strong;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.rule__add-text {
  font-size: 13px;
  font-weight: 600;
  color: $color-primary;
}

/* 底部操作条 */
.pricing__bar {
  background: $color-bg-card;
  padding: 12px 16px 16px;
}
.pricing__save {
  height: 48px;
  border-radius: 12px;
  background: $color-primary;
  /* design effects：保存按钮 drop_shadow(0,6,16,rgba(37,99,235,0.28)) */
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.pricing__save-text {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
}

/* 图标（设计稿用 remixicon 字形；小程序/H5 跨端一致性优先 → CSS 形状占位，见台账登记）
   口径：**盒子尺寸 = 设计图层盒**（declared width × 本页字形行框 fontSize×1.1），形状画进 `::before`。
   盒子进 flex 的占位必须与设计一致（例：添加计费分支按钮 = 12+18+4+73+12 = 119，盒子小 7px 会让框宽变 111）。 */
.ic {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-sizing: border-box;
}
.ic::before {
  content: '';
  display: block;
  box-sizing: border-box;
}
.ic-back {
  /* design 3900d52a w=26 · fs=24 → 盒 26×26（设计 PNG 字形 ink 20..36 / 61..76，居中于盒） */
  width: 26px;
  height: 26px;
}
.ic-back::before {
  width: 10px;
  height: 10px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
}
.ic-chevron-up {
  /* design e47dc806 w=20 · fs=18 → 盒 20×20（设计 PNG ink 382..392 / 140..145，盒右界 398） */
  width: 20px;
  height: 20px;
}
.ic-chevron-up::before {
  width: 10px;
  height: 10px;
  border-left: 2px solid $color-text-placeholder;
  border-bottom: 2px solid $color-text-placeholder;
  transform: rotate(135deg);
}
.ic-chevron-up-sm {
  /* design ebc25539（媒体定价头）/ 990b61af（规则标题行）fs=16 → 盒 18×18 */
  width: 18px;
  height: 18px;
}
.ic-chevron-up-sm::before {
  width: 8px;
  height: 8px;
  border-left: 1.6px solid $color-text-placeholder;
  border-bottom: 1.6px solid $color-text-placeholder;
  transform: rotate(135deg);
}
.ic-caret {
  /* design 00bedca8（计费方式选择框）w=18 · fs=16 → 盒 18×18 */
  width: 18px;
  height: 18px;
}
.ic-caret::before {
  width: 7px;
  height: 7px;
  border-right: 1.6px solid $color-text-placeholder;
  border-bottom: 1.6px solid $color-text-placeholder;
  transform: rotate(45deg);
}
.ic-caret-sm {
  /* design 0c8d1f6c 等条件选择框 fs=14 → 盒 15×15 */
  width: 15px;
  height: 15px;
}
.ic-caret-sm::before {
  width: 6px;
  height: 6px;
  border-right: 1.4px solid $color-text-placeholder;
  border-bottom: 1.4px solid $color-text-placeholder;
  transform: rotate(45deg);
}
.ic-plus-blue {
  /* design 84b1c4b0（添加计费分支）/ a119149b（新增规则组）w=18 · fs=16 → 盒 18×18 */
  width: 18px;
  height: 18px;
}
.ic-plus-blue::before {
  width: 11px;
  height: 11px;
  border-radius: 2px;
  background: $color-primary;
}
.ic-plus-sm {
  /* design 77d95bec / ef6224d5（新增参数 / 新增时间条件）fs=14 → 盒 15×15 */
  width: 15px;
  height: 15px;
}
.ic-plus-sm::before {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: $color-primary;
}
.ic-trash {
  /* design ffbcc2d6（规则组删除）fs=16 → 盒 18×18 */
  width: 18px;
  height: 18px;
}
.ic-trash::before {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background: $color-danger;
}
.ic-check-white {
  /* design e1e80bd3（保存按钮）w=22 · fs=20 → 盒 22×22 */
  width: 22px;
  height: 22px;
}
.ic-check-white::before {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  background: #ffffff;
}
</style>
