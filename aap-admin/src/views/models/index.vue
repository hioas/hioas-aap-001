<template>
  <div class="md">
    <!-- ⚠️ 整页能力缺口（D-ADM-3）：后端没有模型/厂商表，也没有 CRUD 端点。
         唯一只读来源 /admin/sync/models/upstream 实测 E-1501（未配置 ACTIVE new-api 端点）。
         所以本页按设计稿把 UI 与状态实现完整，但数据源与写操作**显式标注后端未提供**。 -->
    <el-alert type="warning" :closable="false" show-icon class="md__gap" data-testid="model-gap-banner">
      <template #title>本页后端暂无能力（D-ADM-3）：无厂商/模型表、无增删改端点</template>
      设计稿要求的「新增厂商 / 新增模型 / 编辑 / 测试 / 启停」后端**一个端点都没有**；
      唯一只读来源 <code>GET /admin/sync/models/upstream</code> 当前返回
      <code>{{ upstreamError || '尚未请求' }}</code>。页面按设计实现，但不伪造数据、不假装成功。
    </el-alert>

    <!-- KPI 4 张（设计稿：接入厂商 / 已接入模型 / 启用中模型 / 本月调用量 / 平均可用率） -->
    <div class="kpi-row" data-testid="model-kpi">
      <div class="aap-card kpi">
        <span class="kpi__label">接入厂商</span>
        <span class="kpi__value">{{ kpi.vendors ?? '—' }}</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">已接入模型</span>
        <span class="kpi__value">{{ kpi.models ?? '—' }}</span>
        <span class="kpi__note">来源：上游模型清单</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">启用中模型</span>
        <span class="kpi__value">{{ kpi.enabled ?? '—' }}</span>
        <span class="kpi__note">启用状态后端无字段 → 未采集</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">本月调用量</span>
        <span class="kpi__value kpi__value--todo">未采集</span>
        <span class="kpi__note">见「用量统计」（/admin/usage/hourly）</span>
      </div>
    </div>

    <!-- 分组 tabs + 筛选 + 操作 -->
    <div class="aap-card md__bar">
      <el-radio-group v-model="tab" data-testid="model-tabs">
        <el-radio-button value="vendor">按厂商分组</el-radio-button>
        <el-radio-button value="all">全部模型</el-radio-button>
        <el-radio-button value="disabled">停用模型</el-radio-button>
      </el-radio-group>
      <el-input v-model="filters.keyword" placeholder="搜索厂商 / 模型名称" clearable style="width: 220px" data-testid="model-search" />
      <el-select v-model="filters.type" placeholder="全部类型" clearable style="width: 130px" data-testid="model-type">
        <el-option label="对话" value="chat" />
        <el-option label="推理" value="reason" />
        <el-option label="向量" value="embedding" />
      </el-select>
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 130px" data-testid="model-status">
        <el-option label="启用" value="ENABLED" />
        <el-option label="停用" value="DISABLED" />
      </el-select>
      <span class="md__spacer" />
      <el-button data-testid="btn-batch" @click="notProvided('批量管理')">批量管理</el-button>
      <el-button data-testid="btn-export" @click="notProvided('导出清单')">导出清单</el-button>
      <el-button data-testid="btn-add-vendor" @click="notProvided('新增厂商')">新增厂商</el-button>
      <el-button type="primary" data-testid="btn-add-model" @click="notProvided('新增模型')">新增模型</el-button>
    </div>

    <!-- 数据主体 -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">{{ tabTitle }}</span>
        <span class="aap-card__hint">按厂商归类展示，可单独配置模型定价与可用性</span>
        <span class="md__spacer" />
        <el-button size="small" :loading="loading" data-testid="btn-refresh" @click="load">刷新</el-button>
      </div>
      <div class="aap-card__body">
        <!-- 上游清单取到时的真实渲染 -->
        <template v-if="groups.length">
          <div v-for="g in groups" :key="g.vendor" class="vendor" :data-testid="`vendor-${g.vendor}`">
            <div class="vendor__head">
              <span class="vendor__badge">{{ g.vendor.slice(0, 1).toUpperCase() }}</span>
              <span class="vendor__name">{{ g.vendor }}</span>
              <span class="aap-badge aap-badge--info">{{ g.models.length }} 个模型</span>
              <span class="md__spacer" />
              <el-button size="small" text @click="notProvided('添加模型')">添加模型</el-button>
            </div>
            <el-table :data="g.models" size="small" :data-testid="`model-table-${g.vendor}`">
              <el-table-column prop="model_name" label="模型名称 / 标识" min-width="220" />
              <el-table-column label="类型" width="90"><template #default>未采集</template></el-table-column>
              <el-table-column label="上下文" width="90"><template #default>未采集</template></el-table-column>
              <el-table-column label="输入价格" width="120"><template #default>未采集</template></el-table-column>
              <el-table-column label="输出价格" width="120"><template #default>未采集</template></el-table-column>
              <el-table-column label="状态" width="90"><template #default><span class="aap-badge aap-badge--muted">未知</span></template></el-table-column>
              <el-table-column label="操作" width="140">
                <template #default>
                  <el-link type="primary" :underline="false" @click="notProvided('编辑')">编辑</el-link>
                  <el-link type="primary" :underline="false" class="md__act" @click="notProvided('测试')">测试</el-link>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>

        <!-- 上游清单不可用时的显式空态（这是当前的真实状态） -->
        <div v-else class="md__empty" data-testid="model-empty">
          <div class="md__empty-title">暂无可展示的模型数据</div>
          <div class="md__empty-body">
            <p>原因：后端无模型/厂商存储，唯一只读来源 <code>/admin/sync/models/upstream</code> 返回
              <code>{{ upstreamError || '（未请求）' }}</code>。</p>
            <p>要让它有数据，需要先满足其一：</p>
            <ol>
              <li>配置 ACTIVE 的 new-api 端点（<code>aap_newapi_endpoint</code>），使上游清单可读；</li>
              <li>或按 D-ADM-3 拍板补后端模型/厂商能力（建表 + CRUD 端点）。</li>
            </ol>
            <p class="md__empty-foot">在补齐前，本页不填充任何示意数据 —— 设计稿的「12 家厂商 · 86 个模型」是画布示意值。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { request } from '@/api/http';

interface UpstreamModel { model_name?: string; name?: string; vendor?: string; provider?: string; owned_by?: string }

const tab = ref<'vendor' | 'all' | 'disabled'>('vendor');
const filters = reactive({ keyword: '', type: '', status: '' });
const loading = ref(false);
const upstreamError = ref('');
const upstream = ref<UpstreamModel[]>([]);

const kpi = reactive<{ vendors: number | null; models: number | null; enabled: number | null }>({
  vendors: null,
  models: null,
  enabled: null
});

const tabTitle = computed(() =>
  ({ vendor: '按厂商分组', all: '全部模型', disabled: '停用模型' })[tab.value]
);

/** 按上游清单的 owned_by / provider 分组（字段名随上游而异，做容错） */
const groups = computed(() => {
  const byVendor = new Map<string, UpstreamModel[]>();
  for (const m of upstream.value) {
    const v = m.vendor ?? m.provider ?? m.owned_by ?? '未分组';
    const list = byVendor.get(v) ?? [];
    list.push(m);
    byVendor.set(v, list);
  }
  const kw = filters.keyword.toLowerCase();
  return [...byVendor.entries()]
    .map(([vendor, models]) => ({
      vendor,
      models: models
        .map((m) => ({ ...m, model_name: m.model_name ?? m.name ?? '(未命名)' }))
        .filter((m) => !kw || m.model_name.toLowerCase().includes(kw) || vendor.toLowerCase().includes(kw))
    }))
    .filter((g) => g.models.length > 0 || !kw);
});

const notProvided = (what: string) => {
  // 绝不假装成功：明确告知后端未提供
  ElMessage.warning(`「${what}」后端未提供接口（D-ADM-3），本次未发出任何请求`);
};

async function load() {
  loading.value = true;
  upstreamError.value = '';
  try {
    const r = await request<unknown>('/admin/sync/models/upstream');
    // 后端可能返回数组，也可能包一层；两种都容错
    const list = Array.isArray(r) ? (r as UpstreamModel[]) : ((r as { models?: UpstreamModel[] })?.models ?? []);
    upstream.value = list;
    kpi.models = list.length;
    kpi.vendors = new Set(list.map((m) => m.vendor ?? m.provider ?? m.owned_by ?? '未分组')).size;
  } catch (e) {
    upstream.value = [];
    kpi.vendors = null;
    kpi.models = null;
    upstreamError.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
defineExpose({ load });
</script>

<style scoped>
.md { display: flex; flex-direction: column; gap: 16px; }
.md__gap { border-radius: var(--r-lg); }
.kpi-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.kpi__label { font-size: var(--fs-base); color: var(--c-text-muted); }
.kpi__value { font-size: var(--fs-kpi); font-weight: 600; line-height: 1.1; }
.kpi__value--todo { font-size: var(--fs-2xl); color: var(--c-warn); }
.kpi__note { font-size: var(--fs-sm); color: var(--c-text-muted); }

.md__bar { display: flex; align-items: center; gap: 10px; padding: 14px 16px; flex-wrap: wrap; }
.md__spacer { flex: 1; }
.aap-card__head { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
.aap-card__title { font-size: var(--fs-lg); font-weight: 600; }
.aap-card__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }
.aap-card__body { padding: 14px 18px 18px; }

.vendor { border: 1px solid var(--c-border); border-radius: var(--r-card); padding: 12px 14px; margin-bottom: 12px; }
.vendor__head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.vendor__badge { width: 26px; height: 26px; border-radius: var(--r-md); background: var(--c-primary-soft); color: var(--c-primary); display: flex; align-items: center; justify-content: center; font-size: var(--fs-md); font-weight: 600; }
.vendor__name { font-size: var(--fs-md); font-weight: 600; }
.md__act { margin-left: 10px; }

.md__empty { padding: 28px 8px; }
.md__empty-title { font-size: var(--fs-md); font-weight: 600; margin-bottom: 10px; }
.md__empty-body { font-size: var(--fs-base); color: var(--c-text-body); line-height: 1.8; }
.md__empty-body ol { padding-left: 20px; }
.md__empty-foot { color: var(--c-text-muted); font-size: var(--fs-sm); }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
