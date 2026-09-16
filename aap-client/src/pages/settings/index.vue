<template>
  <!--
    序号 23【工作台与我的】我的设置（page-23-2 / /pages/settings/index）
    设计真源：.calicat/raw/pages/page-23-2/design.tree.json（430 宽 · 设计总高 797 · **无 TabBar**）
      顶部导航 0..96 · 12 · 账号信息卡 108..331(223) · 12 · 通知设置卡 343..519(176) ·
      12 · 功能入口卡 531..717(186) · 底部说明 718..797(80)
  -->
  <view class="settings">
    <!-- 顶部导航（design 5f81549a：白底 padding 48/16/12/16 · 内容行 36 = 24px 图标 × 1.5） -->
    <view class="nav">
      <view class="nav__back" data-testid="settings-back" @tap="onBack">
        <view class="glyph glyph--back" aria-hidden="true" />
      </view>
      <view class="nav__title-wrap">
        <text class="nav__title" data-testid="settings-title">{{ model.navTitle }}</text>
      </view>
      <view class="nav__spacer" />
    </view>

    <!-- 账号信息卡（design a2608b12：padding 20 r18 · 标题行 27 + 首行 padding-top 16 + 行高 30 + 分隔 12/1/12） -->
    <view class="card card--account" data-testid="account-card">
      <view class="card__head">
        <view class="card__icon-wrap">
          <view class="glyph glyph--user" aria-hidden="true" />
        </view>
        <view class="card__title-wrap">
          <text class="card__title" data-testid="account-title">{{ model.accountTitle }}</text>
        </view>
      </view>

      <view class="rows">
        <template v-for="(row, index) in model.accountRows" :key="row.key">
          <view v-if="index > 0" class="row__sep" />
          <view
            class="row"
            data-testid="account-row"
            :data-key="row.key"
            :data-target="row.target"
            @tap="onAccountTap(row)"
          >
            <text class="row__label" data-testid="account-label">{{ row.label }}</text>
            <view v-if="row.pill" class="row__pill" data-testid="account-pill">
              <view class="row__pill-icon">
                <view class="glyph glyph--check" aria-hidden="true" />
              </view>
              <view class="row__pill-text-wrap">
                <text class="row__pill-text">{{ row.value }}</text>
              </view>
            </view>
            <text v-else class="row__value" data-testid="account-value">{{ row.value }}</text>
            <view class="row__spacer" />
            <view class="chevron-wrap" data-testid="account-chevron">
              <view class="glyph glyph--chevron-right" aria-hidden="true" />
            </view>
          </view>
        </template>
      </view>
    </view>

    <!-- 通知设置卡（design 63885808：padding 20 r18 描边 #EEF2F7 · 行高 34 = 13px 标题行盒 18 + 11px 副文案行盒 16） -->
    <view class="card card--notify" data-testid="notify-card">
      <view class="card__head">
        <view class="card__icon-wrap">
          <view class="glyph glyph--bell" aria-hidden="true" />
        </view>
        <view class="card__title-wrap">
          <text class="card__title" data-testid="notify-title">{{ model.notifyTitle }}</text>
        </view>
      </view>

      <view class="rows">
        <template v-for="(row, index) in model.notifyRows" :key="row.key">
          <view v-if="index > 0" class="row__sep" />
          <view class="nrow" data-testid="notify-row" :data-key="row.key">
            <view class="nrow__text">
              <text class="nrow__title" data-testid="notify-row-title">{{ row.title }}</text>
              <text class="nrow__desc" data-testid="notify-row-desc">{{ row.desc }}</text>
            </view>
            <view class="nrow__spacer" />
            <!-- 短信通知开关（client-only 本地态：18-API 无 /settings 端点 → 不发请求，台账缺口 3） -->
            <view
              v-if="row.control === 'switch'"
              class="switch"
              :class="{ 'switch--on': row.on }"
              data-testid="sms-switch"
              :data-on="row.on ? 'true' : 'false'"
              @tap="onToggleSms"
            >
              <view class="switch__knob" aria-hidden="true" />
            </view>
            <!-- 微信订阅消息徽标（只读展示，设计帧无 chevron） -->
            <template v-else-if="row.pill">
              <view class="row__pill" data-testid="subscribe-badge">
                <view class="row__pill-icon">
                  <view class="glyph glyph--check" aria-hidden="true" />
                </view>
                <view class="row__pill-text-wrap">
                  <text class="row__pill-text">{{ row.value }}</text>
                </view>
              </view>
            </template>
            <text v-else class="nrow__value" data-testid="notify-row-value">{{ row.value }}</text>
          </view>
        </template>
      </view>
    </view>

    <!-- 功能入口卡（design befb43af：padding 8/20 r18 描边 #EEF2F7 · 3 行 × (12 + 32 + 12) + 2 条 1px 分隔） -->
    <view class="card card--entries" data-testid="entry-card">
      <template v-for="(row, index) in model.entryRows" :key="row.key">
        <view v-if="index > 0" class="entry__sep" data-testid="entry-sep" />
        <!-- 行级 hook 沿用序号 21 约定：data-testid=`row-<key>` -->
        <view
          class="erow"
          :data-testid="`row-${row.key}`"
          :data-key="row.key"
          :data-tone="row.tone"
          :data-action="row.action || ''"
          @tap="onEntryTap(row)"
        >
          <view
            class="erow__icon"
            data-testid="entry-icon"
            :class="`erow__icon--${row.tone}`"
            @tap.stop="onEntryAvatar(row)"
          >
            <view class="glyph-wrap">
              <view class="glyph" :class="`glyph--${row.key}`" aria-hidden="true" />
            </view>
          </view>
          <view class="erow__text-wrap">
            <text class="erow__label" :class="`erow__label--${row.tone}`" data-testid="entry-label">
              {{ row.label }}
            </text>
          </view>
          <view class="row__spacer" />
          <view class="chevron-wrap">
            <view class="glyph glyph--chevron-right" aria-hidden="true" />
          </view>
        </view>
      </template>
    </view>

    <!-- 底部说明（design 6c196387：padding 24/0 居中两行 11px 行盒 16） -->
    <view class="footer">
      <text class="footer__version" data-testid="footer-version">{{ model.footer.version }}</text>
      <text class="footer__copyright" data-testid="footer-copyright">{{ model.footer.copyright }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 23【工作台与我的】我的设置（page-23-2 / /pages/settings/index）
 *
 * 设计真源：.calicat/raw/pages/page-23-2/design.tree.json
 *   （430 宽 · 设计总高 797 · 导航 96 · 卡 223/176/186 · 底部说明 80 · **无 TabBar**）
 * 接口真源：18-API设计OpenAPI.md（前缀 /api/v1）「Auth」Tag
 *   GET /auth/me（账号信息三行）· POST /auth/logout（退出登录）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 18-API + 设计稿控件语义；分类见台账序号 23：
 *   返回 = navigation（navigateBack）
 *   手机号 / 微信绑定 / 登录安全三行 = navigation **无落点**（画布 30 页无对应页 → 不跳转、不弹占位提示）
 *   短信通知开关 = client-only（本地态；18-API 无 /settings 端点 → `missing-prd`，不发请求）
 *   微信订阅消息徽标 = client-only（只读展示）
 *   实名与主体信息 = navigation → /pages/profile/index（序号 10.1 已实现）
 *   服务协议与隐私政策 = navigation **无落点**（画布无页 + PRD 无外链地址 → 不臆造 URL）
 *   退出登录 = api → POST /auth/logout（先二次确认；无论成败都 reLaunch 登录页）
 *
 * ⚠️ 缺口（全部记台账序号 23，不臆造）：详见 src/utils/settings-model.ts 文件头注释。
 */
import { computed, onMounted, ref } from 'vue'
import { authApi } from '@/api/auth'
import { LOGIN_PAGE } from '@/utils/routes'
import {
  LOAD_FAIL_TEXT,
  LOGOUT_ACTION,
  LOGOUT_CONFIRM_CONTENT,
  LOGOUT_CONFIRM_TITLE,
  LOGOUT_FAIL_TEXT,
  SMS_NOTIFY_DEFAULT,
  buildSettingsOverview,
  type AccountRow,
  type EntryRow,
  type SettingsRaw
} from '@/utils/settings-model'

const raw = ref<SettingsRaw | null>(null)
/** 短信通知开关：client-only 本地态，初始值取设计帧常量（开） */
const smsOn = ref(SMS_NOTIFY_DEFAULT)

const model = computed(() => buildSettingsOverview(raw.value, smsOn.value))

async function load() {
  try {
    const res = await authApi.me()
    /* MeResult → SettingsRaw：18-API 无字段级 schema，逐字段容错读取（经 unknown 转换，同 http.ts 口径） */
    raw.value = (res as unknown as SettingsRaw) ?? null
  } catch {
    raw.value = null
    uni.showToast({ title: LOAD_FAIL_TEXT, icon: 'none' })
  }
}

/** 返回：navigation（本页由「我的 → 账号与设置」navigateTo 进入，无 TabBar） */
function onBack() {
  uni.navigateBack({ delta: 1 })
}

/**
 * 账号信息三行：设计帧有 chevron，但画布 30 页**无**手机号 / 微信绑定 / 登录安全页，PRD 亦无对应入口
 * → 无落点：不跳转、不弹占位 toast、不臆造路由（同序号 22「明细入口」口径，已记台账待拍板）。
 */
function onAccountTap(_row: AccountRow) {
  /* no-op：等待人类拍板是否新增账号信息 / 登录安全页 */
}

/** 入口图标自身不承担行为（点击冒泡到行），显式吞掉避免与行重复触发 */
function onEntryAvatar(_row: EntryRow) {
  /* no-op */
}

/** 功能入口卡：优先 api 动作（退出登录），其次导航落点，无落点则 no-op */
function onEntryTap(row: EntryRow) {
  if (row.action === LOGOUT_ACTION) {
    void onLogout()
    return
  }
  if (row.target) {
    uni.navigateTo({ url: row.target })
    return
  }
  /* 「服务协议与隐私政策」无画布页、PRD 无外链地址 → 无落点 */
}

/** 短信通知开关：client-only（只改本地态，不发请求 —— 18-API 无 /settings 端点，台账缺口 3） */
function onToggleSms() {
  smsOn.value = !smsOn.value
}

/** 退出登录二次确认（设计帧无弹窗稿 → 占位文案，同序号 8「删除」口径） */
function confirmLogout(): Promise<boolean> {
  return new Promise((resolve) => {
    uni.showModal({
      title: LOGOUT_CONFIRM_TITLE,
      content: LOGOUT_CONFIRM_CONTENT,
      success: (res) => resolve(Boolean(res.confirm)),
      fail: () => resolve(false)
    })
  })
}

/** 退出登录：api（POST /auth/logout）。authApi.logout 的 finally 已清本地 token，故无论成败都回登录页 */
async function onLogout() {
  const confirmed = await confirmLogout()
  if (!confirmed) return
  try {
    await authApi.logout()
  } catch {
    uni.showToast({ title: LOGOUT_FAIL_TEXT, icon: 'none' })
  } finally {
    uni.reLaunch({ url: LOGIN_PAGE })
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.settings {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  box-sizing: border-box;
  background: $color-bg-page;
}

/* ============================== 顶部导航 ============================== */

.nav {
  height: 96px;
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
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav__title-wrap {
  padding-left: 12px;
  flex: none;
  display: flex;
  align-items: center;
}

.nav__title {
  display: block;
  font-size: 17px;
  font-weight: 700;
  line-height: 20.4px;
  color: $color-text-primary;
}

.nav__spacer {
  flex: 1;
  min-width: 0;
}

/* ============================== 卡片通用 ============================== */

.card {
  margin: 12px 16px 0 16px;
  padding: 20px;
  box-sizing: border-box;
  border-radius: $radius-xl;
  background: $color-bg-card;
}

/* 账号信息卡在设计帧里**只有** effects drop_shadow(0,6,20,rgba(15,23,42,.06))、**无** stroke
   （设计树 a2608b12）；通知设置卡 / 功能入口卡（63885808 / befb43af）只有 stroke #EEF2F7、无 effects。
   → 逐卡实现，不许统一（PNG 实测：卡1 下方 12px 间隙最暗 241 = 投影带，卡2 下方间隙 = 页面底色 248/250/252）。
   投影漏实现由载体页 __measure-settings.html 的 account.shadow 断言抓出（红基线 2026-09-16）。 */
.card--account {
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

.card--notify,
.card--entries {
  box-shadow: 0 0 0 1px $color-border-chip;
}

.card__head {
  height: 27px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

/* 图标行盒 = 字号 × 1.5（设计 remixicon 18px → 27），宽取设计声明 20 */
.card__icon-wrap {
  width: 20px;
  height: 27px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $color-primary;
}

.card__title-wrap {
  padding-left: 6px;
  flex: none;
  display: flex;
  align-items: center;
}

.card__title {
  display: block;
  font-size: $font-base;
  font-weight: 600;
  line-height: 16.8px;
  color: $color-text-primary;
}

/* ============================== 账号信息卡 ============================== */

.rows {
  padding-top: 16px;
}

.row__sep {
  height: 1px;
  margin: 12px 0;
  background: $color-bg-subtle;
}

.row {
  height: 30px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

/* 标签列固定 87（设计帧标签与值各声明 width 87）→ 值列起点 x123 */
.row__label {
  display: block;
  width: 87px;
  flex: none;
  font-size: $font-sm;
  line-height: 15.6px;
  color: $color-text-muted;
}

.row__value {
  display: block;
  font-size: $font-sm;
  font-weight: 600;
  line-height: 15.6px;
  color: $color-text-primary;
}

.row__spacer {
  flex: 1;
  min-width: 0;
}

/* chevron 盒：设计声明宽 22 / 行盒 30（20px 图标 × 1.5） */
.chevron-wrap {
  width: 22px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 绿胶囊（已绑定 / 已授权）：h22 r11 #ECFDF5 · icon 14 盒 + 4 + 字 11px Medium */
.row__pill {
  height: 22px;
  padding: 0 8px;
  box-sizing: border-box;
  border-radius: 11px;
  background: $color-success-weak;
  flex: none;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.row__pill-icon {
  width: 14px;
  height: 18px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.row__pill-text-wrap {
  padding-left: 4px;
  flex: none;
}

.row__pill-text {
  display: block;
  font-size: $font-2xs;
  font-weight: 500;
  line-height: 13.2px;
  color: $color-success-text;
}

/* ============================== 通知设置卡 ============================== */

/* 行高 34 = 13px 标题行盒 18 + 11px 副文案行盒 16（设计树显式声明 18 / 16） */
.nrow {
  height: 34px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.nrow__text {
  flex: none;
  display: flex;
  flex-direction: column;
}

.nrow__title {
  display: block;
  font-size: $font-sm;
  font-weight: 500;
  line-height: 18px;
  color: $color-text-primary;
}

.nrow__desc {
  display: block;
  font-size: $font-2xs;
  line-height: 16px;
  color: $color-text-placeholder;
}

.nrow__value {
  display: block;
  font-size: $font-sm;
  font-weight: 600;
  line-height: 15.6px;
  color: $color-text-primary;
}

.nrow__spacer {
  flex: 1;
  min-width: 0;
}

/* 开关：设计帧 46×26 r13 padding 0/4 · 钮 22×20 r10；关态设计未给色 → 中性 #CBD5E1（占位，记台账） */
.switch {
  width: 46px;
  height: 26px;
  padding: 0 4px;
  box-sizing: border-box;
  border-radius: 13px;
  background: $color-border-strong;
  flex: none;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
}

.switch--on {
  background: $color-primary;
  justify-content: flex-end;
}

.switch__knob {
  width: 22px;
  height: 20px;
  border-radius: 10px;
  background: $color-bg-card;
}

/* ============================== 功能入口卡 ============================== */

.card--entries {
  padding: 8px 20px;
}

.entry__sep {
  height: 1px;
  background: $color-bg-subtle;
}

/* 行高 56 = padding 12 + 图标盒 32 + padding 12（设计声明 padding [12,0,12,0] + height=fit_content） */
.erow {
  height: 32px;
  padding: 12px 0;
  box-sizing: content-box;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.erow__icon {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
}

.erow__icon--primary {
  background: $color-primary-weak;
  color: $color-primary;
}

.erow__icon--neutral {
  background: $color-bg-subtle;
  color: $color-text-muted;
}

.erow__icon--danger {
  background: $color-danger-weak;
  color: $color-danger-strong;
}

/* 图标字形行盒 = 字号 × 1.5（18 → 27），宽取设计声明 20 */
.glyph-wrap {
  width: 20px;
  height: 27px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.erow__text-wrap {
  padding-left: 10px;
  flex: none;
}

.erow__label {
  display: block;
  font-size: $font-sm;
  font-weight: 500;
  line-height: 15.6px;
  color: $color-text-primary;
}

.erow__label--danger {
  color: $color-danger-strong;
}

/* ============================== 图标占位（设计用 remixicon 字形，仓库无图标资源；R-26 禁 emoji） ============================== */

.glyph {
  display: block;
  position: relative;
}

/* 设计声明宽 26 / 墨迹 16×16（remixicon 24px） */
.glyph--back {
  width: 16px;
  height: 16px;

  &::before {
    content: '';
    position: absolute;
    left: 2px;
    top: 2px;
    width: 11px;
    height: 11px;
    border-left: 2px solid $color-text-secondary-2;
    border-bottom: 2px solid $color-text-secondary-2;
    transform: rotate(45deg);
  }
}

.glyph--chevron-right {
  width: 8px;
  height: 8px;
  border-top: 1.5px solid $color-border-strong;
  border-right: 1.5px solid $color-border-strong;
  transform: rotate(45deg);
}

/* 「已绑定 / 已授权」胶囊内对勾（设计 remixicon check 12px，声明宽 14） */
.glyph--check {
  width: 10px;
  height: 7px;
  margin-top: -2px;
  border-left: 1.6px solid $color-wechat;
  border-bottom: 1.6px solid $color-wechat;
  transform: rotate(-45deg);
}

/* 账号信息图标（人像） */
.glyph--user {
  width: 16px;
  height: 16px;

  &::before {
    content: '';
    position: absolute;
    left: 4px;
    top: 0;
    width: 8px;
    height: 8px;
    box-sizing: border-box;
    border: 1.6px solid currentColor;
    border-radius: 50%;
  }

  &::after {
    content: '';
    position: absolute;
    left: 1px;
    bottom: 0;
    width: 14px;
    height: 7px;
    box-sizing: border-box;
    border: 1.6px solid currentColor;
    border-bottom: none;
    border-radius: 7px 7px 0 0;
  }
}

/* 通知设置图标（铃铛） */
.glyph--bell {
  width: 16px;
  height: 16px;

  &::before {
    content: '';
    position: absolute;
    left: 2px;
    top: 0;
    width: 12px;
    height: 12px;
    box-sizing: border-box;
    border: 1.6px solid currentColor;
    border-radius: 6px 6px 3px 3px;
  }

  &::after {
    content: '';
    position: absolute;
    left: 7px;
    bottom: 1px;
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: currentColor;
  }
}

/* 实名与主体信息图标（盾牌） */
.glyph--identity {
  width: 16px;
  height: 16px;

  &::before {
    content: '';
    position: absolute;
    left: 2px;
    top: 1px;
    width: 12px;
    height: 14px;
    box-sizing: border-box;
    border: 1.6px solid currentColor;
    border-radius: 4px 4px 7px 7px;
  }
}

/* 服务协议与隐私政策图标（文档 + 两行字） */
.glyph--legal {
  width: 16px;
  height: 16px;

  &::before {
    content: '';
    position: absolute;
    left: 2px;
    top: 1px;
    width: 12px;
    height: 14px;
    box-sizing: border-box;
    border: 1.6px solid currentColor;
    border-radius: 2px;
  }

  &::after {
    content: '';
    position: absolute;
    left: 5px;
    top: 5px;
    width: 6px;
    height: 1.4px;
    background: currentColor;
    box-shadow: 0 3px 0 currentColor;
  }
}

/* 退出登录图标（门 + 箭头） */
.glyph--logout {
  width: 16px;
  height: 16px;

  &::before {
    content: '';
    position: absolute;
    left: 1px;
    top: 2px;
    width: 8px;
    height: 12px;
    box-sizing: border-box;
    border: 1.6px solid currentColor;
    border-right: none;
    border-radius: 2px 0 0 2px;
  }

  &::after {
    content: '';
    position: absolute;
    right: 1px;
    top: 4px;
    width: 6px;
    height: 6px;
    border-top: 1.6px solid currentColor;
    border-right: 1.6px solid currentColor;
    transform: rotate(45deg);
  }
}

/* ============================== 底部说明 ============================== */

.footer {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.footer__version {
  display: block;
  font-size: $font-2xs;
  line-height: 16px;
  color: $color-text-placeholder;
}

.footer__copyright {
  display: block;
  font-size: $font-2xs;
  line-height: 16px;
  color: $color-border-strong;
}
</style>
