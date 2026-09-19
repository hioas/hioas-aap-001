<template>
  <div class="dash">
    <!-- 取数失败/降级必须显式可见，不静默 -->
    <el-alert
      v-if="data.warnings.length"
      type="warning"
      show-icon
      :closable="false"
      class="dash__warn"
      data-testid="data-warnings"
    >
      <template #title>部分数据源取数失败，对应指标已置「—」（未用 0 冒充）</template>
      <ul class="dash__warn-list">
        <li v-for="w in data.warnings" :key="w">{{ w }}</li>
      </ul>
    </el-alert>

    <!-- ① KPI 卡带（设计稿：5 张，间距 17，卡高 132，圆角 14） -->
    <div class="kpi-row" data-testid="kpi-row">
      <div v-for="k in data.kpis" :key="k.key" class="aap-card kpi" :class="`kpi--${k.tone ?? 'default'}`">
        <div class="kpi__head">
          <span class="kpi__label">{{ k.label }}</span>
          <span v-if="k.tone === 'warn'" class="aap-badge aap-badge--warn">待处理</span>
          <span v-else-if="k.tone === 'danger'" class="aap-badge aap-badge--danger">需关注</span>
        </div>
        <div class="kpi__value">{{ k.value === null ? '—' : k.value }}</div>
        <div class="kpi__foot">
          <span v-if="k.delta" class="kpi__delta" :class="`kpi__delta--${k.delta.direction}`">{{ k.delta.text }}</span>
          <span v-else-if="k.deltaNote" class="kpi__note">{{ k.deltaNote }}</span>
        </div>
      </div>
    </div>

    <!-- ② 进件漏斗 + 环节平均耗时（设计稿：一行两卡，高 270） -->
    <div class="row-2">
      <div class="aap-card">
        <div class="aap-card__head">
          <span class="aap-card__title">进件漏斗</span>
          <span class="aap-card__hint">近 30 天</span>
        </div>
        <div class="aap-card__body">
          <div v-for="(s, i) in data.funnel" :key="s.label" class="funnel">
            <span class="funnel__label">{{ s.label }}</span>
            <div class="funnel__track">
              <div class="funnel__bar" :style="{ width: funnelWidth(s.value), background: FUNNEL_COLORS[i] }" />
            </div>
            <span class="funnel__value">{{ s.value === null ? '—' : s.value }}</span>
          </div>
          <p v-if="data.funnelNote" class="funnel__note">{{ data.funnelNote }}</p>
        </div>
      </div>

      <div class="aap-card">
        <div class="aap-card__head">
          <span class="aap-card__title">环节平均耗时</span>
        </div>
        <div class="aap-card__body">
          <div v-for="d in STAGE_DURATIONS" :key="d.label" class="dur">
            <span class="dur__label">{{ d.label }}</span>
            <span class="dur__value">{{ d.value }}</span>
          </div>
          <p class="funnel__note">后端无耗时聚合接口 → 暂按 PRD 13 §4 的 SLA 基线展示，标注为基线而非实测</p>
        </div>
      </div>
    </div>

    <!-- ③ 最近进件动态（设计稿表头 7 列） -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">最近进件动态</span>
        <span class="aap-card__spacer" />
        <el-button size="small" :icon="DownloadIcon" data-testid="export" @click="onExport">导出</el-button>
      </div>
      <div class="aap-card__body">
        <el-table :data="data.providers" size="small" data-testid="intake-table" empty-text="暂无进件数据">
          <el-table-column prop="intakeNo" label="进件单号" min-width="150" />
          <el-table-column prop="provider" label="供应商" min-width="150" />
          <el-table-column prop="stage" label="当前环节" width="110" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${row.statusTone}`">{{ row.status }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="updatedAt" label="更新时间" width="150" />
          <el-table-column prop="owner" label="负责人" width="100" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-link type="primary" :underline="false" @click="go(row.action.route)">{{ row.action.label }}</el-link>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { loadDashboard, type DashboardData } from './model';

const router = useRouter();

/** 设计稿「环节平均耗时」5 项（PRD 13 §4 的 SLA 基线，非实测） */
const STAGE_DURATIONS = [
  { label: '凭证提交', value: '12 分钟' },
  { label: '检测验真', value: '2.4 小时' },
  { label: '报价审核', value: '6.1 小时' },
  { label: '合同签署', value: '1.8 天' },
  { label: '同步上线', value: '9 分钟' }
];

const FUNNEL_COLORS = ['#2563eb', '#3b82f6', '#22c55e', '#16a34a'];

const data = reactive<DashboardData>({
  kpis: [],
  funnel: [],
  funnelNote: null,
  providers: [],
  total: 0,
  warnings: [],
  fetchedAt: ''
});

const funnelWidth = (v: number | null) => {
  const max = Math.max(...data.funnel.map((f) => f.value ?? 0), 1);
  if (v === null) return '0%';
  return `${Math.max(4, Math.round((v / max) * 100))}%`;
};

function go(path: string) {
  router.push(path);
}

function onExport() {
  // PRD 13 §3：导出是**异步任务**（超 5 万行转下载中心）。后端无导出接口 → 显式说明，不假装已导出。
  ElMessage.info('导出为异步任务，后端暂未提供导出接口（已登记 missing-api）');
}

const DownloadIcon = () =>
  h('span', { innerHTML: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12M7 10l5 5 5-5M4 20h16"/></svg>' });

async function refresh() {
  const d = await loadDashboard();
  Object.assign(data, d);
}

onMounted(refresh);

defineExpose({ refresh });
</script>

<style scoped>
.dash { display: flex; flex-direction: column; gap: 16px; }
.dash__warn { border-radius: var(--r-lg); }
.dash__warn-list { margin: 6px 0 0; padding-left: 18px; font-size: var(--fs-base); }

.kpi-row { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 17px; }
@media (max-width: 1500px) { .kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.kpi { height: 132px; padding: 16px 18px; display: flex; flex-direction: column; }
.kpi__head { display: flex; align-items: center; gap: 8px; }
.kpi__label { font-size: var(--fs-base); color: var(--c-text-muted); }
.kpi__value { font-size: var(--fs-kpi); font-weight: 600; color: var(--c-text); margin-top: auto; line-height: 1.1; }
.kpi__foot { margin-top: 8px; min-height: 18px; }
.kpi__delta { font-size: var(--fs-sm); }
.kpi__delta--up { color: var(--c-success); }
.kpi__delta--down { color: var(--c-danger); }
.kpi__note { font-size: var(--fs-sm); color: var(--c-text-muted); }
.kpi--warn .kpi__value { color: var(--c-warn); }
.kpi--danger .kpi__value { color: var(--c-danger); }

.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 1200px) { .row-2 { grid-template-columns: 1fr; } }

.aap-card__head { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
.aap-card__title { font-size: var(--fs-lg); font-weight: 600; }
.aap-card__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }
.aap-card__spacer { flex: 1; }
.aap-card__body { padding: 14px 18px 18px; }

.funnel { display: grid; grid-template-columns: 92px 1fr 56px; align-items: center; gap: 12px; margin-bottom: 14px; }
.funnel__label { font-size: var(--fs-base); color: var(--c-text-body); }
.funnel__track { height: 14px; background: var(--c-surface-alt); border-radius: var(--r-md); overflow: hidden; }
.funnel__bar { height: 100%; border-radius: var(--r-md); transition: width 0.3s; }
.funnel__value { font-size: var(--fs-base); color: var(--c-text); text-align: right; }
.funnel__note { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 10px 0 0; line-height: 1.5; }

.dur { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px dashed var(--c-border); }
.dur:last-of-type { border-bottom: 0; }
.dur__label { font-size: var(--fs-base); color: var(--c-text-sub); }
.dur__value { font-size: var(--fs-base); color: var(--c-text); font-weight: 500; }
</style>
