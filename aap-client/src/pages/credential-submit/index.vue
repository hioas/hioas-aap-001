<template>
  <view class="submit-page">
    <!-- 顶部导航：design id=0fa01a4a（白底 · padding 48/16/12/16 · 返回 24px #334155 · 标题 17px Bold · 主凭证 chip） -->
    <view class="submit-page__topbar">
      <view class="submit-page__icon-btn" data-testid="back-btn" @tap="goBack">
        <view class="glyph glyph--back" aria-hidden="true" />
      </view>
      <text class="submit-page__title">接入凭证</text>
      <view class="submit-page__spacer" />
      <view v-if="isPrimary" class="chip chip--primary" data-testid="primary-chip">
        <text class="chip__text">主凭证</text>
      </view>
    </view>

    <!-- 表单区：design id=0b3224f1（padding 12/16/0/16） -->
    <view class="submit-page__form">
      <!-- 凭证名称卡片：design id=bf10850c（白 · r16 · padding 16/20 · 描边 #EEF2F7） -->
      <view class="card">
        <text class="card__label">凭证名称</text>
        <view class="card__field">
          <view class="input-box">
            <view class="glyph glyph--name" aria-hidden="true" />
            <input
              v-model="alias"
              class="input-box__input"
              data-testid="alias-input"
              maxlength="40"
              placeholder="请输入凭证名称"
              placeholder-class="input-box__placeholder"
            />
          </view>
        </view>
        <!-- 名称校验提示：design id=3ee9857b（建议 6–24 字，设计稿为「建议」非硬校验） -->
        <view class="card__hint">
          <view class="glyph glyph--hint" aria-hidden="true" />
          <text class="card__hint-text">{{ ALIAS_HINT }}</text>
        </view>
      </view>

      <!-- BaseURL 卡片：design id=6fafaef4 -->
      <view class="card card--gap">
        <text class="card__label">BaseURL</text>
        <view class="card__field">
          <view class="input-box">
            <view class="glyph glyph--link" aria-hidden="true" />
            <input
              v-model="baseUrl"
              class="input-box__input"
              data-testid="baseurl-input"
              placeholder="https://api.example.com/v1"
              placeholder-class="input-box__placeholder"
            />
          </view>
        </view>
        <!-- 安全提示：design id=7014d7f1（#FFFBEB · r12 · padding 10） -->
        <view class="note note--gap">
          <view class="glyph glyph--shield" aria-hidden="true" />
          <text class="note__text" data-testid="security-note">{{ ANCHOR_NOTE }}</text>
        </view>
      </view>

      <!-- APIKey 卡片：design id=59efdac0 -->
      <view class="card card--gap">
        <view class="card__title-row">
          <text class="card__label">APIKey</text>
          <view class="card__spacer" />
          <!-- 已配置标签：design id=15e5aeea -->
          <view class="chip chip--success" data-testid="configured-chip">
            <view class="glyph glyph--check" aria-hidden="true" />
            <text class="chip__text chip__text--success">{{ CONFIGURED_LABEL }}</text>
          </view>
        </view>
        <view class="card__field">
          <!-- 脱敏框：design id=7198fdce（46 高 · #F8FAFC · r12 · 描边 #E2E8F0） -->
          <view class="input-box">
            <view class="glyph glyph--key" aria-hidden="true" />
            <text v-if="!apiKeyEditing" class="input-box__value" data-testid="apikey-mask">{{ apiKeyMask }}</text>
            <input
              v-else
              v-model="apiKey"
              class="input-box__input"
              data-testid="apikey-input"
              placeholder="请输入新的 APIKey"
              placeholder-class="input-box__placeholder"
            />
            <view class="input-box__action" data-testid="apikey-edit" @tap="toggleApiKeyEdit">
              <view class="glyph glyph--edit" aria-hidden="true" />
            </view>
          </view>
        </view>
        <view class="card__hint">
          <view class="glyph glyph--hint" aria-hidden="true" />
          <text class="card__hint-text">{{ APIKEY_HINT }}</text>
        </view>
      </view>

      <!-- 模型清单卡片：design id=f3529902（gap 12） -->
      <view class="card card--gap card--models">
        <view class="card__title-row">
          <text class="card__label">模型清单</text>
          <view class="card__spacer" />
          <text class="card__count" data-testid="selected-count">{{ form.selectedCountText }}</text>
        </view>
        <!-- 说明行：design id=5d8ad627 -->
        <text class="card__note">{{ MODEL_SECTION_NOTE }}</text>

        <!-- 厂商分组：design id=60022084 / ddfd78b5（#F8FAFC · r12 · padding 12 · gap 10） -->
        <view v-for="(group, gi) in form.vendors" :key="group.vendor" class="vendor" data-testid="vendor-group">
          <text class="vendor__name">{{ group.vendor }}</text>
          <view
            v-for="(model, mi) in group.models"
            :key="model.key"
            class="model-row"
            data-testid="model-row"
            @tap="onToggle(model.key)"
          >
            <view
              class="model-row__box"
              :class="{ 'model-row__box--checked': model.checked }"
              :data-testid="`model-check-${gi}-${mi}`"
            >
              <view v-if="model.checked" class="glyph glyph--tick" aria-hidden="true" />
            </view>
            <text
              class="model-row__name"
              :class="{ 'model-row__name--checked': model.checked }"
              :data-testid="`model-name-${gi}-${mi}`"
            >{{ model.name }}</text>
            <text class="model-row__spec" :data-testid="`model-spec-${gi}-${mi}`">{{ model.specText }}</text>
          </view>
        </view>

        <!-- 底部提示：design id=05ed9600（仅展示 N 个厂商，查看更多厂商 ›） -->
        <text
          v-if="form.hasCatalog"
          class="card__more"
          data-testid="catalog-more"
          @tap="onMoreVendors"
        >{{ form.catalogMoreText }}</text>
      </view>
    </view>

    <!-- 底部固定操作条：design id=c735e46e（白 · padding 12/16/24/16） -->
    <view class="submit-bar">
      <view class="submit-bar__ghost" data-testid="save-btn" @tap="onSave">
        <text class="submit-bar__ghost-text">保存草稿</text>
      </view>
      <view class="submit-bar__primary" data-testid="submit-btn" @tap="onSubmit">
        <view class="glyph glyph--rocket" aria-hidden="true" />
        <text class="submit-bar__primary-text">提交检测</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 页面 4【检测验真】提交接入凭证 2（序号 4 / page-4-2）
 * 设计真源：.calicat/raw/pages/page-4-2/design.tree.json（430 宽）
 * 接口：18-API Credential Tag → GET/PUT /api/v1/credentials/{id}、POST /api/v1/credentials/{id}/precheck
 *   ⚠️ 该卡片只列路径未列方法 → GET/PUT 为 REST 语义推断，已记台账待确认
 * 交互分类（台账序号 4 行）：
 *   返回 = navigation(navigateBack)
 *   凭证名称输入 / BaseURL 输入 / APIKey 编辑图标与输入 / 模型勾选 = client-only（本地表单态）
 *   「查看更多厂商 ›」= client-only（画布 30 页无厂商目录页 → 不臆造路由）
 *   保存草稿 = api（PUT /credentials/{id}）
 *   提交检测 = api（PUT /credentials/{id} 保存 → POST /credentials/{id}/precheck）+ navigation(/pages/detecting/index)
 * 入参：凭证 id 取自页面 query（H5/小程序 navigateTo 的 ?id=），无 query 时退 storage 键 aap_credential_id。
 */
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/api/http'
import { credentialApi } from '@/api/credential'
import {
  ALIAS_HINT,
  ANCHOR_NOTE,
  APIKEY_HINT,
  CONFIGURED_LABEL,
  MODEL_SECTION_NOTE,
  buildCredentialForm,
  buildSavePayload,
  toggleModel,
  validateBaseUrl,
  type VendorGroup
} from '@/utils/credential-form-model'

/** 页面入参 storage 键（navigateTo 无 query 时的兜底） */
const CREDENTIAL_ID_KEY = 'aap_credential_id'
const DETECTING_PAGE = '/pages/detecting/index'

const credentialId = ref('')
const alias = ref('')
const baseUrl = ref('')
const apiKey = ref('')
const apiKeyMask = ref('')
const isPrimary = ref(false)
const apiKeyEditing = ref(false)
const vendors = ref<VendorGroup[]>([])
const hasCatalog = ref(false)

const form = computed(() => ({
  vendors: vendors.value,
  selectedCountText: `已选 ${selectedCount.value} 个`,
  hasCatalog: hasCatalog.value,
  catalogMoreText: `仅展示 ${vendors.value.length} 个厂商，查看更多厂商 ›`
}))
const selectedCount = computed(() =>
  vendors.value.reduce((sum, g) => sum + g.models.filter((m) => m.checked).length, 0)
)

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

/** 页面入参：优先页面栈 query，其次 storage（单测/无 query 场景） */
function resolveCredentialId(): string {
  try {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
    const current = pages[pages.length - 1] as
      | { options?: Record<string, string>; $page?: { options?: Record<string, string> } }
      | undefined
    const query = current?.options ?? current?.$page?.options ?? {}
    if (query.id) return String(query.id)
  } catch {
    /* 无页面栈时忽略，走 storage 兜底 */
  }
  try {
    return String(uni.getStorageSync(CREDENTIAL_ID_KEY) || '')
  } catch {
    return ''
  }
}

function applyDetail(raw: Parameters<typeof buildCredentialForm>[0]) {
  const model = buildCredentialForm(raw)
  alias.value = model.alias
  baseUrl.value = model.baseUrl
  apiKeyMask.value = model.apiKeyMask
  isPrimary.value = model.isPrimary
  vendors.value = model.vendors
  hasCatalog.value = model.hasCatalog
}

async function load() {
  credentialId.value = resolveCredentialId()
  if (!credentialId.value) return
  try {
    applyDetail(await credentialApi.detail(credentialId.value))
  } catch (err) {
    toast(err instanceof ApiError ? err.message : '数据加载失败，请稍后重试')
  }
}

function goBack() {
  uni.navigateBack({ delta: 1 })
}

function toggleApiKeyEdit() {
  apiKeyEditing.value = !apiKeyEditing.value
}

function onToggle(key: string) {
  vendors.value = toggleModel(vendors.value, key)
}

/** 画布无厂商目录页（.calicat/inventory.json 30 页已核对）→ client-only，不臆造路由 */
function onMoreVendors() {
  toast('更多厂商即将开放')
}

/** 提交前置校验：名称必填 + BaseURL 形态（SSRF 内网拒绝由服务端 E-1201 判定） */
function validateForm(): string | null {
  if (!alias.value.trim()) return '请输入凭证名称'
  return validateBaseUrl(baseUrl.value)
}

function payloadOf() {
  return buildSavePayload({
    alias: alias.value,
    baseUrl: baseUrl.value,
    apiKey: apiKey.value,
    vendors: vendors.value
  })
}

/**
 * 取当前凭证标识；**没有就地新建**。
 *
 * 后端 `POST /credentials` 的 `api_key` 必填（credential-create.schema.json），
 * 故无标识时先校验 APIKey 再新建，避免把必然失败的请求发出去。
 * 新建成功后把 id 落 storage，供「检测进行中」「报告」等后续页面复用。
 */
async function ensureCredentialId(): Promise<string> {
  if (credentialId.value) return credentialId.value
  const payload = payloadOf()
  if (!payload.api_key) throw new ApiError('E-1001', '请输入 APIKey')
  const created = await credentialApi.create(payload)
  const id = String(created?.id ?? '')
  if (!id) throw new ApiError('E-2001', '新建凭证未返回标识')
  credentialId.value = id
  try {
    uni.setStorageSync(CREDENTIAL_ID_KEY, id)
  } catch {
    /* 忽略：落盘失败不影响本次流程 */
  }
  return id
}

async function onSave() {
  const invalid = validateForm()
  if (invalid) return toast(invalid)
  try {
    const id = await ensureCredentialId()
    await credentialApi.save(id, payloadOf())
    toast('已保存草稿')
  } catch (err) {
    toast(err instanceof ApiError ? err.message : '保存失败，请稍后重试')
  }
}

/** 提交检测 = 保存 + 预检（09-PRD §5：提交凭证后创建 DetectionJob 入队，前端不重复建任务） */
async function onSubmit() {
  const invalid = validateForm()
  if (invalid) return toast(invalid)
  uni.showLoading({ title: '提交中' })
  try {
    const id = await ensureCredentialId()
    await credentialApi.save(id, payloadOf())
    const result = await credentialApi.precheck(id)
    // 缺陷 10：把预检探到的**上游模型清单**写回凭证的 model_list。
    // 模型清单由后台接口提供（`PrecheckResult.models` ← 真打 {base_url}/models），
    // 前端此前直接丢弃 → model_list 恒空 → 报价单创建时「按凭证实时带出」带不出模型
    // → 供应商无法报价。没有清单时不写回，**更不能把已有 model_list 覆盖成空**。
    const upstreamModels = Array.isArray(result?.models)
      ? result.models.filter((m) => typeof m === 'string' && m.trim())
      : []
    if (upstreamModels.length > 0) {
      await credentialApi.save(id, {
        ...payloadOf(),
        model_list: upstreamModels.map((m) => ({ model_name: m }))
      })
    }
    const jobId = result?.job_id ?? result?.jobId ?? result?.detection_job_id ?? ''
    const query = jobId ? `?jobId=${encodeURIComponent(String(jobId))}` : ''
    uni.hideLoading()
    uni.navigateTo({ url: `${DETECTING_PAGE}${query}` })
  } catch (err) {
    uni.hideLoading()
    toast(err instanceof ApiError ? err.message : '提交失败，请稍后重试')
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.submit-page {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 顶部导航（design 0fa01a4a） */
.submit-page__topbar {
  background: $color-bg-card;
  /* --status-bar-height 由 uni-app 提供（H5 = 0）：设计帧未含状态栏偏移，此处补平台安全区 */
  padding: calc(48px + var(--status-bar-height, 0px)) 16px 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.submit-page__icon-btn {
  /* 设计 a01faac9 返回图标 = remixicon 24px：盒宽 26，行框 24×1.5 = 36
     —— 36 撑出顶部导航高 48+36+12 = 96（设计 PNG 实测 96；修前 24×24 → 栏高 84，全页上移 12） */
  width: 26px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.submit-page__title {
  margin-left: 12px;
  font-size: 17px;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
}

.submit-page__spacer {
  flex: 1;
}

/* chip：主凭证（design 62c388f2） / 已配置（design 15e5aeea） */
.chip {
  height: 22px;
  border-radius: 11px;
  padding: 0 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  flex: none;
}

.chip--primary {
  background: $color-primary-weak;
}

.chip--success {
  background: $color-success-weak;
}

.chip__text {
  font-size: $font-2xs;
  font-weight: 600;
  color: $color-primary;
  line-height: 1.2;
}

.chip__text--success {
  color: $color-success-text;
  /* 设计 157197ab「已配置」= SourceHanSans-Medium（500）；主凭证仍为 SemiBold（600） */
  font-weight: 500;
}

/* 表单区（design 0b3224f1） */
.submit-page__form {
  padding: 12px 16px 108px 16px; /* 底部留白 = 固定操作条高度 */
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.card {
  width: 100%;
  background: $color-bg-card;
  /* 设计 stroke 是 Figma center 描边（不占布局）：用 border 会把内容宽压成 356，
     而设计声明的内容宽是 358（= 398 - 20×2，design.tree.json 卡 padding [16,20,16,20]）→ 用 box-shadow 表达描边 */
  box-shadow: 0 0 0 1px $color-border-chip;
  border-radius: 16px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.card--gap {
  margin-top: 12px;
}

.card--models {
  gap: 12px;
}

.card__label {
  font-size: $font-sm;
  font-weight: 500;
  color: $color-text-secondary-2;
  /* 设计「凭证名称/BaseURL/APIKey/模型清单」文本层声明 height=18（13px 字，行框 18）→ 行高必须给 18px，
     否则卡片比设计矮 2.4px，下面所有元素整体上移 */
  line-height: 18px;
}

.card__title-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.card__spacer {
  flex: 1;
}

.card__count {
  font-size: $font-xs;
  font-weight: 600;
  color: $color-primary;
  line-height: 1.2;
}

.card__note {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  /* 设计「说明行」声明 height=16（11px 字）→ 行框 16px */
  line-height: 16px;
}

.card__field {
  padding-top: 8px;
  width: 100%;
}

/* 输入框 / 脱敏框（design fcbd984c / 06d0e6b5 / 7198fdce） */
.input-box {
  width: 100%;
  height: 46px;
  background: $color-bg-page;
  border: 1px solid $color-border;
  border-radius: 12px;
  padding: 0 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.input-box__input {
  flex: 1;
  min-width: 0;
  margin-left: 8px;
  font-size: $font-base;
  color: $color-text-secondary-2;
  line-height: 1.2;
  background: transparent;
}

.input-box__value {
  flex: 1;
  min-width: 0;
  margin-left: 8px;
  font-size: $font-base;
  font-weight: 500;
  color: $color-text-secondary-2;
  line-height: 1.2;
  /* 脱敏值必须单行（设计稿一行「sk-••••••••••••••••4f2a」；430 宽下换行会把 46 高输入框撑成两行） */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.input-box__placeholder {
  color: $color-text-placeholder;
}

.input-box__spacer {
  flex: 1;
}

.input-box__action {
  /* 设计 236156ed 编辑图标 = remixicon 18px（盒宽 20 · 行框 18×1.5=27） */
  width: 20px;
  height: 27px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.card__hint {
  width: 100%;
  padding-top: 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.card__hint-text {
  /* 设计 名称校验提示/APIKey提示 的文本容器 padding=[0,0,0,4] → 与图标盒左间距 4（修前 6，文本整体右移 2） */
  margin-left: 4px;
  font-size: $font-xs;
  color: $color-text-placeholder;
  line-height: 1.2;
}

/* 安全提示（design 7014d7f1） */
.note {
  width: 100%;
  background: $color-warning-weak-2;
  border-radius: 12px;
  padding: 10px;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  box-sizing: border-box;
}

.note--gap {
  margin-top: 12px;
}

.note__text {
  margin-left: 8px;
  flex: 1;
  font-size: $font-xs;
  color: $color-warning-text-2;
  /* 设计安全提示盒实测 56 高（padding 10 + 文本 2 行 × 18 行框，PNG 353..408）；
     行框 = 12 × 1.5 = 18 —— 与图标字形行框同一口径 */
  line-height: 18px;
}

/* 厂商分组（design 60022084 / ddfd78b5） */
.vendor {
  width: 100%;
  background: $color-bg-page;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-sizing: border-box;
  overflow: hidden;
}

.vendor__name {
  font-size: $font-sm;
  font-weight: 700;
  color: $color-text-primary;
  /* 设计「厂商名」声明 height=18（13px 字 Bold）→ 行框 18px */
  line-height: 18px;
}

.model-row {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  box-sizing: border-box;
}

.model-row__box {
  width: 18px;
  height: 18px;
  border: 1.5px solid $color-border-strong;
  border-radius: 5px;
  background: $color-bg-card;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  box-sizing: border-box;
}

.model-row__box--checked {
  background: $color-primary;
  border-color: $color-primary;
}

.model-row__name {
  flex: 1;
  min-width: 0;
  font-size: $font-sm;
  font-weight: 500;
  color: $color-text-tertiary;
  /* 设计「模型名」声明 height=18（13px 字 Medium）→ 行框 18px（= 勾选框高，模型行高 18） */
  line-height: 18px;
}

.model-row__name--checked {
  color: $color-text-primary;
}

.model-row__spec {
  font-size: $font-2xs;
  color: $color-text-placeholder;
  line-height: 1.2;
  flex: none;
}

.card__more {
  width: 100%;
  text-align: center;
  font-size: $font-2xs;
  color: $color-text-placeholder;
  /* 设计「底部提示」声明 height=16（11px 字）→ 行框 16px */
  line-height: 16px;
}

/* 底部固定操作条（design c735e46e） */
.submit-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  box-sizing: border-box;
  background: $color-bg-card;
  padding: 12px 16px 24px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.submit-bar__ghost {
  width: 156px;
  height: 48px;
  flex: none;
  background: $color-bg-card;
  border: 1px solid $color-border-strong;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 设计稿 stroke 为内描边（156x48 含边框）→ border-box 保证高度仍为 48，操作条总高与设计一致 */
  box-sizing: border-box;
}

.submit-bar__ghost-text {
  font-size: $font-base;
  font-weight: 500;
  color: $color-text-tertiary;
  line-height: 1.2;
}

.submit-bar__primary {
  margin-left: 12px;
  flex: 1;
  height: 48px;
  background: $color-primary;
  border-radius: 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.submit-bar__primary-text {
  font-size: $font-md;
  font-weight: 600;
  color: #ffffff;
  line-height: 1.2;
}

/* 图标占位（设计稿为 remixicon 矢量图标，PRD08 禁 emoji → CSS 形状占位，与序号 1/2/3 一致）
   ⚠️ 占位形状画进 ::before，外层 .glyph--* 的**盒子**尺寸 = 设计图层的声明盒
   （宽 = 图层 width；高 = 字号 × 1.5 行框）—— 图标盒撑起所在行的高度，
   盒子给错会让图标后的文本与整张卡片的高度都对不上（见 __measure-submit.html 的 overriddenByDecision） */
.glyph {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

/* 返回图标（设计 a01faac9：24px → 26×36） */
.glyph--back { width: 26px; height: 36px; }
.glyph--back::before {
  content: '';
  width: 9px;
  height: 9px;
  border-left: 2px solid $color-text-secondary-2;
  border-bottom: 2px solid $color-text-secondary-2;
  transform: rotate(45deg);
  margin-left: 3px;
}

/* 凭证名称图标（设计 20c5e850：18px → 20×27） */
.glyph--name { width: 20px; height: 27px; }
.glyph--name::before {
  content: '';
  width: 14px;
  height: 14px;
  border: 1.5px solid $color-text-placeholder;
  border-radius: 3px;
  box-sizing: border-box;
}

/* BaseURL 图标（设计 93df1e70：18px → 20×27） */
.glyph--link { width: 20px; height: 27px; }
.glyph--link::before {
  content: '';
  width: 14px;
  height: 14px;
  border: 1.5px solid $color-text-placeholder;
  border-radius: 50%;
  box-sizing: border-box;
}

/* APIKey 图标（设计 f29363b4：18px → 20×27） */
.glyph--key { width: 20px; height: 27px; }
.glyph--key::before {
  content: '';
  width: 12px;
  height: 12px;
  border: 2px solid $color-text-placeholder;
  border-radius: 50%;
  box-sizing: border-box;
}

/* 脱敏框编辑图标（设计 236156ed：18px → 20×27） */
.glyph--edit { width: 20px; height: 27px; }
.glyph--edit::before {
  content: '';
  width: 13px;
  height: 9px;
  border: 1.5px solid $color-text-placeholder;
  border-top: none;
  box-sizing: border-box;
  transform: rotate(-45deg);
}

/* 提示图标（设计 2fc23292 / a7fa3830：14px → 16×21；21 即设计提示行高） */
.glyph--hint { width: 16px; height: 21px; }
.glyph--hint::before {
  content: '';
  width: 12px;
  height: 12px;
  border: 1.5px solid $color-text-placeholder;
  border-radius: 50%;
  box-sizing: border-box;
}

/* 安全提示图标（设计 346a4a81：18px → 20×27） */
.glyph--shield { width: 20px; height: 27px; }
.glyph--shield::before {
  content: '';
  width: 14px;
  height: 14px;
  background: $color-warning-text;
  border-radius: 3px 3px 7px 7px;
}

/* 「已配置」勾（设计 0464d2d8：12px → 14×18） */
.glyph--check { width: 14px; height: 18px; }
.glyph--check::before {
  content: '';
  width: 7px;
  height: 4px;
  border-left: 1.5px solid $color-success;
  border-bottom: 1.5px solid $color-success;
  transform: rotate(-45deg);
}

/* 模型勾选态对勾（设计 cce69f8f：框 18×18 已由 .model-row__box 占位，形状保持原尺寸） */
.glyph--tick {
  width: 8px;
  height: 4px;
  border-left: 2px solid #ffffff;
  border-bottom: 2px solid #ffffff;
  transform: rotate(-45deg);
  margin-bottom: 2px;
}

/* 提交检测图标（设计 863cb3fd：20px → 22×30） */
.glyph--rocket {
  width: 22px;
  height: 30px;
  position: relative;
}

.glyph--rocket::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 11px;
  width: 9px;
  height: 8px;
  background: #ffffff;
  border-radius: 2px;
}

.glyph--rocket::after {
  content: '';
  position: absolute;
  left: 13px;
  top: 8px;
  width: 6px;
  height: 6px;
  border-top: 2px solid #ffffff;
  border-right: 2px solid #ffffff;
  transform: rotate(45deg);
}
</style>
