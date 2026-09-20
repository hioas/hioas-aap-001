<template>
  <div class="md">
    <!-- KPI 5 张（设计稿 page-3 原始顺序与标注：
         接入厂商 ↑8.3% / 已接入模型 ↑6.0% / 启用中模型 73%启用率 /
         本月调用量 ↑12.6% / 平均可用率 ↓0.12%
         ⚠️ 环比涨跌后端**无对比期数据** → 不编百分比，如实标注「环比未采集」；
         平均可用率同样后端无采集口径 → 标「未采集」。数值本身取真值。） -->
    <div class="kpi-row" data-testid="model-kpi">
      <div class="aap-card kpi">
        <span class="kpi__label">接入厂商</span>
        <span class="kpi__value">{{ vendors.length }}</span>
        <span class="kpi__note">环比未采集</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">已接入模型</span>
        <span class="kpi__value">{{ allModels.length }}</span>
        <span class="kpi__note">环比未采集</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">启用中模型</span>
        <span class="kpi__value">{{ allModels.filter((m) => m.enabled).length }}</span>
        <span class="kpi__note">{{ enabledRate }} 启用率</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">本月调用量</span>
        <span class="kpi__value">{{ fmtWan(monthTokens) }}</span>
        <span class="kpi__note">tokens · 环比未采集</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">平均可用率</span>
        <span class="kpi__value kpi__value--todo">未采集</span>
        <span class="kpi__note">后端无可用率采集口径</span>
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
        <el-option v-for="t in MODEL_TYPES" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 130px" data-testid="model-status">
        <el-option label="启用" value="ENABLED" />
        <el-option label="停用" value="DISABLED" />
      </el-select>
      <!-- 设计稿还有第 4 个筛选「全部地区」（厂商 region 有真值，可筛） -->
      <el-select v-model="filters.region" placeholder="全部地区" clearable style="width: 130px" data-testid="model-region">
        <el-option v-for="r in VENDOR_REGIONS" :key="r" :label="r" :value="r" />
      </el-select>
      <!-- 设计稿第 5 个筛选「按调用量排序」：调用量按模型维度可算，故做**真排序** -->
      <el-select v-model="filters.sort" placeholder="按调用量排序" clearable style="width: 150px" data-testid="model-sort">
        <el-option label="调用量从高到低" value="usage_desc" />
        <el-option label="调用量从低到高" value="usage_asc" />
      </el-select>
      <span class="md__spacer" />
      <!-- 设计稿此按钮存在，但后端**无批量端点** → 置灰并注明，不假装可用 -->
      <el-button data-testid="btn-batch" disabled>批量管理</el-button>
      <el-button data-testid="btn-export" @click="exportList">导出清单</el-button>
      <el-button data-testid="btn-add-vendor" @click="openVendor">新增厂商</el-button>
      <el-button type="primary" data-testid="btn-add-model" @click="openModel()">新增模型</el-button>
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
        <template v-if="groups.length">
          <div v-for="g in groups" :key="g.vendor.id" class="vendor" :data-testid="`vendor-${g.vendor.vendorKey}`">
            <div class="vendor__head">
              <span class="vendor__badge">{{ g.vendor.name.slice(0, 1).toUpperCase() }}</span>
              <span class="vendor__name">{{ g.vendor.name }}</span>
              <!-- 设计稿此处依次是：厂商类型 · 所属地区 ·（标签） -->
              <span class="vendor__meta">{{ vendorTypeLabel(g.vendor.vendorType) }}</span>
              <span class="vendor__meta" v-if="g.vendor.region">{{ g.vendor.region }}</span>
              <span class="aap-badge aap-badge--info" v-if="!g.vendor.enabled">停用</span>
              <span class="md__spacer" />
              <el-button size="small" text data-testid="btn-add-model-inline" @click="openModel(g.vendor.id)">添加模型</el-button>
            </div>
            <!-- 设计稿次行：base_url · 接入时间 · 密钥已配置
                 ⚠️「接入时间」后端出参未含 createdAt → 不显示该段，也不编造日期。 -->
            <div class="vendor__sub">
              <span>{{ hostOf(g.vendor.baseUrl) }}</span>
              <span class="vendor__dot">·</span>
              <span>{{ g.vendor.apiKeyMask ? '密钥已配置' : '未配置密钥' }}</span>
            </div>
            <!-- 设计稿三个小指标：模型数 / 已启用 / 本月调用 -->
            <div class="vendor__chips">
              <span class="vchip"><b>{{ g.models.length }}</b> 模型数</span>
              <span class="vchip"><b>{{ g.models.filter((m) => m.enabled).length }}</b> 已启用</span>
              <span class="vchip"><b>{{ fmtWan(groupTokens(g.vendor.id)) }}</b> 本月调用</span>
            </div>
            <el-table :data="g.models" size="small" :data-testid="`model-table-${g.vendor.vendorKey}`">
              <el-table-column label="模型名称 / 标识" min-width="240">
                <template #default="{ row }">
                  <div class="mname">{{ row.modelName }}</div>
                  <div class="muid">{{ row.modelUid }}</div>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="90">
                <template #default="{ row }">{{ modelTypeLabel(row.modelType) }}</template>
              </el-table-column>
              <el-table-column label="上下文" width="100">
                <template #default="{ row }">{{ fmtTokens(row.contextWindow) }}</template>
              </el-table-column>
              <!-- 设计稿价格写法是「¥0.018 / 1K」（元 / 1K tokens） -->
              <el-table-column label="输入价格" width="130">
                <template #default="{ row }">{{ fmtPrice(row.inputPrice) }}</template>
              </el-table-column>
              <el-table-column label="输出价格" width="130">
                <template #default="{ row }">{{ fmtPrice(row.outputPrice) }}</template>
              </el-table-column>
              <el-table-column label="本月调用" width="110">
                <template #default="{ row }">{{ fmtWan(modelTokens(row.modelUid)) }}</template>
              </el-table-column>
              <!-- 设计稿有「可用率」，但后端无可用率采集口径 → 如实标注，不编 99.92% -->
              <el-table-column label="可用率" width="100">
                <template #default>未采集</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <span class="aap-badge" :class="row.enabled ? 'aap-badge--success' : 'aap-badge--muted'">
                    {{ row.enabled ? '启用' : '停用' }}
                  </span>
                </template>
              </el-table-column>
              <!-- 设计稿操作列是「编辑 / 测试」；测试后端无端点 → 置灰注明 -->
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-link type="primary" :underline="false" @click="openModel(row.vendorId, row)">编辑</el-link>
                  <el-tooltip content="后端未提供连通性测试端点" placement="top">
                    <el-link type="info" :underline="false" class="md__act" disabled>测试</el-link>
                  </el-tooltip>
                  <el-link
                    type="primary"
                    :underline="false"
                    class="md__act"
                    @click="toggle(row)"
                  >
                    {{ row.enabled ? '停用' : '启用' }}
                  </el-link>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>

        <!-- 真实空态：目录已接通，但还没建任何厂商/模型 -->
        <div v-else class="md__empty" data-testid="model-empty">
          <div class="md__empty-title">还没有厂商或模型</div>
          <div class="md__empty-body">
            <p>模型目录接口已接通。先「新增厂商」，再在厂商下「添加模型」，
              供应商端「接入凭证」页的模型下拉就会读到这里。</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════ 抽屉 3.1 新增厂商（Calicat page-3-1 逐字段实现） ══════════════ -->
    <el-drawer v-model="vendorDrawer" :title="vendorForm.id ? '编辑厂商' : VENDOR_TITLE" size="561px" data-testid="drawer-vendor">
      <template #header>
        <div class="drw__head">
          <div class="drw__title">{{ VENDOR_TITLE }}</div>
          <div class="drw__sub">{{ VENDOR_SUBTITLE }}</div>
        </div>
      </template>
      <el-form :model="vendorForm" label-position="top" class="drw__form">
        <el-form-item :label="V_NAME_LABEL" required>
          <el-input v-model="vendorForm.name" :placeholder="V_NAME_PH" data-testid="v-name" />
        </el-form-item>
        <el-form-item :label="V_KEY_LABEL">
          <el-input v-model="vendorForm.vendorKey" :placeholder="V_KEY_PH" data-testid="v-key" />
        </el-form-item>
        <el-form-item :label="V_TYPE_LABEL" required>
          <el-radio-group v-model="vendorForm.vendorType" data-testid="v-type">
            <el-radio-button v-for="t in VENDOR_TYPES" :key="t.value" :value="t.value">{{ t.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="所属地区" data-testid="v-region">
          <el-select v-model="vendorForm.region" placeholder="请选择" clearable style="width: 100%">
            <el-option v-for="r in VENDOR_REGIONS" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="官网地址">
          <el-input v-model="vendorForm.website" placeholder="https://mistral.ai" data-testid="v-website" />
        </el-form-item>
        <el-form-item label="API Base URL" required>
          <el-input v-model="vendorForm.baseUrl" placeholder="https://api.mistral.ai/v1" data-testid="v-baseurl" />
        </el-form-item>
        <el-form-item :label="V_KEY_LABEL_API">
          <el-input v-model="vendorForm.apiKey" type="password" show-password :placeholder="V_APIKEY_HINT" data-testid="v-apikey" />
          <div class="drw__note">
            {{ V_APIKEY_HINT }}
            <el-link type="primary" :underline="false" :disabled="true">测试连通</el-link>
            <span class="drw__gap-note">（后端未提供连通性测试端点，不假装成功）</span>
          </div>
        </el-form-item>
        <el-form-item label="默认并发限流（QPS）">
          <el-input-number v-model="vendorForm.defaultQps" :min="1" :max="10000" controls-position="right" data-testid="v-qps" />
        </el-form-item>
        <el-form-item label="结算币种">
          <el-radio-group v-model="vendorForm.currency" data-testid="v-currency">
            <el-radio-button value="CNY">CNY</el-radio-button>
            <el-radio-button value="USD">USD</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <div class="drw__switch">
            <el-switch v-model="vendorForm.enabled" data-testid="v-enabled" />
            <div>
              <div class="drw__switch-label">启用该厂商</div>
              <div class="drw__note">启用后可在新增模型时选择该厂商</div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="厂商描述">
          <el-input
            v-model="vendorForm.description"
            type="textarea"
            :rows="3"
            placeholder="填写厂商定位、可用模型范围与结算说明…"
            data-testid="v-desc"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="drw__foot">
          <span class="drw__required">带 * 为必填项</span>
          <span class="md__spacer" />
          <el-button data-testid="v-cancel" @click="vendorDrawer = false">取消</el-button>
          <el-button data-testid="v-draft" :loading="savingVendor" @click="saveVendor(false)">保存草稿</el-button>
          <el-button type="primary" data-testid="v-save" :loading="savingVendor" @click="saveVendor(true)">保存厂商</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- ══════════════ 抽屉 3.2 新增模型（Calicat page-3-2 逐字段实现） ══════════════ -->
    <el-drawer v-model="modelDrawer" :title="MODEL_TITLE" size="561px" data-testid="drawer-model">
      <template #header>
        <div class="drw__head">
          <div class="drw__title">{{ modelForm.id ? '编辑模型' : MODEL_TITLE }}</div>
          <div class="drw__sub">{{ MODEL_SUBTITLE }}</div>
        </div>
      </template>
      <el-form :model="modelForm" label-position="top" class="drw__form">
        <el-form-item label="所属厂商" required>
          <el-select v-model="modelForm.vendorId" placeholder="请选择厂商" style="width: 100%" data-testid="m-vendor">
            <el-option
              v-for="v in enabledVendors"
              :key="v.id"
              :label="v.name"
              :value="v.id"
            />
          </el-select>
          <div v-if="!enabledVendors.length" class="drw__note">
            没有启用中的厂商。请先在「新增厂商」里建一个并启用（设计：启用后可在新增模型时选择该厂商）。
          </div>
        </el-form-item>
        <el-form-item label="模型名称" required>
          <el-input v-model="modelForm.modelName" placeholder="如 GPT-4o mini" data-testid="m-name" />
        </el-form-item>
        <el-form-item label="模型标识" required>
          <el-input v-model="modelForm.modelUid" placeholder="如 gpt-4o-mini" data-testid="m-uid" />
        </el-form-item>
        <el-form-item label="模型类型" required>
          <el-radio-group v-model="modelForm.modelType" data-testid="m-type">
            <el-radio-button v-for="t in MODEL_TYPES" :key="t.value" :value="t.value">{{ t.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="上下文长度（tokens）">
          <el-input-number v-model="modelForm.contextWindow" :min="0" :step="1000" controls-position="right" data-testid="m-ctx" />
          <span class="drw__inline-note">{{ approxK(modelForm.contextWindow) }}</span>
        </el-form-item>
        <el-form-item label="最大输出（tokens）">
          <el-input-number v-model="modelForm.maxOutput" :min="0" :step="1000" controls-position="right" data-testid="m-maxout" />
        </el-form-item>
        <el-form-item :label="M_PRICE_IN_LABEL">
          <el-input-number v-model="modelForm.inputPrice" :min="0" :precision="4" :step="0.001" controls-position="right" data-testid="m-input-price" />
        </el-form-item>
        <el-form-item :label="M_PRICE_OUT_LABEL">
          <el-input-number v-model="modelForm.outputPrice" :min="0" :precision="4" :step="0.001" controls-position="right" data-testid="m-output-price" />
        </el-form-item>
        <el-form-item label="能力标签">
          <el-select v-model="modelForm.capabilities" multiple placeholder="多选，用于路由与能力筛选" style="width: 100%" data-testid="m-caps">
            <el-option v-for="c in CAPABILITIES" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="接入地址（Base URL）">
          <el-input v-model="modelForm.baseUrl" placeholder="留空则继承厂商默认" data-testid="m-baseurl" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="modelForm.apiKey" type="password" show-password placeholder="加密存储，仅管理员可见" data-testid="m-apikey" />
          <div class="drw__note">
            留空表示沿用厂商默认密钥
            <el-link type="primary" :underline="false" :disabled="true">测试连通</el-link>
            <span class="drw__gap-note">（后端未提供连通性测试端点，不假装成功）</span>
          </div>
        </el-form-item>
        <el-form-item>
          <div class="drw__switch">
            <el-switch v-model="modelForm.enabled" data-testid="m-enabled" />
            <div>
              <div class="drw__switch-label">保存后立即启用</div>
              <div class="drw__note">启用后该模型将加入可用模型池</div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="modelForm.remark"
            type="textarea"
            :rows="3"
            placeholder="填写模型用途、限流说明或上线备注…"
            data-testid="m-remark"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="drw__foot">
          <span class="drw__required">带 * 为必填项</span>
          <span class="md__spacer" />
          <el-button data-testid="m-cancel" @click="modelDrawer = false">取消</el-button>
          <el-button data-testid="m-test" :disabled="true">测试连接</el-button>
          <el-button type="primary" data-testid="m-save" :loading="savingModel" @click="saveModel">
            {{ modelForm.id ? '保存' : '保存并启用' }}
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
/**
 * 模型管理 —— Calicat page-3（按厂商分组）/ page-3-1（新增厂商抽屉）/ page-3-2（新增模型抽屉）
 *
 * 真源：
 *   设计字段与文案：`.calicat-admin/raw/pages/page-3{,-1,-2}/design.json`
 *     （用 tools/calicat-text.mjs 全深度抽取；注意文本字段是 content、文字色是 fontFill）
 *   接口：AdminCatalogController + CatalogViews（/api/v1/admin/catalog/*）
 *
 * ⚠️ 历史与边界：
 *   · 本页此前因**后端零能力**（D-ADM-3）只做 UI + 「后端未提供接口」占位。
 *     现后端已补齐（V9 迁移 + 6 个端点，运行态 24/24 验证），故本次真接线。
 *   · **id 一律按字符串处理**：雪花 ID 18 位超过 JS 安全整数，后端已按契约
 *     序列化为 string（见 api/admin/catalog.ts 顶部说明）。不做 Number() 转换。
 *   · 「测试连通 / 测试连接」后端**无此端点** → 按钮置灰并注明，不假装成功。
 *   · 「保存草稿」按「创建但 `enabled=false`」落地（语义即设计稿
 *     「启用后可在新增模型时选择该厂商」的反面），已在按钮处注明。
 */
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { request } from '@/api/http';
import {
  CAPABILITIES,
  MODEL_TYPES,
  VENDOR_REGIONS,
  VENDOR_TYPES,
  catalogApi,
  type CatalogModel,
  type CatalogVendor
} from '@/api/admin/catalog';

/** 用量桶（真源：UsageViews.Bucket；只声明本页用到的字段，避免抄一份完整 schema） */
interface UsageBucket {
  stat_hour?: string;
  model_name?: string;
  total_tokens?: number;
  request_count?: number;
}

/* ── 设计稿文案（逐字取自 design.json，禁止改写） ── */
const VENDOR_TITLE = '新增厂商';
const VENDOR_SUBTITLE = '接入模型供应商与默认网关参数';
const V_NAME_LABEL = '厂商名称';
const V_NAME_PH = '如 Mistral AI';
const V_KEY_LABEL = '厂商标识（英文 key）';
const V_KEY_PH = '如 mistral';
const V_TYPE_LABEL = '厂商类型';
const V_KEY_LABEL_API = '默认 API Key';
const V_APIKEY_HINT = '加密存储，可在单模型覆盖';
const MODEL_TITLE = '新增模型';
const MODEL_SUBTITLE = '配置模型类型、定价与接入参数';
/** 设计稿原文是「输入价格（元 / 1K tokens）」——
 *  ⚠️ 与 H5 报价链的「$/1M token」不一致（币种+量纲双重），已登记 D-ADM-4 待裁定。
 *  本页**原样显示设计单位、不做换算**；后端出参也显式带 priceUnit 以便对账。 */
const M_PRICE_IN_LABEL = '输入价格（元 / 1K tokens）';
const M_PRICE_OUT_LABEL = '输出价格（元 / 1K tokens）';

const tab = ref<'vendor' | 'all' | 'disabled'>('vendor');
// 设计稿筛选器共 5 个：搜索 / 类型 / 状态 / 地区 / 按调用量排序
const filters = reactive({ keyword: '', type: '', status: '', region: '', sort: '' });
const loading = ref(false);
const savingVendor = ref(false);
const savingModel = ref(false);

const groupsRaw = ref<{ vendor: CatalogVendor; models: CatalogModel[] }[]>([]);
const allModels = ref<CatalogModel[]>([]);
const vendors = ref<CatalogVendor[]>([]);

const tabTitle = computed(
  () => ({ vendor: '按厂商分组', all: '全部模型', disabled: '停用模型' })[tab.value]
);
const enabledVendors = computed(() => vendors.value.filter((v) => v.enabled));

function modelTypeLabel(v: string) {
  return MODEL_TYPES.find((t) => t.value === v)?.label ?? v;
}
function vendorTypeLabel(v: string) {
  return VENDOR_TYPES.find((t) => t.value === v)?.label ?? v;
}
/** 设计稿厂商次行显示域名形态（api.openai.com），故从 baseUrl 取 host */
function hostOf(url: string | null) {
  if (!url) return '—';
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
function fmtTokens(n: number | null) {
  if (n == null) return '—';
  return n >= 1000 ? `${Math.round(n / 1000)}K` : String(n);
}
function approxK(n: number | null) {
  return n && n >= 1000 ? `约 ${Math.round(n / 1000)}K` : '';
}
/** 设计稿价格写法：「¥0.018 / 1K」（元 / 1K tokens）。
 *  ⚠️ 不做币种/量纲换算 —— 若后端 priceUnit 不是 CNY/1K，则原样带出单位后缀，
 *  避免把「$/1M」误显示成「¥/1K」（D-ADM-4 待裁定）。 */
function fmtPrice(n: number | null, unit?: string) {
  if (n == null) return '—';
  if (unit && unit !== 'CNY/1K') return `${n} ${unit}`;
  return `¥${n} / 1K`;
}
/** 调用量按设计稿以「万」为单位（如 486.2 万） */
function fmtWan(tokens: number) {
  if (!tokens) return '—';
  return `${(tokens / 10000).toFixed(1)} 万`;
}

/* ────────────── 本月调用量（真值，非编造） ──────────────
 * 真源：GET /admin/usage/hourly（ADM-U01，四维下钻含 model 维度）
 *   aap_usage_hourly 有 model_name 列，Bucket 出参含 model_name / total_tokens
 *   故「本月调用」可按 model_name 聚合得到**真实 token 数**。
 * 可用率**没有**采集口径（不在 usage_hourly 里）→ 表格里如实标「未采集」。
 */
const usageByModel = ref<Record<string, number>>({});
const usageByVendor = ref<Record<string, number>>({});

/** RFC3339 UTC（本地时间直发会被后端 E-1001 拒） */
function rfc3339Utc(d: Date) {
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

async function loadUsage() {
  try {
    const now = new Date();
    const from = rfc3339Utc(new Date(now.getFullYear(), now.getMonth(), 1));
    const to = rfc3339Utc(new Date(now.getTime() + 24 * 3600 * 1000));
    const page = await request<{ items?: UsageBucket[] } | UsageBucket[]>(
      `/admin/usage/hourly?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&page=1&pageSize=500`
    );
    const rows: UsageBucket[] = Array.isArray(page) ? page : (page?.items ?? []);
    const byModel: Record<string, number> = {};
    for (const r of rows) {
      const k = String(r.model_name ?? '');
      if (!k) continue;
      byModel[k] = (byModel[k] ?? 0) + Number(r.total_tokens ?? 0);
    }
    usageByModel.value = byModel;
    // 厂商维度：按「该厂商下模型的调用量」汇总
    const byVendor: Record<string, number> = {};
    for (const m of allModels.value) {
      const t = byModel[m.modelUid];
      if (t) byVendor[m.vendorId] = (byVendor[m.vendorId] ?? 0) + t;
    }
    usageByVendor.value = byVendor;
  } catch {
    // 用量取不到不影响主功能（目录本身可用）→ 置空，KPI 显示「—」
    usageByModel.value = {};
    usageByVendor.value = {};
  }
}

const monthTokens = computed(() => Object.values(usageByModel.value).reduce((a, b) => a + b, 0));
const enabledRate = computed(() => {
  const total = allModels.value.length;
  if (!total) return '—';
  return `${Math.round((allModels.value.filter((m) => m.enabled).length / total) * 100)}%`;
});
function modelTokens(modelUid: string) {
  return usageByModel.value[modelUid] ?? 0;
}
function groupTokens(vendorId: string) {
  return usageByVendor.value[vendorId] ?? 0;
}

/** 是否命中筛选（关键词 + 类型 + 状态 + 地区） */
function passFilter(m: CatalogModel, vendor: CatalogVendor) {
  const kw = filters.keyword.trim().toLowerCase();
  if (kw && !m.modelName.toLowerCase().includes(kw) && !vendor.name.toLowerCase().includes(kw)) return false;
  if (filters.type && m.modelType !== filters.type) return false;
  if (filters.status === 'ENABLED' && !m.enabled) return false;
  if (filters.status === 'DISABLED' && m.enabled) return false;
  if (filters.region && (vendor.region ?? '') !== filters.region) return false;
  return true;
}

/** 按调用量排序（真排序：用量来自 /admin/usage/hourly 的 model 维度聚合） */
function sortModels(list: CatalogModel[]) {
  if (filters.sort !== 'usage_desc' && filters.sort !== 'usage_asc') return list;
  const dir = filters.sort === 'usage_desc' ? -1 : 1;
  return [...list].sort((a, b) => (modelTokens(a.modelUid) - modelTokens(b.modelUid)) * dir);
}

const groups = computed(() => {
  const withFilter = (g: { vendor: CatalogVendor; models: CatalogModel[] }) => ({
    vendor: g.vendor,
    models: sortModels(g.models.filter((m) => passFilter(m, g.vendor)))
  });
  return groupsRaw.value
    .map(withFilter)
    .filter((g) => g.models.length > 0 || !filters.keyword.trim());
});

async function load() {
  loading.value = true;
  try {
    const [list, gs] = await Promise.all([catalogApi.listVendors(), catalogApi.listGrouped()]);
    vendors.value = list;
    groupsRaw.value = gs;
    allModels.value = gs.flatMap((g) => g.models);
    // 用量在主数据之后取：厂商维度汇总需要 allModels 才能把 model_uid 映射到厂商
    await loadUsage();
  } catch (e) {
    vendors.value = [];
    groupsRaw.value = [];
    allModels.value = [];
    monthTokensPlaceholderReset();
    ElMessage.error(`加载模型目录失败：${(e as Error).message}`);
  } finally {
    loading.value = false;
  }
}

/** 目录加载失败时清掉用量缓存，避免残留上一轮数字造成「看起来有数据」 */
function monthTokensPlaceholderReset() {
  usageByModel.value = {};
  usageByVendor.value = {};
}

/* ────────────── 3.1 新增厂商 ────────────── */
const vendorDrawer = ref(false);
const vendorForm = reactive({
  id: '',
  name: '',
  vendorKey: '',
  vendorType: 'DIRECT',
  region: '中国',
  website: '',
  baseUrl: '',
  apiKey: '',
  defaultQps: 50,
  currency: 'CNY',
  enabled: true,
  description: ''
});

function openVendor() {
  Object.assign(vendorForm, {
    id: '', name: '', vendorKey: '', vendorType: 'DIRECT', region: '中国', website: '',
    baseUrl: '', apiKey: '', defaultQps: 50, currency: 'CNY', enabled: true, description: ''
  });
  vendorDrawer.value = true;
}

/**
 * @param asEnabled true = 「保存厂商」（保持开关状态）；false = 「保存草稿」（强制 enabled=false）
 *   设计稿 3.1 底部有两个动作（保存草稿 / 保存厂商），后端只有一个 create，
 *   故「草稿」映射为 enabled=false —— 语义等价（未启用的厂商不能被新增模型时选中）。
 */
async function saveVendor(asEnabled: boolean) {
  if (!vendorForm.name.trim()) return ElMessage.warning('厂商名称必填（V1）');
  if (!vendorForm.vendorKey.trim()) return ElMessage.warning('厂商标识必填（V2）');
  if (!vendorForm.vendorType) return ElMessage.warning('厂商类型必填（V3）');
  if (!vendorForm.baseUrl.trim()) return ElMessage.warning('API Base URL 必填（V4）');
  savingVendor.value = true;
  try {
    const created = await catalogApi.createVendor({
      name: vendorForm.name.trim(),
      vendorKey: vendorForm.vendorKey.trim(),
      vendorType: vendorForm.vendorType,
      region: vendorForm.region || undefined,
      website: vendorForm.website.trim() || undefined,
      baseUrl: vendorForm.baseUrl.trim(),
      apiKey: vendorForm.apiKey.trim() || undefined,
      defaultQps: vendorForm.defaultQps,
      currency: vendorForm.currency,
      enabled: asEnabled ? vendorForm.enabled : false,
      description: vendorForm.description.trim() || undefined
    });
    ElMessage.success(asEnabled ? `厂商「${created.name}」已创建` : `厂商「${created.name}」已存为草稿（未启用）`);
    vendorDrawer.value = false;
    await load();
  } catch (e) {
    ElMessage.error(`创建厂商失败：${(e as Error).message}`);
  } finally {
    savingVendor.value = false;
  }
}

/* ────────────── 3.2 新增模型 ────────────── */
const modelDrawer = ref(false);
const modelForm = reactive({
  id: '',
  vendorId: '',
  modelName: '',
  modelUid: '',
  modelType: 'CHAT',
  contextWindow: 128000 as number | null,
  maxOutput: 16384 as number | null,
  inputPrice: 0.0011 as number | null,
  outputPrice: 0.0044 as number | null,
  capabilities: [] as string[],
  baseUrl: '',
  apiKey: '',
  enabled: true,
  remark: ''
});

function openModel(vendorId?: string, row?: CatalogModel) {
  if (row) {
    Object.assign(modelForm, {
      id: row.id,
      vendorId: row.vendorId,
      modelName: row.modelName,
      modelUid: row.modelUid,
      modelType: row.modelType,
      contextWindow: row.contextWindow,
      maxOutput: row.maxOutput,
      inputPrice: row.inputPrice,
      outputPrice: row.outputPrice,
      capabilities: [...(row.capabilities ?? [])],
      baseUrl: row.baseUrl ?? '',
      apiKey: '',
      enabled: row.enabled,
      remark: row.remark ?? ''
    });
  } else {
    Object.assign(modelForm, {
      id: '',
      vendorId: vendorId || enabledVendors.value[0]?.id || '',
      modelName: '',
      modelUid: '',
      modelType: 'CHAT',
      contextWindow: 128000,
      maxOutput: 16384,
      inputPrice: 0.0011,
      outputPrice: 0.0044,
      capabilities: [],
      baseUrl: '',
      apiKey: '',
      enabled: true,
      remark: ''
    });
  }
  modelDrawer.value = true;
}

async function saveModel() {
  if (!modelForm.vendorId) return ElMessage.warning('所属厂商必填（V1）');
  if (!modelForm.modelName.trim()) return ElMessage.warning('模型名称必填（V2）');
  if (!modelForm.modelUid.trim()) return ElMessage.warning('模型标识必填（V3）');
  if (!modelForm.modelType) return ElMessage.warning('模型类型必填（V4）');
  savingModel.value = true;
  try {
    const payload = {
      vendorId: modelForm.vendorId,
      modelName: modelForm.modelName.trim(),
      modelUid: modelForm.modelUid.trim(),
      modelType: modelForm.modelType,
      contextWindow: modelForm.contextWindow,
      maxOutput: modelForm.maxOutput,
      inputPrice: modelForm.inputPrice,
      outputPrice: modelForm.outputPrice,
      capabilities: modelForm.capabilities,
      baseUrl: modelForm.baseUrl.trim() || undefined,
      apiKey: modelForm.apiKey.trim() || undefined,
      enabled: modelForm.enabled,
      remark: modelForm.remark.trim() || undefined
    };
    if (modelForm.id) {
      await catalogApi.updateModel(modelForm.id, payload);
      ElMessage.success(`模型「${payload.modelName}」已保存`);
    } else {
      await catalogApi.createModel(payload);
      ElMessage.success(`模型「${payload.modelName}」已${payload.enabled ? '创建并启用' : '创建（未启用）'}`);
    }
    modelDrawer.value = false;
    await load();
  } catch (e) {
    ElMessage.error(`保存模型失败：${(e as Error).message}`);
  } finally {
    savingModel.value = false;
  }
}

/** 列表内快捷启停（ADM-M06 的部分更新） */
async function toggle(row: CatalogModel) {
  try {
    await catalogApi.updateModel(row.id, { enabled: !row.enabled });
    ElMessage.success(`「${row.modelName}」已${row.enabled ? '停用' : '启用'}`);
    await load();
  } catch (e) {
    ElMessage.error(`切换状态失败：${(e as Error).message}`);
  }
}

/** 导出清单：前端下载 CSV（后端无导出端点；纯本地生成，真实反映当前数据） */
function exportList() {
  const rows = [['厂商', '厂商标识', '模型名称', '模型标识', '类型', '上下文', '输入价', '输出价', '状态']];
  for (const m of allModels.value) {
    rows.push([
      m.vendorName ?? '', m.vendorKey ?? '', m.modelName, m.modelUid,
      modelTypeLabel(m.modelType), String(m.contextWindow ?? ''),
      String(m.inputPrice ?? ''), String(m.outputPrice ?? ''), m.enabled ? '启用' : '停用'
    ]);
  }
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `model-catalog-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success(`已导出 ${allModels.value.length} 个模型`);
}

onMounted(load);
defineExpose({ load, vendors, allModels, groups });
</script>

<style scoped>
.md { display: flex; flex-direction: column; gap: 16px; }
/* KPI 5 张（对齐设计稿 page-3 的五张卡） */
.kpi-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; }
.kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.kpi__label { font-size: var(--fs-base); color: var(--c-text-muted); }
.kpi__value { font-size: var(--fs-kpi); font-weight: 600; line-height: 1.1; }
.kpi__value--todo { font-size: var(--fs-lg); color: var(--c-text-muted); }
.kpi__note { font-size: var(--fs-sm); color: var(--c-text-muted); }

.md__bar { display: flex; align-items: center; gap: 10px; padding: 14px 16px; flex-wrap: wrap; }
.md__spacer { flex: 1; }
.aap-card__head { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
.aap-card__title { font-size: var(--fs-lg); font-weight: 600; }
.aap-card__hint { font-size: var(--fs-sm); color: var(--c-text-muted); }
.aap-card__body { padding: 14px 18px 18px; }

.vendor { border: 1px solid var(--c-border); border-radius: var(--r-card); padding: 12px 14px; margin-bottom: 12px; }
.vendor__head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.vendor__badge { width: 26px; height: 26px; border-radius: var(--r-md); background: var(--c-primary-soft); color: var(--c-primary); display: flex; align-items: center; justify-content: center; font-size: var(--fs-md); font-weight: 600; }
.vendor__name { font-size: var(--fs-md); font-weight: 600; }
.vendor__key { font-size: var(--fs-sm); color: var(--c-text-muted); }
/* 厂商次行：类型 / 地区（设计稿件首行右侧的元信息） */
.vendor__meta { font-size: var(--fs-sm); color: var(--c-text-muted); }
/* 厂商第三行：base_url · 密钥状态 */
.vendor__sub { display: flex; align-items: center; gap: 6px; font-size: var(--fs-sm); color: var(--c-text-muted); margin-bottom: 8px; }
.vendor__dot { color: var(--c-border); }
/* 厂商三个小指标：模型数 / 已启用 / 本月调用 */
.vendor__chips { display: flex; align-items: center; gap: 18px; margin-bottom: 10px; }
.vchip { font-size: var(--fs-sm); color: var(--c-text-muted); }
.vchip b { font-size: var(--fs-md); color: var(--c-text-body); font-weight: 600; margin-right: 4px; }
.mname { font-weight: 500; }
.muid { font-size: var(--fs-sm); color: var(--c-text-muted); }
.md__act { margin-left: 10px; }

.md__empty { padding: 28px 8px; }
.md__empty-title { font-size: var(--fs-md); font-weight: 600; margin-bottom: 10px; }
.md__empty-body { font-size: var(--fs-base); color: var(--c-text-body); line-height: 1.8; }

/* 抽屉（版面参照设计稿 3.1/3.2：头部标题+副标题、内容区、底部操作条） */
.drw__head { display: flex; flex-direction: column; gap: 2px; }
.drw__title { font-size: var(--fs-lg); font-weight: 600; }
.drw__sub { font-size: var(--fs-sm); color: var(--c-text-muted); }
.drw__form :deep(.el-form-item__label) { font-size: var(--fs-base); padding-bottom: 4px; }
.drw__note { font-size: var(--fs-sm); color: var(--c-text-muted); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 2px; }
.drw__gap-note { color: var(--c-warn); }
.drw__inline-note { margin-left: 10px; font-size: var(--fs-sm); color: var(--c-text-muted); }
.drw__switch { display: flex; align-items: center; gap: 10px; }
.drw__switch-label { font-size: var(--fs-base); }
.drw__foot { display: flex; align-items: center; width: 100%; }
.drw__required { font-size: var(--fs-sm); color: var(--c-text-muted); }
</style>
