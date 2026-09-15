<template>
  <!-- 序号 12-v2【报价管理】新增报价单-APIKey 下拉展开（page-apikey）→ 共用视图（variant=expanded） -->
  <QuoteFormView :variant="VARIANT_EXPANDED" />
</template>

<script setup lang="ts">
/**
 * 序号 12-v2 · /pages/quote-form/apikey（page-apikey：凭证下拉展开态）
 * 与 12-v1 同页不同帧：共用 src/components/quote-form/QuoteFormView.vue，
 * 帧级差异（本帧无步骤卡 / 无空态提示卡 / 空态说明文案与包裹层不同 / 面板展开）由 variantFlags 控制。
 * 设计与缺口真源：.calicat/raw/pages/page-apikey/design.tree.json + src/utils/quote-form-model.ts 顶部注释。
 */
import QuoteFormView from '@/components/quote-form/QuoteFormView.vue'
import { VARIANT_EXPANDED } from '@/utils/quote-form-model'
</script>
