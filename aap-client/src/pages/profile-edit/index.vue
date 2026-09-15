<template>
  <view class="profile-edit">
    <!-- 顶部导航（design 553188bc：padding 48/16/12/16 · 白底 · 图标 24 · 标题 17 Bold · 完整度胶囊 h24 r12 #EFF6FF） -->
    <view class="topbar">
      <view class="topbar__row">
        <view class="icon-btn" data-testid="back-btn" @tap="goBack">
          <view class="glyph glyph--back" aria-hidden="true" />
        </view>
        <view class="topbar__title-wrap">
          <text class="topbar__title" data-testid="page-title">{{ PAGE_TITLE }}</text>
        </view>
        <!-- 完整度：PRD/数据字典零命中 → 仅服务端给值时才渲染（不臆造公式） -->
        <view v-if="completenessLabel" class="completeness" data-testid="completeness-chip">
          <text class="completeness__text">{{ completenessLabel }}</text>
        </view>
      </view>
    </view>

    <!-- 主体信息卡（design c2a309c7：r18 · padding20 · 描边 #EEF2F7 · 头部高 27 · 字段间距 16） -->
    <view class="section">
      <view class="card">
        <view class="card__head">
          <view class="glyph glyph--basic" aria-hidden="true" />
          <text class="card__title">{{ SECTION_BASIC }}</text>
        </view>

        <view class="field" data-testid="field-company">
          <text class="field__label">{{ LABEL_COMPANY }}</text>
          <view class="field__box">
            <input
              v-model="form.companyName"
              class="field__input"
              data-testid="company-input"
              :placeholder="PLACEHOLDER_COMPANY"
              placeholder-class="field__placeholder"
              :maxlength="MAX_COMPANY_NAME"
            />
          </view>
        </view>

        <view class="field" data-testid="field-uscc">
          <text class="field__label">{{ LABEL_USCC }}</text>
          <view class="field__box">
            <input
              v-model="form.uscc"
              class="field__input"
              data-testid="uscc-input"
              :placeholder="PLACEHOLDER_USCC"
              placeholder-class="field__placeholder"
              :maxlength="MAX_USCC"
            />
            <!-- 格式通过标记（设计稿绿勾；规则 = 本地 18 位字母数字校验） -->
            <view v-if="usccOk" class="glyph glyph--check" data-testid="uscc-ok" aria-hidden="true" />
          </view>
        </view>

        <view class="field" data-testid="field-industry">
          <text class="field__label">{{ LABEL_INDUSTRY }}</text>
          <view class="type-row">
            <view
              v-for="option in INDUSTRY_OPTIONS"
              :key="option.code"
              class="type-chip"
              :class="{ 'type-chip--checked': form.industry === option.code }"
              :data-checked="form.industry === option.code ? 'true' : 'false'"
              data-testid="industry-chip"
              @tap="form.industry = option.code"
            >
              <text class="type-chip__text">{{ option.label }}</text>
            </view>
          </view>
        </view>

        <view class="field" data-testid="field-region">
          <text class="field__label">{{ LABEL_REGION }}</text>
          <!-- 地区选择用 uni 原生 region picker（地区数据源 PRD 无定义 → 用平台内置数据，记 missing-prd） -->
          <picker
            mode="region"
            data-testid="region-picker"
            class="region-picker"
            :value="regionValue"
            @change="onRegionChange"
          >
            <view class="region-row">
              <view class="field__box field__box--half">
                <text :class="regionTextClass(form.province)" data-testid="province-value">{{
                  form.province || PLACEHOLDER_REGION
                }}</text>
                <view class="glyph glyph--chevron" aria-hidden="true" />
              </view>
              <view class="field__box field__box--half">
                <text :class="regionTextClass(form.city)" data-testid="city-value">{{
                  form.city || PLACEHOLDER_REGION
                }}</text>
                <view class="glyph glyph--chevron" aria-hidden="true" />
              </view>
            </view>
          </picker>
        </view>

        <view class="field" data-testid="field-address">
          <text class="field__label">{{ LABEL_ADDRESS }}</text>
          <view class="field__box">
            <input
              v-model="form.address"
              class="field__input"
              data-testid="address-input"
              :placeholder="PLACEHOLDER_ADDRESS"
              placeholder-class="field__placeholder"
              :maxlength="MAX_ADDRESS"
            />
          </view>
        </view>

        <view class="field" data-testid="field-website">
          <text class="field__label">{{ LABEL_WEBSITE }}</text>
          <view class="field__box">
            <input
              v-model="form.website"
              class="field__input"
              data-testid="website-input"
              :placeholder="PLACEHOLDER_WEBSITE"
              placeholder-class="field__placeholder"
              :maxlength="MAX_WEBSITE"
            />
          </view>
        </view>
      </view>
    </view>

    <!-- 联系信息卡（design 67023af5） -->
    <view class="section">
      <view class="card">
        <view class="card__head">
          <view class="glyph glyph--contact" aria-hidden="true" />
          <text class="card__title">{{ SECTION_CONTACT }}</text>
        </view>

        <view class="two-col">
          <view class="field field--half" data-testid="field-contact">
            <text class="field__label">{{ LABEL_CONTACT_NAME }}</text>
            <view class="field__box">
              <input
                v-model="form.contactName"
                class="field__input"
                data-testid="contact-input"
                :placeholder="PLACEHOLDER_CONTACT_NAME"
                placeholder-class="field__placeholder"
                :maxlength="MAX_CONTACT_NAME"
              />
            </view>
          </view>
          <view class="field field--half" data-testid="field-title">
            <text class="field__label">{{ LABEL_CONTACT_TITLE }}</text>
            <view class="field__box">
              <input
                v-model="form.contactTitle"
                class="field__input"
                data-testid="title-input"
                :placeholder="PLACEHOLDER_CONTACT_TITLE"
                placeholder-class="field__placeholder"
                :maxlength="MAX_CONTACT_TITLE"
              />
            </view>
          </view>
        </view>

        <view class="two-col">
          <view class="field field--half" data-testid="field-phone">
            <text class="field__label">{{ LABEL_PHONE }}</text>
            <view class="field__box">
              <input
                v-model="form.phone"
                class="field__input"
                data-testid="phone-input"
                type="number"
                :placeholder="PLACEHOLDER_PHONE"
                placeholder-class="field__placeholder"
                maxlength="11"
              />
            </view>
          </view>
          <view class="field field--half" data-testid="field-email">
            <text class="field__label">{{ LABEL_EMAIL }}</text>
            <view class="field__box">
              <input
                v-model="form.email"
                class="field__input"
                data-testid="email-input"
                :placeholder="PLACEHOLDER_EMAIL"
                placeholder-class="field__placeholder"
                :maxlength="MAX_EMAIL"
              />
            </view>
          </view>
        </view>

        <view class="field" data-testid="field-intro">
          <view class="field__label-row">
            <text class="field__label">{{ LABEL_INTRO }}</text>
            <text class="field__counter" data-testid="intro-counter">{{ introCounter }}</text>
          </view>
          <view class="intro-box">
            <textarea
              v-model="form.intro"
              class="intro-box__textarea"
              data-testid="intro-input"
              :placeholder="PLACEHOLDER_INTRO"
              placeholder-class="field__placeholder"
              :maxlength="MAX_INTRO"
            />
          </view>
        </view>
      </view>
    </view>

    <!-- 资质文件卡（design 85da8ac1：三行固定分类，行高 46 · 行间距 16） -->
    <view class="section">
      <view class="card">
        <view class="card__head card__head--between">
          <view class="card__head-left">
            <view class="glyph glyph--files" aria-hidden="true" />
            <text class="card__title">{{ SECTION_FILES }}</text>
          </view>
          <text class="card__tip" data-testid="files-tip">{{ FILES_TIP }}</text>
        </view>

        <view
          v-for="(row, index) in rows"
          :key="row.key"
          class="qual-row"
          data-testid="qual-row"
          @tap="onRowTap(row, index)"
        >
          <view class="qual-row__thumb" :class="{ 'qual-row__thumb--empty': !uploaded(row) }">
            <view class="glyph glyph--doc" aria-hidden="true" />
          </view>
          <view class="qual-row__info">
            <view class="qual-row__name-row">
              <text class="qual-row__name" data-testid="qual-name">{{ row.name }}</text>
              <!-- 角标 1：必传 / 条件必传（设计 必传标 = 红底 #FEF2F2 文字 #B91C1C / 条件必传 = 橙底 #FFF7ED 文字 #B45309） -->
              <view
                v-if="row.badge"
                class="qual-row__badge"
                :class="badgeClass(row)"
                :data-badge="row.badge === BADGE_REQUIRED ? 'required' : 'conditional'"
                data-testid="qual-badge"
              >
                <text class="qual-row__badge-text">{{ row.badge }}</text>
              </view>
              <!-- 角标 2：已上传（设计 已上传标 = 绿底 #ECFDF5 + 对勾 + 文字 #15803D，**独立于必传角标**） -->
              <view
                v-if="uploaded(row)"
                class="qual-row__badge qual-row__badge--uploaded"
                data-badge="uploaded"
                data-testid="qual-badge"
              >
                <view class="glyph glyph--check-sm" aria-hidden="true" />
                <text class="qual-row__badge-text">{{ BADGE_UPLOADED }}</text>
              </view>
            </view>
            <text v-if="uploaded(row)" class="qual-row__file" data-testid="qual-file">{{
              row.file?.fileName
            }}</text>
            <text v-else-if="row.hint" class="qual-row__hint" data-testid="qual-hint">{{ row.hint }}</text>
            <text v-else-if="row.desc" class="qual-row__hint" data-testid="qual-desc">{{ row.desc }}</text>
          </view>
          <template v-if="uploaded(row)">
            <view
              class="icon-tap"
              :data-testid="`qual-del-${index}`"
              @tap.stop="onRemove(row, index)"
            >
              <view class="glyph glyph--trash" aria-hidden="true" />
            </view>
            <view class="icon-tap" :data-testid="`qual-view-${index}`" @tap.stop="onView(row)">
              <view class="glyph glyph--chevron" aria-hidden="true" />
            </view>
          </template>
          <view v-else class="icon-tap" :data-testid="`qual-upload-${index}`">
            <view class="glyph glyph--chevron" aria-hidden="true" />
          </view>
        </view>
      </view>
    </view>

    <!-- 底部操作条（design 1648cc81：padding 12/16/24/16 · 草稿 156×48 · 保存 自适应×48 #2563EB） -->
    <view class="bar-wrap">
      <view class="bar">
        <view class="btn btn--ghost" data-testid="btn-draft" @tap="onSaveDraft">{{ BTN_DRAFT }}</view>
        <view class="btn btn--primary" data-testid="btn-save" @tap="onSave">
          <text class="btn__text">{{ BTN_SAVE }}</text>
          <view class="glyph glyph--arrow-white" aria-hidden="true" />
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 10【档案与凭证】供应商档案编辑（page-10-2 / 编辑主体档案）— 430 宽 · 设计总高 1409 · 无 TabBar
 * 设计真源：.calicat/raw/pages/page-10-2/design.tree.json + 设计截图像素量尺
 *   （卡1 108..687 · 卡2 698..1042 · 卡3 1057..1308 · 底栏 1324..1408 · 卡内头部 27 · 字段 标签18+8+框44）
 * 接口真源：18-API「Provider」→ GET/PUT /provider/profile · GET/POST /provider/qualifications ·
 *          DELETE /provider/qualifications/{id}（前缀 /api/v1；该卡片只列路径未列方法 → 方法为推断）
 * 交互分类（写进 .agents/state/aap-feature-status.csv 序号 10）：
 *   返回 = navigation(navigateBack) · 输入/类型/地区/简介/字数 = client-only
 *   档案加载 = api(GET /provider/profile) · 资质加载 = api(GET /provider/qualifications)
 *   保存 = api(PUT /provider/profile) · 保存草稿 = client-only(本地草稿 storage，PRD 无草稿语义)
 *   上传资质 = api(POST /provider/qualifications) · 删除资质 = api(DELETE /provider/qualifications/{id})
 *   查看箭头 = client-only(18-API 无文件查看接口 → 不臆造路由)
 * 缺口见 src/utils/profile-edit-model.ts 头部（不臆造字段/文案）。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ApiError } from '@/api/http'
import { providerApi, type ProviderProfile } from '@/api/provider'
import {
  BADGE_CONDITIONAL,
  BADGE_REQUIRED,
  BADGE_UPLOADED,
  BTN_DRAFT,
  BTN_SAVE,
  FILES_TIP,
  INDUSTRY_OPTIONS,
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
  MAX_ADDRESS,
  MAX_COMPANY_NAME,
  MAX_CONTACT_NAME,
  MAX_CONTACT_TITLE,
  MAX_EMAIL,
  MAX_INTRO,
  MAX_USCC,
  MAX_WEBSITE,
  PAGE_TITLE,
  PLACEHOLDER_ADDRESS,
  PLACEHOLDER_COMPANY,
  PLACEHOLDER_CONTACT_NAME,
  PLACEHOLDER_CONTACT_TITLE,
  PLACEHOLDER_EMAIL,
  PLACEHOLDER_INTRO,
  PLACEHOLDER_PHONE,
  PLACEHOLDER_REGION,
  PLACEHOLDER_USCC,
  PLACEHOLDER_WEBSITE,
  SECTION_BASIC,
  SECTION_CONTACT,
  SECTION_FILES,
  USCC_PATTERN,
  bioCounter,
  buildProfilePayload,
  buildQualificationRows,
  completenessText,
  emptyProfileForm,
  mapProfileToForm,
  uploadPayload,
  validateProfileForm,
  type ProfileForm,
  type QualificationItem,
  type QualificationRow
} from '@/utils/profile-edit-model'

/** 本地草稿键（PRD 无草稿语义 → 只落本地，不臆造服务端字段） */
const DRAFT_KEY = 'aap_provider_profile_draft'

const TOAST_LOAD_FAIL = '档案加载失败，请稍后重试'
const TOAST_SAVED = '保存成功'
const TOAST_SAVE_FAIL = '保存失败，请稍后重试'
const TOAST_DRAFT = '已存为草稿'
const TOAST_UPLOADED = '已上传'
const TOAST_UPLOAD_FAIL = '上传失败，请稍后重试'
const TOAST_DELETED = '已删除'
const TOAST_DELETE_FAIL = '删除失败，请稍后重试'
const TOAST_NO_PICKER = '当前环境不支持选择文件'
const TOAST_VIEW_TODO = '暂不支持在线预览'
const DELETE_TITLE = '删除资质文件'
const DELETE_CONTENT = '确认删除该资质文件？删除后不可恢复。'

const form = reactive<ProfileForm>(emptyProfileForm())
const rows = ref<QualificationRow[]>(buildQualificationRows([]))
const completeness = ref<unknown>(undefined)

const completenessLabel = computed(() => completenessText(completeness.value))
const introCounter = computed(() => bioCounter(form.intro))
const usccOk = computed(() => USCC_PATTERN.test(form.uscc.trim()))
const regionValue = computed<[string, string, string]>(() => [
  form.province || '浙江省',
  form.city || '杭州市',
  ''
])

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

function uploaded(row: QualificationRow): boolean {
  return Boolean(row.file?.fileName)
}

function badgeClass(row: QualificationRow): string {
  return row.badge === BADGE_CONDITIONAL ? 'qual-row__badge--conditional' : 'qual-row__badge--required'
}

function regionTextClass(value: string): string {
  return value ? 'field__value' : 'field__value field__value--placeholder'
}

function applyForm(next: Partial<ProfileForm> | Record<string, unknown>) {
  Object.assign(form, next)
}

/** 本地草稿：存在则覆盖服务端值（保存草稿的恢复路径） */
function applyDraft() {
  try {
    const raw = uni.getStorageSync(DRAFT_KEY) as string
    if (!raw) return
    const parsed = JSON.parse(raw) as Record<string, unknown>
    if (parsed && typeof parsed === 'object') {
      applyForm(mapProfileToForm(parsed as never))
    }
  } catch {
    /* 草稿损坏 → 忽略，继续用服务端值 */
  }
}

function normalizeQualItems(payload: unknown): QualificationItem[] {
  if (Array.isArray(payload)) return payload as QualificationItem[]
  const items = (payload as { items?: unknown } | null)?.items
  return Array.isArray(items) ? (items as QualificationItem[]) : []
}

async function loadProfile() {
  try {
    const data = await providerApi.profile()
    applyForm(mapProfileToForm(data as ProviderProfile))
    completeness.value = (data as ProviderProfile | undefined)?.completeness
    applyDraft()
  } catch (err) {
    toast(err instanceof ApiError ? err.message : TOAST_LOAD_FAIL)
  }
}

async function loadQualifications() {
  try {
    const data = await providerApi.qualifications()
    rows.value = buildQualificationRows(normalizeQualItems(data))
  } catch {
    rows.value = buildQualificationRows([])
  }
}

onMounted(() => {
  void loadProfile()
  void loadQualifications()
})

function goBack() {
  uni.navigateBack({ delta: 1 })
}

/** uni region picker：value = [省, 市, 区] */
function onRegionChange(event: { detail?: { value?: unknown } } | undefined) {
  const value = event?.detail?.value
  if (!Array.isArray(value)) return
  form.province = typeof value[0] === 'string' ? value[0] : ''
  form.city = typeof value[1] === 'string' ? value[1] : ''
}

async function onSave() {
  const invalid = validateProfileForm(form)
  if (invalid) return toast(invalid)

  uni.showLoading({ title: '保存中' })
  try {
    const result = await providerApi.saveProfile(buildProfilePayload(form))
    uni.hideLoading()
    const nextCompleteness = (result as { completeness?: unknown } | undefined)?.completeness
    if (typeof nextCompleteness === 'number') completeness.value = nextCompleteness
    toast(TOAST_SAVED)
  } catch (err) {
    uni.hideLoading()
    toast(err instanceof ApiError ? err.message : TOAST_SAVE_FAIL)
  }
}

function onSaveDraft() {
  uni.setStorageSync(DRAFT_KEY, JSON.stringify(buildProfilePayload(form)))
  toast(TOAST_DRAFT)
}

/** 上传：uni.chooseFile 仅 H5、uni.chooseMessageFile 仅小程序 → 双路径取其一 */
type UniPicker = {
  chooseFile?: (options: Record<string, unknown>) => unknown
  chooseMessageFile?: (options: Record<string, unknown>) => unknown
}

function pickFile(onPicked: (file: { name: string; size: number }) => void) {
  const picker = uni as unknown as UniPicker
  const success = (res: unknown) => {
    const first = (res as { tempFiles?: Array<{ name?: string; size?: number }> } | undefined)?.tempFiles?.[0]
    if (!first) return
    onPicked({ name: String(first.name ?? ''), size: Number(first.size ?? 0) })
  }
  const options = { count: 1, success, fail: () => undefined }

  if (typeof picker.chooseFile === 'function') {
    picker.chooseFile(options)
    return
  }
  if (typeof picker.chooseMessageFile === 'function') {
    picker.chooseMessageFile({ ...options, type: 'file' })
    return
  }
  toast(TOAST_NO_PICKER)
}

async function onRowTap(row: QualificationRow, index: number) {
  if (uploaded(row)) return // 已上传行：上传/删除/查看由内部按钮承担
  void index
  onUpload(row)
}

function onUpload(row: QualificationRow) {
  pickFile(async (file) => {
    uni.showLoading({ title: '上传中' })
    try {
      await providerApi.uploadQualification(uploadPayload(row, file))
      uni.hideLoading()
      toast(TOAST_UPLOADED)
      await loadQualifications()
    } catch (err) {
      uni.hideLoading()
      toast(err instanceof ApiError ? err.message : TOAST_UPLOAD_FAIL)
    }
  })
}

function onView(_row: QualificationRow) {
  // 18-API 无资质文件查看接口 + 画布无预览页 → client-only（不臆造路由）
  toast(TOAST_VIEW_TODO)
}

function onRemove(row: QualificationRow, _index: number) {
  const id = row.file?.id
  uni.showModal({
    title: DELETE_TITLE,
    content: DELETE_CONTENT,
    success: async (res: { confirm?: boolean }) => {
      if (!res?.confirm) return
      if (!id) {
        toast(TOAST_DELETE_FAIL)
        return
      }
      try {
        await providerApi.removeQualification(id)
        toast(TOAST_DELETED)
        await loadQualifications()
      } catch (err) {
        toast(err instanceof ApiError ? err.message : TOAST_DELETE_FAIL)
      }
    }
  })
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.profile-edit {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* ===== 顶部导航（design 553188bc：48 上 / 12 下 / 16 左右 · 内容行 36 · 合计 96） ===== */
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

.completeness {
  margin-left: auto;
  height: 24px;
  padding: 0 8px;
  border-radius: 12px;
  background: $color-primary-weak;
  display: flex;
  align-items: center;
  box-sizing: border-box;
}

.completeness__text {
  font-size: $font-2xs; /* 11 */
  line-height: 24px;
  font-weight: 500;
  color: $color-primary;
}

/* ===== 卡片区（design：卡间距 12 · 卡 padding20 r18 描边 #EEF2F7） ===== */
.section {
  width: 100%;
  padding: 12px 16px 0 16px;
  box-sizing: border-box;
}

.card {
  width: 100%;
  background: $color-bg-card;
  /* 描边用 ring 而不是 border：设计稿的 stroke 画在盒子外部
     （卡高 579 = 20 + 内容 + 20，不含描边；chip 声明 40 而可见 42）→ border 会多占 2px 并挤下全部内容 */
  box-shadow: 0 0 0 1px $color-border-chip;
  border-radius: 18px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.card__head {
  width: 100%;
  height: 27px;
  margin-bottom: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.card__head--between {
  justify-content: space-between;
}

.card__head-left {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  height: 27px;
}

.card__title {
  font-size: $font-base; /* 14 */
  font-weight: 600;
  color: $color-text-primary;
}

.card__tip {
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
}

/* ===== 字段（design：标签 18 · 间距 8 · 框 44 r12 #F8FAFC 描边 #E2E8F0 · 字段间 16） ===== */
.field {
  width: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 卡内每个直接子块之间 16px（设计：头部 27 之后每个 container padding-top 16）；
   ⚠️ 不能写成 `.field + .field` —— 那会把两列行里的第二个半栏也加上 16px（实测 top 差 +16） */
.card > .field,
.card > .two-col,
.card > .qual-row {
  margin-top: 16px;
}

.field__label {
  display: block;
  height: 18px;
  font-size: $font-sm; /* 13 */
  font-weight: 500;
  color: $color-text-secondary-2;
  line-height: 18px;
}

.field__label-row {
  width: 100%;
  height: 18px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.field__counter {
  display: block;
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 18px;
}

.field__box {
  width: 100%;
  height: 44px;
  margin-top: 8px;
  padding: 0 12px;
  background: $color-bg-page;
  border: 1px solid $color-border;
  border-radius: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
  overflow: hidden;
}

.field__input {
  flex: 1;
  min-width: 0;
  height: 20px;
  font-size: $font-base; /* 14 */
  font-weight: 500;
  color: $color-text-secondary-2;
  line-height: 20px;
  background: transparent;
}

.field__placeholder {
  font-weight: 400;
  color: $color-text-placeholder;
}

.field__value {
  display: block;
  flex: 1;
  min-width: 0;
  font-size: $font-base; /* 14 */
  font-weight: 500;
  color: $color-text-secondary-2;
  line-height: 20px;
}

.field__value--placeholder {
  font-weight: 400;
  color: $color-text-placeholder;
}

/* 供应商类型 chip（design：h40 · padding 0/16 · r12 · 间距 9） */
.type-row {
  width: 100%;
  margin-top: 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 9px;
}

.type-chip {
  height: 40px;
  padding: 0 16px;
  border-radius: 12px;
  background: $color-bg-card;
  /* 设计稿 chip 声明 40、可见 42 → stroke 画在盒外（同上），用 ring 实现 */
  box-shadow: 0 0 0 1px $color-border-strong;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.type-chip--checked {
  background: $color-primary;
  box-shadow: 0 0 0 1px $color-primary;
}

.type-chip__text {
  font-size: $font-sm; /* 13 */
  font-weight: 500;
  color: $color-text-tertiary;
}

.type-chip--checked .type-chip__text {
  color: #ffffff;
}

/* 地区两列（design：间距 13） */
.region-picker {
  display: block;
  width: 100%;
}

.region-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 13px;
}

.field__box--half {
  flex: 1;
  min-width: 0;
  margin-top: 8px;
  justify-content: space-between;
}

/* 两列表单行（design：间距 13） */
.two-col {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 13px;
}

.field--half {
  flex: 1;
  min-width: 0;
}

/* 简介框（design 0.6.：padding 12 · r12 · 文本 40 → 合计 64） */
.intro-box {
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  background: $color-bg-page;
  /* 设计总高 64 = 12 + 文本 40 + 12（描边在盒外，同卡片） */
  box-shadow: 0 0 0 1px $color-border;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.intro-box__textarea {
  width: 100%;
  height: 40px;
  font-size: $font-sm; /* 13 */
  color: $color-text-tertiary;
  line-height: 20px;
  background: transparent;
}

/* ===== 资质行（design：行高 46 · 行间距 16 · 缩略图 47/46 r10） ===== */
.qual-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.qual-row + .qual-row {
  margin-top: 16px;
}

.qual-row__thumb {
  width: 47px;
  height: 46px;
  border-radius: 10px;
  background: $color-primary-weak;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  box-sizing: border-box;
}

/* 未上传行的图标框：设计声明 46 而可见 44 → 描边画在盒内（与输入框一致），保留 border */
.qual-row__thumb--empty {
  width: 46px;
  background: $color-bg-page;
  border: 1px solid $color-border-strong;
  box-sizing: border-box;
}

.qual-row__info {
  flex: 1;
  min-width: 0;
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-sizing: border-box;
}

.qual-row__name-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  height: 18px;
}

.qual-row__name {
  display: block;
  font-size: $font-sm; /* 13 */
  font-weight: 600;
  color: $color-text-primary;
  line-height: 18px;
}

.qual-row__badge {
  height: 18px;
  margin-left: 8px;
  padding: 0 8px;
  border-radius: 9px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 2px;
  box-sizing: border-box;
}

.qual-row__badge--required {
  background: $color-danger-weak;
}

.qual-row__badge--conditional {
  background: $color-warning-weak;
}

.qual-row__badge--uploaded {
  background: $color-success-weak;
}

.qual-row__badge-text {
  font-size: 10px;
  font-weight: 500;
  line-height: 16px;
}

.qual-row__badge--required .qual-row__badge-text {
  color: $color-danger-text;
}

.qual-row__badge--conditional .qual-row__badge-text {
  color: $color-warning-text-3;
}

.qual-row__badge--uploaded .qual-row__badge-text {
  color: $color-success-text;
}

.qual-row__file {
  display: block;
  margin-top: 2px;
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 16px;
}

.qual-row__hint {
  display: block;
  margin-top: 2px;
  font-size: $font-2xs; /* 11 */
  color: $color-text-placeholder;
  line-height: 16px;
}

.icon-tap {
  width: 20px;
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

/* ===== 底部操作条（design 1648cc81：padding 12/16/24/16 · 草稿 156×48 · 保存 自适应×48） ===== */
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
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.btn--ghost {
  width: 156px;
  flex: none;
  background: $color-bg-card;
  border: 1px solid $color-border-strong;
  font-size: $font-base; /* 14 */
  font-weight: 500;
  color: $color-text-tertiary;
}

.btn--primary {
  flex: 1;
  min-width: 0;
  background: $color-primary;
  gap: 4px;
  padding: 0 4px;
}

.btn__text {
  font-size: $font-md; /* 15 */
  font-weight: 600;
  color: #ffffff;
}

/* ===== 图标占位（设计稿为 remixicon 矢量；PRD08 禁 emoji → CSS 形状占位，与序号 1~9 一致） ===== */
.glyph--back {
  width: 9px;
  height: 9px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
  margin-left: 2px;
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

.glyph--check {
  width: 12px;
  height: 7px;
  border-left: 2px solid $color-success;
  border-bottom: 2px solid $color-success;
  transform: rotate(-45deg);
  margin-bottom: 3px;
  flex: none;
}

.glyph--check-sm {
  width: 7px;
  height: 4px;
  border-left: 1.5px solid $color-success;
  border-bottom: 1.5px solid $color-success;
  transform: rotate(-45deg);
  margin-bottom: 1px;
  flex: none;
}

.glyph--chevron {
  width: 7px;
  height: 7px;
  border-right: 1.5px solid $color-text-placeholder;
  border-top: 1.5px solid $color-text-placeholder;
  transform: rotate(45deg);
  flex: none;
}

.glyph--trash {
  width: 14px;
  height: 15px;
  border: 1.5px solid $color-border-strong;
  border-top: none;
  border-radius: 0 0 3px 3px;
  position: relative;
  box-sizing: border-box;
}

.glyph--trash::before {
  content: '';
  position: absolute;
  left: -3px;
  top: -5px;
  width: 18px;
  height: 1.5px;
  background: $color-border-strong;
}

.glyph--doc {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: $color-primary;
}

.qual-row__thumb--empty .glyph--doc {
  background: $color-text-placeholder;
}

.glyph--arrow-white {
  width: 8px;
  height: 8px;
  border-right: 2px solid #ffffff;
  border-top: 2px solid #ffffff;
  transform: rotate(45deg);
  flex: none;
}
</style>
