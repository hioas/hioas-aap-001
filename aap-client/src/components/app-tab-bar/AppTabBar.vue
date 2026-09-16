<template>
  <!--
    底部 TabBar（共享组件，序号 21 抽出）
    设计真源：page-21-2 `底部TabBar`(9385b03b) / page-20-2 `TabBar`(c02e59d8) 同一版式
      padding 8/0/24 · 4 项各 104 · 图标 33 块 + 3 + 文字 16 = 84 高
    逐帧差异：高亮色 → activeColor prop（21-2 = #2563EB，20-2 = #007AFF）
  -->
  <view class="tabbar">
    <view
      v-for="tab in TAB_ITEMS"
      :key="tab.label"
      class="tabbar__item"
      :data-testid="`tab-${tab.label}`"
      @tap="onTabTap(tab)"
    >
      <view class="tabbar__icon">
        <view
          class="tabbar__glyph"
          :style="{ background: glyphColor(tab.label) }"
          aria-hidden="true"
        />
      </view>
      <view class="tabbar__gap" />
      <text
        class="tabbar__label"
        :class="{ 'tabbar__label--active': isActiveTab(tab.label, active) }"
        :style="{ color: labelColor(tab.label), fontWeight: labelWeight(tab.label) }"
      >
        {{ tab.label }}
      </text>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 共享底部 TabBar。页面只需 <AppTabBar :active="..." :active-color="..." :active-weight="..." />
 * 交互：navigation —— 当前模块不跳转；未实现的目标路由由 uni 侧降级（台账已记）。
 * 图标：CSS 形状占位（设计用 remixicon 字形，仓库无图标资源；R-26 禁 emoji）→ 记台账。
 *
 * 逐帧差异（两帧同一版式，仅高亮态两处不同 → 都做成 prop，不各写一套）：
 *  · activeColor：page-21-2 = #2563EB · page-20-2 = #007AFF
 *  · activeWeight：page-21-2「我的」= SourceHanSans-SemiBold(600) · page-20-2 四行全为 Regular(400)
 *    （非高亮项两帧一致 = Regular 400）
 */
import {
  ACTIVE_TAB,
  TAB_ACTIVE_COLOR,
  TAB_ITEMS,
  isActiveTab,
  resolveTabTarget,
  tabGlyphColor,
  tabLabelColor,
  type TabItem
} from '@/utils/app-tab-bar-model'

const props = withDefaults(
  defineProps<{
    active?: string
    activeColor?: string
    activeWeight?: number
  }>(),
  { active: ACTIVE_TAB, activeColor: TAB_ACTIVE_COLOR, activeWeight: 600 }
)

const glyphColor = (label: string) => tabGlyphColor(label, props.active, props.activeColor)
const labelColor = (label: string) => tabLabelColor(label, props.active, props.activeColor)
/** 高亮项字重逐帧（见文件头）；非高亮项两帧一致 400 */
const labelWeight = (label: string) => (isActiveTab(label, props.active) ? props.activeWeight : 400)

function onTabTap(tab: TabItem) {
  const target = resolveTabTarget(tab.url, tab.label, props.active)
  if (!target) return
  uni.navigateTo({ url: target })
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  height: 84px;
  box-sizing: border-box;
  background: $color-bg-card;
  padding: 8px 0 24px 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.tabbar__item {
  width: 104px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tabbar__icon {
  height: 33px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tabbar__glyph {
  width: 18px;
  height: 18px;
  border-radius: 50%;
}

.tabbar__gap {
  height: 3px;
}

.tabbar__label {
  font-size: $font-2xs;
  line-height: 16px;
}

/* 高亮项字重逐帧 → 由 activeWeight prop 以内联样式给出（page-21-2 = 600 / page-20-2 = 400），
   这里不再写死 font-weight，避免覆盖内联值造成"看类名猜不出实际字重" */
.tabbar__label--active {
  /* 仅作态标记（供页面/探针断言当前高亮项），视觉差异全部走内联样式 */
}
</style>
