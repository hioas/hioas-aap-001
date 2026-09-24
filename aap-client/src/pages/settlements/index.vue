<template>
  <!--
    供应商端结算单（SET-01 列表 / SET-02 明细）
    设计稿：**无**（.calicat/prd/12-供应商端PRD.md 是 18 字节空壳，画布也没有结算/对账页）
    → 本页为工程新增页，不套设计稿像素约束，但沿用用量/工作台页的视觉语言。
    口径（与后端 SettlementService 完全一致，前端不重新推导）：
      净额 = 总额 − 平台服务费；状态 DRAFT/CONFIRMED/VOID；周期 = 自然月（UTC）。
  -->
  <view class="st">
    <view class="nav">
      <view class="nav__back" data-testid="st-back" @tap="onBack">
        <text class="nav__back-text">‹</text>
      </view>
      <text class="nav__title" data-testid="st-title">结算单</text>
      <view class="nav__spacer" />
    </view>

    <view v-if="error" class="err" data-testid="st-error">{{ error }}</view>
    <view v-else-if="loading" class="hint" data-testid="st-loading">加载中…</view>
    <view v-else-if="!rows.length" class="hint" data-testid="st-empty">
      暂无结算单。平台出账后，这里会按<b>自然月</b>显示用量金额、平台服务费与净额。
    </view>

    <view
      v-for="row in rows"
      :key="row.id"
      class="card"
      :data-testid="`st-row-${row.id}`"
      @tap="openDetail(row)"
    >
      <view class="card__head">
        <text class="card__no" data-testid="st-no">{{ row.no }}</text>
        <text class="badge" :class="`badge--${row.tone}`" data-testid="st-status">{{ row.statusLabel }}</text>
      </view>
      <text class="card__period" data-testid="st-period">{{ row.period }}</text>
      <view class="grid">
        <view class="grid__cell">
          <text class="grid__label">用量金额</text>
          <text class="grid__value" data-testid="st-total">{{ row.total }}</text>
        </view>
        <view class="grid__cell">
          <text class="grid__label">平台服务费</text>
          <text class="grid__value" data-testid="st-fee">{{ row.fee }}</text>
        </view>
        <view class="grid__cell">
          <text class="grid__label">净额</text>
          <text class="grid__value" data-testid="st-net">{{ row.net }}</text>
        </view>
      </view>
    </view>

    <view v-if="detailOpen" class="sheet">
      <view class="sheet__mask" @tap="closeDetail" />
      <view class="sheet__body" data-testid="st-detail">
        <text class="sheet__title" data-testid="st-detail-title">{{ detail?.no || '结算单' }}</text>
        <text class="sheet__sub">
          明细（渠道 × 模型） · 已关联打款 {{ detail?.payments ?? 0 }} 笔
        </text>
        <view v-if="detailError" class="err" data-testid="st-detail-error">{{ detailError }}</view>
        <view v-else-if="detailLoading" class="hint">加载明细…</view>
        <view v-else-if="lines.length" class="lines">
          <view v-for="l in lines" :key="l.key" class="line" data-testid="st-line">
            <view class="line__left">
              <text class="line__model">{{ l.model }}</text>
              <text class="line__sub">渠道 {{ l.channel }} · {{ l.tokens }} tokens</text>
            </view>
            <text class="line__amount">{{ l.amount }}</text>
          </view>
        </view>
        <view v-else class="hint" data-testid="st-detail-empty">该单据暂无明细行</view>
        <view class="sheet__foot">
          <text class="sheet__note">
            资金走线下对公，平台不做资金流转（PRD 10 R-42）；结算单是<b>对账凭证</b>。
          </text>
          <view class="btn" data-testid="st-detail-close" @tap="closeDetail">关闭</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { settlementApi } from '@/api/payment';
import {
  toSettlementDetail,
  toSettlementLines,
  toSettlementList,
  type SettlementLineView,
  type SettlementListView
} from '@/utils/settlement-model';

const rows = ref<SettlementListView[]>([]);
const loading = ref(true);
const error = ref('');

const detailOpen = ref(false);
const detailLoading = ref(false);
const detailError = ref('');
const detail = ref<(SettlementListView & { payments: number }) | null>(null);
const lines = ref<SettlementLineView[]>([]);

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const raw = await settlementApi.list({ page: 1, pageSize: 20 });
    rows.value = toSettlementList(raw);
  } catch (e) {
    // 不把失败渲染成空列表：空列表会被误读成「没有结算单」
    error.value = (e as Error).message || '结算单加载失败';
  } finally {
    loading.value = false;
  }
}

async function openDetail(row: SettlementListView) {
  detailOpen.value = true;
  detailLoading.value = true;
  detailError.value = '';
  detail.value = null;
  lines.value = [];
  try {
    const raw = await settlementApi.detail(row.id);
    detail.value = toSettlementDetail(raw);
    lines.value = toSettlementLines(raw);
  } catch (e) {
    detailError.value = (e as Error).message || '明细加载失败';
  } finally {
    detailLoading.value = false;
  }
}

function closeDetail() {
  detailOpen.value = false;
}

function onBack() {
  uni.navigateBack();
}

onMounted(load);
</script>

<style lang="scss" scoped>
.st {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  box-sizing: border-box;
  background: #f8fafc;
  padding: 0 12px 32px;
}

.nav {
  display: flex;
  align-items: center;
  height: 56px;
}
.nav__back {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nav__back-text {
  font-size: 24px;
  color: #0f172a;
}
.nav__title {
  flex: 1;
  text-align: center;
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
}
.nav__spacer {
  width: 32px;
}

.hint {
  padding: 20px 12px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}
.err {
  margin: 12px 0;
  padding: 12px;
  border-radius: 10px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
}

.card {
  margin-bottom: 12px;
  padding: 16px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}
.card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card__no {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}
.card__period {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
}
.badge--warn {
  background: #fff7ed;
  color: #c2410c;
}
.badge--success {
  background: #ecfdf5;
  color: #047857;
}
.badge--muted {
  background: #f1f5f9;
  color: #64748b;
}

.grid {
  display: flex;
  margin-top: 12px;
}
.grid__cell {
  flex: 1;
}
.grid__label {
  display: block;
  font-size: 11px;
  color: #94a3b8;
}
.grid__value {
  display: block;
  margin-top: 4px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.sheet {
  position: fixed;
  inset: 0;
  z-index: 20;
}
.sheet__mask {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
}
.sheet__body {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-height: 76vh;
  padding: 16px;
  border-radius: 18px 18px 0 0;
  background: #ffffff;
  overflow-y: auto;
}
.sheet__title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}
.sheet__sub {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}
.lines {
  margin-top: 12px;
}
.line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f1f5f9;
}
.line__model {
  font-size: 13px;
  color: #0f172a;
}
.line__sub {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
}
.line__amount {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.sheet__foot {
  margin-top: 16px;
}
.sheet__note {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.6;
}
.btn {
  margin-top: 12px;
  height: 44px;
  line-height: 44px;
  text-align: center;
  border-radius: 12px;
  background: #0f172a;
  color: #ffffff;
  font-size: 15px;
}
</style>
