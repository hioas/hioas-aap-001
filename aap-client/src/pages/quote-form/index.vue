<template>
  <!-- 序号 12-v1【报价管理】新增报价单-初始态（page-26）→ 共用视图（variant=initial） -->
  <QuoteFormView :variant="VARIANT_INITIAL" />
</template>

<script setup lang="ts">
/**
 * 序号 12-v1 · /pages/quote-form/index（page-26：初始态）
 * 页面本体在共用视图 src/components/quote-form/QuoteFormView.vue（12-v1/12-v2 两帧共用，
 * 帧级差异由 variantFlags 开关，不各写一套）；文案与缺口说明见 src/utils/quote-form-model.ts。
 */
import QuoteFormView from '@/components/quote-form/QuoteFormView.vue'
import { VARIANT_INITIAL } from '@/utils/quote-form-model'
</script>
