<template>
  <view class="access-form">
    <!-- 顶部栏：design id=8dd86532（白底 · padding 16/20/16/20 · 底部 1px 分隔投影 · 左返回 36 圆 + 标题块，右扫描 36 圆） -->
    <view class="access-form__topbar">
      <view class="access-form__topbar-left">
        <view class="icon-btn" data-testid="back-btn" @tap="goBack">
          <view class="glyph glyph--back" aria-hidden="true" />
        </view>
        <view class="access-form__title-block">
          <text class="access-form__title" data-testid="page-title">{{ PAGE_TITLE }}</text>
          <text class="access-form__subtitle" data-testid="page-subtitle">{{ PAGE_SUBTITLE }}</text>
        </view>
      </view>
      <!-- 扫描按钮：画布 30 页无对应页面 → client-only（不臆造路由），见文件头说明 -->
      <view class="icon-btn" data-testid="scan-btn" @tap="onScan">
        <view class="glyph glyph--scan" aria-hidden="true" />
      </view>
    </view>

    <!-- 内容区：design id=647d9c22（padding 16/20/16/20 · gap 16） -->
    <view class="access-form__content">
      <!-- 基本信息卡：design id=aa34f953（白 · r16 · padding 16 · gap 14） -->
      <view class="card card--basic">
        <view class="card__head">
          <view class="card__bar" aria-hidden="true" />
          <text class="card__title" data-testid="section-title">{{ SECTION_BASIC }}</text>
        </view>

        <view class="field">
          <view class="field__label-row">
            <text class="field__label" data-testid="field-label">{{ LABEL_COMPANY }}</text>
            <text class="field__star" data-testid="field-star">{{ REQUIRED_STAR }}</text>
          </view>
          <view class="input-box">
            <input
              v-model="companyName"
              class="input-box__input"
              data-testid="company-input"
              :placeholder="PLACEHOLDER_COMPANY"
              placeholder-class="input-box__placeholder"
              maxlength="64"
            />
          </view>
        </view>

        <view class="field">
          <view class="field__label-row">
            <text class="field__label" data-testid="field-label">{{ LABEL_USCC }}</text>
            <text class="field__star" data-testid="field-star">{{ REQUIRED_STAR }}</text>
          </view>
          <view class="input-box">
            <input
              v-model="uscc"
              class="input-box__input"
              data-testid="uscc-input"
              :placeholder="PLACEHOLDER_USCC"
              placeholder-class="input-box__placeholder"
              maxlength="24"
            />
          </view>
        </view>

        <view class="field">
          <view class="field__label-row">
            <text class="field__label" data-testid="field-label">{{ LABEL_CONTACT }}</text>
          </view>
          <view class="input-box">
            <input
              v-model="contactName"
              class="input-box__input"
              data-testid="contact-input"
              :placeholder="PLACEHOLDER_CONTACT"
              placeholder-class="input-box__placeholder"
              maxlength="32"
            />
          </view>
        </view>

        <view class="field">
          <view class="field__label-row">
            <text class="field__label" data-testid="field-label">{{ LABEL_PHONE }}</text>
          </view>
          <view class="input-box">
            <input
              v-model="contactPhone"
              class="input-box__input"
              data-testid="phone-input"
              :placeholder="PLACEHOLDER_PHONE"
              placeholder-class="input-box__placeholder"
              maxlength="11"
            />
          </view>
        </view>
      </view>

      <!-- 检测类型卡：design id=844ad0c2（gap 12）—— ⚠️ 枚举无 PRD 依据 → 纯 UI 选中态，不进提交体 -->
      <view class="card">
        <view class="card__head">
          <view class="card__bar" aria-hidden="true" />
          <text class="card__title" data-testid="section-title">{{ SECTION_DETECTION }}</text>
        </view>
        <view class="type-row">
          <view
            v-for="type in DETECTION_TYPES"
            :key="type"
            class="type-chip"
            :class="{ 'type-chip--checked': detectionType === type }"
            :data-checked="detectionType === type ? 'true' : 'false'"
            data-testid="type-chip"
            @tap="onSelectType(type)"
          >
            <text class="type-chip__text">{{ type }}</text>
          </view>
        </view>
      </view>

      <!-- 凭证资料卡：design id=1a3b0d4d（gap 12；上传区虚线描边 #CBD5E1 · r12 · padding 24/0） -->
      <view class="card">
        <view class="card__head card__head--between">
          <view class="card__head-left">
            <view class="card__bar" aria-hidden="true" />
            <text class="card__title" data-testid="section-title">{{ SECTION_FILES }}</text>
          </view>
          <text class="card__tip" data-testid="upload-tip">{{ UPLOAD_TIP }}</text>
        </view>

        <view class="upload" data-testid="upload-box" @tap="onPickFile">
          <view class="upload__icon">
            <view class="glyph glyph--cloud" aria-hidden="true" />
          </view>
          <text class="upload__main" data-testid="upload-main">{{ UPLOAD_MAIN }}</text>
          <text class="upload__limit" data-testid="upload-limit">{{ UPLOAD_LIMIT }}</text>
        </view>

        <!-- 已上传文件行：design id=0126e565（#F8FAFC · r10 · padding 10/12 · gap 10） -->
        <view v-for="(file, index) in files" :key="`${file.name}-${index}`" class="file-row" data-testid="file-row">
          <view class="glyph glyph--file" aria-hidden="true" />
          <view class="file-row__info">
            <text class="file-row__name" data-testid="file-name">{{ file.name }}</text>
            <text class="file-row__size" data-testid="file-size">{{ formatFileSize(file.size) }}</text>
          </view>
          <view class="file-row__del" :data-testid="`file-del-${index}`" @tap.stop="onRemoveFile(index)">
            <view class="glyph glyph--close" aria-hidden="true" />
          </view>
        </view>
      </view>

      <!-- 备注卡：design id=0ff82e01（gap 10；备注框 padding 12/12/24/12）—— ⚠️ 无对应字段 → 不进提交体 -->
      <view class="card card--remark">
        <view class="card__head">
          <view class="card__bar" aria-hidden="true" />
          <text class="card__title" data-testid="section-title">{{ SECTION_REMARK }}</text>
        </view>
        <view class="remark-box">
          <textarea
            v-model="remark"
            class="remark-box__textarea"
            data-testid="remark-input"
            :placeholder="PLACEHOLDER_REMARK"
            placeholder-class="input-box__placeholder"
            :maxlength="200"
          />
        </view>
      </view>

      <!-- 提交按钮：design id=c29d94c6（48 高 · r12 · 投影 rgba(37,99,235,0.28) · gap 6） -->
      <view class="submit-btn" data-testid="submit-btn" @tap="onSubmit">
        <view class="glyph glyph--check-white" aria-hidden="true" />
        <text class="submit-btn__text">{{ SUBMIT_LABEL }}</text>
      </view>

      <!-- 提交提示：design id=3f8c7ae8（padding-bottom 4 · gap 6） -->
      <view class="footnote">
        <view class="glyph glyph--shield" aria-hidden="true" />
        <text class="footnote__text" data-testid="submit-footnote">{{ SUBMIT_FOOTNOTE }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 页面 4-v1「接入凭证-表单」（准入表单变体）— 序号 4-v1 / page-24（430 宽）
 * 设计真源：.calicat/raw/pages/page-24/design.tree.json
 * 接口：18-API Provider Tag → POST /api/v1/provider/qualifications（见 src/api/access-application.ts 头部说明）
 * 交互分类（台账序号 4-v1 行）：
 *   返回按钮      = navigation(uni.navigateBack delta 1)
 *   扫描按钮      = client-only（画布 30 页无对应页面 → 不臆造路由，仅提示）
 *   4 个输入框    = client-only（本地表单态）
 *   检测类型 3 项 = client-only（枚举无 PRD 依据 → 只做 UI 选中态，不拼提交体）
 *   上传/删文件   = client-only 选择（18-API 无上传接口 → 只登记文件名 + 字节数）
 *   提交接入      = api(POST /provider/qualifications) + navigation(/pages/detecting/index)
 */
import { ref } from 'vue'
import { ApiError } from '@/api/http'
import { accessApplicationApi } from '@/api/access-application'
import {
  DEFAULT_DETECTION_TYPE,
  DETECTION_TYPES,
  LABEL_COMPANY,
  LABEL_CONTACT,
  LABEL_PHONE,
  LABEL_USCC,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  PLACEHOLDER_COMPANY,
  PLACEHOLDER_CONTACT,
  PLACEHOLDER_PHONE,
  PLACEHOLDER_REMARK,
  PLACEHOLDER_USCC,
  REQUIRED_STAR,
  SECTION_BASIC,
  SECTION_DETECTION,
  SECTION_FILES,
  SECTION_REMARK,
  SUBMIT_FOOTNOTE,
  SUBMIT_LABEL,
  UPLOAD_LIMIT,
  UPLOAD_MAIN,
  UPLOAD_TIP,
  ACCEPT_EXTENSIONS,
  addFile,
  buildAccessApplicationPayload,
  formatFileSize,
  removeFileAt,
  toggleDetectionType,
  validateAccessApplication,
  type AccessApplicationForm,
  type DetectionType,
  type UploadFileMeta
} from '@/utils/access-application-model'

/** 提交成功后跳「检测进行中」（序号 5 / page-5-2，画布已存在该页） */
const DETECTING_PAGE = '/pages/detecting/index'
/** 服务端未返回任务号时的兜底提示（不编造任务号） */
const NO_JOB_HINT = '已提交接入申请'

const companyName = ref('')
const uscc = ref('')
const contactName = ref('')
const contactPhone = ref('')
const remark = ref('')
const detectionType = ref<DetectionType>(DEFAULT_DETECTION_TYPE)
const files = ref<UploadFileMeta[]>([])

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

function currentForm(): AccessApplicationForm {
  return {
    companyName: companyName.value,
    uscc: uscc.value,
    contactName: contactName.value,
    contactPhone: contactPhone.value,
    remark: remark.value,
    detectionType: detectionType.value,
    files: files.value
  }
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** 画布 30 页无对应页面 → client-only，不臆造路由 */
function onScan() {
  toast('扫描功能即将开放')
}

function onSelectType(type: string) {
  detectionType.value = toggleDetectionType(detectionType.value, type)
}

/** uni.chooseFile 仅 H5 可用、uni.chooseMessageFile 仅小程序可用 → 双路径，取其一 */
type UniPicker = {
  chooseFile?: (options: Record<string, unknown>) => unknown
  chooseMessageFile?: (options: Record<string, unknown>) => unknown
}

function onPickFile() {
  const picker = uni as unknown as UniPicker
  const onSuccess = (res: unknown) => {
    const first = (res as { tempFiles?: Array<Partial<UploadFileMeta>> } | undefined)?.tempFiles?.[0]
    if (!first) return
    const added = addFile(files.value, {
      name: String(first.name ?? ''),
      size: Number(first.size ?? 0)
    })
    if (added.error) return toast(added.error)
    files.value = added.files
  }
  const options = { count: 1, extension: [...ACCEPT_EXTENSIONS], success: onSuccess, fail: () => undefined }

  if (typeof picker.chooseFile === 'function') {
    picker.chooseFile(options)
    return
  }
  if (typeof picker.chooseMessageFile === 'function') {
    picker.chooseMessageFile({ ...options, type: 'file' })
    return
  }
  toast('当前环境不支持选择文件')
}

function onRemoveFile(index: number) {
  files.value = removeFileAt(files.value, index)
}

/**
 * 提交接入 = 本地校验 → POST /provider/qualifications → 跳「检测进行中」。
 * 设计脚注「提交后系统将自动发起检测」是服务端副作用（09-PRD §5），前端不再调 /detection-jobs。
 */
async function onSubmit() {
  const invalid = validateAccessApplication(currentForm())
  if (invalid) return toast(invalid)

  uni.showLoading({ title: '提交中' })
  try {
    const result = await accessApplicationApi.submit(buildAccessApplicationPayload(currentForm()))
    const jobId = result?.detection_job_id ?? result?.job_id ?? ''
    uni.hideLoading()
    if (!jobId) toast(NO_JOB_HINT)
    uni.navigateTo({
      url: jobId ? `${DETECTING_PAGE}?jobId=${encodeURIComponent(String(jobId))}` : DETECTING_PAGE
    })
  } catch (err) {
    uni.hideLoading()
    toast(err instanceof ApiError ? err.message : '提交失败，请稍后重试')
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.access-form {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page-2; /* design 页面容器 rgba(245,247,251,1) */
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部栏（design 8dd86532） */
.access-form__topbar {
  width: 100%;
  background: $color-bg-card;
  /* 设计帧未含状态栏偏移 → 补平台安全区（H5 为 0） */
  padding: calc(16px + var(--status-bar-height, 0px)) 20px 16px 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 0 rgba(241, 245, 249, 1);
  box-sizing: border-box;
}

.access-form__topbar-left {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px; /* design 855de236 gap 12 */
}

.access-form__title-block {
  display: flex;
  flex-direction: column;
}

.access-form__title {
  font-size: $font-xl; /* 18 */
  font-weight: 700; /* design a7c44e71 SourceHanSans-Bold */
  color: $color-text-primary;
  line-height: 24px; /* design a7c44e71 声明 height 24（标题块 24+18=42 决定顶部栏高 74） */
}

.access-form__subtitle {
  font-size: $font-xs; /* 12 */
  color: $color-text-placeholder;
  line-height: 18px; /* design 8bd171e3 声明 height 18 */
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  box-sizing: border-box;
}

/* 内容区（design 647d9c22） */
.access-form__content {
  width: 100%;
  padding: 16px 20px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-sizing: border-box;
}

.card {
  width: 100%;
  background: $color-bg-card;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06); /* design effect */
  box-sizing: border-box;
}

.card--basic {
  gap: 14px; /* design aa34f953 gap 14 */
}

.card--remark {
  gap: 10px; /* design 0ff82e01 gap 10 */
}

.card__head {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.card__head--between {
  justify-content: space-between;
}

.card__head-left {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.card__bar {
  width: 5px;
  height: 16px;
  border-radius: 2px;
  background: $color-primary;
  flex: none;
}

.card__title {
  font-size: $font-base; /* 14 */
  font-weight: 700; /* design 99b6172b 等 SourceHanSans-Bold */
  color: $color-text-primary;
  line-height: 20px; /* fit_content 行框 = 14px 的度量行框（设计 PNG 色带实测 20；竖条 16 不决定行高） */
}

.card__tip {
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 16px; /* 11px 行框（design 919871df 等声明 height 16） */
}

.field {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field__label-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
}

.field__label {
  font-size: $font-xs; /* 12 */
  font-weight: 600; /* design b0317376 SourceHanSans-SemiBold */
  color: $color-text-secondary-2;
  line-height: 18px; /* 12px 行框（标签行实测 18） */
}

.field__star {
  font-size: $font-xs;
  color: $color-danger;
  line-height: 18px;
}

/* 输入框（design ae346709 等：44 高 · r10 · #F8FAFC · 中心描边 0.8 #EEF2F7 —— 描边用 box-shadow 表达，
   Figma center stroke 不占布局；用 border 会把内容宽 358 压成 356、输入文本左移 1px） */
.input-box {
  width: 100%;
  height: 44px;
  background: $color-bg-page;
  box-shadow: 0 0 0 0.8px $color-border-chip;
  border-radius: 10px;
  padding: 0 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
  overflow: hidden;
}

.input-box__input {
  flex: 1;
  min-width: 0;
  font-size: $font-sm; /* 13 */
  color: $color-text-primary;
  line-height: 20px; /* 13px 行框（design 3901f022 等 fit_content 实测 20） */
  background: transparent;
}

.input-box__placeholder {
  color: $color-text-placeholder;
}

/* 检测类型 chip（design 36550710 选中 / 6120d5c8 未选中：padding 8/14 · r10） */
.type-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.type-chip {
  padding: 8px 14px;
  border-radius: 10px;
  background: $color-bg-page;
  box-shadow: 0 0 0 0.8px $color-border-chip; /* design 6120d5c8 stroke 0.8（中心描边不占布局） */
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

/* design 36550710（选中）只有 fills、无 stroke → 去掉描边 */
.type-chip--checked {
  background: $color-primary;
  box-shadow: none;
}

.type-chip__text {
  font-size: $font-xs; /* 12 */
  font-weight: 600; /* design ab52b55a SourceHanSans-SemiBold */
  color: $color-text-tertiary;
  line-height: 18px; /* 12px 行框 → chip 高 8+18+8 = 34（设计实测 34） */
}

.type-chip--checked .type-chip__text {
  color: #ffffff;
}

/* 上传区（design f9f7f369：r12 · **实线**中心描边 0.8 #CBD5E1 · padding 24/0 · gap 8） */
.upload {
  width: 100%;
  padding: 24px 0;
  box-shadow: 0 0 0 0.8px $color-border-strong; /* 设计为实线 stroke（设计 PNG 行 655 连续 334px 无断点），非 dashed */
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-sizing: border-box;
}

.upload__icon {
  width: 44px;
  height: 44px;
  border-radius: 22px;
  background: $color-primary-weak;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.upload__main {
  font-size: $font-sm; /* 13 */
  font-weight: 600; /* design ee12aef8 SourceHanSans-SemiBold */
  color: $color-text-secondary-2;
  line-height: 20px; /* design ee12aef8 声明 height 20 */
}

.upload__limit {
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 16px; /* 设计声明 height 16 */
}

/* 已上传文件行（design 0126e565：gap 10 · padding 10/12 · r10 · 高 54） */
.file-row {
  width: 100%;
  background: $color-bg-page;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  box-sizing: border-box;
  overflow: hidden;
}

.file-row__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.file-row__name {
  font-size: $font-xs; /* 12 */
  font-weight: 600; /* design 7549512f SourceHanSans-SemiBold */
  color: $color-text-primary;
  line-height: 18px; /* 设计声明 height 18 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-row__size {
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 16px; /* 设计声明 height 16 */
}

/* 删除盒：设计 8b46f292 图标图层 width 20 · fontSize 18 → 行框 27（形状仍为 18 圆） */
.file-row__del {
  width: 20px;
  height: 27px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

/* 备注框（design 0e5a46b9：r10 · #F8FAFC · 中心描边 0.8 #EEF2F7 · padding 12/12/24/12 → 总高 12+20+24 = 56） */
.remark-box {
  width: 100%;
  height: 56px;
  background: $color-bg-page;
  box-shadow: 0 0 0 0.8px $color-border-chip;
  border-radius: 10px;
  padding: 12px 12px 24px 12px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.remark-box__textarea {
  width: 100%;
  height: 20px; /* 13px 行框（占位文本单行） */
  font-size: $font-sm; /* 13 */
  color: $color-text-primary;
  line-height: 20px;
  background: transparent;
}

/* 提交按钮（design c29d94c6：48 高 · r12 · 投影 0 6 16 rgba(37,99,235,0.28) · gap 6） */
.submit-btn {
  width: 100%;
  height: 48px;
  background: $color-primary;
  border-radius: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
  box-sizing: border-box;
}

.submit-btn__text {
  font-size: $font-md; /* 15 */
  font-weight: 600;
  color: #ffffff;
  line-height: 1.2;
}

/* 提交提示（design 3f8c7ae8：gap 6 · padding-bottom 4） */
.footnote {
  width: 100%;
  padding: 0 0 4px 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-sizing: border-box;
}

.footnote__text {
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 16px; /* 11px 行框（设计 5735195f 声明 height 16） */
}

/* 图标占位（设计稿为 remixicon 矢量字形；PRD08 禁 emoji → CSS 形状占位，与序号 1/2/3/4 一致）
   ⚠️ 盒子尺寸必须按设计图层声明：宽 = 该图层 width、行框高 = fontSize×1.5 ——
   否则图标后的文本整体偏移、行/卡高不再等于设计（序号 4 已实测过这条）。形状画在 ::before/::after 里。
   设计：1f674160 返回 20×27 · 7a694441 扫描 20×27 · 6af08bbd 上传圆内 24×33 ·
        0126e565 文件 22×30 · 8b46f292 删除 20×27 · c29d94c6 提交 22×30 · 3f8c7ae8 脚注 16×21 */
.glyph--back {
  width: 20px;
  height: 27px;
  position: relative;
  flex: none;
}

.glyph--back::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 50%;
  width: 8px;
  height: 8px;
  margin-top: -4px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
}

.glyph--scan {
  width: 20px;
  height: 27px;
  position: relative;
  flex: none;
}

.glyph--scan::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 50%;
  width: 16px;
  height: 16px;
  margin-top: -8px;
  border: 1.5px solid $color-text-muted;
  border-radius: 2px;
  box-sizing: border-box;
}

.glyph--scan::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 50%;
  width: 16px;
  height: 1.5px;
  margin-top: -0.75px;
  background: $color-text-muted;
}

.glyph--cloud {
  width: 24px;
  height: 33px;
  position: relative;
  flex: none;
}

.glyph--cloud::before {
  content: '';
  position: absolute;
  left: 3px;
  top: 50%;
  margin-top: -1px;
  width: 18px;
  height: 8px;
  border-radius: 4px;
  background: $color-primary;
}

.glyph--cloud::after {
  content: '';
  position: absolute;
  left: 7px;
  top: 50%;
  margin-top: -11px;
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-bottom: 7px solid $color-primary;
}

.glyph--file {
  width: 22px;
  height: 30px;
  position: relative;
  flex: none;
}

.glyph--file::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 50%;
  margin-top: -9px;
  width: 15px;
  height: 18px;
  border: 1.5px solid $color-primary;
  border-radius: 3px;
  box-sizing: border-box;
}

.glyph--file::after {
  content: '';
  position: absolute;
  left: 12px;
  top: 50%;
  margin-top: -9px;
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-top: 6px solid $color-primary;
}

/* 删除图标形状仍是 18 圆（盒子 20×27 在 .file-row__del 上） */
.glyph--close {
  width: 18px;
  height: 18px;
  border: 1px solid $color-text-placeholder;
  border-radius: 50%;
  position: relative;
  box-sizing: border-box;
  flex: none;
}

.glyph--close::before,
.glyph--close::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 7.5px;
  width: 10px;
  height: 1px;
  background: $color-text-placeholder;
}

.glyph--close::before {
  transform: rotate(45deg);
}

.glyph--close::after {
  transform: rotate(-45deg);
}

.glyph--check-white {
  width: 22px;
  height: 30px;
  position: relative;
  flex: none;
}

.glyph--check-white::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 8px;
  height: 4px;
  margin-left: -4px;
  margin-top: -3px;
  border-left: 2px solid #ffffff;
  border-bottom: 2px solid #ffffff;
  transform: rotate(-45deg);
}

.glyph--shield {
  width: 16px;
  height: 21px;
  position: relative;
  flex: none;
}

.glyph--shield::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 50%;
  margin-top: -6px;
  width: 12px;
  height: 12px;
  border-radius: 2px 2px 6px 6px;
  background: $color-text-placeholder;
}
</style>
