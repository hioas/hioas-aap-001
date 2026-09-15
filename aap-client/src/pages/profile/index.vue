<template>
  <view class="profile">
    <!-- 顶部导航（design e3487a61：padding 48/16/12/16 · 白底 · 图标 24 · 标题 17 Bold · 完整度胶囊 h24 r12 #FFF7ED） -->
    <view class="topbar">
      <view class="topbar__row">
        <view class="icon-btn" data-testid="back-btn" @tap="goBack">
          <view class="glyph glyph--back" aria-hidden="true" />
        </view>
        <view class="topbar__title-wrap">
          <text class="topbar__title" data-testid="page-title">{{ PAGE_TITLE }}</text>
        </view>
        <!-- 完整度：22 份 PRD 零命中 → 仅服务端给数字时才渲染（不臆造公式） -->
        <view v-if="pillText" class="completeness" data-testid="completeness-pill">
          <view class="glyph glyph--completeness" aria-hidden="true" />
          <text class="completeness__text">{{ pillText }}</text>
        </view>
      </view>
    </view>

    <!-- 完整度进度卡（design 44fc1ec9：无描边 + 投影 0/6/20 rgba(15,23,42,.06) · padding20 r18） -->
    <view class="section">
      <view class="card card--shadow">
        <view class="head-line">
          <text class="card__title">{{ SECTION_COMPLETENESS }}</text>
          <text v-if="percentText" class="head-line__percent" data-testid="completeness-percent">{{
            percentText
          }}</text>
        </view>
        <view class="progress">
          <view class="progress__fill" data-testid="completeness-bar" :style="{ width: barWidth }" />
        </view>
        <view class="gate">
          <view class="gate__icon"><view class="glyph glyph--warn" aria-hidden="true" /></view>
          <text class="gate__text" data-testid="gate-hint">{{ GATE_HINT }}</text>
        </view>
      </view>
    </view>

    <!-- 主体信息卡（design 4207fc77：r18 · padding20 · 描边 #EEF2F7 · 头部 27 · 字段 = 标签16+2+值20） -->
    <view class="section">
      <view class="card card--ring">
        <view class="card__head">
          <view class="glyph glyph--basic" aria-hidden="true" />
          <text class="card__title">{{ SECTION_BASIC }}</text>
          <view class="lock-badge" data-testid="lock-badge">
            <view class="glyph glyph--lock" aria-hidden="true" />
            <text class="lock-badge__text">{{ BADGE_LOCKED }}</text>
          </view>
        </view>

        <view class="field">
          <text class="field__label" data-testid="field-label">{{ LABEL_COMPANY }}</text>
          <text class="field__value" data-testid="v-company" data-tone="text">{{ view.company }}</text>
        </view>

        <view class="field">
          <text class="field__label" data-testid="field-label">{{ LABEL_USCC }}</text>
          <text class="field__value" data-testid="v-uscc" data-tone="text">{{ view.uscc }}</text>
        </view>

        <!-- 供应商类型（chip）+ 所在地区：设计稿同一行两栏，align-items center -->
        <view class="row">
          <view class="row__col">
            <text class="field__label" data-testid="field-label">{{ LABEL_INDUSTRY }}</text>
            <view class="type-chip">
              <text class="type-chip__text" data-testid="v-industry" data-tone="chip">{{ view.industryLabel }}</text>
            </view>
          </view>
          <view class="row__col">
            <text class="field__label" data-testid="field-label">{{ LABEL_REGION }}</text>
            <text class="field__value" data-testid="v-region" data-tone="text">{{ view.region }}</text>
          </view>
        </view>

        <view class="field">
          <text class="field__label" data-testid="field-label">{{ LABEL_ADDRESS }}</text>
          <text class="field__value" data-testid="v-address" data-tone="text">{{ view.address }}</text>
        </view>

        <!-- 官网：设计稿 fontFill 为主色蓝（rgba(37,99,235,1)）→ 展示色不同，仍为只读（无跳转依据） -->
        <view class="field">
          <text class="field__label" data-testid="field-label">{{ LABEL_WEBSITE }}</text>
          <text class="field__value field__value--link" data-testid="v-website" data-tone="link">{{
            view.website
          }}</text>
        </view>

        <view class="note">
          <view class="note__icon"><view class="glyph glyph--note" aria-hidden="true" /></view>
          <text class="note__text" data-testid="note-basic">{{ NOTE_BASIC_LOCKED }}</text>
        </view>
      </view>
    </view>

    <!-- 联系信息卡（design 99da5e10：右上「编辑」入口 → 序号 10 编辑页） -->
    <view class="section">
      <view class="card card--ring">
        <view class="card__head">
          <view class="glyph glyph--contact" aria-hidden="true" />
          <text class="card__title">{{ SECTION_CONTACT }}</text>
          <text class="card__action" data-testid="action-edit" @tap="goEdit">{{ ACTION_EDIT }}</text>
        </view>

        <view class="two-col">
          <view class="field field--half">
            <text class="field__label" data-testid="field-label">{{ LABEL_CONTACT_NAME }}</text>
            <text class="field__value" data-testid="v-contact" data-tone="text">{{ view.contactName }}</text>
          </view>
          <view class="field field--half">
            <text class="field__label" data-testid="field-label">{{ LABEL_CONTACT_TITLE }}</text>
            <text class="field__value" data-testid="v-title" data-tone="text">{{ view.contactTitle }}</text>
          </view>
        </view>

        <view class="two-col">
          <view class="field field--half">
            <text class="field__label" data-testid="field-label">{{ LABEL_PHONE }}</text>
            <text class="field__value" data-testid="v-phone" data-tone="text">{{ view.phone }}</text>
          </view>
          <view class="field field--half">
            <text class="field__label" data-testid="field-label">{{ LABEL_EMAIL }}</text>
            <text class="field__value" data-testid="v-email" data-tone="text">{{ view.email }}</text>
          </view>
        </view>

        <view class="field">
          <text class="field__label" data-testid="field-label">{{ LABEL_INTRO }}</text>
          <view class="intro-box">
            <text class="intro-box__text" data-testid="v-intro" data-tone="text">{{ view.intro }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 资质文件卡（design 495c465e：三行固定 · 行高 48 · 行间距 16 · 右上「管理」） -->
    <view class="section">
      <view class="card card--ring">
        <view class="card__head">
          <view class="glyph glyph--files" aria-hidden="true" />
          <text class="card__title">{{ SECTION_FILES }}</text>
          <text class="card__action" data-testid="action-manage" @tap="goEdit">{{ ACTION_MANAGE }}</text>
        </view>

        <view v-for="row in rows" :key="row.key" class="qual-row" data-testid="qual-row">
          <view class="qual-row__thumb" :class="`qual-row__thumb--${row.tone}`">
            <view class="glyph glyph--doc" aria-hidden="true" />
          </view>
          <view class="qual-row__info">
            <text class="qual-row__name" data-testid="qual-name">{{ row.name }}</text>
            <text class="qual-row__subtitle" data-testid="qual-subtitle">{{ row.subtitle }}</text>
          </view>
          <view
            v-if="row.badge"
            class="qual-row__badge"
            :class="`qual-row__badge--${row.badgeTone}`"
            :data-tone="row.badgeTone"
            data-testid="qual-badge"
          >
            <text class="qual-row__badge-text">{{ row.badge }}</text>
          </view>
          <view v-if="row.chevron" class="glyph glyph--chevron" data-testid="qual-chevron" aria-hidden="true" />
        </view>

        <!-- 「上传新资质」落编辑页：本页固定三行、无新增行位，且资质分类码全 PRD 无定义 → 不臆造 POST -->
        <view class="btn-upload" data-testid="btn-upload" @tap="goEdit">
          <view class="glyph glyph--plus" aria-hidden="true" />
          <text class="btn-upload__text">{{ BTN_UPLOAD }}</text>
        </view>
      </view>
    </view>

    <!-- 底部操作条（design 370608ca：padding 12/16/24/16 · 保存 193×48 白底描边 · 去补全资质 自适应 #2563EB） -->
    <view class="bar-wrap">
      <view class="bar">
        <view class="btn btn--ghost" data-testid="btn-save" @tap="onSave">
          <text class="btn--ghost__text">{{ BTN_SAVE }}</text>
        </view>
        <view class="btn btn--primary" data-testid="btn-complete" @tap="goEdit">
          <text class="btn__text">{{ BTN_COMPLETE }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 10.1【档案与凭证】供应商档案（page-10-1-2 / 主体档案）— 430 宽 · 设计总高 1414 · 无 TabBar
 *
 * 设计真源：.calicat/raw/pages/page-10-1-2/design.tree.json + 设计截图像素量尺
 *   （顶栏 0..95(96) · 卡1 108..265(158) · 卡2 278..690(413) · 卡3 703..981(279) · 卡4 995..1313(319) ·
 *    底栏 1330..1413(84) · 页高 1414 · 卡 padding20 r18 · 卡间距 12 · 字段 = 标签16 + 2 + 值20 ·
 *    卡内头部 27（18px 图标 × 1.5）· 资质行 48 + 间距 16 · 上传按钮 44）
 * 接口真源：18-API「Provider」→ GET /provider/profile、GET /provider/qualifications、PUT /provider/profile
 *          （前缀 /api/v1；该卡片只列路径未列方法 → 方法为 REST 语义推断）
 * 交互分类（写进 .agents/state/aap-feature-status.csv 序号 10.1）：
 *   返回 = navigation(navigateBack) · 档案加载 = api(GET /provider/profile)
 *   资质加载 = api(GET /provider/qualifications) · 保存 = api(PUT /provider/profile)
 *   「编辑」「管理」「上传新资质」「去补全资质」= navigation(/pages/profile-edit/index，画布唯一的档案编辑页)
 *   完整度卡 / 主体信息全部字段 / 联系信息全部字段 / 资质行 = client-only（渲染态，无点击）
 * 缺口（不臆造）见 src/utils/profile-model.ts 头部。
 */
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/api/http'
import { providerApi, type ProviderProfile } from '@/api/provider'
import { buildProfilePayload, mapProfileToForm } from '@/utils/profile-edit-model'
import {
  ACTION_EDIT,
  ACTION_MANAGE,
  BADGE_LOCKED,
  BTN_COMPLETE,
  BTN_SAVE,
  BTN_UPLOAD,
  GATE_HINT,
  LABEL_ADDRESS,
  LABEL_COMPANY,
  LABEL_CONTACT_NAME,
  LABEL_CONTACT_TITLE,
  LABEL_EMAIL,
  LABEL_INDUSTRY,
  LABEL_INTRO,
  LABEL_PHONE,
  LABEL_REGION,
  LABEL_USCC,
  LABEL_WEBSITE,
  NOTE_BASIC_LOCKED,
  PAGE_TITLE,
  SECTION_BASIC,
  SECTION_COMPLETENESS,
  SECTION_CONTACT,
  SECTION_FILES,
  completenessBarWidth,
  completenessPercent,
  completenessPillText,
  mapProfileView,
  qualificationViewRows,
  toQualificationItems,
  type ProfileViewSource,
  type QualificationView
} from '@/utils/profile-model'

/** 画布中唯一的「主体档案」编辑页（序号 10，page-10-2） */
const EDIT_PAGE = '/pages/profile-edit/index'

const TOAST_LOAD_FAIL = '档案加载失败，请稍后重试'
const TOAST_SAVED = '保存成功'
const TOAST_SAVE_FAIL = '保存失败，请稍后重试'

const profile = ref<ProfileViewSource | null>(null)
const rows = ref<QualificationView[]>(qualificationViewRows([]))

const view = computed(() => mapProfileView(profile.value))
const percentText = computed(() => {
  const percent = completenessPercent(profile.value?.completeness)
  return percent === undefined ? '' : `${percent}%`
})
const pillText = computed(() => completenessPillText(profile.value?.completeness))
const barWidth = computed(() => completenessBarWidth(profile.value?.completeness))

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

async function loadProfile() {
  try {
    const data = (await providerApi.profile()) as ProviderProfile | undefined
    profile.value = (data ?? null) as ProfileViewSource | null
  } catch (err) {
    toast(err instanceof ApiError ? err.message : TOAST_LOAD_FAIL)
  }
}

async function loadQualifications() {
  try {
    const data = await providerApi.qualifications()
    rows.value = qualificationViewRows(toQualificationItems(data))
  } catch {
    rows.value = qualificationViewRows([])
  }
}

onMounted(() => {
  void loadProfile()
  void loadQualifications()
})

function goBack() {
  uni.navigateBack({ delta: 1 })
}

function goEdit() {
  uni.navigateTo({ url: EDIT_PAGE })
}

/** 保存：只读页无输入控件，语义在 PRD 未定义 → 按序号 10 编辑页同义的 /provider/profile 写接口落库 */
async function onSave() {
  uni.showLoading({ title: '保存中' })
  try {
    const result = await providerApi.saveProfile(buildProfilePayload(mapProfileToForm(profile.value as never)))
    uni.hideLoading()
    const next = (result as { completeness?: unknown } | undefined)?.completeness
    if (typeof next === 'number') {
      profile.value = { ...(profile.value ?? {}), completeness: next }
    }
    toast(TOAST_SAVED)
  } catch (err) {
    uni.hideLoading()
    toast(err instanceof ApiError ? err.message : TOAST_SAVE_FAIL)
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.profile {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* ===== 顶部导航（design e3487a61：48 上 / 12 下 / 16 左右 · 内容行 36 · 合计 96） ===== */
.topbar {
  width: 100%;
  background: $color-bg-card;
  /* 设计帧的 padding-top 48 已含状态栏 → H5 为 0，小程序补安全区 */
  padding: calc(48px + var(--status-bar-height, 0px)) 16px 12px 16px;
  box-sizing: border-box;
}

.topbar__row {
  display: flex;
  flex-direction: row;
  align-items: center;
  height: 36px;
}

.icon-btn {
  width: 26px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex: none;
}

.topbar__title-wrap {
  padding-left: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  height: 36px;
}

.topbar__title {
  font-size: 17px;
  line-height: 22px;
  font-weight: 700;
  color: $color-text-primary;
}

/* 完整度胶囊（design c440ccf2：h24 · padding 0/8 · r12 · #FFF7ED） */
.completeness {
  margin-left: auto;
  height: 24px;
  padding: 0 8px;
  border-radius: 12px;
  background: $color-warning-weak;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  flex: none;
  box-sizing: border-box;
}

.completeness__text {
  font-size: $font-2xs; /* 11 */
  line-height: 24px;
  font-weight: 500;
  color: $color-warning-text-3;
}

/* ===== 卡片区（design：卡间距 12 · 卡 padding20 r18） ===== */
.section {
  width: 100%;
  padding: 12px 16px 0 16px;
  box-sizing: border-box;
}

.card {
  width: 100%;
  background: $color-bg-card;
  border-radius: 18px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 完整度卡无描边、有投影（design 44fc1ec9：offsetY 6 · blur 20 · rgba(15,23,42,.06)） */
.card--shadow {
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

/* 其余卡片：描边画在盒外（声明高度不含描边）→ 用 ring，不用 border */
.card--ring {
  box-shadow: 0 0 0 1px $color-border-chip;
}

.card__head {
  width: 100%;
  height: 27px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.card__title {
  font-size: $font-base; /* 14 */
  font-weight: 600;
  color: $color-text-primary;
}

.card__action {
  margin-left: auto;
  font-size: $font-xs; /* 12 */
  font-weight: 500;
  color: $color-primary;
}

/* 完整度标题行（design 8f58bea7：14px 行盒 20，占满宽两侧对齐） */
.head-line {
  width: 100%;
  height: 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.head-line__percent {
  font-size: $font-base; /* 14 */
  line-height: 20px;
  font-weight: 700;
  color: $color-primary;
}

/* 进度条（design 67c8119f：条 h10 r5 #E2E8F0 · 填充 h10 r5 #2563EB，容器 padding-top 12） */
.progress {
  width: 100%;
  height: 10px;
  margin-top: 12px;
  border-radius: 5px;
  background: $color-border;
  overflow: hidden;
}

.progress__fill {
  height: 10px;
  border-radius: 5px;
  background: $color-primary;
}

/* 闸门提示（design 87815f1d：padding12 r12 #FFFBEB · 容器 padding-top 16 · 合计 60） */
.gate {
  width: 100%;
  margin-top: 16px;
  padding: 12px;
  border-radius: 12px;
  background: $color-warning-weak-2;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
  box-sizing: border-box;
}

.gate__text {
  display: block;
  flex: 1;
  min-width: 0;
  font-size: $font-xs; /* 12 */
  line-height: 18px;
  color: $color-warning-text-2;
}

/* ⚠️ 设计稿的图标是 18px 的 remixicon 段落 → 行盒 18 × 1.5 = 27（不是 18）。
   锁定提示盒高 51 = 12 + 27 + 12 全靠它；只画 18 高的形状会矮 9px（实测 42 vs 51），
   且卡2 之后的**整页**都会跟着上移 9px。 */
.gate__icon,
.note__icon {
  width: 20px;
  height: 27px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  flex: none;
}

/* ===== 只读字段（design：标签 12px 行盒 16 · 值 14px 行盒 20 · 间距 2 · 字段间 16） ===== */
.field {
  width: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 卡内直接子块之间 16px（设计：头部 27 之后每个 container padding-top 16） */
.card > .field,
.card > .two-col,
.card > .row,
.card > .note,
.card > .qual-row,
.card > .btn-upload {
  margin-top: 16px;
}

.field__label {
  display: block;
  height: 16px;
  font-size: $font-xs; /* 12 */
  font-weight: 400;
  color: $color-text-placeholder;
  line-height: 16px;
}

.field__value {
  display: block;
  margin-top: 2px;
  height: 20px;
  font-size: $font-base; /* 14 */
  font-weight: 600;
  color: $color-text-primary;
  line-height: 20px;
}

.field__value--link {
  color: $color-primary;
}

/* 供应商类型 + 所在地区两栏（design 8994daf8：align-items center · 两栏等分无间距） */
.row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.row__col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* 类型 chip（design c2cd28be：h24 · padding 0/12 · r12 · #EFF6FF，容器 padding-top 8） */
.type-chip {
  margin-top: 8px;
  height: 24px;
  padding: 0 12px;
  border-radius: 12px;
  background: $color-primary-weak;
  display: flex;
  flex-direction: row;
  align-items: center;
  align-self: flex-start;
  box-sizing: border-box;
}

.type-chip__text {
  font-size: $font-2xs; /* 11 */
  line-height: 14px;
  font-weight: 500;
  color: $color-primary;
}

/* 锁定角标（design a957abfa：h22 · padding 0/8 · r11 · #F1F5F9） */
.lock-badge {
  margin-left: auto;
  height: 22px;
  padding: 0 8px;
  border-radius: 11px;
  background: $color-bg-subtle;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  flex: none;
  box-sizing: border-box;
}

.lock-badge__text {
  font-size: $font-2xs; /* 11 */
  line-height: 14px;
  font-weight: 500;
  color: $color-text-muted;
}

/* 锁定提示盒（design 8e8a6705：padding12 r12 #F8FAFC · 合计 51） */
.note {
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  background: $color-bg-page;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
  box-sizing: border-box;
}

.note__text {
  display: block;
  flex: 1;
  min-width: 0;
  font-size: $font-xs; /* 12 */
  line-height: 18px;
  color: $color-text-muted;
}

/* ===== 两列字段行（design 40542c22：两栏等分无间距） ===== */
.two-col {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

.field--half {
  flex: 1;
  min-width: 0;
}

/* 简介框（design 36a918be：padding12 r12 #F8FAFC · 文本 2 行 40 → 合计 64） */
.intro-box {
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  border-radius: 12px;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.intro-box__text {
  display: block;
  width: 100%;
  font-size: $font-xs; /* 12 */
  line-height: 20px;
  color: $color-text-tertiary;
}

/* ===== 资质行（design c778e5fd：缩略图 48×48 r12 · 行间距 16 · 角标 h20 r10） ===== */
.qual-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.qual-row__thumb {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  box-sizing: border-box;
}

.qual-row__thumb--primary {
  background: $color-primary-weak;
}

.qual-row__thumb--muted {
  background: $color-bg-page;
}

.qual-row__info {
  flex: 1;
  min-width: 0;
  padding-left: 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-sizing: border-box;
}

.qual-row__name {
  display: block;
  font-size: $font-sm; /* 13 */
  font-weight: 600;
  color: $color-text-primary;
  line-height: 18px;
}

.qual-row__subtitle {
  display: block;
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 14px;
}

.qual-row__badge {
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  display: flex;
  flex-direction: row;
  align-items: center;
  flex: none;
  box-sizing: border-box;
}

.qual-row__badge--success {
  background: $color-success-weak;
}

.qual-row__badge--warning {
  background: $color-warning-weak;
}

.qual-row__badge-text {
  font-size: $font-2xs; /* 11 */
  line-height: 14px;
  font-weight: 500;
}

.qual-row__badge--success .qual-row__badge-text {
  color: $color-success-text;
}

.qual-row__badge--warning .qual-row__badge-text {
  color: $color-warning-text-3;
}

/* 上传新资质（design f79c7824：h44 · r12 · 白底 · 描边 #93C5FD） */
.btn-upload {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  background: $color-bg-card;
  border: 1px solid $color-primary-border-light;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 5px;
  box-sizing: border-box;
}

.btn-upload__text {
  font-size: $font-sm; /* 13 */
  line-height: 18px;
  font-weight: 500;
  color: $color-primary;
}

/* ===== 底部操作条（design 370608ca：padding 12/16/24/16 · 保存 193×48 · 去补全资质 自适应×48） ===== */
.bar-wrap {
  width: 100%;
  padding: 16px 0 0 0;
  box-sizing: border-box;
}

.bar {
  width: 100%;
  background: $color-bg-card;
  padding: 12px 16px 24px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  box-sizing: border-box;
}

.btn {
  height: 48px;
  border-radius: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.btn--ghost {
  width: 193px;
  flex: none;
  background: $color-bg-card;
  border: 1px solid $color-border-strong;
}

.btn--ghost__text {
  font-size: $font-base; /* 14 */
  font-weight: 500;
  color: $color-text-tertiary;
}

.btn--primary {
  flex: 1;
  min-width: 0;
  background: $color-primary;
}

.btn__text {
  font-size: $font-md; /* 15 */
  font-weight: 600;
  color: #ffffff;
}

/* ===== 图标占位（设计稿为 remixicon 矢量；PRD08 禁 emoji → CSS 形状占位，与序号 1~10 一致） ===== */
.glyph--back {
  width: 9px;
  height: 9px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
  margin-left: 2px;
}

.glyph--completeness {
  width: 13px;
  height: 13px;
  border-radius: 3px;
  background: $color-warning-text;
  flex: none;
}

.glyph--basic,
.glyph--contact,
.glyph--files {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: $color-primary;
  flex: none;
}

.glyph--contact {
  border-radius: 9px;
}

.glyph--files {
  border-radius: 4px;
}

.glyph--lock {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  background: $color-text-placeholder;
  flex: none;
}

.glyph--warn {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: $color-warning-text;
  flex: none;
}

.glyph--note {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: $color-text-placeholder;
  flex: none;
}

.glyph--doc {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: $color-primary;
}

.qual-row__thumb--muted .glyph--doc {
  background: $color-text-placeholder;
}

.glyph--plus {
  width: 18px;
  height: 18px;
  border-radius: 3px;
  background: $color-primary;
  flex: none;
}

.glyph--chevron {
  width: 7px;
  height: 7px;
  border-right: 1.5px solid $color-border-strong;
  border-top: 1.5px solid $color-border-strong;
  transform: rotate(45deg);
  flex: none;
}
</style>
