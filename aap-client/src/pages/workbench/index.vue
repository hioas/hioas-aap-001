<template>
  <view class="placeholder">
    <text class="placeholder__title">工作台</text>
    <text class="placeholder__note">页面 2 待实现（Calicat page-2-b）· 当前为登录跳转落点占位</text>
  </view>
</template>

<script setup lang="ts">
// 占位页：仅用于保证登录成功后 navigateTo 的落点存在（小程序对不存在页面会静默失败）。
// 页面 2【工作台与我的】实现时整体替换。
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.placeholder {
  min-height: 100vh;
  background: $color-bg-page;
  padding: 80px $page-padding;
  display: flex;
  flex-direction: column;
  align-items: center;

  &__title {
    font-size: $font-2xl;
    color: $color-text-primary;
  }

  &__note {
    margin-top: $gap-md;
    font-size: $font-xs;
    color: $color-text-secondary;
    text-align: center;
  }
}
</style>
