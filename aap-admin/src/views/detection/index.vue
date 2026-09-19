<template>
  <div class="dc">
    <!-- ⚠️ 能力缺口（D-ADM-5）：管理端**没有检测任务列表接口**。
         设计稿 page-5-pc 的四个 KPI + 任务表格无法用真实数据渲染 —— 不填示意值、不用 0 冒充未知。 -->
    <el-alert type="warning" :closable="false" show-icon class="dc__gap" data-testid="detection-gap-banner">
      <template #title>任务监控暂无数据来源（D-ADM-5）：管理端没有检测任务列表接口</template>
      全仓 admin 侧与检测任务相关的端点只有 <code>POST /detection-jobs/{id}/release</code>（按 id 人工放行）；
      <code>DET-01…05</code> 全部限供应商本人（管理端调用得 403 <code>E-1901</code>）→
      设计稿的「运行中任务 / 排队等待 / 今日已完成 / 失败率」与任务表格**无法**用真实数据渲染。
      本页因此只渲染<b>真实可用的能力</b>（按任务 ID 人工放行 + 检测项配置），其余显式标注未知。
    </el-alert>

    <!-- KPI 4 张（设计稿：运行中任务 / 排队等待 / 今日已完成 / 失败率） -->
    <div class="kpi-row" data-testid="detection-kpi">
      <div class="aap-card kpi">
        <span class="kpi__label">运行中任务</span>
        <span class="kpi__value kpi__value--todo">—</span>
        <span class="kpi__note">无列表接口 → 未知（不是 0）</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">排队等待</span>
        <span class="kpi__value kpi__value--todo">—</span>
        <span class="kpi__note">无列表接口 → 未知（不是 0）</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">今日已完成</span>
        <span class="kpi__value kpi__value--todo">—</span>
        <span class="kpi__note">无列表接口 → 未知（不是 0）</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">失败率</span>
        <span class="kpi__value kpi__value--todo">—</span>
        <span class="kpi__note">无列表接口 → 未知（不是 0%）</span>
      </div>
    </div>

    <!-- 筛选卡：设计稿有，但没有列表接口 → 控件显式禁用（不给出点了没反应的假筛选） -->
    <div class="aap-card dc__bar">
      <el-input v-model="filters.keyword" placeholder="搜索任务 ID / 供应商" clearable style="width: 260px" disabled data-testid="task-search" />
      <el-select v-model="filters.status" placeholder="全部状态" style="width: 150px" disabled data-testid="task-status">
        <el-option v-for="(v, k) in JOB_STATUS" :key="k" :label="v.label" :value="k" />
      </el-select>
      <el-select v-model="filters.probe" placeholder="全部检测项" style="width: 150px" disabled data-testid="task-probe">
        <el-option v-for="(name, code) in PROBE_NAMES" :key="code" :label="`${code} ${name}`" :value="code" />
      </el-select>
      <span class="dc__spacer" />
      <el-switch v-model="autoRefresh" disabled data-testid="task-auto-refresh" />
      <span class="dc__hint">自动刷新</span>
      <el-button type="primary" disabled data-testid="btn-new-task">新建检测任务</el-button>
      <span class="dc__hint">（以上筛选/新建均依赖任务列表接口，DET-01 亦仅供应商本人可用）</span>
    </div>

    <!-- 任务表格：设计稿列全在，但**没有数据来源** → 可执行的空态 -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">任务监控</span>
        <span class="aap-card__hint">任务 ID / 供应商·线路 / 进度 / 状态 / 耗时 / 操作</span>
      </div>
      <div class="aap-card__body">
        <el-table :data="[]" size="small" data-testid="detection-table" empty-text="无数据来源（后端无管理端任务列表接口）">
          <el-table-column label="任务 ID" min-width="150" />
          <el-table-column label="供应商 / 线路" min-width="180" />
          <el-table-column label="进度" min-width="150" />
          <el-table-column label="状态" width="110" />
          <el-table-column label="耗时" width="110" />
          <el-table-column label="操作" width="180" />
        </el-table>
        <div class="dc__empty" data-testid="detection-empty">
          <p><b>为什么是空的：</b>后端没有「管理端检测任务列表」端点（见上）。</p>
          <p>要让它有数据，需要先满足其一：</p>
          <ol>
            <li>按 <b>D-ADM-5</b> 拍板补管理端任务列表接口（按状态/供应商分页 + 聚合计数）；</li>
            <li>或先解 <b>缺陷1</b>（检测执行器缺失：<code>recordProbeResults</code> 全仓零调用方）——
              任务恒 <code>QUEUED</code>，靠 DET-06 人工放行推进，列表也没有可看的进度。</li>
          </ol>
          <p class="dc__empty-foot">补齐前本页不填充任何示意数据 —— 设计稿的「8 / 12 / 46 / 4.2%」是画布示意值。</p>
        </div>
      </div>
    </div>

    <!-- 真实能力 ①：人工放行（DET-06，理由必填） -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">人工放行（DET-06）</span>
        <span class="aap-badge aap-badge--info">技术运营 / 超管</span>
        <span class="aap-card__hint">这是管理端**唯一**可用的检测任务端点</span>
      </div>
      <div class="aap-card__body">
        <div class="dc__form">
          <el-input v-model="release.jobId" placeholder="检测任务 ID（雪花 ID）" style="width: 260px" data-testid="release-job-id" />
          <el-input v-model="release.reason" placeholder="放行理由（必填，后端 E-1001）" style="width: 320px" data-testid="release-reason" />
          <el-button type="primary" :loading="releasing" data-testid="release-submit" @click="onRelease">人工放行</el-button>
        </div>
        <p v-if="releaseError" class="dc__err" data-testid="release-error">{{ releaseError }}</p>
        <el-descriptions v-if="released" :column="3" border size="small" class="dc__result" data-testid="release-result">
          <el-descriptions-item label="任务号">{{ released.job_no || released.job_id || '—' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <span class="aap-badge" :class="`aap-badge--${jobTone(released.status)}`">{{ jobLabel(released.status) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="结论">
            <span class="aap-badge" :class="`aap-badge--${resultTone(released.result)}`">{{ resultLabel(released.result) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="报告">{{ released.report_id || '未生成' }}</el-descriptions-item>
          <el-descriptions-item label="凭证">{{ released.credential_id || '—' }}</el-descriptions-item>
          <el-descriptions-item label="错误信息">{{ released.error_msg || '—' }}</el-descriptions-item>
        </el-descriptions>
        <p class="dc__note">
          放行会把任务置 <code>COMPLETED</code>、凭证置 <code>PASS</code>，并**1:1 生成报告**（AC-18）——
          这条 1:1 曾被缺陷9 破坏（放行不产报告且任务已终态、报告再也产不出来），已修复并留回归。
        </p>
      </div>
    </div>

    <!-- 真实能力 ②：检测项配置（ADM-CFG01…05） -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">检测项配置</span>
        <span class="aap-badge aap-badge--info">{{ configs.length }} 份</span>
        <span class="dc__spacer" />
        <el-button size="small" :loading="loadingConfigs" data-testid="cfg-refresh" @click="loadConfigs">刷新</el-button>
        <el-button size="small" type="primary" :disabled="!canConfig" data-testid="cfg-new" @click="openCreate">新建配置</el-button>
      </div>
      <div class="aap-card__body">
        <el-table :data="configs" size="small" data-testid="cfg-table" empty-text="暂无检测配置（真实为空）">
          <el-table-column label="版本" width="90">
            <template #default="{ row }">{{ row.version_no || '—' }}</template>
          </el-table-column>
          <el-table-column label="名称" min-width="180">
            <template #default="{ row }">{{ row.name || '—' }}</template>
          </el-table-column>
          <el-table-column label="及格分" width="90">
            <template #default="{ row }">{{ row.pass_score ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="检测项" min-width="240">
            <template #default="{ row }">
              <span v-if="row.probes?.length">{{ probeSummary(row.probes) }}</span>
              <span v-else class="dc__hint">未配置检测项</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${cfgTone(row.status)}`">{{ cfgLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="发布时间" width="160">
            <template #default="{ row }">{{ fmt(row.published_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-link
                v-if="row.status === 'DRAFT'"
                type="primary"
                :underline="false"
                data-testid="cfg-publish"
                @click="onPublish(row)"
              >
                发布
              </el-link>
              <span v-else class="dc__hint">—</span>
            </template>
          </el-table-column>
        </el-table>
        <p v-if="configError" class="dc__err" data-testid="cfg-error">{{ configError }}</p>
        <p class="dc__note">
          发布 = <code>DRAFT → PUBLISHED</code>，旧活版自动置 <code>SUPERSEDED</code>（ADM-CFG05）；
          修改只在 <code>DRAFT</code> 允许（ADM-CFG04，非草稿得 409 <code>E-1601</code>）。
        </p>
      </div>
    </div>

    <!-- 新建配置对话框 -->
    <el-dialog v-model="createOpen" title="新建检测配置（ADM-CFG02）" width="640px">
      <div class="dc__dlg">
        <div class="dc__field">
          <label>配置名称 <em>*</em></label>
          <el-input v-model="draft.name" placeholder="例如：默认检测配置" data-testid="cfg-name" />
        </div>
        <div class="dc__field">
          <label>及格分（0–100）</label>
          <el-input-number v-model="draft.passScore" :min="0" :max="100" controls-position="right" data-testid="cfg-pass-score" />
        </div>
        <div class="dc__field">
          <label>检测项（只允许后端字典 D1–D8）</label>
          <div class="dc__probes">
            <div v-for="(name, code) in PROBE_NAMES" :key="code" class="dc__probe" :data-testid="`cfg-probe-${code}`">
              <el-checkbox v-model="draft.probes[code].enabled">{{ code }} {{ name }}</el-checkbox>
              <el-input-number
                v-model="draft.probes[code].weight"
                :min="0"
                :step="0.5"
                :disabled="!draft.probes[code].enabled"
                size="small"
                controls-position="right"
                style="width: 110px"
              />
              <span class="dc__hint">权重</span>
              <el-input-number
                v-model="draft.probes[code].timeout"
                :min="1"
                :max="3600"
                :disabled="!draft.probes[code].enabled"
                size="small"
                controls-position="right"
                style="width: 120px"
              />
              <span class="dc__hint">超时(s)</span>
            </div>
          </div>
        </div>
        <p v-if="draftError" class="dc__err" data-testid="cfg-draft-error">{{ draftError }}</p>
      </div>
      <template #footer>
        <el-button data-testid="cfg-cancel" @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" data-testid="cfg-create-submit" @click="onCreate">创建草稿</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import {
  detectionApi, JOB_STATUS, JOB_RESULT, CONFIG_STATUS, PROBE_NAMES,
  DEFAULT_TIMEOUT_SECONDS, LONG_TIMEOUT_CODES, LONG_TIMEOUT_SECONDS,
  type DetectionConfig, type DetectionJob, type DetectionProbe
} from '@/api/admin/detection';
import { useSession } from '@/composables/useSession';
import { can, type AdminRole } from '@/config/nav';

const { role } = useSession();
/** 检测配置属技术侧能力（PRD 13 §1）；前端只做渲染过滤，后端另有二次校验 */
const canConfig = computed(() => can(role.value as AdminRole, 'detection.config'));

const filters = reactive({ keyword: '', status: '', probe: '' });
const autoRefresh = ref(true); // 设计帧开关为开；列表接口缺失 → 控件禁用

const release = reactive({ jobId: '', reason: '' });
const releasing = ref(false);
const releaseError = ref('');
const released = ref<DetectionJob | null>(null);

const configs = ref<DetectionConfig[]>([]);
const loadingConfigs = ref(false);
const configError = ref('');

const createOpen = ref(false);
const creating = ref(false);
const draftError = ref('');
const draft = reactive({
  name: '',
  passScore: 60,
  probes: Object.fromEntries(
    Object.keys(PROBE_NAMES).map((code) => [
      code,
      { enabled: false, weight: 1, timeout: LONG_TIMEOUT_CODES.includes(code) ? LONG_TIMEOUT_SECONDS : DEFAULT_TIMEOUT_SECONDS }
    ])
  ) as Record<string, { enabled: boolean; weight: number; timeout: number }>
});

const jobLabel = (s: string | null | undefined) => (s ? JOB_STATUS[s]?.label ?? s : '—');
const jobTone = (s: string | null | undefined) => (s ? JOB_STATUS[s]?.tone : undefined) ?? 'muted';
const resultLabel = (s: string | null | undefined) => (s ? JOB_RESULT[s]?.label ?? s : '—');
const resultTone = (s: string | null | undefined) => (s ? JOB_RESULT[s]?.tone : undefined) ?? 'muted';
const cfgLabel = (s: string | null | undefined) => (s ? CONFIG_STATUS[s]?.label ?? s : '—');
const cfgTone = (s: string | null | undefined) => (s ? CONFIG_STATUS[s]?.tone : undefined) ?? 'muted';
const fmt = (s: string | null | undefined) => (s ? String(s).replace('T', ' ').slice(0, 16) : '—');

/** 检测项摘要：D1×1 · D2(停)×0.5 …（权重与启停都要看得见） */
const probeSummary = (probes: DetectionProbe[] | undefined): string =>
  (probes ?? []).map((p) => `${p.probe_code}${p.enabled ? '' : '(停)'}×${p.weight}`).join(' · ');

async function onRelease() {
  releaseError.value = '';
  released.value = null;
  if (!release.jobId.trim()) {
    releaseError.value = '请填写检测任务 ID';
    return;
  }
  if (!release.reason.trim()) {
    releaseError.value = '人工放行必须填写理由（后端 E-1001）';
    return;
  }
  releasing.value = true;
  try {
    released.value = await detectionApi.release(release.jobId.trim(), release.reason.trim());
    ElMessage.success('已人工放行');
  } catch (e) {
    // E-1304 任务不存在 / E-1601 已取消 / E-1001 理由缺失 —— 原样透传服务端 message
    releaseError.value = (e as Error).message;
  } finally {
    releasing.value = false;
  }
}

async function loadConfigs() {
  loadingConfigs.value = true;
  configError.value = '';
  try {
    const r = await detectionApi.listConfigs(undefined, 1, 50);
    configs.value = r?.items ?? [];
  } catch (e) {
    configs.value = [];
    configError.value = (e as Error).message;
  } finally {
    loadingConfigs.value = false;
  }
}

function openCreate() {
  draft.name = '';
  draft.passScore = 60;
  draftError.value = '';
  for (const code of Object.keys(PROBE_NAMES)) {
    draft.probes[code].enabled = false;
    draft.probes[code].weight = 1;
    draft.probes[code].timeout = LONG_TIMEOUT_CODES.includes(code) ? LONG_TIMEOUT_SECONDS : DEFAULT_TIMEOUT_SECONDS;
  }
  createOpen.value = true;
}

async function onCreate() {
  draftError.value = '';
  if (!draft.name.trim()) {
    draftError.value = '配置名称必填（后端 E-1001）';
    return;
  }
  const probes = Object.entries(draft.probes)
    .filter(([, v]) => v.enabled)
    .map(([probe_code, v]) => ({
      probe_code,
      enabled: true,
      weight: v.weight,
      timeout_seconds: v.timeout
    }));
  if (!probes.length) {
    draftError.value = '至少启用一个检测项（后端允许空 probes，但空配置无法产出结论）';
    return;
  }
  creating.value = true;
  try {
    await detectionApi.createConfig({ name: draft.name.trim(), pass_score: draft.passScore, probes });
    ElMessage.success('已创建草稿配置（DRAFT）');
    createOpen.value = false;
    await loadConfigs();
  } catch (e) {
    draftError.value = (e as Error).message;
  } finally {
    creating.value = false;
  }
}

async function onPublish(row: DetectionConfig) {
  try {
    const r = await detectionApi.publishConfig(row.id);
    ElMessage.success(`已发布：${r.version_no ?? row.id}（status=${r.status}）`);
    await loadConfigs();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

onMounted(loadConfigs);
defineExpose({ loadConfigs, onRelease });
</script>

<style scoped>
.dc { display: flex; flex-direction: column; gap: 16px; }
.dc__gap { border-radius: var(--r-lg); }
.kpi-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.kpi__label { font-size: var(--fs-base); color: var(--c-text-muted); }
.kpi__value { font-size: var(--fs-kpi); font-weight: 600; line-height: 1.1; }
.kpi__value--todo { color: var(--c-text-muted); }
.kpi__note { font-size: var(--fs-sm); color: var(--c-text-muted); }

.dc__bar { display: flex; align-items: center; gap: 10px; padding: 14px 16px; flex-wrap: wrap; }
.dc__spacer { flex: 1; }
.dc__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }
.aap-card__head { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
.aap-card__title { font-size: var(--fs-lg); font-weight: 600; }
.aap-card__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }
.aap-card__body { padding: 14px 18px 18px; }

.dc__empty { padding: 18px 8px 4px; font-size: var(--fs-base); color: var(--c-text-body); line-height: 1.8; }
.dc__empty ol { padding-left: 20px; }
.dc__empty-foot { color: var(--c-text-muted); font-size: var(--fs-sm); }

.dc__form { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.dc__result { margin-top: 14px; }
.dc__note { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 12px 0 0; line-height: 1.7; }
.dc__err { color: var(--c-danger); font-size: var(--fs-base); margin: 10px 0 0; }

.dc__dlg { display: flex; flex-direction: column; gap: 14px; }
.dc__field { display: flex; flex-direction: column; gap: 6px; }
.dc__field label { font-size: var(--fs-base); color: var(--c-text-body); }
.dc__field em { color: var(--c-danger); font-style: normal; }
.dc__probes { display: flex; flex-direction: column; gap: 8px; }
.dc__probe { display: flex; align-items: center; gap: 8px; }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
