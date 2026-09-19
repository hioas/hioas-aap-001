<template>
  <div class="rev">
    <!-- ⚠️ 设计/PRD 冲突（calicat skill 铁律 #7：记录 + 请求裁定，不静默选一边）
         设计稿 page-6-pc 有「批量通过」；PRD 13 §5 明确「**不提供批量通过**」
         （通过触发合同+编译链式副作用，必须逐单确认）。
         此处以 PRD 为准**不渲染**该按钮，并显式提示等裁定。 -->
    <el-alert type="info" :closable="false" show-icon class="rev__conflict" data-testid="design-prd-conflict">
      <template #title>设计/PRD 冲突待裁定：设计稿有「批量通过」，PRD 13 §5 明确「不提供批量通过」</template>
      已按 PRD 处理（不渲染批量通过）。来源：Calicat page-6-pc / <code>.calicat/prd/13-管理端PRD.md</code> §5。
    </el-alert>

    <div class="rev__body">
      <aside class="aap-card rev__pool">
        <div class="rev__pool-head">
          <span class="aap-card__title">待审核列表</span>
          <span class="aap-badge aap-badge--warn">{{ pool.length }} 单</span>
          <span class="rev__spacer" />
          <el-button size="small" :loading="loading" data-testid="refresh-pool" @click="loadPool">刷新</el-button>
        </div>
        <el-scrollbar height="calc(100vh - 260px)">
          <div v-if="!pool.length && !loading" class="rev__empty" data-testid="pool-empty">暂无待审报价单</div>
          <div
            v-for="t in pool"
            :key="t.id"
            class="pool-item"
            :class="{ 'pool-item--active': current?.id === t.id }"
            :data-testid="`pool-item-${t.id}`"
            @click="select(t)"
          >
            <div class="pool-item__row1">
              <span class="pool-item__name">{{ t.quote_no || t.quote_id }}</span>
              <span class="aap-badge" :class="`aap-badge--${tone(t.status)}`">{{ statusLabel(t.status) }}</span>
            </div>
            <div class="pool-item__row2">{{ t.provider_name || '—' }}</div>
            <div class="pool-item__row3">提交于 {{ fmt(t.created_at) }}</div>
          </div>
        </el-scrollbar>
      </aside>

      <section class="rev__main">
        <div v-if="!current" class="aap-card rev__placeholder" data-testid="no-selection">从左侧选择一单开始审核</div>

        <template v-else>
          <div class="aap-card">
            <div class="aap-card__head">
              <span class="aap-card__title">{{ current.quote_no || current.quote_id }}</span>
              <span class="aap-badge aap-badge--muted">供应商提交 · 只读</span>
              <span class="rev__spacer" />
              <span class="rev__meta">{{ current.provider_name || '—' }}</span>
            </div>
            <div class="aap-card__body">
              <el-descriptions :column="3" border size="small" data-testid="evidence-summary">
                <el-descriptions-item label="报价单号">{{ current.quote_no || '—' }}</el-descriptions-item>
                <el-descriptions-item label="供应商">{{ current.provider_name || '—' }}</el-descriptions-item>
                <el-descriptions-item label="当前状态">
                  <span class="aap-badge" :class="`aap-badge--${tone(current.status)}`">{{ statusLabel(current.status) }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="提交时间">{{ fmt(current.created_at) }}</el-descriptions-item>
                <el-descriptions-item label="领取人">{{ current.claimed_by || '未领取' }}</el-descriptions-item>
                <el-descriptions-item label="技术指标快照">{{ current.tech_metrics_snapshot ? '有' : '未提供' }}</el-descriptions-item>
              </el-descriptions>

              <template v-if="current.tech_metrics_snapshot">
                <div class="rev__sub-title">技术指标快照</div>
                <pre class="rev__code">{{ pretty(current.tech_metrics_snapshot) }}</pre>
              </template>

              <div class="rev__sub-title">逐模型价格明细</div>
              <el-table :data="items" size="small" data-testid="price-table" empty-text="该报价单暂无明细（或接口未返回）">
                <el-table-column prop="model_name" label="模型" min-width="160" />
                <el-table-column prop="input_price" label="输入价" width="100" />
                <el-table-column prop="output_price" label="输出价" width="100" />
                <el-table-column prop="cache_read_price" label="缓存读" width="100" />
                <el-table-column prop="billing_mode" label="计价方式" width="120" />
                <el-table-column label="与市场均价偏差" min-width="170">
                  <template #default><span class="rev__todo">未采集（后端无市场均价接口）</span></template>
                </el-table-column>
              </el-table>
              <p class="rev__note">
                设计稿的「市场均价 / 偏差%」后端无对应字段或接口 → 已登记 missing-api，此处显式标注未采集，
                不填假数字（PRD 13 §0 诚实边界）。
              </p>
            </div>
          </div>

          <div class="aap-card">
            <div class="aap-card__head"><span class="aap-card__title">审核决策</span></div>
            <div class="aap-card__body">
              <el-form label-position="top">
                <el-form-item label="审核意见">
                  <el-input v-model="comment" type="textarea" :rows="3" maxlength="500" show-word-limit
                    placeholder="请输入审核意见（驳回时必填）…" data-testid="comment" />
                </el-form-item>
                <el-form-item label="驳回原因（驳回时必填）">
                  <el-select v-model="reasonCode" placeholder="请选择驳回原因" data-testid="reason-code" style="width: 260px">
                    <el-option v-for="r in REJECT_REASON_CODES" :key="r.code" :label="r.label" :value="r.code" />
                  </el-select>
                </el-form-item>
              </el-form>

              <el-alert v-if="error" type="error" :closable="false" show-icon class="rev__msg" data-testid="action-error">{{ error }}</el-alert>
              <el-alert v-if="okMsg" type="success" :closable="false" show-icon class="rev__msg" data-testid="action-ok">{{ okMsg }}</el-alert>

              <div class="rev__actions">
                <el-button :disabled="!canWrite" :loading="acting" data-testid="btn-claim" @click="onClaim">领取</el-button>
                <el-button type="primary" :disabled="!canWrite" :loading="acting" data-testid="btn-approve" @click="onApprove">通过并下发</el-button>
                <el-button type="danger" plain :disabled="!canWrite" :loading="acting" data-testid="btn-reject" @click="onReject">驳回</el-button>
              </div>
              <p v-if="!canWrite" class="rev__note" data-testid="rbac-note">
                当前角色（技术运营）仅可做技术指标复核；通过/驳回/领取需运营商务或超管（PRD 13 §1）。
                后端对这三个接口另有 <code>hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')</code> 二次校验。
              </p>
              <p v-else class="rev__note">通过将**自动生成合同**（ADM-R03）—— PRD 13 §5 要求逐单确认，故不提供批量通过。</p>
            </div>
          </div>

          <div class="aap-card">
            <div class="aap-card__head"><span class="aap-card__title">审核记录</span></div>
            <div class="aap-card__body">
              <el-timeline v-if="records.length" data-testid="timeline">
                <el-timeline-item v-for="r in records" :key="r.id" :timestamp="fmt(r.created_at)" placement="top">
                  <b>{{ r.action }}</b>
                  <span v-if="r.before_status || r.after_status"> · {{ r.before_status }} → {{ r.after_status }}</span>
                  <span v-if="r.operator_name"> · {{ r.operator_name }}</span>
                  <div v-if="r.comment" class="rev__tc">{{ r.comment }}</div>
                </el-timeline-item>
              </el-timeline>
              <p v-else class="rev__note" data-testid="timeline-empty">暂无审核记录</p>
            </div>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { request, type PageResult } from '@/api/http';
import {
  reviewApi, REVIEW_STATUS, REJECT_REASON_CODES,
  type ReviewRecord, type ReviewTask, type RejectReasonCode
} from '@/api/admin/reviews';
import { useSession } from '@/composables/useSession';
import { can, type AdminRole } from '@/config/nav';

const { role } = useSession();
/** 前端只做渲染过滤；后端对 claim/approve/reject 另有角色校验（不是安全边界） */
const canWrite = computed(() => can(role.value as AdminRole, 'quote.approve'));

const pool = ref<ReviewTask[]>([]);
const current = ref<ReviewTask | null>(null);
const items = ref<Record<string, unknown>[]>([]);
const records = ref<ReviewRecord[]>([]);
const comment = ref('');
const reasonCode = ref<RejectReasonCode | ''>('');
const loading = ref(false);
const acting = ref(false);
const error = ref('');
const okMsg = ref('');

const statusLabel = (s: string) => REVIEW_STATUS[s]?.label ?? s;
const tone = (s: string) => REVIEW_STATUS[s]?.tone ?? 'muted';
const fmt = (s: string | null) => (s ? String(s).replace('T', ' ').slice(0, 16) : '—');
const pretty = (v: unknown) => {
  try { return JSON.stringify(v, null, 2).slice(0, 2000); } catch { return String(v); }
};

async function loadPool() {
  loading.value = true;
  error.value = '';
  try {
    // 待审池 = PENDING + CLAIMED（后端 REVIEWABLE 两态）
    const [p, c] = await Promise.all([
      reviewApi.list('PENDING', 1, 50).catch(() => ({ total: 0, items: [] }) as PageResult<ReviewTask>),
      reviewApi.list('CLAIMED', 1, 50).catch(() => ({ total: 0, items: [] }) as PageResult<ReviewTask>)
    ]);
    pool.value = [...p.items, ...c.items];
    if (!pool.value.length) current.value = null;
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}

async function select(t: ReviewTask) {
  current.value = t;
  comment.value = t.review_comment ?? '';
  reasonCode.value = (t.reject_reason_code as RejectReasonCode) ?? '';
  error.value = '';
  okMsg.value = '';
  items.value = [];
  records.value = [];
  // 明细/时间线取不到不阻断审核，但保持为空并在表 empty-text 说明（不假装有数据）
  try {
    const r = await request<PageResult<Record<string, unknown>>>(`/quotes/${t.quote_id}/items`, { query: { page: 1, page_size: 100 } });
    items.value = r?.items ?? [];
  } catch { /* 保持空 */ }
  try {
    const rec = await reviewApi.records(t.quote_id);
    records.value = rec?.items ?? [];
  } catch { /* 保持空 */ }
}

async function onClaim() {
  if (!current.value) return;
  acting.value = true;
  error.value = '';
  try {
    const t = await reviewApi.claim(current.value.id);
    ElMessage.success('已领取');
    Object.assign(current.value, t);
    await loadPool();
  } catch (e) {
    error.value = (e as Error).message; // E-1601 = 并发下已被他人领取
  } finally {
    acting.value = false;
  }
}

async function onApprove() {
  if (!current.value) return;
  const id = current.value.id;
  try {
    await ElMessageBox.confirm('通过后将自动生成合同（ADM-R03），确认继续？', '确认通过', { type: 'warning' });
  } catch {
    return;
  }
  acting.value = true;
  error.value = '';
  try {
    const t = await reviewApi.approve(id, comment.value);
    okMsg.value = `已通过：${t.quote_no ?? t.quote_id}（status=${t.status}）`;
    ElMessage.success('审核通过');
    await loadPool();
    await select({ ...(current.value as ReviewTask), ...t });
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    acting.value = false;
  }
}

async function onReject() {
  if (!current.value) return;
  if (!reasonCode.value) {
    error.value = '驳回原因必填（后端 reason_code 必须命中枚举，否则 E-1001）';
    return;
  }
  acting.value = true;
  error.value = '';
  try {
    const t = await reviewApi.reject(current.value.id, reasonCode.value, comment.value);
    okMsg.value = `已驳回：${t.quote_no ?? t.quote_id}（原因 ${reasonCode.value}）`;
    ElMessage.success('已驳回');
    await loadPool();
    await select({ ...(current.value as ReviewTask), ...t });
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    acting.value = false;
  }
}

onMounted(loadPool);
defineExpose({ loadPool, select });
</script>

<style scoped>
.rev { display: flex; flex-direction: column; gap: 14px; }
.rev__conflict { border-radius: var(--r-lg); }
.rev__body { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 14px; }
@media (max-width: 1280px) { .rev__body { grid-template-columns: 1fr; } }
.rev__pool { display: flex; flex-direction: column; overflow: hidden; }
.rev__pool-head { display: flex; align-items: center; gap: 8px; padding: 14px 16px; border-bottom: 1px solid var(--c-border); }
.rev__spacer { flex: 1; }
.rev__empty { padding: 28px 16px; text-align: center; color: var(--c-text-muted); font-size: var(--fs-base); }
.pool-item { padding: 12px 16px; border-bottom: 1px solid var(--c-border); cursor: pointer; }
.pool-item:hover { background: var(--c-surface-alt); }
.pool-item--active { background: var(--c-primary-soft); border-left: 3px solid var(--c-primary); }
.pool-item__row1 { display: flex; align-items: center; gap: 8px; }
.pool-item__name { font-size: var(--fs-md); font-weight: 500; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pool-item__row2 { font-size: var(--fs-sm); color: var(--c-text-body); margin-top: 6px; }
.pool-item__row3 { font-size: var(--fs-sm); color: var(--c-text-muted); margin-top: 3px; }
.rev__main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.rev__placeholder { padding: 60px; text-align: center; color: var(--c-text-muted); }
.rev__meta { font-size: var(--fs-base); color: var(--c-text-sub); }
.rev__sub-title { font-size: var(--fs-md); font-weight: 600; margin: 16px 0 8px; }
.rev__code { background: var(--c-surface-alt); border: 1px solid var(--c-border); border-radius: var(--r-md); padding: 10px 12px; font-size: var(--fs-sm); overflow-x: auto; margin: 0; }
.rev__note { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 10px 0 0; line-height: 1.6; }
.rev__todo { font-size: var(--fs-sm); color: var(--c-warn-strong); }
.rev__msg { margin-bottom: 12px; }
.rev__actions { display: flex; gap: 10px; }
.rev__tc { font-size: var(--fs-base); color: var(--c-text-sub); margin-top: 4px; }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
