<template>
  <div class="us">
    <!-- KPI 4 张（设计稿：总请求数 / 总 Token / 总收入 / 综合毛利） -->
    <div class="kpi-row" data-testid="usage-kpi">
      <div class="aap-card kpi">
        <span class="kpi__label">总请求数</span>
        <span class="kpi__value">{{ humanCount(summary.requests) }}</span>
        <span class="kpi__note">环比：后端无历史快照，不可比</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">总 Token</span>
        <span class="kpi__value">{{ humanCount(summary.tokens) }}</span>
        <span class="kpi__note">prompt + completion 之和</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">成本（USD）</span>
        <span class="kpi__value">{{ money(summary.cost, '$') }}</span>
        <span class="kpi__note">cost_usd 汇总</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">综合毛利</span>
        <span class="kpi__value kpi__value--todo">未采集</span>
        <span class="kpi__note">后端 Bucket 无售价/毛利字段（设计稿有此维度）</span>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="aap-card us__filter">
      <el-date-picker
        v-model="range"
        type="datetimerange"
        range-separator="~"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        style="width: 380px"
        data-testid="filter-range"
      />
      <el-select v-model="filters.model" placeholder="全部模型" clearable filterable style="width: 200px" data-testid="filter-model">
        <el-option v-for="m in modelOptions" :key="m" :label="m" :value="m" />
      </el-select>
      <el-button type="primary" data-testid="btn-query" @click="load">查询</el-button>
      <el-button :loading="loading" data-testid="btn-refresh" @click="load">刷新</el-button>
      <el-button
        v-if="canRefresh"
        :loading="refreshing"
        data-testid="btn-aggregate-refresh"
        title="POST /admin/usage/refresh：从上游日志源拉取并幂等 UPSERT 到 aap_usage_hourly（ADM-U02）"
        @click="onAggregateRefresh"
      >
        聚合刷新
      </el-button>
      <span class="us__spacer" />
      <el-button data-testid="btn-export" @click="onExport">导出报表</el-button>
    </div>

    <!-- 趋势折线（ECharts，PRD 13 §0 载体要求） -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">调用与消耗趋势</span>
        <span class="aap-card__hint">{{ rangeLabel }}</span>
      </div>
      <div class="aap-card__body">
        <div ref="chartEl" class="us__chart" data-testid="usage-chart" />
        <p v-if="!series.hours.length" class="us__note" data-testid="chart-empty">
          该时间范围内没有用量桶。可先到「配置中心 → 任务监控」触发聚合刷新，
          或确认 new-api 日志源已配置（后端 app.usage.log-file）。
        </p>
      </div>
    </div>

    <div class="row-2">
      <!-- 供应商消耗排行 -->
      <div class="aap-card">
        <div class="aap-card__head"><span class="aap-card__title">供应商消耗排行</span></div>
        <div class="aap-card__body">
          <div v-if="!ranking.length" class="us__empty" data-testid="ranking-empty">暂无数据</div>
          <div v-for="(r, i) in ranking" :key="r.providerId" class="rank" :data-testid="`rank-${i + 1}`">
            <span class="rank__no" :class="{ 'rank__no--top': i < 3 }">{{ i + 1 }}</span>
            <span class="rank__name">{{ r.providerName }}</span>
            <div class="rank__track"><div class="rank__bar" :style="{ width: r.width }" /></div>
            <span class="rank__amt">{{ money(r.amount) }}</span>
          </div>
          <p class="us__note">
            按 cost_usd 汇总（后端无「售价」口径，故展示成本而非收入）。设计稿的
            「供应商消耗排行」金额口径若为售价，需后端补字段 —— 已登记 missing-api。
          </p>
        </div>
      </div>

      <!-- 模型维度用量 -->
      <div class="aap-card">
        <div class="aap-card__head">
          <span class="aap-card__title">模型维度用量</span>
          <span class="aap-card__hint">数据每小时更新</span>
        </div>
        <div class="aap-card__body">
          <el-table :data="modelRows" size="small" data-testid="model-table" empty-text="暂无数据">
            <el-table-column prop="model" label="模型" min-width="160" />
            <el-table-column label="请求数" width="110">
              <template #default="{ row }">{{ humanCount(row.requests) }}</template>
            </el-table-column>
            <el-table-column label="Token" width="110">
              <template #default="{ row }">{{ humanCount(row.tokens) }}</template>
            </el-table-column>
            <el-table-column label="成本" width="120">
              <template #default="{ row }">{{ money(row.cost, '$') }}</template>
            </el-table-column>
            <el-table-column label="缓存命中" width="110">
              <template #default="{ row }">
                <span v-if="row.cacheStatus === 'NO_CACHE_FIELD'" class="us__todo" title="该桶无缓存字段">未采集</span>
                <span v-else>{{ row.cacheHit ?? '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="占比" width="90">
              <template #default="{ row }">{{ row.share }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { usageApi, toRfc3339Utc, humanCount, money, type UsageBucket } from '@/api/admin/usage';
import { useSession } from '@/composables/useSession';
import { can, type AdminRole } from '@/config/nav';

const { role } = useSession();
/** ADM-U02 与后端 @PreAuthorize 对齐（TECH_OPS/SUPER_ADMIN）：无权限者看不到按钮，也不发请求 */
const canRefresh = computed(() => can(role.value as AdminRole, 'usage.refresh'));
const refreshing = ref(false);

const buckets = ref<UsageBucket[]>([]);
const loading = ref(false);
const error = ref('');
const chartEl = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

const now = new Date();
const start = new Date(now.getTime() - 14 * 24 * 3600 * 1000);
const range = ref<[Date, Date]>([start, now]);
const filters = reactive({ model: '' });

const rangeLabel = computed(() => {
  const [a, b] = range.value ?? [];
  if (!a || !b) return '';
  const f = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  return `${f(a)} ~ ${f(b)}`;
});

const summary = computed(() => {
  const requests = buckets.value.reduce((a, b) => a + Number(b.request_count ?? 0), 0);
  const tokens = buckets.value.reduce((a, b) => a + Number(b.total_tokens ?? 0), 0);
  const cost = buckets.value.reduce((a, b) => a + Number(b.cost_usd ?? 0), 0);
  return { requests, tokens, cost };
});

const modelOptions = computed(() => [...new Set(buckets.value.map((b) => b.model_name).filter(Boolean))] as string[]);

/** 按小时聚合（折线图：请求数 + 消耗） */
const series = computed(() => {
  const byHour = new Map<string, { req: number; cost: number }>();
  for (const b of buckets.value) {
    const h = (b.stat_hour ?? '').slice(0, 16);
    if (!h) continue;
    const cur = byHour.get(h) ?? { req: 0, cost: 0 };
    cur.req += Number(b.request_count ?? 0);
    cur.cost += Number(b.cost_usd ?? 0);
    byHour.set(h, cur);
  }
  const hours = [...byHour.keys()].sort();
  return { hours, req: hours.map((h) => byHour.get(h)!.req), cost: hours.map((h) => byHour.get(h)!.cost) };
});

/** 供应商消耗排行（按 cost_usd） */
const ranking = computed(() => {
  const byProvider = new Map<string, { name: string; amount: number }>();
  for (const b of buckets.value) {
    const id = b.provider_id ?? b.channel_id ?? '未知';
    const cur = byProvider.get(id) ?? { name: b.channel_name ?? id, amount: 0 };
    cur.amount += Number(b.cost_usd ?? 0);
    byProvider.set(id, cur);
  }
  const list = [...byProvider.entries()].map(([providerId, v]) => ({ providerId, providerName: v.name, amount: v.amount }));
  list.sort((a, b) => b.amount - a.amount);
  const max = list[0]?.amount || 1;
  return list.slice(0, 8).map((r) => ({ ...r, width: `${Math.max(4, Math.round((r.amount / max) * 100))}%` }));
});

/** 模型维度（请求/Token/成本/缓存命中/占比） */
const modelRows = computed(() => {
  const byModel = new Map<string, { requests: number; tokens: number; cost: number; cacheStatus: string | null; cacheRead: number }>();
  for (const b of buckets.value) {
    const m = b.model_name ?? '(未知模型)';
    const cur = byModel.get(m) ?? { requests: 0, tokens: 0, cost: 0, cacheStatus: b.cache_parse_status, cacheRead: 0 };
    cur.requests += Number(b.request_count ?? 0);
    cur.tokens += Number(b.total_tokens ?? 0);
    cur.cost += Number(b.cost_usd ?? 0);
    cur.cacheRead += Number(b.cache_read_tokens ?? 0);
    // 只要有一个桶是 NO_CACHE_FIELD，就按 PRD 13 §9 标注「未采集」
    if (b.cache_parse_status === 'NO_CACHE_FIELD') cur.cacheStatus = 'NO_CACHE_FIELD';
    byModel.set(m, cur);
  }
  const totalTokens = [...byModel.values()].reduce((a, x) => a + x.tokens, 0) || 1;
  return [...byModel.entries()]
    .map(([model, v]) => ({
      model,
      ...v,
      cacheHit: v.cacheRead > 0 ? `${v.cacheRead.toLocaleString('zh-CN')} tok` : null,
      share: `${((v.tokens / totalTokens) * 100).toFixed(1)}%`
    }))
    .sort((a, b) => b.tokens - a.tokens);
});

function renderChart() {
  if (!chartEl.value) return;
  if (!chart) chart = echarts.init(chartEl.value);
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['请求数', '消耗（USD）'], right: 10, top: 0, textStyle: { fontSize: 12 } },
    grid: { left: 56, right: 56, top: 36, bottom: 40 },
    xAxis: { type: 'category', data: series.value.hours, axisLabel: { fontSize: 11, color: '#94a3b8' } },
    yAxis: [
      { type: 'value', name: '请求数', axisLabel: { fontSize: 11, color: '#94a3b8' }, splitLine: { lineStyle: { color: '#eef2f7' } } },
      { type: 'value', name: '消耗', axisLabel: { fontSize: 11, color: '#94a3b8' }, splitLine: { show: false } }
    ],
    series: [
      { name: '请求数', type: 'line', smooth: true, showSymbol: false, data: series.value.req, lineStyle: { width: 2, color: '#2563eb' }, itemStyle: { color: '#2563eb' } },
      { name: '消耗（USD）', type: 'line', smooth: true, showSymbol: false, yAxisIndex: 1, data: series.value.cost, lineStyle: { width: 2, color: '#16a34a' }, itemStyle: { color: '#16a34a' } }
    ]
  });
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [a, b] = range.value ?? [start, now];
    const r = await usageApi.hourly({
      from: toRfc3339Utc(a),
      to: toRfc3339Utc(b),
      model: filters.model || undefined,
      page: 1,
      pageSize: 500
    });
    buckets.value = r?.items ?? [];
    await nextTick();
    renderChart();
  } catch (e) {
    error.value = (e as Error).message;
    ElMessage.error(error.value);
  } finally {
    loading.value = false;
  }
}

/**
 * ADM-U02 聚合刷新（2026-09-24 接线；此前接口有封装、页面零调用）。
 * 诚实边界：后端读的是 `app.usage.log-file` 这个本地日志源（mock 适配器），不是真实 new-api Log 表；
 * 未配置该文件时后端返回 503 E-1801 —— 这里原样透出，绝不显示"已刷新"假成功。
 */
async function onAggregateRefresh() {
  const [a, b] = range.value ?? [start, now];
  refreshing.value = true;
  try {
    const r = await usageApi.refresh(toRfc3339Utc(a), toRfc3339Utc(b));
    const body = (r ?? {}) as Record<string, unknown>;
    const inserted = Number(body.inserted);
    const updated = Number(body.updated);
    const counts =
      Number.isFinite(inserted) || Number.isFinite(updated)
        ? `（新增 ${Number.isFinite(inserted) ? inserted : '—'} 桶 / 更新 ${Number.isFinite(updated) ? updated : '—'} 桶）`
        : '';
    ElMessage.success(`聚合刷新已执行${counts}，批次 ${body.batch_id ?? '—'}`);
    await load();
  } catch (e) {
    ElMessage.error((e as Error).message);
  } finally {
    refreshing.value = false;
  }
}

function onExport() {
  // PRD 13 §3：导出是异步任务；后端无导出接口 → 显式说明，不假装已导出
  ElMessage.info('导出为异步任务，后端暂未提供导出接口（已登记 missing-api）');
}

const onResize = () => chart?.resize();
onMounted(() => {
  load();
  window.addEventListener('resize', onResize);
});
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  chart?.dispose();
});
watch(series, () => nextTick(renderChart));

defineExpose({ load });
</script>

<style scoped>
.us { display: flex; flex-direction: column; gap: 16px; }
.kpi-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.kpi__label { font-size: var(--fs-base); color: var(--c-text-muted); }
.kpi__value { font-size: var(--fs-kpi); font-weight: 600; line-height: 1.1; }
.kpi__value--todo { font-size: var(--fs-2xl); color: var(--c-warn); }
.kpi__note { font-size: var(--fs-sm); color: var(--c-text-muted); }

.us__filter { display: flex; align-items: center; gap: 10px; padding: 14px 16px; flex-wrap: wrap; }
.us__spacer { flex: 1; }
.aap-card__head { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
.aap-card__title { font-size: var(--fs-lg); font-weight: 600; }
.aap-card__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }
.aap-card__body { padding: 14px 18px 18px; }
.us__chart { width: 100%; height: 300px; }
.us__note { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 10px 0 0; line-height: 1.6; }
.us__empty { padding: 20px; text-align: center; color: var(--c-text-muted); font-size: var(--fs-base); }
.us__todo { font-size: var(--fs-sm); color: var(--c-warn-strong); }

.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 1280px) { .row-2 { grid-template-columns: 1fr; } }

.rank { display: grid; grid-template-columns: 24px 150px 1fr 110px; align-items: center; gap: 10px; padding: 8px 0; }
.rank__no { width: 20px; height: 20px; border-radius: 50%; background: var(--c-surface-alt); color: var(--c-text-sub); font-size: var(--fs-sm); display: flex; align-items: center; justify-content: center; }
.rank__no--top { background: var(--c-primary); color: #fff; }
.rank__name { font-size: var(--fs-base); color: var(--c-text-body); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank__track { height: 10px; background: var(--c-surface-alt); border-radius: var(--r-md); overflow: hidden; }
.rank__bar { height: 100%; background: var(--c-primary); border-radius: var(--r-md); }
.rank__amt { font-size: var(--fs-base); color: var(--c-text); text-align: right; }
</style>
