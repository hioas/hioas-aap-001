<template>
  <view class="messages">
    <!-- 顶部导航（design 49663acf：padding 48/16/12/16 · 标题 20px Bold + 未读胶囊 + 全部已读） -->
    <view class="messages__topbar">
      <text class="messages__title">{{ PAGE_TITLE }}</text>
      <view v-if="model.badgeText" class="messages__badge-wrap">
        <view class="messages__badge" data-testid="unread-badge">
          <text class="messages__badge-text">{{ model.badgeText }}</text>
        </view>
      </view>
      <view class="messages__spacer" />
      <view class="messages__read-all" data-testid="read-all" @tap="markAllRead">
        <view class="messages__read-all-icon">
          <view class="messages__read-all-glyph" aria-hidden="true" />
        </view>
        <view class="messages__read-all-text-wrap">
          <text class="messages__read-all-text">{{ READ_ALL_TEXT }}</text>
        </view>
      </view>
    </view>

    <!-- 筛选行（design 42d2aeb5：padding 12/16 · chip h30 r10 · 间距 9） -->
    <view class="messages__filters">
      <view
        v-for="(filter, index) in FILTERS"
        :key="filter.key"
        class="chip"
        :class="[{ 'chip--active': filter.key === active }, index ? 'chip--gap' : '']"
        :data-testid="`filter-${filter.key}`"
        @tap="onFilterTap(filter.key)"
      >
        <text class="chip__text">{{ filter.label }}</text>
      </view>
    </view>

    <!-- 消息列表区（design 863dc36b：padding 12/16/0/16 · 卡 92 高 · 间距 12） -->
    <view class="messages__list">
      <view
        v-for="row in model.rows"
        :key="row.id"
        class="msg"
        data-testid="message-row"
        :data-target="row.target"
        @tap="onRowTap(row)"
      >
        <view class="msg__icon" :style="{ background: row.iconBg }">
          <!-- 图标占位（D5）：盒子 = 设计图层尺寸（remixicon fs20 声明 w22 · 字形行盒 = 字号×1.5 = 30），形状画在盒内 -->
          <view class="msg__glyph-box">
            <view class="msg__glyph" :style="{ background: row.iconColor }" aria-hidden="true" />
          </view>
        </view>
        <view class="msg__body">
          <view class="msg__content-wrap">
            <view class="msg__title-row">
              <text class="msg__title" :style="{ color: row.titleColor }">{{ row.title }}</text>
              <view v-if="row.unread" class="msg__dot-wrap">
                <view class="msg__dot" data-testid="unread-dot" aria-hidden="true" />
              </view>
            </view>
            <view class="msg__content-row">
              <text class="msg__content" :style="{ color: row.contentColor }">{{ row.content }}</text>
            </view>
            <view class="msg__time-row">
              <text class="msg__time" :style="{ color: row.timeColor }">{{ row.timeText }}</text>
            </view>
          </view>
        </view>
      </view>

      <view v-if="model.empty" class="messages__empty">
        <text class="messages__empty-text">暂无站内信</text>
      </view>
    </view>

    <!-- 底部 TabBar（design c02e59d8：padding 8/0/24 · 4 项各 104 · 图标 33 + 3 + 文字 16 = 84）
         序号 21 起抽为共享组件 src/components/app-tab-bar/AppTabBar.vue
         本帧（page-20-2）逐帧差异：高亮色 #007AFF + 高亮字重 400（该帧四行文本全为 SourceHanSans-Regular，
         而 page-21-2 帧的高亮项是 SemiBold 600） -->
    <AppTabBar active-color="#007AFF" :active-weight="400" />
  </view>
</template>

<script setup lang="ts">
/**
 * 序号 20【合同与通知】站内信列表（page-20-2 / /pages/messages/index）
 *
 * 设计真源：.calicat/raw/pages/page-20-2/design.tree.json
 *   （430 宽 · 设计总高 760 · 顶部导航 86 · 筛选行 54 · 5 卡 × 92 + 4 间隙 × 12 · TabBar 84）
 * 接口真源：18-API「Audit/Notification」Tag → GET /api/v1/notifications、POST /api/v1/notifications/{id}/read
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 18-API + 设计稿控件语义；分类见台账序号 20：
 *   「全部已读」= api（逐条 POST /notifications/{id}/read，18-API 无批量接口）
 *   筛选 chip = api（GET /notifications?unread=|category=，参数名与取值集合为推断 → missing-prd）
 *   消息卡 = api（标记已读）+ navigation（biz_type 映射落点，未知不跳转）
 *   TabBar = navigation（我的 = 本模块，不跳转）
 */
import { computed, onMounted, ref } from 'vue'
import AppTabBar from '@/components/app-tab-bar/AppTabBar.vue'
import { notificationApi } from '@/api/notification'
import {
  DEFAULT_FILTER,
  FILTERS,
  PAGE_TITLE,
  READ_ALL_TEXT,
  buildMessageQuery,
  buildMessagesModel,
  type MessageFilterKey,
  type MessageListRaw,
  type MessageRow
} from '@/utils/messages-model'

const PAGE_SIZE = 20

/** 失败提示文案：设计稿无 toast 稿 → 占位（已记台账序号 20） */
const LOAD_FAIL_TEXT = '数据加载失败，请稍后重试'
const ACTION_FAIL_TEXT = '操作失败，请稍后重试'

const raw = ref<MessageListRaw | null>(null)
const active = ref<MessageFilterKey>(DEFAULT_FILTER)
const model = computed(() => buildMessagesModel(raw.value, active.value))

async function load() {
  try {
    raw.value = (await notificationApi.list({ page: 1, pageSize: PAGE_SIZE, ...buildMessageQuery(active.value) })) ?? null
  } catch {
    raw.value = null
    uni.showToast({ title: LOAD_FAIL_TEXT, icon: 'none' })
  }
}

/** 筛选 chip：切换后按对应查询参数重新取数（点当前项不重复请求） */
async function onFilterTap(key: MessageFilterKey) {
  if (key === active.value) return
  active.value = key
  await load()
}

/**
 * 全部已读：18-API 只有 /notifications/{id}/read（无批量接口）→ 按当前列表逐条标记，成功后再拉一次列表。
 * 任一条失败即中止并提示（不假装成功，也不继续发剩余写请求）。
 */
async function markAllRead() {
  const unread = model.value.rows.filter((r) => r.unread)
  if (!unread.length) return
  try {
    for (const row of unread) await notificationApi.markRead(row.id)
    await load()
  } catch {
    uni.showToast({ title: ACTION_FAIL_TEXT, icon: 'none' })
  }
}

/** 消息卡：未读先标记已读（失败只提示、不阻断跳转），有落点则跳转 */
async function onRowTap(row: MessageRow) {
  if (row.unread && row.id) {
    try {
      await notificationApi.markRead(row.id)
      await load()
    } catch {
      uni.showToast({ title: ACTION_FAIL_TEXT, icon: 'none' })
    }
  }
  if (row.target) uni.navigateTo({ url: row.target })
}

/** TabBar 已抽为共享组件（src/components/app-tab-bar/AppTabBar.vue，本帧高亮 #007AFF） */

onMounted(load)
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.messages {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  /* 设计帧：列表区结束 660 + 16 间隙 + TabBar 84 = 760（TabBar fixed 后手动补回占位） */
  padding-bottom: 100px;
  box-sizing: border-box;
}

/* 顶部导航（design 49663acf） */
.messages__topbar {
  background: $color-bg-card;
  /* --status-bar-height 由 uni-app 提供（H5 = 0）：设计帧未含状态栏偏移，此处补平台安全区 */
  padding: calc(48px + var(--status-bar-height, 0px)) 16px 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.messages__title {
  font-size: $font-2xl;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 26px; /* design 行盒 26（导航内容高 26 → 导航 86） */
}

.messages__badge-wrap {
  padding-left: 8px;
  display: flex;
  align-items: center;
}

.messages__badge {
  height: 22px;
  border-radius: 11px;
  padding: 0 8px;
  background: $color-danger-weak;
  display: flex;
  align-items: center;
  box-sizing: border-box;
}

.messages__badge-text {
  font-size: $font-2xs;
  font-weight: 600;
  color: $color-danger-text;
  line-height: 13.2px; /* 设计 lineHeight 1.2 × 11（胶囊 h22 固定，行盒不影响布局） */
}

.messages__spacer {
  flex: 1;
}

.messages__read-all {
  display: flex;
  flex-direction: row;
  align-items: center;
}

/* 图标段落行盒 = 字号 × 1.5（16 → 24） */
.messages__read-all-icon {
  width: 18px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.messages__read-all-glyph {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: $color-primary;
}

.messages__read-all-text-wrap {
  padding-left: 4px;
  display: flex;
  align-items: center;
}

.messages__read-all-text {
  font-size: $font-xs;
  font-weight: 500;
  color: $color-primary;
  line-height: 14.4px; /* 设计 lineHeight 1.2 × 12（按钮行高由 24 的图标盒决定） */
}

/* 筛选行（design 42d2aeb5） */
.messages__filters {
  background: $color-bg-card;
  padding: 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.chip {
  height: 30px;
  border-radius: 10px;
  padding: 0 12px;
  background: $color-bg-subtle;
  display: flex;
  align-items: center;
  box-sizing: border-box;
}

.chip--gap {
  margin-left: 9px;
}

.chip--active {
  background: $color-primary;
}

.chip__text {
  font-size: $font-xs;
  font-weight: 500;
  color: $color-text-muted;
  line-height: 14.4px; /* 设计 lineHeight 1.2 × 12（chip h30 固定，行盒居中不影响布局） */
}

.chip--active .chip__text {
  color: $color-bg-card;
}

/* 消息列表区（design 863dc36b） */
.messages__list {
  padding: 12px 16px 0 16px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 卡 92 高 = 16 + 内容 60 + 16；描边在盒外（design stroke 1px #EEF2F7）→ ring 不占布局 */
.msg {
  background: $color-bg-card;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 0 0 1px $color-border-chip;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  box-sizing: border-box;
}

.msg + .msg {
  margin-top: 12px;
}

.msg__icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 图标字形盒 = 设计图层尺寸（fs20 remixicon 声明 w22 · 字形行盒 = 字号×1.5 = 30）；形状为 CSS 占位（D5）：
   实心圆（避免被误读成勾选框），墨迹按设计 17。盒子不参与布局（外层 38×38 居中），对齐设计声明值即可。 */
.msg__glyph-box {
  width: 22px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.msg__glyph {
  width: 17px;
  height: 17px;
  border-radius: 50%;
}

.msg__body {
  flex: 1;
  min-width: 0;
  padding-left: 12px;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

.msg__content-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.msg__title-row {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.msg__title {
  font-size: $font-sm;
  font-weight: 600;
  line-height: 18px;
}

.msg__dot-wrap {
  padding-left: 8px;
  display: flex;
  align-items: center;
}

.msg__dot {
  width: 9px;
  height: 8px;
  border-radius: 4px;
  background: $color-danger;
}

.msg__content-row {
  padding-top: 4px;
  display: flex;
  flex-direction: row;
}

.msg__content {
  font-size: $font-xs;
  line-height: 18px;
}

.msg__time-row {
  padding-top: 4px;
  display: flex;
  flex-direction: row;
}

.msg__time {
  font-size: $font-2xs;
  line-height: 16px;
}

.messages__empty {
  padding: 40px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.messages__empty-text {
  font-size: $font-xs;
  color: $color-text-placeholder;
}

/* 底部 TabBar 样式随共享组件（src/components/app-tab-bar/AppTabBar.vue）—— 页面不再各写一套 */
</style>
