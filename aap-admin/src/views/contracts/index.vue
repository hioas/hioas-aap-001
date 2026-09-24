<template>
  <div class="ct">
    <!-- KPI 3 张（设计稿：待签署合同 / 本月采购金额 / 待打款 / 本月已结算） -->
    <div class="kpi-row" data-testid="contract-kpi">
      <div class="aap-card kpi">
        <span class="kpi__label">待签署合同</span>
        <span class="kpi__value">{{ kpi.pendingSign === null ? '—' : kpi.pendingSign }}</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">本月采购金额</span>
        <span class="kpi__value">{{ money(kpi.monthAmount) }}</span>
        <span class="kpi__note">按结算台账 total_amount 汇总</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">待打款</span>
        <span class="kpi__value kpi__value--warn">{{ money(kpi.pendingPay) }}</span>
      </div>
      <div class="aap-card kpi">
        <span class="kpi__label">本月已结算</span>
        <span class="kpi__value kpi__value--ok">{{ money(kpi.settled) }}</span>
      </div>
    </div>

    <!-- 筛选区（PRD 13 §3：条件写 URL query） -->
    <div class="aap-card ct__filter">
      <el-input v-model="filters.keyword" placeholder="搜索合同编号 / 供应商" clearable style="width: 240px" data-testid="filter-keyword" />
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px" data-testid="filter-status">
        <el-option v-for="(v, k) in CONTRACT_STATUS" :key="k" :label="v.label" :value="k" />
      </el-select>
      <el-button type="primary" data-testid="btn-query" @click="loadAll">查询</el-button>
      <el-button :loading="loading" data-testid="btn-refresh" @click="loadAll">刷新</el-button>
      <span class="ct__spacer" />
      <el-button data-testid="btn-export" @click="onExport">导出对账</el-button>
    </div>

    <!-- 台账表（设计稿列：合同编号/供应商/合作模式/状态/签约日期/本期结算额/操作） -->
    <div class="aap-card">
      <div class="aap-card__head">
        <span class="aap-card__title">合同与结算台账</span>
        <span v-if="pendingPayCount" class="aap-badge aap-badge--warn">{{ pendingPayCount }} 笔待打款</span>
      </div>
      <div class="aap-card__body">
        <el-table :data="rows" size="small" data-testid="contract-table" empty-text="暂无合同">
          <el-table-column prop="contract_no" label="合同编号" min-width="170" />
          <el-table-column label="供应商" min-width="160">
            <template #default="{ row }">{{ row.supplier_name || '—' }}</template>
          </el-table-column>
          <el-table-column label="合作模式" width="110">
            <template #default="{ row }">{{ row.cooperation_mode || '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <span class="aap-badge" :class="`aap-badge--${ctTone(row.status)}`">{{ ctLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="签约日期" width="130">
            <template #default="{ row }">{{ fmt(row.signed_at) }}</template>
          </el-table-column>
          <el-table-column label="本期结算额" width="130">
            <template #default="{ row }">
              <!-- 后端 Contract 视图没有「本期结算额」字段（它在 Statement 上）→ 显式标注，不编造 -->
              <span class="ct__todo" :title="`合同 ${row.contract_no} 的结算额需查结算台账`">
                {{ amountOf(row.id) ?? '见结算台账' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-link type="primary" :underline="false" data-testid="act-view" @click="openDetail(row)">查看</el-link>
              <el-link
                v-if="canWrite"
                type="primary"
                :underline="false"
                class="ct__act"
                data-testid="act-issue"
                @click="onIssue(row)"
              >
                发起
              </el-link>
              <el-link
                v-if="canWrite && isSignedPending(row)"
                type="warning"
                :underline="false"
                class="ct__act"
                data-testid="act-confirm-sign"
                @click="onConfirmSign(row)"
              >
                签署确认
              </el-link>
              <el-link
                v-if="canWrite && isRecordable(row)"
                type="success"
                :underline="false"
                class="ct__act"
                data-testid="act-record-pay"
                @click="openRecord(row)"
              >
                记录打款
              </el-link>
            </template>
          </el-table-column>
        </el-table>
        <p v-if="error" class="ct__err" data-testid="page-error">{{ error }}</p>
      </div>
    </div>

    <!-- 本月结算明细 + 待打款批次（设计稿右栏两块） -->
    <div class="row-2">
      <div class="aap-card">
        <div class="aap-card__head">
          <span class="aap-card__title">结算台账明细</span>
          <span class="ct__spacer" />
          <el-button size="small" :disabled="!canWrite" data-testid="btn-gen-statement" @click="openGenerate">
            生成结算单
          </el-button>
        </div>
        <div class="aap-card__body">
          <el-table :data="statements" size="small" data-testid="statement-table" empty-text="暂无结算台账">
            <el-table-column prop="statement_no" label="结算单号" min-width="150" />
            <el-table-column label="周期" min-width="170">
              <template #default="{ row }">{{ fmt(row.period_from) }} ~ {{ fmt(row.period_to) }}</template>
            </el-table-column>
            <el-table-column label="调用费用合计" width="130">
              <template #default="{ row }">{{ money(row.total_amount) }}</template>
            </el-table-column>
            <el-table-column label="平台服务费" width="120">
              <template #default="{ row }">{{ money(row.platform_fee) }}</template>
            </el-table-column>
            <el-table-column label="净额" width="110">
              <template #default="{ row }">{{ money(stNet(row)) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <span class="aap-badge" :class="`aap-badge--${stTone(row.status)}`">{{ stLabel(row.status) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-link
                  type="primary"
                  :underline="false"
                  :data-testid="`act-statement-detail-${row.id}`"
                  @click="openStatement(row)"
                >
                  明细
                </el-link>
                <el-link
                  v-if="canWrite && row.status === 'DRAFT'"
                  type="primary"
                  :underline="false"
                  :data-testid="`act-confirm-statement-${row.id}`"
                  @click="onConfirmStatement(row)"
                >
                  确认出账
                </el-link>
                <el-link
                  v-if="canWrite && row.status === 'DRAFT'"
                  type="danger"
                  :underline="false"
                  :data-testid="`act-void-statement-${row.id}`"
                  @click="onVoidStatement(row)"
                >
                  作废
                </el-link>
              </template>
            </el-table-column>
          </el-table>
          <!-- 口径出处：`.agents/state/aap-decisions.md` D-SETTLE-02（2026-09-24 自主拍板并实现）。
               此前这段文案写的是「系统当前不生成结算单」——写实现后已过时，UI 不能继续这么讲。 -->
          <p v-if="!statements.length" class="ct__note" data-testid="statement-gap">
            结算台账为空 = <b>该筛选范围内还没有结算单</b>：点右上角<b>「生成结算单」</b>按供应商 + 月份出账。
            <br />
            出账口径（<b>D-SETTLE-02</b>）：①周期 = <b>自然月（UTC）</b>，与用量窗口 <code>YYYY-MM</code> 同口径
            ②金额基数 = 用量 <code>cost_usd</code> 合计 ③平台费 = 合同 <code>platform_fee_rate</code> × 基数
            ④明细维度 = <b>渠道 × 模型</b> ⑤门槛 = 合同 <code>min_settlement_amount</code>（不足不出账）。
            三项口径在服务端 <code>app.settlement.*</code> 可配，口径变化不需要改代码。
            <br />
            <b>不出空单</b>：周期内无用量 → 返回 409 <code>E-1601</code>，不生成 0 元单（0 会冒充「有数据」）。
            确认出账（<code>CONFIRMED</code>）为终态；草稿可作废后重算，历史单保留可追溯。
            <br />
            资金仍走线下对公（PRD 10 R-42「不做资金流转」）—— 结算单是<b>对账凭证</b>，不是支付动作。
          </p>
        </div>
      </div>

      <div class="aap-card">
        <div class="aap-card__head">
          <span class="aap-card__title">待打款批次</span>
          <span class="ct__spacer" />
          <el-button size="small" :disabled="!canWrite || !pendingPayments.length" data-testid="btn-batch-pay" @click="onBatchPay">
            发起批量打款
          </el-button>
        </div>
        <div class="aap-card__body">
          <div v-if="!pendingPayments.length" class="ct__empty" data-testid="pay-empty">暂无待打款记录</div>
          <div v-for="p in pendingPayments" :key="p.id" class="pay-item" :data-testid="`pay-item-${p.id}`">
            <div class="pay-item__left">
              <div class="pay-item__no">{{ p.contract_no || p.id }}</div>
              <div class="pay-item__sub">{{ p.remark || '待补充信息' }}</div>
            </div>
            <div class="pay-item__amt">{{ money(p.amount) }}</div>
            <el-button v-if="canWrite" size="small" data-testid="act-confirm-pay" @click="onConfirmPay(p)">确认打款</el-button>
            <el-button v-if="canWrite && canVoidPay(p)" size="small" text type="danger" data-testid="act-void-pay" @click="onVoidPay(p)">
              作废
            </el-button>
          </div>
          <p class="ct__note">
            PRD 13 §6：「**不做资金流转，仅记录**」—— 此处只更新记录状态，不触发任何转账。
            批量打款按 PRD 允许（与「批量通过」「批量确认写入」不同，后两者被 PRD 明确禁止）。
          </p>
        </div>
      </div>
    </div>

    <!-- 生成结算单（ADM-PAY06，口径 D-SETTLE-02） -->
    <el-dialog v-model="genOpen" title="生成结算单" width="520px">
      <el-form label-width="96px" data-testid="gen-statement-form">
        <el-form-item label="供应商">
          <el-select
            v-model="genForm.provider_id"
            placeholder="选择供应商（需有生效合同）"
            style="width: 100%"
            data-testid="gen-provider"
          >
            <el-option v-for="p in signedProviders" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="出账月份">
          <el-input v-model="genForm.month" placeholder="YYYY-MM" data-testid="gen-month" />
        </el-form-item>
      </el-form>
      <p class="ct__note">
        周期按<b>自然月（UTC）</b>出账（与用量窗口同口径）；金额 = 用量 <code>cost_usd</code> 合计，
        平台费 = 合同 <code>platform_fee_rate</code> × 金额。周期内无用量或低于合同门槛会返回
        <code>E-1601</code> —— <b>不生成 0 元单</b>。
      </p>
      <p v-if="genErr" class="ct__err" data-testid="gen-error">{{ genErr }}</p>
      <template #footer>
        <el-button @click="genOpen = false">取消</el-button>
        <el-button type="primary" :loading="genLoading" data-testid="gen-submit" @click="onGenerate">
          生成
        </el-button>
      </template>
    </el-dialog>

    <!-- 结算单明细（ADM-PAY07） -->
    <el-dialog v-model="stOpen" :title="stDetail?.statement_no || '结算单明细'" width="760px">
      <div v-if="stLoading" class="ct__note">加载中…</div>
      <template v-else-if="stDetail">
        <el-descriptions :column="3" border size="small" data-testid="statement-detail">
          <el-descriptions-item label="供应商">
            {{ stDetail.provider_name || stDetail.provider_id || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="周期">
            {{ fmt(stDetail.period_from) }} ~ {{ fmt(stDetail.period_to) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">{{ stLabel(stDetail.status) }}</el-descriptions-item>
          <el-descriptions-item label="金额合计">{{ money(stDetail.total_amount) }}</el-descriptions-item>
          <el-descriptions-item label="平台费">{{ money(stDetail.platform_fee) }}</el-descriptions-item>
          <el-descriptions-item label="净额">{{ money(stNet(stDetail)) }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="stDetail.lines" size="small" data-testid="statement-lines" empty-text="无明细行">
          <el-table-column prop="channel_id" label="渠道" width="150" />
          <el-table-column prop="model_name" label="模型" min-width="180" />
          <el-table-column label="Tokens" width="130">
            <template #default="{ row }">{{ Number(row.total_tokens ?? 0).toLocaleString('zh-CN') }}</template>
          </el-table-column>
          <el-table-column label="金额" width="120">
            <template #default="{ row }">{{ money(row.amount) }}</template>
          </el-table-column>
        </el-table>
        <p class="ct__note">
          明细按 <b>渠道 × 模型</b> 汇总；已关联打款 {{ stDetail.payments?.length ?? 0 }} 笔
          （打款是资金<b>凭证留痕</b>，与结算金额独立）。资金走线下对公，系统不做资金流转。
        </p>
      </template>
    </el-dialog>

    <!-- 合同详情抽屉 -->
    <el-drawer v-model="detailOpen" :title="detail?.contract_no || '合同详情'" size="620px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" data-testid="contract-detail">
          <el-descriptions-item label="合同编号">{{ detail.contract_no || '—' }}</el-descriptions-item>
          <el-descriptions-item label="关联报价单">{{ detail.quote_no || '—' }}</el-descriptions-item>
          <el-descriptions-item label="供应商">{{ detail.supplier_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="合作模式">{{ detail.cooperation_mode || '—' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <span class="aap-badge" :class="`aap-badge--${ctTone(detail.status)}`">{{ ctLabel(detail.status) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="签署渠道">{{ detail.sign_channel || 'OFFLINE（预留 ONLINE）' }}</el-descriptions-item>
          <el-descriptions-item label="有效期">
            {{ fmt(detail.valid_from) }} ~ {{ fmt(detail.valid_to) }}
          </el-descriptions-item>
          <el-descriptions-item label="平台服务费率">
            {{ detail.platform_fee_rate != null ? `${detail.platform_fee_rate}` : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="签署人">{{ detail.signer_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="签署人手机">{{ detail.signer_phone_masked || '—' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="detail.terms?.length" class="ct__terms">
          <div class="ct__sub">合同条款</div>
          <ol><li v-for="(t, i) in detail.terms" :key="i">{{ t }}</li></ol>
        </div>
        <p class="ct__note">
          合同文本 PDF / 盖章件：文件服务**代码已就绪**（缺陷2 已修，提交 <code>9cf495f</code>：
          <code>POST /files</code> 上传 + <code>GET /files/{id}</code> 下载；⚠️ 当前 dev 实例未重启到该版本，
          实测 <code>POST /files</code> 仍 404 <code>E-1406</code>）→ 当前 <code>file_id</code> 为
          <code>{{ detail.file_id || '空' }}</code>（本单尚未发起带文件的签发）。
          合同专属下载端点 <code>GET /contracts/{id}/file</code> 仅供应商本人可用（CON-03）→
          管理端若要预览需另立「管理端下载」端点或明确权限口径。
        </p>
      </template>
    </el-drawer>

    <!-- 记录打款（ADM-PAY04）：运营线下打款后录入留痕；PRD 10 R-42 只记录不流转 -->
    <el-dialog v-model="recordOpen" title="记录打款（仅留痕，不产生资金流转）" width="520px" data-testid="record-dialog">
      <el-form label-width="92px">
        <el-form-item label="合同">
          <span data-testid="rec-contract">{{ recordTarget?.contract_no || recordTarget?.id }}</span>
          <span class="ct__hint">· 供应商 {{ recordTarget?.supplier_name || recordTarget?.provider_id }}</span>
        </el-form-item>
        <el-form-item label="打款金额">
          <el-input-number v-model="recordForm.amount" :min="0.01" :precision="2" :step="100" data-testid="rec-amount" />
          <span class="ct__hint">币种 {{ recordForm.currency || recordTarget?.currency || '—' }}（须与合同一致，C4）</span>
        </el-form-item>
        <el-form-item label="打款凭证">
          <input type="file" accept="image/*,.pdf" data-testid="rec-voucher" @change="onVoucherPick" />
          <span v-if="recordForm.voucherName" class="ct__hint">已上传：{{ recordForm.voucherName }}</span>
          <span v-else class="ct__hint">凭证截图必填（C5）</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="recordForm.remark" maxlength="255" placeholder="如：对公转账，流水号 …" data-testid="rec-remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-testid="rec-submit" @click="onSubmitRecord">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  contractApi, uploadVoucher, CONTRACT_STATUS, PAYMENT_STATUS, STATEMENT_STATUS,
  type ContractRow, type PaymentRow, type StatementDetail, type StatementRow
} from '@/api/admin/contracts';
import { useSession } from '@/composables/useSession';
import { can, type AdminRole } from '@/config/nav';

const { role } = useSession();
/** 合同写操作仅运营商务+超管（PRD 13 §1）；后端另有二次校验 */
const canWrite = computed(() => can(role.value as AdminRole, 'contract.write'));

const rows = ref<ContractRow[]>([]);
const payments = ref<PaymentRow[]>([]);
const statements = ref<StatementRow[]>([]);
const loading = ref(false);
const error = ref('');
const detailOpen = ref(false);
const detail = ref<ContractRow | null>(null);
// 结算出账对话框
const genOpen = ref(false);
const genErr = ref('');
const genLoading = ref(false);
// 月份默认取**本机 UTC 当月**：后端出账周期就是自然月 UTC，两边必须同一口径
const genForm = reactive({ provider_id: '', month: new Date().toISOString().slice(0, 7) });
// 结算明细对话框
const stOpen = ref(false);
const stLoading = ref(false);
const stDetail = ref<StatementDetail | null>(null);

/** 可出账的供应商：由 SIGNED 合同推导（后端要求生效合同，否则 409 E-1701，两边同口径） */
const signedProviders = computed(() => {
  const seen = new Map<string, string>();
  for (const r of rows.value) {
    if (r.status === 'SIGNED' && r.provider_id) seen.set(r.provider_id, r.supplier_name || r.provider_id);
  }
  return [...seen].map(([id, name]) => ({ id, name }));
});
const filters = reactive({ keyword: '', status: '' });

const ctLabel = (s: string) => CONTRACT_STATUS[s]?.label ?? s;
const ctTone = (s: string) => CONTRACT_STATUS[s]?.tone ?? 'muted';
const payLabel = (s: string) => PAYMENT_STATUS[s]?.label ?? s;
// 结算状态与打款状态是两套状态机，映射不可复用（否则 DRAFT 显示成原始码）
const stLabel = (s: string) => STATEMENT_STATUS[s]?.label ?? s;
const stTone = (s: string) => STATEMENT_STATUS[s]?.tone ?? 'muted';
/** 净额 = 总额 − 平台费；列表视图若没带 net_amount 就按同口径现算（与后端一致） */
const stNet = (r: StatementRow) =>
  r.net_amount ?? Number(r.total_amount ?? 0) - Number(r.platform_fee ?? 0);
const fmt = (s: string | null | undefined) => (s ? String(s).replace('T', ' ').slice(0, 10) : '—');
const money = (v: number | null | undefined) =>
  v == null ? '—' : `¥${Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** 待确认的打款记录：后端四态里的 PAYMENT_RECORDED（旧值 UNSETTLED 一并兼容） */
const pendingPayments = computed(() => payments.value.filter((p) => ['PAYMENT_RECORDED', 'UNSETTLED'].includes(p.status)));
const pendingPayCount = computed(() => payments.value.filter((p) => p.status === 'PAYMENT_RECORDED').length);

/** 合同 ↔ 结算额映射：后端 Contract 视图无「本期结算额」，从 Statement 按 contract_id 找（找不到就显式留白） */
function amountOf(contractId: string): string | null {
  const s = statements.value.find((x) => (x as unknown as { contract_id?: string }).contract_id === contractId);
  return s ? money(s.total_amount) : null;
}

const isSignedPending = (r: ContractRow) => ['PENDING', 'PENDING_SIGN'].includes(r.status);

const kpi = reactive<{ pendingSign: number | null; monthAmount: number | null; pendingPay: number | null; settled: number | null }>({
  pendingSign: null,
  monthAmount: null,
  pendingPay: null,
  settled: null
});

async function loadAll() {
  loading.value = true;
  error.value = '';
  try {
    const [c, p, s] = await Promise.all([
      contractApi.list(filters.status || undefined, 1, 50),
      contractApi.payments(undefined, 1, 50),
      contractApi.statements(1, 50)
    ]);
    rows.value = (c?.items ?? []).filter((r) => {
      if (!filters.keyword) return true;
      const k = filters.keyword.toLowerCase();
      return (r.contract_no ?? '').toLowerCase().includes(k) || (r.supplier_name ?? '').toLowerCase().includes(k);
    });
    payments.value = p?.items ?? [];
    statements.value = s?.items ?? [];

    // KPI 由真实数据如实统计（后端无聚合接口）
    kpi.pendingSign = (c?.items ?? []).filter(isSignedPending).length;
    kpi.monthAmount = statements.value.reduce((a, x) => a + Number(x.total_amount ?? 0), 0);
    kpi.pendingPay = payments.value.filter((x) => x.status === 'PAYMENT_RECORDED').reduce((a, x) => a + Number(x.amount ?? 0), 0);
    kpi.settled = payments.value.filter((x) => x.status === 'CONFIRMED').reduce((a, x) => a + Number(x.amount ?? 0), 0);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}

function openDetail(r: ContractRow) {
  detail.value = r;
  detailOpen.value = true;
}

async function onIssue(r: ContractRow) {
  try {
    await ElMessageBox.confirm(`确认为合同 ${r.contract_no} 发起（生成合同文件）？`, '确认发起', { type: 'warning' });
  } catch {
    return;
  }
  try {
    const t = await contractApi.issue(r.id);
    ElMessage.success(`已发起：${t.contract_no ?? r.id}`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

async function onConfirmSign(r: ContractRow) {
  try {
    const t = await contractApi.confirmSign(r.id);
    ElMessage.success(`签署确认：${t.contract_no ?? r.id}（status=${t.status}）`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

function openGenerate() {
  genErr.value = '';
  genForm.provider_id = signedProviders.value[0]?.id ?? '';
  genForm.month = new Date().toISOString().slice(0, 7);
  genOpen.value = true;
}

async function onGenerate() {
  genErr.value = '';
  if (!genForm.provider_id) {
    genErr.value = '请选择供应商 —— 只有「已签署（SIGNED）」合同的供应商可出账';
    return;
  }
  genLoading.value = true;
  try {
    const d = await contractApi.generateStatement({ provider_id: genForm.provider_id, month: genForm.month });
    ElMessage.success(
      `结算单 ${d.statement_no ?? d.id}：金额 ${money(d.total_amount)}，平台费 ${money(d.platform_fee)}，状态 ${d.status}`
    );
    genOpen.value = false;
    await loadAll();
  } catch (e) {
    // 409 E-1601（无用量/低于门槛）、E-1701（无生效合同）的真实原因直接显示——不吞、不假成功
    genErr.value = (e as Error).message;
  } finally {
    genLoading.value = false;
  }
}

async function openStatement(r: StatementRow) {
  stOpen.value = true;
  stLoading.value = true;
  stDetail.value = null;
  try {
    stDetail.value = await contractApi.statementDetail(r.id);
  } catch (e) {
    ElMessage.error((e as Error).message);
  } finally {
    stLoading.value = false;
  }
}

async function onConfirmStatement(r: StatementRow) {
  try {
    await ElMessageBox.confirm(
      `确认出账 ${r.statement_no ?? r.id}？确认后为终态、不可再作废。`,
      '确认出账',
      { type: 'warning' }
    );
  } catch {
    return;
  }
  try {
    const d = await contractApi.confirmStatement(r.id);
    ElMessage.success(`已出账：${d.statement_no ?? d.id}（${d.status}）`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

async function onVoidStatement(r: StatementRow) {
  let reason = '';
  try {
    const res = await ElMessageBox.prompt(`作废 ${r.statement_no ?? r.id} 的理由（必填，落审计）`, '作废结算单', {
      type: 'warning',
      inputValidator: (v: string) => (v && v.trim() ? true : '理由必填')
    });
    reason = (res.value || '').trim();
  } catch {
    return;
  }
  try {
    const d = await contractApi.voidStatement(r.id, reason);
    ElMessage.success(`已作废：${d.statement_no ?? d.id}（${d.status}）；该周期可重新生成`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

async function onConfirmPay(p: PaymentRow) {
  try {
    const t = await contractApi.confirmPayment(p.id);
    ElMessage.success(`已确认打款记录：${t.contract_no ?? p.id}`);
    await loadAll();
  } catch (e) {
    ElMessage.error((e as Error).message);
  }
}

function onBatchPay() {
  // PRD 13 §6 允许批量打款（仅记录）。后端无批量接口 → 逐条确认，不假装有批量端点。
  ElMessage.info(`后端无批量打款接口，请逐条确认（当前 ${pendingPayCount.value} 笔待确认）`);
}

// ---------------------------------------------------------------- 记录打款 / 作废（ADM-PAY04/05）
const recordOpen = ref(false);
const recordTarget = ref<ContractRow | null>(null);
const saving = ref(false);
const recordForm = reactive({ amount: 0, currency: '', voucherId: '', voucherName: '', remark: '' });

/** 仅「已签署」合同可记录打款（后端：未签署 409 E-1601，AC-40 未签署禁打款） */
const isRecordable = (r: ContractRow) => r.status === 'SIGNED';
/** 可作废：后端 VOIDABLE = PAYMENT_RECORDED / CONFIRMED */
const canVoidPay = (p: PaymentRow) => ['PAYMENT_RECORDED', 'CONFIRMED'].includes(p.status);

function openRecord(r: ContractRow) {
  recordTarget.value = r;
  recordForm.amount = 0;
  recordForm.currency = r.currency ?? '';
  recordForm.voucherId = '';
  recordForm.voucherName = '';
  recordForm.remark = '';
  recordOpen.value = true;
}

async function onVoucherPick(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  try {
    recordForm.voucherId = await uploadVoucher(file);
    recordForm.voucherName = file.name;
    ElMessage.success('凭证已上传');
  } catch (err) {
    ElMessage.error((err as Error).message);
  }
}

async function onSubmitRecord() {
  const t = recordTarget.value;
  if (!t) return;
  if (!(recordForm.amount > 0)) {
    ElMessage.warning('打款金额必须大于 0（C4）');
    return;
  }
  if (!recordForm.voucherId) {
    ElMessage.warning('请先上传打款凭证（C5）');
    return;
  }
  saving.value = true;
  try {
    const p = await contractApi.recordPayment({
      contract_id: t.id,
      amount: recordForm.amount,
      currency: recordForm.currency || null,
      voucher_file_id: recordForm.voucherId,
      remark: recordForm.remark || null
    });
    ElMessage.success(`已记录打款：${p.contract_no ?? t.contract_no}（${payLabel(p.status)}）`);
    recordOpen.value = false;
    await loadAll();
  } catch (err) {
    ElMessage.error((err as Error).message);
  } finally {
    saving.value = false;
  }
}

async function onVoidPay(p: PaymentRow) {
  try {
    const { value } = await ElMessageBox.prompt('作废后该笔不计入钱包，可重新录入。请填写作废理由：', '作废打款', {
      inputPlaceholder: '如：金额填错',
      inputValidator: (v: string) => (v && v.trim() ? true : '理由必填')
    });
    await contractApi.voidPayment(p.id, value.trim());
    ElMessage.success('已作废');
    await loadAll();
  } catch (e) {
    // 取消（字符串 'cancel'/'close'）不报错，只提示真实失败
    if (e instanceof Error) ElMessage.error(e.message);
  }
}

function onExport() {
  ElMessage.info('导出为异步任务，后端暂未提供导出接口（已登记 missing-api）');
}

onMounted(loadAll);
defineExpose({ loadAll });
</script>

<style scoped>
.ct { display: flex; flex-direction: column; gap: 16px; }
.kpi-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 8px; }
.kpi__label { font-size: var(--fs-base); color: var(--c-text-muted); }
.kpi__value { font-size: var(--fs-kpi); font-weight: 600; line-height: 1.1; }
.kpi__value--warn { color: var(--c-warn); }
.kpi__value--ok { color: var(--c-success); }
.kpi__note { font-size: var(--fs-sm); color: var(--c-text-muted); }

.ct__filter { display: flex; align-items: center; gap: 10px; padding: 14px 16px; flex-wrap: wrap; }
.ct__spacer { flex: 1; }
.aap-card__head { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
.aap-card__title { font-size: var(--fs-lg); font-weight: 600; }
.aap-card__body { padding: 14px 18px 18px; }
.ct__act { margin-left: 10px; }
.ct__todo { font-size: var(--fs-sm); color: var(--c-text-muted); }
.ct__err { color: var(--c-danger); font-size: var(--fs-base); margin: 10px 0 0; }
.ct__empty { padding: 20px; text-align: center; color: var(--c-text-muted); font-size: var(--fs-base); }
.ct__note { font-size: var(--fs-sm); color: var(--c-text-muted); margin: 12px 0 0; line-height: 1.6; }

/* 表单内联提示（记录打款弹窗：币种口径 / 凭证状态） */
.ct__hint { font-size: var(--fs-sm); color: var(--c-text-muted); margin-left: 8px; }

.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 1280px) { .row-2 { grid-template-columns: 1fr; } }

.pay-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px dashed var(--c-border); }
.pay-item:last-of-type { border-bottom: 0; }
.pay-item__left { flex: 1; min-width: 0; }
.pay-item__no { font-size: var(--fs-base); color: var(--c-text); }
.pay-item__sub { font-size: var(--fs-sm); color: var(--c-text-muted); margin-top: 3px; }
.pay-item__amt { font-size: var(--fs-md); font-weight: 600; color: var(--c-text); }

.ct__terms { margin-top: 16px; }
.ct__sub { font-size: var(--fs-md); font-weight: 600; margin-bottom: 8px; }
.ct__terms ol { margin: 0; padding-left: 20px; font-size: var(--fs-base); color: var(--c-text-body); line-height: 1.8; }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
