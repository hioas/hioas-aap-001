<template>
  <div class="cp">
    <el-alert type="info" :closable="false" show-icon class="cp__note" data-testid="compile-note">
      <template #title>编译确认台（ADM-Q01 + ADM-CP01…04，2026-09-23 接线）</template>
      报价单审核通过后可发起编译 → 生成逐模型 billingexpr → 跑 V1–V6 模拟验证 → **人工确认**才解除写入封锁
      （<code>publish_blocked=false</code>），之后才能进入 new-api 同步写入。
      编译/验证/确认**仅技术运营与超管**可用（后端二次校验 403 <code>E-1901</code>）。
    </el-alert>

    <!-- 发起编译（ADM-Q01）：报价单须为审核通过；未通过 → E-1601 -->
    <div class="aap-card cp__bar">
      <span class="cp__label">发起编译</span>
      <el-input
        v-model="compileQuoteId"
        placeholder="报价单 ID（从「报价审核」页复制审核通过的报价单 ID）"
        style="width: 420px"
        clearable
        data-testid="compile-quote-id"
      />
      <el-button type="primary" :loading="compiling" :disabled="!canConfirm" data-testid="btn-compile" @click="onCompile">
        发起编译
      </el-button>
      <span class="cp__hint">{{ canConfirm ? '未审核通过的报价单会返回 E-1601' : '当前角色无权发起编译' }}</span>
    </div>

    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">编译记录</span>
        <span class="aap-card__hint" data-testid="compile-count">共 {{ total }} 条</span>
        <span class="cp__spacer" />
        <el-select v-model="status" placeholder="全部状态" clearable style="width: 170px" data-testid="compile-status" @change="load">
          <el-option v-for="(v, k) in COMPILATION_STATUS" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button size="small" :loading="loading" data-testid="btn-refresh" @click="load">刷新</el-button>
      </div>
      <div class="aap-card__body">
        <el-table v-loading="loading" :data="rows" size="small" data-testid="compile-table" empty-text="暂无编译记录">
          <el-table-column label="编译 ID" min-width="170">
            <template #default="{ row }"><span class="cp__mono">{{ row.compilation_id || row.id }}</span></template>
          </el-table-column>
          <el-table-column label="报价单" min-width="170">
            <template #default="{ row }">
              <span class="cp__mono">{{ row.quote_id || '—' }}</span>
              <span class="cp__hint">v{{ row.quote_version ?? '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="170">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${statusMeta(row.status)?.tone || 'muted'}`">
                {{ statusMeta(row.status)?.label || row.status || '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="写入" width="120">
            <template #default="{ row }">
              <span v-if="row.publish_blocked === false" class="aap-badge aap-badge--success">已解锁</span>
              <span v-else class="aap-badge aap-badge--warn">封锁中</span>
            </template>
          </el-table-column>
          <el-table-column label="验证" width="120">
            <template #default="{ row }">
              <span v-if="row.verify_report" :data-testid="`verify-sum-${row.id}`">
                {{ row.verify_report.case_passed ?? 0 }}/{{ row.verify_report.case_total ?? 0 }}
              </span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ row.created_at || '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="230">
            <template #default="{ row }">
              <el-button size="small" type="primary" link :data-testid="`act-detail-${row.id}`" @click="openDetail(row)">详情</el-button>
              <el-button size="small" type="warning" link :disabled="!canConfirm" :data-testid="`act-verify-${row.id}`" @click="onVerify(row)">模拟验证</el-button>
              <el-button
                size="small" type="success" link
                :disabled="!canConfirm || row.status === 'CONFIRMED'"
                :data-testid="`act-confirm-${row.id}`"
                @click="onConfirm(row)"
              >人工确认</el-button>
            </template>
          </el-table-column>
        </el-table>
        <p v-if="error" class="cp__err" data-testid="compile-error">{{ error }}</p>
      </div>
    </div>

    <!-- 详情：表达式三栏对照 + 模拟验证报告 -->
    <el-drawer v-model="detailOpen" title="编译详情" size="62%" data-testid="compile-drawer">
      <template v-if="current">
        <el-descriptions :column="3" border size="small" class="cp__desc">
          <el-descriptions-item label="编译 ID">{{ current.compilation_id || current.id }}</el-descriptions-item>
          <el-descriptions-item label="报价单">{{ current.quote_id || '—' }} · v{{ current.quote_version ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <span class="aap-badge" :class="`aap-badge--${statusMeta(current.status)?.tone || 'muted'}`">
              {{ statusMeta(current.status)?.label || current.status }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="source_hash">{{ current.source_hash || '—' }}</el-descriptions-item>
          <el-descriptions-item label="编译器版本">{{ current.compiler_version || '—' }}</el-descriptions-item>
          <el-descriptions-item label="确认时间">{{ current.confirmed_at || '未确认' }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="cp__h4">逐模型表达式（billingexpr）</h4>
        <el-table :data="current.compiled || []" size="small" data-testid="expr-table" empty-text="无表达式">
          <el-table-column label="模型" min-width="150">
            <template #default="{ row }">{{ row.model_name || '—' }}</template>
          </el-table-column>
          <el-table-column label="表达式" min-width="260">
            <template #default="{ row }"><span class="cp__mono cp__expr">{{ row.expr || '—' }}</span></template>
          </el-table-column>
          <el-table-column label="展开式" min-width="220">
            <template #default="{ row }"><span class="cp__mono cp__hint">{{ row.inline_expanded || '—' }}</span></template>
          </el-table-column>
          <el-table-column label="分层" width="120">
            <template #default="{ row }">{{ (row.tier_labels || []).join(' / ') || '—' }}</template>
          </el-table-column>
          <el-table-column label="命中规则" width="140">
            <template #default="{ row }">{{ (row.rule_hits || []).join(', ') || '—' }}</template>
          </el-table-column>
          <el-table-column label="已验证" width="90">
            <template #default="{ row }">{{ row.verified ? '是' : '否' }}</template>
          </el-table-column>
        </el-table>

        <h4 class="cp__h4">模拟验证报告（V1–V6）</h4>
        <template v-if="current.verify_report">
          <p class="cp__sum" data-testid="verify-summary">
            结果 <b>{{ current.verify_report.status }}</b> ·
            通过 {{ current.verify_report.case_passed ?? 0 }}/{{ current.verify_report.case_total ?? 0 }}
            <span v-if="current.verify_report.failed_field"> · 失败字段 <code>{{ current.verify_report.failed_field }}</code></span>
          </p>
          <el-table :data="current.verify_report.cases || []" size="small" data-testid="verify-table" empty-text="无用例">
            <el-table-column label="用例" width="130">
              <template #default="{ row }">
                {{ row.case_code }} <span class="cp__hint">{{ VERIFY_CASE_NAMES[row.case_code] || row.case_name || '' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="输入" min-width="220">
              <template #default="{ row }"><span class="cp__mono cp__hint">{{ compact(row.input) }}</span></template>
            </el-table-column>
            <el-table-column label="期望" width="110">
              <template #default="{ row }">{{ row.expected ?? '—' }}</template>
            </el-table-column>
            <el-table-column label="实际" width="110">
              <template #default="{ row }">{{ row.actual ?? '—' }}</template>
            </el-table-column>
            <el-table-column label="通过" width="80">
              <template #default="{ row }">
                <span :class="row.passed ? 'cp__ok' : 'cp__bad'">{{ row.passed ? '✓' : '✗' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="差异说明" min-width="160">
              <template #default="{ row }">{{ row.diff_note || '—' }}</template>
            </el-table-column>
          </el-table>
        </template>
        <p v-else class="cp__hint">尚未运行模拟验证 —— 点下方「模拟验证」。</p>

        <template v-if="current.previous_expr">
          <h4 class="cp__h4">上一版表达式（变更留档）</h4>
          <pre class="cp__pre" data-testid="prev-expr">{{ JSON.stringify(current.previous_expr, null, 2) }}</pre>
        </template>

        <div class="cp__actions">
          <el-button :disabled="!canConfirm" :loading="busy" data-testid="drawer-verify" @click="onVerify(current)">模拟验证</el-button>
          <el-button
            type="primary" :disabled="!canConfirm || current.status === 'CONFIRMED'" :loading="busy"
            data-testid="drawer-confirm" @click="onConfirm(current)"
          >人工确认（解除写入封锁）</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  compileApi, COMPILATION_STATUS, VERIFY_CASE_NAMES, type CompilationResult
} from '@/api/admin/compile';
import { can, type AdminRole } from '@/config/nav';
import { useSession } from '@/composables/useSession';

const { role } = useSession();
/** 编译/验证/确认 仅技术运营与超管（PRD 13 §1；后端 hasAnyRole 二次校验） */
const canConfirm = computed(() => can(role.value as AdminRole, 'compile.confirm'));

const rows = ref<CompilationResult[]>([]);
const total = ref(0);
const status = ref('');
const loading = ref(false);
const error = ref('');
const compileQuoteId = ref('');
const compiling = ref(false);
const detailOpen = ref(false);
const current = ref<CompilationResult | null>(null);
const busy = ref(false);

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const res = await compileApi.list({ page: 1, pageSize: 50, status: status.value || undefined });
    rows.value = res?.items ?? [];
    total.value = res?.total ?? rows.value.length;
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}

async function onCompile() {
  const id = compileQuoteId.value.trim();
  if (!/^\d+$/.test(id)) return ElMessage.warning('请填报价单 ID（雪花 ID 数字串）');
  compiling.value = true;
  try {
    const res = await compileApi.compile(id);
    ElMessage.success(`已编译：${COMPILATION_STATUS[res.status ?? '']?.label || res.status}`);
    await load();
    await openDetail(res);
  } catch (e) {
    ElMessage.error((e as Error).message); // 未审核通过 → E-1601
  } finally {
    compiling.value = false;
  }
}

async function openDetail(row: CompilationResult) {
  try {
    current.value = await compileApi.detail(String(row.id));
    detailOpen.value = true;
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

async function onVerify(row: CompilationResult) {
  busy.value = true;
  try {
    const report = await compileApi.verify(String(row.id));
    ElMessage.success(`验证完成：${report?.status}（通过 ${report?.case_passed ?? 0}/${report?.case_total ?? 0}）`);
    await load();
    if (current.value && String(current.value.id) === String(row.id)) {
      current.value = await compileApi.detail(String(row.id));
    }
  } catch (e) {
    // 验证不过 → E-1405（报告仍保留，故刷新详情让运营看到哪条用例红了）
    ElMessage.error((e as Error).message);
    if (current.value && String(current.value.id) === String(row.id)) {
      current.value = await compileApi.detail(String(row.id)).catch(() => current.value);
    }
  } finally {
    busy.value = false;
  }
}

async function onConfirm(row: CompilationResult) {
  try {
    await ElMessageBox.confirm(
      '人工确认后 publish_blocked=false，该报价单的表达式**可进入同步写入**。确认核对过表达式与验证报告？',
      '人工确认（ADM-CP04）',
      { type: 'warning' }
    );
  } catch {
    return;
  }
  busy.value = true;
  try {
    const res = await compileApi.confirm(String(row.id));
    ElMessage.success(`已确认：${COMPILATION_STATUS[res.status ?? '']?.label || res.status}`);
    await load();
    if (current.value && String(current.value.id) === String(row.id)) {
      current.value = await compileApi.detail(String(row.id));
    }
  } catch (e) {
    ElMessage.error((e as Error).message); // 未验证 → E-1407
  } finally {
    busy.value = false;
  }
}

/** 状态 → 徽章元数据（row.status 可空，直接下标会被 TS 拦为 null index） */
const statusMeta = (s: string | null | undefined) => (s ? COMPILATION_STATUS[s] : undefined);

/** 用例输入是任意 JSON：压缩成一行便于表格展示 */
function compact(v: unknown): string {
  if (v == null) return '—';
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

// 角色是异步回填的（AdminLayout 取 /auth/me）：canConfirm 变 true 时才拉列表。
// 不做一次性判断（否则刷新后按钮被误锁）；运营商务调用本页接口后端也会 403，故不预取。
watch(canConfirm, (ok) => { if (ok) load(); }, { immediate: true });
</script>

<style scoped>
.cp__note { margin-bottom: 12px; }
.cp__bar { display: flex; align-items: center; gap: 10px; padding: 12px 16px; margin-bottom: 12px; }
.cp__label { font-weight: 600; }
.cp__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }
.cp__spacer { flex: 1; }
.cp__err { color: var(--c-danger, #d03050); font-size: var(--fs-sm); margin: 8px 0 0; }
.cp__mono { font-family: var(--font-mono, ui-monospace, monospace); font-size: var(--fs-sm); }
.cp__expr { word-break: break-all; }
.cp__desc { margin-bottom: 16px; }
.cp__h4 { margin: 18px 0 8px; font-size: var(--fs-base); font-weight: 600; }
.cp__sum { font-size: var(--fs-sm); margin: 0 0 8px; }
.cp__ok { color: #17a673; font-weight: 600; }
.cp__bad { color: var(--c-danger, #d03050); font-weight: 600; }
.cp__pre {
  background: var(--c-surface-alt, #f5f6f8); padding: 10px; border-radius: var(--r-sm, 4px);
  font-size: var(--fs-sm); max-height: 220px; overflow: auto;
}
.cp__actions { margin-top: 18px; display: flex; gap: 10px; }
</style>
