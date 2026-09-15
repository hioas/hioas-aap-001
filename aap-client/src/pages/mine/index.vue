<template>
  <!--
    序号 21【工作台与我的】我的页（page-21-2 / /pages/mine/index）
    设计真源：.calicat/raw/pages/page-21-2/design.tree.json（430 宽 · 设计总高 990）
      用户头部 0..127(128) · 12 · 钱包卡 140..331(192) · 12 · 报价入口卡 344..642(299) ·
      12 · 主体与证照卡 655..889(235) · 16 · 底部 TabBar 906..989(84)
  -->
  <view class="mine">
    <!-- 用户头部（design ab268cad：padding 48/16/24/16 · #1D4ED8） -->
    <view class="head">
      <view class="head__avatar">
        <view class="head__avatar-glyph" aria-hidden="true" />
      </view>
      <view class="head__info">
        <text class="head__company" data-testid="mine-company">{{ model.head.company }}</text>
        <view class="head__tags">
          <view v-if="model.head.typeLabel" class="head__type" data-testid="mine-type">
            <text class="head__type-text">{{ model.head.typeLabel }}</text>
          </view>
          <view class="head__tag-gap" />
          <view v-if="model.head.verified" class="head__verified" data-testid="mine-verified">
            <view class="head__dot" />
            <text class="head__verified-text">{{ VERIFIED_TEXT }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 我的钱包卡（design 0a649e83：padding 20 · r18 · 描边 #EEF2F7） -->
    <view class="card card--wallet">
      <view class="wallet__title-row">
        <text class="wallet__title">{{ WALLET_TITLE }}</text>
        <view class="card__spacer" />
        <view class="chevron" aria-hidden="true" />
      </view>

      <view class="wallet__balance-row">
        <view class="wallet__balance">
          <text class="wallet__label">{{ WALLET_AVAILABLE_LABEL }}</text>
          <text class="wallet__amount" data-testid="wallet-available">{{ model.wallet.available }}</text>
        </view>
        <view class="card__spacer" />
        <view class="withdraw" data-testid="wallet-withdraw" @tap="onWithdraw">
          <text class="withdraw__text">{{ WITHDRAW_TEXT }}</text>
        </view>
      </view>

      <view class="wallet__detail-row">
        <view class="wallet__detail">
          <text class="wallet__label">{{ PENDING_LABEL }}</text>
          <text class="wallet__sub-amount" data-testid="wallet-pending">{{ model.wallet.pending }}</text>
        </view>
        <view class="wallet__divider" :style="{ background: WALLET_DIVIDER_COLOR }" />
        <view class="wallet__detail">
          <text class="wallet__label">{{ SETTLED_LABEL }}</text>
          <text class="wallet__sub-amount" data-testid="wallet-settled">{{ model.wallet.settled }}</text>
        </view>
      </view>
    </view>

    <!-- 我的报价入口卡（design cda20980：padding 8/20 · 5 行 + 横分隔1~3） -->
    <view class="card card--entries">
      <template v-for="(row, index) in entries" :key="row.key">
        <view v-if="index > 0 && index < entries.length - 1" class="row__sep" />
        <view class="row" :data-testid="`row-${row.key}`" @tap="onRowTap(row)">
          <view class="row__icon" :style="{ background: row.iconBg }">
            <view
              class="row__glyph"
              :class="`row__glyph--${row.glyph}`"
              :style="{ color: row.iconColor }"
              aria-hidden="true"
            />
          </view>
          <text class="row__label">{{ row.label }}</text>
          <view class="card__spacer" />
          <text
            v-if="row.value"
            class="row__value"
            :data-tone="row.valueTone"
            :style="{ color: valueColor(row) }"
          >
            {{ row.value }}
          </text>
          <view class="chevron chevron--row" aria-hidden="true" />
        </view>
      </template>
    </view>

    <!-- 主体与证照卡（design cd8b4c81：padding 8/20 · 4 行 + 横分隔4~6） -->
    <view class="card card--records">
      <template v-for="(row, index) in records" :key="row.key">
        <view v-if="index > 0" class="row__sep" />
        <view class="row" :data-testid="`row-${row.key}`" @tap="onRowTap(row)">
          <view class="row__glyph row__glyph--plain" :style="{ color: row.iconColor }" aria-hidden="true" />
          <text class="row__label">{{ row.label }}</text>
          <view class="card__spacer" />
          <view v-if="row.value && row.pill" class="row__pill">
            <text class="row__pill-text" :style="{ color: PILL_TEXT_COLOR }">{{ row.value }}</text>
          </view>
          <text
            v-else-if="row.value"
            class="row__value"
            :data-tone="row.valueTone"
            :style="{ color: valueColor(row) }"
          >
            {{ row.value }}
          </text>
          <view class="chevron chevron--row" aria-hidden="true" />
        </view>
      </template>
    </view>

    <!-- 底部 TabBar（共享组件；本帧高亮「我的」#2563EB） -->
    <AppTabBar :active-color="TAB_ACTIVE_COLOR" />
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 21【工作台与我的】我的页（page-21-2 / /pages/mine/index）
 *
 * 设计真源：.calicat/raw/pages/page-21-2/design.tree.json
 *   （430 宽 · 设计总高 990 · 头部 128 · 钱包卡 192 · 报价入口卡 299 · 主体与证照卡 235 · TabBar 84）
 * 接口真源：18-API设计OpenAPI.md（前缀 /api/v1）
 *   GET /provider/profile（企业名 / 类型 / 已认证 / 完整度）
 *   GET /payments（钱包三金额）· GET /quotes · GET /reports · GET /contracts?status=PENDING_SIGN ·
 *   GET /credentials · GET /notifications?unread=true（各入口右侧计数）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 18-API + 设计稿控件语义；分类见台账序号 21：
 *   9 个入口行 = navigation（结算账户无落点 → 阻塞，已记台账）
 *   「提现」= **missing-prd**（18-API 无提现端点；02-PRD「供应商侧资金结算/提现（走线下）」与设计稿冲突）→ 占位提示
 *   TabBar = navigation（我的 = 当前模块，不跳转）
 *
 * ⚠️ 缺口（全部记台账序号 21，不臆造）：
 *   1. 钱包三金额字段名与归属为推断（18-API 无钱包汇总 schema）；缺字段渲染「—」；
 *   2. 各入口计数无汇总接口 → 用各模块列表接口 pageSize=1 取 total；
 *   3. 「已认证」PRD 零命中 → verified 布尔优先，其次 status==='PUBLISHED'；
 *   4. 「结算账户 / 已绑定」PRD 零命中且画布无该页 → 无落点；
 *   5. 设计帧第 4/5 行之间**无**分隔线（设计树 kids 只有 横分隔1~3）→ 按设计实现；
 *   6. 图标为 CSS 形状占位（设计用 remixicon 字形，仓库无图标资源；R-26 禁 emoji）。
 */
import { computed, onMounted, ref } from 'vue'
import AppTabBar from '@/components/app-tab-bar/AppTabBar.vue'
import { TAB_ACTIVE_COLOR } from '@/utils/app-tab-bar-model'
import { credentialApi } from '@/api/credential'
import { contractApi } from '@/api/contract'
import { notificationApi } from '@/api/notification'
import { paymentApi } from '@/api/payment'
import { providerApi } from '@/api/provider'
import { quoteApi } from '@/api/quote'
import { reportApi } from '@/api/report'
import {
  LOAD_FAIL_TEXT,
  PENDING_LABEL,
  SETTLED_LABEL,
  VERIFIED_TEXT,
  WALLET_AVAILABLE_LABEL,
  WALLET_TITLE,
  WITHDRAW_PLACEHOLDER_TEXT,
  WITHDRAW_TEXT,
  buildMineModel,
  countOf,
  type MineCounts,
  type MineProfileSource,
  type MineRowView,
  type MineWalletSource
} from '@/utils/mine-model'

/** 设计帧取色（逐值来自 design.tree.json） */
const WALLET_DIVIDER_COLOR = '#E2E8F0'
const PILL_TEXT_COLOR = '#15803D'
const VALUE_COLORS: Record<string, string> = {
  muted: '#94A3B8',
  warning: '#D97706',
  plain: '#000000',
  success: '#15803D'
}

/** 待签署计数口径（10-PRD §4.2 状态机 PENDING_SIGN；CREATED 是否合并计数待拍板 → 台账） */
const PENDING_SIGN_STATUS = 'PENDING_SIGN'

const profileRaw = ref<MineProfileSource | null>(null)
const walletRaw = ref<MineWalletSource | null>(null)
const counts = ref<MineCounts>({})

const model = computed(() =>
  buildMineModel({ profile: profileRaw.value, wallet: walletRaw.value, counts: counts.value })
)
const entries = computed(() => model.value.rows.filter((row) => row.group === 'quote'))
const records = computed(() => model.value.rows.filter((row) => row.group === 'profile'))

const valueColor = (row: MineRowView) => VALUE_COLORS[row.valueTone] ?? VALUE_COLORS.muted

/**
 * 首屏取数：7 个只读 GET 并发。
 * 计数接口一律 pageSize=1（只要 total，不拉列表实体）；任一失败 → 占位「—」+ 占位提示。
 */
async function load() {
  try {
    const [profile, wallet, quotes, reports, contracts, credentials, notifications] = await Promise.all([
      providerApi.profile(),
      paymentApi.list(),
      quoteApi.list({ page: 1, pageSize: 1 }),
      reportApi.list({ page: 1, pageSize: 1 }),
      contractApi.list({ page: 1, pageSize: 1, status: PENDING_SIGN_STATUS }),
      credentialApi.list({ page: 1, pageSize: 1 }),
      notificationApi.list({ page: 1, pageSize: 1, unread: 'true' })
    ])
    profileRaw.value = (profile as MineProfileSource) ?? null
    walletRaw.value = (wallet as MineWalletSource) ?? null
    counts.value = {
      quotes: countOf(quotes),
      reports: countOf(reports),
      contracts: countOf(contracts),
      credentials: countOf(credentials),
      unread: countOf(notifications)
    }
  } catch {
    profileRaw.value = null
    walletRaw.value = null
    counts.value = {}
    uni.showToast({ title: LOAD_FAIL_TEXT, icon: 'none' })
  }
}

/** 入口行：navigation（无落点行不跳转 —— 结算账户记台账阻塞） */
function onRowTap(row: MineRowView) {
  if (!row.target) return
  uni.navigateTo({ url: row.target })
}

/**
 * 提现：**missing-prd** —— 18-API 无提现端点，02-PRD 写「供应商侧资金结算/提现（走线下）」，
 * 与设计稿按钮冲突（已记台账待拍板）→ 不臆造流程，只做占位提示。
 */
function onWithdraw() {
  uni.showToast({ title: WITHDRAW_PLACEHOLDER_TEXT, icon: 'none' })
}

onMounted(load)
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.mine {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  box-sizing: border-box;
  background: $color-bg-page;
  /* 底部留白 = 16 间隙 + TabBar 84（设计：卡3 结束 889 → TabBar 906..989） */
  padding-bottom: 100px;
}

/* ============================== 用户头部 ============================== */

.head {
  height: 128px;
  box-sizing: border-box;
  padding: 48px 16px 24px 16px;
  background: $color-brand;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.head__avatar {
  width: 56px;
  height: 56px;
  flex: none;
  border-radius: 28px;
  background: $color-bg-card;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 头像图形（design 用 remixicon \uf274 30px）→ CSS 占位：人形剪影（避开复选框/单选框同形） */
.head__avatar-glyph {
  position: relative;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: $color-brand;

  &::after {
    content: '';
    position: absolute;
    left: -4px;
    top: 19px;
    width: 24px;
    height: 10px;
    border-radius: 6px 6px 0 0;
    background: $color-brand;
  }
}

.head__info {
  flex: none;
  padding-left: 12px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.head__company {
  display: block;
  font-size: $font-xl;
  font-weight: 700;
  line-height: 26px;
  color: $color-bg-card;
}

.head__tags {
  padding-top: 8px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.head__type {
  height: 22px;
  box-sizing: border-box;
  padding: 0 8px;
  border-radius: 11px;
  background: $color-bg-card;
  display: flex;
  align-items: center;
}

.head__type-text {
  display: block;
  font-size: $font-2xs;
  font-weight: 600;
  line-height: 16px;
  color: $color-brand;
}

.head__tag-gap {
  width: 9px;
  height: 1px;
}

.head__verified {
  height: 22px;
  box-sizing: border-box;
  padding: 0 8px;
  border-radius: 11px;
  background: $color-verified-weak;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.head__dot {
  width: 9px;
  height: 7px;
  flex: none;
  border-radius: 4px;
  background: $color-success;
}

.head__verified-text {
  display: block;
  margin-left: 4px;
  font-size: $font-2xs;
  font-weight: 500;
  line-height: 16px;
  color: $color-verified-text;
}

/* ============================== 卡片通用 ============================== */

.card {
  padding: 8px 20px;
  border-radius: $radius-xl;
  background: $color-bg-card;
  /* 设计描边画在盒外（可见尺寸 = 声明尺寸）→ 用 ring，不占布局（SKILL §4.8） */
  box-shadow: 0 0 0 1px $color-border-chip;
}

.card--wallet {
  margin: 12px 16px 0 16px;
  padding: 20px;
}

.card--entries {
  margin: 12px 16px 0 16px;
}

.card--records {
  margin: 12px 16px 0 16px;
}

.card__spacer {
  flex: 1;
  min-width: 0;
}

/* 行右侧 chevron（design 图标段落 20px → 行盒 30；宽度取设计声明 22） */
.chevron {
  width: 22px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;

  &::after {
    content: '';
    width: 8px;
    height: 8px;
    border-top: 1.5px solid $color-border-strong;
    border-right: 1.5px solid $color-border-strong;
    transform: rotate(45deg);
  }
}

.chevron--row {
  padding-left: 4px;
  box-sizing: content-box;
}

/* ============================== 我的钱包卡 ============================== */

.wallet__title-row {
  height: 30px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.wallet__title {
  display: block;
  font-size: $font-base;
  font-weight: 600;
  line-height: 21px;
  color: $color-text-primary;
}

.wallet__balance-row {
  margin-top: 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.wallet__balance {
  width: 134px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.wallet__label {
  display: block;
  font-size: $font-2xs;
  line-height: 16px;
  color: $color-text-placeholder;
}

.wallet__amount {
  display: block;
  margin-top: 2px;
  font-size: 24px;
  font-weight: 800;
  line-height: 34px;
  color: $color-text-primary;
}

.withdraw {
  height: 38px;
  flex: none;
  box-sizing: border-box;
  padding: 0 16px;
  border-radius: $radius-md;
  background: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;
}

.withdraw__text {
  display: block;
  font-size: $font-sm;
  font-weight: 500;
  line-height: 20px;
  color: $color-bg-card;
}

.wallet__detail-row {
  margin-top: 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.wallet__detail {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.wallet__divider {
  width: 2px;
  height: 32px;
  flex: none;
}

.wallet__sub-amount {
  display: block;
  font-size: $font-base;
  font-weight: 600;
  line-height: 22px;
  color: $color-text-primary;
}

/* ============================== 入口行（两卡共用） ============================== */

.row {
  height: 56px;
  box-sizing: border-box;
  padding: 12px 0;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.card--records .row {
  height: 54px;
}

.row__sep {
  height: 1px;
  background: $color-bg-subtle;
}

.row__icon {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 图标字形（design 用 remixicon 18px）→ CSS 占位；颜色由行模型内联到 color，形状取 currentColor
   （占位块 16×16 接近设计字形墨迹 14~16，避免实心大块被误读成图片位） */
.row__glyph {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: currentColor;
}

.row__glyph--plain {
  width: 20px;
  height: 27px;
  flex: none;
  background: transparent;
}

.row__glyph--plain::after {
  content: '';
  display: block;
  width: 16px;
  height: 16px;
  margin: 5.5px 2px 0 2px;
  border-radius: 4px;
  background: currentColor;
}

.row__label {
  display: block;
  margin-left: 10px;
  font-size: $font-sm;
  font-weight: 500;
  line-height: 19.5px;
  color: $color-text-primary;
}

.row__value {
  display: block;
  font-size: $font-xs;
  line-height: 18px;
  flex: none;
}

.row__pill {
  height: 20px;
  flex: none;
  box-sizing: border-box;
  padding: 0 8px;
  border-radius: 10px;
  background: $color-success-weak;
  display: flex;
  align-items: center;
}

.row__pill-text {
  display: block;
  font-size: 10px;
  font-weight: 500;
  line-height: 14px;
}
</style>
