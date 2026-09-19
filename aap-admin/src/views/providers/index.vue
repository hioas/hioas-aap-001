<template>
  <div class="pv">
    <!-- 工具条（设计真源 page-4-pc 顶部栏：标题旁「共 N 家」+ 新增供应商 + 搜索 + 类型/状态 + 重置/查询） -->
    <div class="aap-card pv__bar">
      <span class="pv__count" data-testid="provider-count">共 {{ total }} 家</span>
      <el-button type="primary" data-testid="btn-new" @click="openNew">新增供应商</el-button>
      <el-input
        v-model="filters.keyword"
        placeholder="搜索供应商名称 / 信用代码"
        clearable
        style="width: 240px"
        data-testid="filter-keyword"
        @keyup.enter="onQuery"
      />
      <el-select v-model="filters.category" placeholder="全部类型" clearable style="width: 140px" data-testid="filter-category">
        <el-option v-for="c in CATEGORY_OPTIONS" :key="c.value" :label="c.label" :value="c.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 160px" data-testid="filter-status">
        <el-option v-for="(v, k) in PROVIDER_STATUS" :key="k" :label="v.label" :value="k" />
      </el-select>
      <span class="pv__spacer" />
      <el-button data-testid="btn-reset" @click="onReset">重置</el-button>
      <el-button type="primary" :loading="loading" data-testid="btn-query" @click="onQuery">查询</el-button>
    </div>

    <!-- 台账表（设计稿列：供应商 / 类型 / 接入线路 / 档案完整度 / 状态 / 最近更新 / 操作） -->
    <div class="aap-card">
      <div class="aap-card__body">
        <el-table :data="visibleRows" size="small" data-testid="provider-table" empty-text="暂无供应商">
          <el-table-column label="供应商" min-width="220">
            <template #default="{ row }">
              <div class="pv__name">{{ row.company_name || row.provider_code || '—' }}</div>
              <div class="pv__uscc">{{ row.uscc || '统一社会信用代码未填' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${industryTone(row.industry_category)}`">
                {{ industryLabel(row.industry_category) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="接入线路" width="96">
            <template #default>
              <!-- 后端 ProviderProfileResponse 无线路/凭证计数字段 → 未知，不写 0 -->
              <span class="pv__todo" title="后端无线路计数字段，也没有管理端凭证列表接口" data-testid="cell-access-lines">
                {{ UNKNOWN }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="档案完整度" width="150">
            <template #default="{ row }">
              <div class="pv__meter">
                <el-progress
                  :percentage="meterPercent(row.completeness)"
                  :stroke-width="8"
                  :show-text="false"
                  :color="meterColor(completenessTone(row.completeness))"
                  class="pv__meter-bar"
                />
                <span class="pv__meter-text">{{ completenessText(row.completeness) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="112">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${statusTone(row.status)}`">{{ statusLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最近更新" width="120">
            <template #default="{ row }">{{ fmtShortDate(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-link type="primary" :underline="false" data-testid="act-detail" @click="openDetail(row)">详情</el-link>
              <el-link
                type="primary"
                :underline="false"
                class="pv__act"
                data-testid="act-quotes"
                title="管理端无「按供应商查报价单」接口，此处跳报价审核台（全部待审）"
                @click="goQuotes"
              >
                报价
              </el-link>
              <el-link
                v-if="!isSuspended(row.status)"
                type="danger"
                :underline="false"
                class="pv__act"
                data-testid="act-suspend"
                @click="onSuspend(row)"
              >
                停用
              </el-link>
              <el-link
                v-else
                type="success"
                :underline="false"
                class="pv__act"
                data-testid="act-resume"
                @click="onResume(row)"
              >
                恢复
              </el-link>
            </template>
          </el-table-column>
        </el-table>

        <p v-if="error" class="pv__err" data-testid="page-error">{{ error }}</p>

        <div class="pv__foot">
          <span class="pv__summary" data-testid="page-summary">{{ pageSummary(total, pageSize) }}</span>
          <span class="pv__spacer" />
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            background
            data-testid="pager"
            @current-change="load"
          />
        </div>

        <p class="pv__note" data-testid="missing-actions-note">{{ MISSING_ACTIONS_NOTE }}</p>
        <p class="pv__note" data-testid="category-filter-note">{{ CATEGORY_FILTER_NOTE }}</p>
        <p class="pv__note" data-testid="rbac-note">
          前端按角色渲染，但**不是安全边界**：后端对 ADM-P01/02/03 另有
          <code>hasAnyRole('BIZ_OPERATOR','TECH_OPS','SUPER_ADMIN')</code> 二次校验（PRD 13 §1/§11）。
        </p>
      </div>
    </div>

    <!-- 详情抽屉：只用列表已返回的真实字段，缺的显式标注 -->
    <el-drawer v-model="detailOpen" :title="detail?.company_name || '供应商详情'" size="620px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" data-testid="detail-desc">
          <el-descriptions-item label="供应商编号">{{ detail.provider_no || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="供应商标识">{{ detail.provider_code || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="统一社会信用代码">{{ detail.uscc || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ industryLabel(detail.industry_category) }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
          <el-descriptions-item label="档案完整度">{{ completenessText(detail.completeness) }}</el-descriptions-item>
          <el-descriptions-item label="地区">{{ [detail.province, detail.city].filter(Boolean).join(' ') || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="地址">{{ detail.address || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="官网">{{ detail.website || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="复检周期">{{ detail.recheck_interval_days }} 天</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ detail.contact_name || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ detail.contact_phone_masked || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="联系邮箱">{{ detail.contact_email || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="登录账号">{{ detail.account?.phone_masked || UNKNOWN }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ fmtDateTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="最近更新">{{ fmtDateTime(detail.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <p v-if="detail.manual_override" class="pv__note">
          人工放行：{{ detail.override_reason || '（未填理由）' }}
        </p>

        <div class="pv__sub">资质文件</div>
        <el-table v-if="detail.qualification_files?.length" :data="detail.qualification_files" size="small" data-testid="qual-table">
          <el-table-column prop="file_name" label="文件名" min-width="180" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="size" label="大小(字节)" width="110" />
        </el-table>
        <p v-else class="pv__note" data-testid="qual-empty">
          该供应商资质文件为空（= 没有上传过，不是「取不到」）。
          文件服务**代码已就绪**（缺陷2 已修，提交 <code>9cf495f</code>：<code>POST /files</code> 上传 +
          <code>GET /files/{id}</code> 下载）；⚠️ 当前 dev 实例**尚未重启到含该版本的构建** ——
          实测 <code>POST /files</code> 仍返回 404 <code>E-1406</code>，重启后再验。
          另外「把文件挂到某供应商资质上」的 <code>POST /provider/qualifications</code> 仅**供应商本人**可用
          （管理端调用得 403 <code>E-1901</code>）→ 管理端目前仍无法代上传，只能只读展示。
        </p>
      </template>
    </el-drawer>

    <!-- 新增供应商抽屉（设计真源 page-4-1，含校验错误态） -->
    <el-drawer v-model="newOpen" title="新增供应商" size="640px" data-testid="new-drawer">
      <div class="nv">
        <div v-if="errorCount > 0" class="nv__summary" data-testid="new-error-summary">
          {{ vendorErrorSummary(errors) }}
        </div>

        <div class="nv__group"><span class="nv__bar" />基础信息</div>

        <div class="nv__field">
          <label class="nv__label">供应商名称 <em>*</em></label>
          <el-input v-model="form.name" placeholder="请输入供应商名称" data-testid="new-name" />
          <p v-if="errors.name" class="nv__error" data-testid="err-name">{{ errors.name }}</p>
        </div>

        <div class="nv__field">
          <label class="nv__label">供应商标识 <em>*</em><span class="nv__hint">{{ VENDOR_CODE_HINT }}</span></label>
          <el-input v-model="form.code" placeholder="mistral" data-testid="new-code" />
          <p v-if="errors.code" class="nv__error" data-testid="err-code">{{ errors.code }}</p>
        </div>

        <div class="nv__field">
          <label class="nv__label">供应商类型 <em>*</em></label>
          <div class="nv__chips">
            <button
              v-for="c in CATEGORY_OPTIONS"
              :key="c.value"
              class="nv__chip"
              :class="{ 'nv__chip--on': form.category === c.value }"
              type="button"
              :data-testid="`new-cat-${c.value}`"
              @click="form.category = c.value"
            >
              {{ c.label }}
            </button>
          </div>
          <p v-if="errors.category" class="nv__error" data-testid="err-category">{{ errors.category }}</p>
          <p class="nv__hint-block" data-testid="new-cat-note">
            设计稿在列表页把同一组枚举写成「原厂 / 渠道商 / 中转商」，此处抽屉写「官方直连 / 第三方代理 / 自建网关」——
            两处措辞不一致，取值统一为后端枚举 ORIGINAL / RESELLER / AGGREGATOR（偏差已登记）。
          </p>
        </div>

        <div class="nv__field">
          <label class="nv__label">所属地区</label>
          <div class="nv__chips">
            <button
              v-for="r in REGION_OPTIONS"
              :key="r"
              class="nv__chip"
              :class="{ 'nv__chip--on': form.region === r }"
              type="button"
              :data-testid="`new-region-${r}`"
              @click="form.region = r"
            >
              {{ r }}
            </button>
          </div>
        </div>

        <div class="nv__group"><span class="nv__bar" />接入配置</div>

        <div class="nv__field">
          <label class="nv__label">API Base URL <em>*</em></label>
          <el-input v-model="form.baseUrl" placeholder="api.mistral.ai/v1" data-testid="new-baseurl" />
          <p v-if="errors.baseUrl" class="nv__error" data-testid="err-baseurl">{{ errors.baseUrl }}</p>
        </div>

        <div class="nv__field">
          <label class="nv__label">默认 API Key <em>*</em></label>
          <div class="nv__row">
            <el-input v-model="form.apiKey" type="password" show-password placeholder="请输入 API Key" data-testid="new-apikey" />
            <el-button data-testid="new-test-conn" @click="onTestConn">测试连通</el-button>
          </div>
          <p v-if="errors.apiKey" class="nv__error" data-testid="err-apikey">{{ errors.apiKey }}</p>
        </div>

        <div class="nv__grid">
          <div class="nv__field">
            <label class="nv__label">请求超时（ms）</label>
            <el-input-number v-model="form.timeoutMs" :min="1000" :step="1000" controls-position="right" data-testid="new-timeout" />
            <p v-if="errors.timeoutMs" class="nv__error">{{ errors.timeoutMs }}</p>
          </div>
          <div class="nv__field">
            <label class="nv__label">失败重试次数</label>
            <el-input-number v-model="form.retries" :min="0" :max="10" controls-position="right" data-testid="new-retries" />
            <p v-if="errors.retries" class="nv__error">{{ errors.retries }}</p>
          </div>
        </div>

        <div class="nv__group"><span class="nv__bar" />计费与限流</div>

        <div class="nv__grid">
          <div class="nv__field">
            <label class="nv__label">结算币种</label>
            <div class="nv__chips">
              <button
                v-for="c in CURRENCY_OPTIONS"
                :key="c"
                class="nv__chip"
                :class="{ 'nv__chip--on': form.currency === c }"
                type="button"
                :data-testid="`new-cur-${c}`"
                @click="form.currency = c"
              >
                {{ c }}
              </button>
            </div>
          </div>
          <div class="nv__field">
            <label class="nv__label">默认并发限流（QPS）</label>
            <el-input-number v-model="form.qps" :min="1" controls-position="right" data-testid="new-qps" />
            <p v-if="errors.qps" class="nv__error">{{ errors.qps }}</p>
          </div>
        </div>

        <div class="nv__group"><span class="nv__bar" />状态与备注</div>
        <div class="nv__switch-row">
          <div>
            <div class="nv__switch-title">启用该供应商</div>
            <div class="nv__switch-sub">修正上方问题后可保存并立即启用</div>
          </div>
          <el-switch v-model="form.enabled" data-testid="new-enabled" />
        </div>

        <p class="nv__notice" data-testid="new-no-api-note">{{ NO_CREATE_API_NOTICE }}</p>
      </div>

      <template #footer>
        <div class="nv__footer">
          <span v-if="errorCount > 0" class="nv__footer-hint" data-testid="new-footer-hint">{{ vendorFooterHint(errors) }}</span>
          <span class="pv__spacer" />
          <el-button data-testid="new-cancel" @click="newOpen = false">取消</el-button>
          <el-button data-testid="new-draft" @click="onDraft">保存草稿</el-button>
          <el-button type="primary" :disabled="errorCount > 0" data-testid="new-save" @click="onSave">保存</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  providerApi, INDUSTRY_CATEGORY, PROVIDER_STATUS, SUSPEND_REASON_MAX,
  type ProviderRow
} from '@/api/admin/providers';
import {
  fmtShortDate, fmtDateTime, completenessTone, completenessText, industryLabel, industryTone,
  statusLabel, statusTone, isSuspended, pageSummary, UNKNOWN, MISSING_ACTIONS_NOTE, CATEGORY_FILTER_NOTE
} from './model';
import {
  emptyVendorForm, validateVendorForm, vendorErrorSummary, vendorFooterHint,
  REGION_OPTIONS, CURRENCY_OPTIONS, CATEGORY_OPTIONS, VENDOR_CODE_HINT,
  NO_CREATE_API_NOTICE, NO_TEST_CONN_API_NOTICE, type VendorForm
} from './form';

const router = useRouter();

const rows = ref<ProviderRow[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loading = ref(false);
const error = ref('');
const filters = reactive({ keyword: '', category: '' as '' | keyof typeof INDUSTRY_CATEGORY, status: '' });

const detailOpen = ref(false);
const detail = ref<ProviderRow | null>(null);

const newOpen = ref(false);
const form = reactive<VendorForm>(emptyVendorForm());
const errors = computed(() => validateVendorForm(form));
const errorCount = computed(() => Object.keys(errors.value).length);

const meterColor = (tone: string) =>
  tone === 'success' ? 'rgba(22,163,74,1)' : tone === 'warn' ? 'rgba(217,119,6,1)' : 'rgba(220,38,38,1)';

/** el-progress 只接受 0–100；后端 completeness 理论上是 0–100，仍夹紧避免脏数据把条画飞 */
const meterPercent = (v: number | null | undefined) =>
  v == null || !Number.isFinite(v) ? 0 : Math.min(100, Math.max(0, Math.round(v)));

/** 类型筛选是前端过滤（后端无该参数），所以对当前页生效 —— 见 CATEGORY_FILTER_NOTE */
const visibleRows = computed(() =>
  filters.category ? rows.value.filter((r) => r.industry_category === filters.category) : rows.value
);

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const r = await providerApi.list({
      page: page.value,
      pageSize,
      status: filters.status || undefined,
      keyword: filters.keyword.trim() || undefined
    });
    rows.value = r?.items ?? [];
    total.value = r?.total ?? rows.value.length;
  } catch (e) {
    error.value = (e as Error).message;
    rows.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function onQuery() {
  page.value = 1;
  return load();
}

function onReset() {
  filters.keyword = '';
  filters.category = '';
  filters.status = '';
  page.value = 1;
  return load();
}

function openDetail(row: ProviderRow) {
  detail.value = row;
  detailOpen.value = true;
}

function goQuotes() {
  router.push('/reviews');
}

async function onSuspend(row: ProviderRow) {
  let reason = '';
  try {
    const r = await ElMessageBox.prompt(
      `暂停后该供应商不可继续接单（原因 2–${SUSPEND_REASON_MAX} 字，必填）。`,
      `停用「${row.company_name || row.provider_code || row.id}」`,
      { inputPlaceholder: '请填写暂停原因', inputValidator: (v: string) => (v && v.trim().length >= 2) || '暂停原因至少 2 个字' }
    );
    reason = (r.value || '').trim();
  } catch {
    return;
  }
  try {
    await providerApi.suspend(row.id, reason);
    ElMessage.success('已暂停');
    await load();
  } catch (e) {
    // E-1601 = 状态非法（如已是暂停态）→ 原样透传服务端 message
    ElMessage.error((e as Error).message);
  }
}

async function onResume(row: ProviderRow) {
  try {
    await ElMessageBox.confirm('恢复后回到暂停前状态，确认继续？', '确认恢复', { type: 'warning' });
  } catch {
    return;
  }
  try {
    await providerApi.resume(row.id);
    ElMessage.success('已恢复');
    await load();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

function openNew() {
  Object.assign(form, emptyVendorForm());
  newOpen.value = true;
}

function onTestConn() {
  ElMessage.info(NO_TEST_CONN_API_NOTICE);
}

function onDraft() {
  ElMessage.info(NO_CREATE_API_NOTICE);
}

function onSave() {
  // 校验通过才允许点，但仍无接口 —— 必须明确「没发请求」，不得假装成功
  ElMessage.warning(NO_CREATE_API_NOTICE);
}

onMounted(load);
defineExpose({ load, visibleRows });
</script>

<style scoped>
.pv { display: flex; flex-direction: column; gap: 16px; }
.pv__bar { display: flex; align-items: center; gap: 10px; padding: 14px 16px; flex-wrap: wrap; }
.pv__count { font-size: var(--fs-md); color: var(--c-text-sub); }
.pv__spacer { flex: 1; }
.pv__name { font-size: var(--fs-md); color: var(--c-text); font-weight: 500; }
.pv__uscc { font-size: var(--fs-sm); color: var(--c-text-muted); margin-top: 3px; }
.pv__todo { font-size: var(--fs-base); color: var(--c-text-muted); }
.pv__meter { display: flex; align-items: center; gap: 8px; }
.pv__meter-bar { flex: 1; min-width: 60px; }
.pv__meter-text { font-size: var(--fs-sm); color: var(--c-text-sub); width: 34px; text-align: right; }
.pv__act { margin-left: 10px; }
.pv__foot { display: flex; align-items: center; gap: 10px; padding-top: 14px; }
.pv__summary { font-size: var(--fs-base); color: var(--c-text-muted); }
.pv__note { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 10px 0 0; line-height: 1.7; }
.pv__err { color: var(--c-danger); font-size: var(--fs-base); margin: 10px 0 0; }
.pv__sub { font-size: var(--fs-md); font-weight: 600; margin: 16px 0 8px; }

/* ── 新增抽屉（page-4-1） ───────────────────────────── */
.nv { display: flex; flex-direction: column; gap: 14px; }
.nv__summary {
  background: var(--c-danger-soft); color: var(--c-danger);
  border-radius: var(--r-md); padding: 12px 14px; font-size: var(--fs-base);
}
.nv__group { display: flex; align-items: center; gap: 8px; font-size: var(--fs-md); font-weight: 600; margin-top: 4px; }
.nv__bar { width: 4px; height: 14px; border-radius: 2px; background: var(--c-primary); }
.nv__field { display: flex; flex-direction: column; gap: 6px; }
.nv__label { font-size: var(--fs-base); color: var(--c-text-body); }
.nv__label em { color: var(--c-danger); font-style: normal; margin-left: 2px; }
.nv__hint { font-size: var(--fs-sm); color: var(--c-text-muted); margin-left: 8px; }
.nv__hint-block { font-size: var(--fs-sm); color: var(--c-text-muted); line-height: 1.6; margin: 0; }
.nv__error { font-size: var(--fs-sm); color: var(--c-danger); margin: 0; }
.nv__row { display: flex; gap: 10px; }
.nv__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.nv__chips { display: flex; gap: 8px; flex-wrap: wrap; }
.nv__chip {
  height: 32px; padding: 0 12px; border-radius: var(--r-lg);
  border: 1px solid var(--c-border); background: var(--c-surface);
  color: var(--c-text-body); font-size: var(--fs-base); cursor: pointer;
}
.nv__chip--on { background: var(--c-primary-soft); border-color: var(--c-primary); color: var(--c-primary); }
.nv__switch-row {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--c-surface-alt); border-radius: var(--r-lg); padding: 12px 14px;
}
.nv__switch-title { font-size: var(--fs-md); }
.nv__switch-sub { font-size: var(--fs-sm); color: var(--c-text-muted); margin-top: 3px; }
.nv__notice {
  font-size: var(--fs-sm); color: var(--c-warn-strong); background: var(--c-warn-soft);
  border-radius: var(--r-md); padding: 10px 12px; line-height: 1.7; margin: 0;
}
.nv__footer { display: flex; align-items: center; gap: 10px; }
.nv__footer-hint { font-size: var(--fs-base); color: var(--c-danger); }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
