<template>
  <div class="sy">
    <!-- 顶部操作条（设计稿：同步状态标签 + 自动同步开关 + 立即同步） -->
    <div class="aap-card sy__bar">
      <span class="aap-badge" :class="`aap-badge--${healthTone}`" data-testid="sync-health">
        <span class="sy__dot" :style="{ background: healthDot }" />{{ healthLabel }}
      </span>
      <span class="sy__spacer" />
      <el-switch v-model="autoSync" disabled data-testid="sync-auto" />
      <span class="sy__hint" title="后端无同步计划配置端点（D-ADM-6）">自动同步</span>
      <el-button v-if="canRegisterEndpoint" size="small" data-testid="btn-register-endpoint" @click="openEndpointDialog">
        登记同步端点
      </el-button>
      <el-button
        type="primary"
        data-testid="btn-sync-now"
        :disabled="!canRun"
        title="按任务发起上架同步（ADM-S08 → ADM-S09）；后端无「按渠道立即同步」端点"
        @click="openPublishDialog"
      >立即同步</el-button>
    </div>

    <!-- KPI 4 张（设计稿：渠道总数 / 已同步 / 待同步 / 同步失败） -->
    <div class="kpi-row" data-testid="sync-kpi">
      <div class="aap-card kpi">
        <span class="kpi__label">渠道总数</span>
        <span class="kpi__value">{{ bindingsTotal }}</span>
        <span class="kpi__note">ADM-S04 绑定总数</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">已同步</span>
        <span class="kpi__value kpi__value--ok">{{ syncedCount }}</span>
        <span class="kpi__note">状态 ∈ SYNCED / ENABLED</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">待同步</span>
        <span class="kpi__value kpi__value--warn">{{ pendingCount }}</span>
        <span class="kpi__note">从未同步（last_synced_at 为空）或 PENDING</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">同步失败</span>
        <span class="kpi__value kpi__value--danger">{{ failedTaskCount }}</span>
        <span class="kpi__note">ADM-S01 任务 status=FAILED</span>
      </div>
    </div>

    <!-- 同步计划卡（设计稿：上次同步 / 下次同步 / 同步间隔 / 接口健康） -->
    <div class="aap-card sy__plan">
      <div class="plan">
        <div class="plan__label">上次同步</div>
        <div class="plan__value">{{ lastSyncedAt }}</div>
      </div>
      <div class="plan__sep" />
      <div class="plan">
        <div class="plan__label">下次同步</div>
        <div class="plan__value plan__value--todo">—</div>
      </div>
      <div class="plan__sep" />
      <div class="plan">
        <div class="plan__label">同步间隔</div>
        <div class="plan__value plan__value--todo">—</div>
      </div>
      <div class="plan__sep" />
      <div class="plan">
        <div class="plan__label">接口健康</div>
        <div class="plan__value">
          <span class="aap-badge" :class="`aap-badge--${healthTone}`">{{ healthLabel }}</span>
        </div>
      </div>
    </div>
    <p class="sy__note" data-testid="plan-note">
      「下次同步 / 同步间隔」后端**没有**调度配置端点（<code>aap_newapi_endpoint</code> 无计划字段）→ 渲染成
      <code>—</code>，不编造时间。接口健康取 <code>GET /admin/sync/models/upstream</code> 的实测结果：
      成功 = 正常；<code>E-1501</code>（未配置 ACTIVE 端点）= 异常并显示原因。
    </p>

    <!-- 渠道同步表（设计稿：渠道 ID / 供应商 / 模型 / 同步价格 / 状态 / 最近同步 / 操作） -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">渠道价格同步状态</span>
        <span class="aap-badge aap-badge--muted">{{ bindingsTotal }} 条绑定</span>
        <span v-if="failedTaskCount" class="aap-badge aap-badge--danger">{{ failedTaskCount }} 条失败需处理</span>
        <span class="sy__spacer" />
        <el-button size="small" :loading="loading" data-testid="sync-refresh" @click="loadAll">刷新</el-button>
      </div>
      <div class="aap-card__body">
        <el-table :data="bindings" size="small" data-testid="binding-table" empty-text="暂无渠道绑定（真实为空）">
          <el-table-column label="渠道 ID" width="120">
            <template #default="{ row }">{{ row.channel_id ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="供应商" min-width="180">
            <template #default="{ row }">{{ providerName(row.provider_id) }}</template>
          </el-table-column>
          <el-table-column label="模型" min-width="200">
            <template #default="{ row }">
              <span v-if="row.models?.length">{{ row.models.join(' · ') }}</span>
              <span v-else class="sy__hint">—</span>
            </template>
          </el-table-column>
          <el-table-column label="同步价格" width="170">
            <template #default>
              <!-- 渠道绑定视图里没有单价字段（价格在编译产物/报价单上）→ 未知，不写 0 -->
              <span class="sy__todo" title="ChannelBinding 无价格字段；价格见报价单/编译产物">—</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${bindingTone(row.status)}`">{{ bindingLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最近同步" width="160">
            <template #default="{ row }">{{ fmt(row.last_synced_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="170" fixed="right">
            <template #default="{ row }">
              <el-link
                v-if="canSwitch(row.status)"
                :type="row.status === 'ENABLED' ? 'danger' : 'primary'"
                :underline="false"
                :disabled="!canRun"
                :data-testid="row.status === 'ENABLED' ? 'bind-disable' : 'bind-enable'"
                @click="onSwitch(row)"
              >
                {{ row.status === 'ENABLED' ? '停用' : '启用' }}
              </el-link>
              <span v-else class="sy__hint" title="后端只允许 SYNCED/ENABLED/DISABLED 启停">不可启停</span>
            </template>
          </el-table-column>
        </el-table>
        <p class="sy__note" data-testid="binding-note">
          设计稿的「查看 / 同步 / 日志」在渠道行上没有对应端点：管理端**没有**「立即同步单个渠道」接口
          （只有按任务重试 ADM-S03）→ 未渲染；重试放在下方「同步任务」里（那才是真实可重试的对象）。
        </p>
      </div>
    </div>

    <!-- 同步任务 / 日志（真实数据：ADM-S01 + ADM-S03 重试） -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">同步任务与日志</span>
        <span class="aap-badge aap-badge--muted">{{ tasks.length }} 条</span>
        <span class="sy__spacer" />
        <el-select v-model="taskStatus" placeholder="全部状态" clearable size="small" style="width: 150px" data-testid="task-filter-status" @change="loadAll">
          <el-option v-for="(v, k) in SYNC_TASK_STATUS" :key="k" :label="v.label" :value="k" />
        </el-select>
      </div>
      <div class="aap-card__body">
        <el-table :data="tasks" size="small" data-testid="sync-task-table" empty-text="暂无同步任务（真实为空）">
          <el-table-column label="任务号" min-width="160">
            <template #default="{ row }">{{ row.task_no || row.task_id }}</template>
          </el-table-column>
          <el-table-column label="类型" width="120">
            <template #default="{ row }">{{ row.task_type || '—' }}</template>
          </el-table-column>
          <el-table-column label="渠道" width="130">
            <template #default="{ row }">{{ bindingLabelOf(row.binding_id) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${taskTone(row.status)}`">{{ taskLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="尝试" width="70">
            <template #default="{ row }">{{ row.attempt_count ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="回读一致" width="90">
            <template #default="{ row }">
              <span v-if="row.readback_equal === true" class="aap-badge aap-badge--success">一致</span>
              <span v-else-if="row.readback_equal === false" class="aap-badge aap-badge--danger">不一致</span>
              <span v-else class="sy__hint">—</span>
            </template>
          </el-table-column>
          <el-table-column label="错误" min-width="200">
            <template #default="{ row }">
              <span v-if="row.last_error" class="sy__err">{{ row.last_error }}</span>
              <span v-else class="sy__hint">—</span>
            </template>
          </el-table-column>
          <el-table-column label="最近更新" width="150">
            <template #default="{ row }">{{ fmt(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <el-link
                v-if="canExecute(row.status)"
                type="primary"
                :underline="false"
                :disabled="!canRun"
                data-testid="task-execute"
                @click="onExecute(row)"
              >
                执行
              </el-link>
              <el-link
                type="primary"
                :underline="false"
                :style="{ marginLeft: canExecute(row.status) ? '8px' : '0' }"
                data-testid="task-detail"
                @click="openTaskDetail(row)"
              >
                详情
              </el-link>
              <el-link
                v-if="canRetry(row.status)"
                type="warning"
                :underline="false"
                style="margin-left: 8px"
                :disabled="!canRun"
                data-testid="task-retry"
                @click="onRetry(row)"
              >
                重试
              </el-link>
            </template>
          </el-table-column>
        </el-table>

        <!-- ADM-S02 任务详情抽屉（含 operations 明细与 payload）：接口此前有封装、页面零调用，本次接线 -->
        <el-drawer v-model="detailVisible" title="同步任务详情" size="560px" data-testid="task-detail-drawer">
          <div v-if="detail" class="dt">
            <div class="dt__row"><span class="dt__k">任务号</span><span class="dt__v">{{ detail.task_no || detail.task_id }}</span></div>
            <div class="dt__row"><span class="dt__k">状态</span><span class="dt__v">{{ taskLabel(detail.status) }}</span></div>
            <div class="dt__row"><span class="dt__k">类型</span><span class="dt__v">{{ detail.task_type || '—' }}</span></div>
            <div class="dt__row"><span class="dt__k">供应商</span><span class="dt__v">{{ providerName(detail.provider_id) }}</span></div>
            <div class="dt__row"><span class="dt__k">编译产物</span><span class="dt__v">{{ detail.compilation_id || '—' }}</span></div>
            <div class="dt__row"><span class="dt__k">尝试次数</span><span class="dt__v">{{ detail.attempt_count ?? '—' }}</span></div>
            <div class="dt__row">
              <span class="dt__k">回读一致</span>
              <span class="dt__v">{{ detail.readback_equal == null ? '—' : detail.readback_equal ? '一致' : '不一致' }}</span>
            </div>
            <div class="dt__row"><span class="dt__k">幂等键</span><span class="dt__v dt__v--mono">{{ detail.idempotency_key || '—' }}</span></div>
            <div class="dt__row"><span class="dt__k">最近错误</span><span class="dt__v">{{ detail.last_error || '—' }}</span></div>

            <div class="dt__title">执行明细（aap_sync_operation）</div>
            <el-table :data="detail.operations ?? []" size="small" data-testid="task-operation-table" empty-text="暂无明细">
              <el-table-column label="操作" width="130" prop="operation" />
              <el-table-column label="结果" width="100" prop="result" />
              <el-table-column label="第几次" width="80" prop="attempt_no" />
              <el-table-column label="回读" width="90">
                <template #default="{ row }">
                  {{ row.readback_equal == null ? '—' : row.readback_equal ? '一致' : '不一致' }}
                </template>
              </el-table-column>
              <el-table-column label="错误" min-width="160" prop="error" />
            </el-table>

            <div class="dt__title">任务载荷（读前写后三段式的输入）</div>
            <pre class="dt__json" data-testid="task-payload">{{ pretty(detail.payload) }}</pre>
          </div>
          <p v-else class="sy__hint">加载中…</p>
        </el-drawer>

        <!-- ADM-S07 登记 new-api 端点（仅 SUPER_ADMIN） -->
        <el-dialog v-model="endpointDialog" title="登记 new-api 同步端点" width="560px" data-testid="endpoint-dialog">
          <el-form label-width="110px">
            <el-form-item label="名称">
              <el-input v-model="endpointForm.name" maxlength="64" data-testid="endpoint-name" />
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="endpointForm.base_url" maxlength="255" placeholder="https://newapi.example.com" data-testid="endpoint-base-url" />
            </el-form-item>
            <el-form-item label="Api Key">
              <el-input v-model="endpointForm.api_key" type="password" show-password maxlength="512" data-testid="endpoint-api-key" />
            </el-form-item>
            <el-form-item label="只读端点">
              <el-switch v-model="endpointForm.readonly" />
            </el-form-item>
          </el-form>
          <p class="sy__note">
            Api Key 加密落库（<code>api_key_cipher</code>），响应只回掩码 —— 页面不会、也无法回显明文。
            标记「只读」后该端点的写操作一律 <code>E-1505</code>。
          </p>
          <template #footer>
            <el-button @click="endpointDialog = false">取消</el-button>
            <el-button type="primary" :loading="submitting" data-testid="endpoint-submit" @click="onRegisterEndpoint">登记</el-button>
          </template>
        </el-dialog>

        <!-- ADM-S08 发起上架同步（建渠道 + 写价；执行在 ADM-S09） -->
        <el-dialog v-model="publishDialog" title="发起上架同步（建渠道 + 写价）" width="600px" data-testid="publish-dialog">
          <el-form label-width="130px">
            <el-form-item label="供应商">
              <el-select v-model="publishForm.provider_id" filterable placeholder="选择供应商" style="width: 100%" data-testid="publish-provider">
                <el-option v-for="p in providers" :key="p.id" :label="p.company_name || p.provider_code || p.id" :value="String(p.id)" />
              </el-select>
            </el-form-item>
            <el-form-item label="编译产物 ID">
              <el-input v-model="publishForm.compilation_id" placeholder="留空 = 取该供应商最近一条已确认产物" data-testid="publish-compilation" />
            </el-form-item>
            <el-form-item label="渠道名">
              <el-input v-model="publishForm.channel_name" placeholder="留空 = 服务端按 AAP-{简称}-{序号} 生成" data-testid="publish-channel-name" />
            </el-form-item>
            <el-form-item label="模式">
              <el-select v-model="publishForm.mode" style="width: 100%" data-testid="publish-mode">
                <el-option label="审核后应用（REVIEW_THEN_APPLY）" value="REVIEW_THEN_APPLY" />
                <el-option label="仅预演（DRY_RUN）" value="DRY_RUN" />
              </el-select>
            </el-form-item>
          </el-form>
          <p class="sy__note">
            闸门③：该供应商必须已有 <strong>CONFIRMED</strong> 编译产物，否则 409 <code>E-1407</code>（不绕过）。
            幂等键 <code>sha256(provider_id|ADD_CHANNEL|channel_name)</code> —— 同供应商同名渠道重复发起会复用同一条任务。
            本步只建任务（<code>PENDING</code>），真正写入 new-api 在「执行」（ADM-S09）。
          </p>
          <template #footer>
            <el-button @click="publishDialog = false">取消</el-button>
            <el-button type="primary" :loading="submitting" data-testid="publish-submit" @click="onCreateTask">发起同步</el-button>
          </template>
        </el-dialog>

        <div class="sy__logs">
          <div class="sy__logs-title">同步日志</div>
          <div v-if="!tasks.length" class="sy__hint" data-testid="log-empty">
            暂无日志（没有同步任务 = 没有日志；不填充示意行）。
          </div>
          <div v-for="t in tasks.slice(0, 8)" :key="`log-${t.id}`" class="log" :data-testid="`log-${t.id}`">
            <span class="log__dot" :style="{ background: taskDot(t.status) }" />
            <span class="log__time">{{ fmt(t.updated_at) }}</span>
            <span class="log__text">
              {{ t.task_no || t.task_id }} · {{ t.task_type || '同步' }} · {{ taskLabel(t.status) }}
              <template v-if="t.last_error">：{{ t.last_error }}</template>
            </span>
          </div>
        </div>

        <p v-if="error" class="sy__err-block" data-testid="sync-error">{{ error }}</p>
        <p class="sy__note">
          重试按后端退避 30s/2m/8m/30m/2h、≤5 次（ADM-S03）；鉴权类失败（<code>E-1505</code>）不重试、直接转
          <code>MANUAL</code>。启停要求渠道已同步成功（<code>SYNCED</code>），否则 409 <code>E-1601</code>。
          前端按角色渲染开关，后端另有 <code>hasAnyRole('TECH_OPS','SUPER_ADMIN')</code> 二次校验。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  syncApi, SYNC_TASK_STATUS, BINDING_STATUS, SWITCHABLE_BINDING_STATUS, RETRYABLE_TASK_STATUS,
  type ChannelBinding, type SyncTask
} from '@/api/admin/sync';
import { providerApi, type ProviderRow } from '@/api/admin/providers';
import { useSession } from '@/composables/useSession';
import { can, type AdminRole } from '@/config/nav';

const { role } = useSession();
/** 同步属技术侧能力（PRD 13 §1：运营商务看不到 new-api 连接配置）；后端另有二次校验 */
const canRun = computed(() => can(role.value as AdminRole, 'sync.run'));

const loading = ref(false);
const error = ref('');
const bindings = ref<ChannelBinding[]>([]);
const bindingsTotal = ref(0);
const tasks = ref<SyncTask[]>([]);
const providers = ref<ProviderRow[]>([]);
const taskStatus = ref('');
const autoSync = ref(true); // 设计帧开关为开；无配置端点 → 控件禁用
const upstreamOk = ref<boolean | null>(null);

/* ── ADM-S07/S08/S09 上架闭环（2026-09-24 接线）────────────────────────────
 * 此前这三条后端端点已实现且有契约测试，但页面零调用 ⇒ 管理端看不到、也点不动上架。
 * 本次只做「接线」：不新增端点、不改错误语义，错误原样透出（尤其闸门③ E-1407）。
 * ──────────────────────────────────────────────────────────────────────── */
const canRegisterEndpoint = computed(() => can(role.value as AdminRole, 'newapi.config'));
const submitting = ref(false);

const endpointDialog = ref(false);
const endpointForm = reactive({ name: '', base_url: '', api_key: '', readonly: false });

const publishDialog = ref(false);
const publishForm = reactive({
  provider_id: '',
  compilation_id: '',
  channel_name: '',
  mode: 'REVIEW_THEN_APPLY' as 'REVIEW_THEN_APPLY' | 'DRY_RUN'
});

const detailVisible = ref(false);
const detail = ref<SyncTask | null>(null);

const bindingLabel = (s: string | null | undefined) => (s ? BINDING_STATUS[s]?.label ?? s : '—');
const bindingTone = (s: string | null | undefined) => (s ? BINDING_STATUS[s]?.tone : undefined) ?? 'muted';
const taskLabel = (s: string | null | undefined) => (s ? SYNC_TASK_STATUS[s]?.label ?? s : '—');
const taskTone = (s: string | null | undefined) => (s ? SYNC_TASK_STATUS[s]?.tone : undefined) ?? 'muted';
const fmt = (s: string | null | undefined) => (s ? String(s).replace('T', ' ').slice(0, 16) : '—');

const taskDot = (s: string) =>
  s === 'SUCCESS' ? 'rgba(22,163,74,1)' : s === 'FAILED' ? 'rgba(220,38,38,1)' : 'rgba(217,119,6,1)';

const syncedCount = computed(() => bindings.value.filter((b) => b.status === 'SYNCED' || b.status === 'ENABLED').length);
const pendingCount = computed(
  () => bindings.value.filter((b) => !b.last_synced_at || b.status === 'PENDING').length
);
const failedTaskCount = computed(() => tasks.value.filter((t) => t.status === 'FAILED').length);

/** 上次同步：取绑定里最新的 last_synced_at（无绑定 → 未知，不写时间） */
const lastSyncedAt = computed(() => {
  const stamps = bindings.value.map((b) => b.last_synced_at).filter(Boolean) as string[];
  if (!stamps.length) return '—';
  return fmt(stamps.sort().slice(-1)[0]);
});

const healthLabel = computed(() => (upstreamOk.value == null ? '未探测' : upstreamOk.value ? '同步服务运行中' : '接口异常'));
const healthTone = computed(() => (upstreamOk.value == null ? 'muted' : upstreamOk.value ? 'success' : 'danger'));
const healthDot = computed(() =>
  upstreamOk.value == null ? 'rgba(148,163,184,1)' : upstreamOk.value ? 'rgba(22,163,74,1)' : 'rgba(220,38,38,1)'
);

const canSwitch = (s: string) => SWITCHABLE_BINDING_STATUS.includes(s);
const canRetry = (s: string) => RETRYABLE_TASK_STATUS.includes(s);
/** ADM-S09 可执行的任务状态（与 SyncPublishService.execute 的状态闸门一致；RUNNING 不可重入） */
const EXECUTABLE_TASK_STATUS = ['PENDING', 'SYNCED', 'FAILED', 'MANUAL'];
const canExecute = (s: string) => EXECUTABLE_TASK_STATUS.includes(s);

/** 供应商名由 /admin/providers 关联（绑定视图只有 provider_id） */
function providerName(id: string | null | undefined): string {
  if (!id) return '—';
  const p = providers.value.find((x) => x.id === id || x.provider_id === id);
  return p?.company_name || p?.provider_code || id;
}

function bindingLabelOf(bindingId: string | null | undefined): string {
  if (!bindingId) return '—';
  const b = bindings.value.find((x) => x.id === bindingId || x.binding_id === bindingId);
  return b?.channel_name || (b?.channel_id != null ? `ch-${b.channel_id}` : bindingId);
}

async function loadAll() {
  loading.value = true;
  error.value = '';
  try {
    const [b, t] = await Promise.all([
      syncApi.listBindings(1, 50),
      syncApi.listTasks({ page: 1, pageSize: 50, status: taskStatus.value || undefined })
    ]);
    bindings.value = b?.items ?? [];
    bindingsTotal.value = b?.total ?? bindings.value.length;
    tasks.value = t?.items ?? [];
  } catch (e) {
    error.value = (e as Error).message;
    bindings.value = [];
    tasks.value = [];
  } finally {
    loading.value = false;
  }
  // 供应商名关联（取不到就显示 id，不假装有名字）
  try {
    const p = await providerApi.list({ page: 1, pageSize: 100 });
    providers.value = p?.items ?? [];
  } catch { /* 保持空：providerName 会退化为显示 id */ }
  // 接口健康：真实探测一次上游清单（E-1501 是「未配置端点」的已知形态）
  try {
    await syncApi.upstreamModels();
    upstreamOk.value = true;
  } catch {
    upstreamOk.value = false;
  }
}

async function onSwitch(row: ChannelBinding) {
  const target = row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED';
  try {
    await syncApi.changeBindingStatus(row.id, target);
    ElMessage.success(`渠道已${target === 'ENABLED' ? '启用' : '停用'}`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

async function onRetry(row: SyncTask) {
  try {
    await syncApi.retry(row.task_id || row.id);
    ElMessage.success('已提交重试');
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

/** payload 展示：对象美化、字符串原样、空值给「—」（不假装有内容） */
function pretty(v: unknown): string {
  if (v == null) return '—';
  if (typeof v === 'string') return v;
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

/** ADM-S07：登记 new-api 端点（仅 SUPER_ADMIN；api_key 只进不出） */
function openEndpointDialog() {
  endpointForm.name = '';
  endpointForm.base_url = '';
  endpointForm.api_key = '';
  endpointForm.readonly = false;
  endpointDialog.value = true;
}

async function onRegisterEndpoint() {
  if (!endpointForm.name.trim() || !endpointForm.base_url.trim() || !endpointForm.api_key.trim()) {
    ElMessage.warning('名称 / Base URL / Api Key 均为必填');
    return;
  }
  submitting.value = true;
  try {
    const ep = await syncApi.registerEndpoint({
      name: endpointForm.name.trim(),
      base_url: endpointForm.base_url.trim(),
      api_key: endpointForm.api_key,
      readonly: endpointForm.readonly
    });
    endpointDialog.value = false;
    endpointForm.api_key = ''; // 明文不留在内存里
    ElMessage.success(`端点已登记：${ep?.name ?? ''}（key 掩码 ${ep?.api_key_mask ?? '—'}）`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  } finally {
    submitting.value = false;
  }
}

/** ADM-S08：发起上架同步（建渠道 + 写价）——闸门③ 未确认编译产物会被后端以 E-1407 拒绝 */
function openPublishDialog() {
  publishDialog.value = true;
}

async function onCreateTask() {
  if (!publishForm.provider_id) {
    ElMessage.warning('请选择供应商');
    return;
  }
  submitting.value = true;
  try {
    const t = await syncApi.createTask({
      provider_id: publishForm.provider_id,
      compilation_id: publishForm.compilation_id.trim() || undefined,
      channel_name: publishForm.channel_name.trim() || undefined,
      mode: publishForm.mode
    });
    publishDialog.value = false;
    ElMessage.success(
      `已建上架任务 ${t?.task_no || t?.task_id || ''}（${t?.status ?? ''}）—— 下一步在任务行点「执行」才真正写入 new-api`
    );
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  } finally {
    submitting.value = false;
  }
}

/** ADM-S09：执行上架（真写上游 → 回读比对）。写操作先二次确认，不做静默写入 */
async function onExecute(row: SyncTask) {
  const id = row.task_id || row.id;
  try {
    await ElMessageBox.confirm(
      `将对 new-api 真实写入渠道与价格（读前 → 写后 → 回读一致），任务 ${row.task_no || id}。是否继续？`,
      '执行上架同步',
      { type: 'warning', confirmButtonText: '执行', cancelButtonText: '取消' }
    );
  } catch {
    return; // 用户取消
  }
  try {
    const t = await syncApi.executeTask(id);
    const note = t?.readback_equal === false ? '（回读不一致：本地状态未沿用，需人工核对）' : '';
    ElMessage.success(`上架执行完成：${t?.status ?? ''}${note}`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

/** ADM-S02：任务详情抽屉（先用行数据占位避免空白，再拉全量含 operations） */
async function openTaskDetail(row: SyncTask) {
  detail.value = row;
  detailVisible.value = true;
  try {
    detail.value = (await syncApi.taskDetail(row.task_id || row.id)) ?? row;
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

onMounted(loadAll);
defineExpose({ loadAll });
</script>

<style scoped>
.sy { display: flex; flex-direction: column; gap: 16px; }
.sy__bar { display: flex; align-items: center; gap: 10px; padding: 14px 16px; flex-wrap: wrap; }
.sy__spacer { flex: 1; }
.sy__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }

/* ADM-S02 详情抽屉 / S07-S08 对话框（2026-09-24 接线新增） */
.sy__note {
  margin: 4px 0 0;
  font-size: var(--fs-sm);
  line-height: 1.6;
  color: var(--c-text-muted);
}
.sy__note code {
  padding: 1px 4px;
  border-radius: 4px;
  background: var(--c-fill, rgba(148, 163, 184, 0.16));
}
.dt { display: flex; flex-direction: column; gap: 6px; }
.dt__row { display: flex; gap: 12px; font-size: var(--fs-base); }
.dt__k { width: 92px; flex: none; color: var(--c-text-muted); }
.dt__v { flex: 1; word-break: break-all; }
.dt__v--mono { font-family: var(--font-mono, monospace); font-size: var(--fs-sm); }
.dt__title {
  margin-top: 14px;
  font-size: var(--fs-base);
  font-weight: 600;
}
.dt__json {
  max-height: 220px;
  overflow: auto;
  margin: 0;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--c-fill, rgba(148, 163, 184, 0.12));
  font-family: var(--font-mono, monospace);
  font-size: var(--fs-sm);
  white-space: pre-wrap;
  word-break: break-all;
}
.sy__todo { font-size: var(--fs-base); color: var(--c-text-muted); }
.sy__err { font-size: var(--fs-base); color: var(--c-danger); }
.sy__err-block { color: var(--c-danger); font-size: var(--fs-base); margin: 10px 0 0; }
.sy__dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }

.kpi-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.kpi__label { font-size: var(--fs-base); color: var(--c-text-muted); }
.kpi__value { font-size: var(--fs-kpi); font-weight: 600; line-height: 1.1; }
.kpi__value--ok { color: var(--c-success); }
.kpi__value--warn { color: var(--c-warn); }
.kpi__value--danger { color: var(--c-danger); }
.kpi__note { font-size: var(--fs-sm); color: var(--c-text-muted); }

.sy__plan { display: flex; align-items: center; padding: 16px 18px; gap: 16px; }
.plan { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.plan__label { font-size: var(--fs-sm); color: var(--c-text-muted); }
.plan__value { font-size: var(--fs-md); color: var(--c-text); }
.plan__value--todo { color: var(--c-text-muted); }
.plan__sep { width: 1px; height: 32px; background: var(--c-border); }

.aap-card__head { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
.aap-card__title { font-size: var(--fs-lg); font-weight: 600; }
.aap-card__body { padding: 14px 18px 18px; }
.sy__note { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 12px 0 0; line-height: 1.7; }

.sy__logs { margin-top: 16px; }
.sy__logs-title { font-size: var(--fs-md); font-weight: 600; margin-bottom: 8px; }
.log { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px dashed var(--c-border); font-size: var(--fs-base); }
.log:last-of-type { border-bottom: 0; }
.log__dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 8px; }
.log__time { color: var(--c-text-muted); width: 120px; flex: 0 0 120px; }
.log__text { color: var(--c-text-body); }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
