<template>
  <div class="au">
    <el-alert type="info" :closable="false" show-icon class="au__note" data-testid="admin-users-note">
      <template #title>运营账号自助开通（ADM-AUTH02…05，2026-09-23 新增）</template>
      此前开账号只能手写 SQL，生产运维无法自助开通。手机号即登录名，短信验证码登录；
      手机号一律只显示**脱敏值**。建号/停用属提权操作，**仅超级管理员**可用
      （运营商务 / 技术运营看不到本页；后端另有二次校验 403 <code>E-1901</code>）。
    </el-alert>

    <div v-if="!isSuperAdmin" class="aap-card">
      <div class="aap-card__body">
        <p class="au__err" data-testid="admin-users-forbidden">
          当前角色（{{ roleLabel }}）无权管理运营账号 —— 仅超级管理员可开号/停用。后端同样会拒（403 E-1901）。
        </p>
      </div>
    </div>

    <template v-else>
      <!-- 筛选 + 开号 -->
      <div class="aap-card au__bar">
        <el-input v-model="filters.keyword" placeholder="搜索账号 / 显示名 / 手机号" clearable style="width: 240px" data-testid="au-keyword" @keyup.enter="load" />
        <el-select v-model="filters.role" placeholder="全部角色" clearable style="width: 150px" data-testid="au-role" @change="load">
          <el-option v-for="(label, k) in ADMIN_ROLE_LABEL" :key="k" :label="label" :value="k" />
        </el-select>
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 140px" data-testid="au-status" @change="load">
          <el-option v-for="(v, k) in ADMIN_USER_STATUS" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button data-testid="au-query" @click="load">查询</el-button>
        <span class="au__spacer" />
        <el-button type="primary" data-testid="btn-new-admin-user" @click="openCreate">开通运营账号</el-button>
      </div>

      <div class="aap-card">
        <div class="aap-card__head">
          <span class="aap-card__title">运营账号</span>
          <span class="aap-card__hint" data-testid="au-count">共 {{ total }} 个</span>
        </div>
        <div class="aap-card__body">
          <el-table v-loading="loading" :data="rows" size="small" data-testid="au-table" empty-text="暂无运营账号">
            <el-table-column prop="username" label="账号" min-width="140" />
            <el-table-column prop="display_name" label="显示名" min-width="120" />
            <el-table-column label="角色" width="130">
              <template #default="{ row }">
                <span class="aap-badge aap-badge--info">{{ ADMIN_ROLE_LABEL[row.role] || row.role }}</span>
              </template>
            </el-table-column>
            <el-table-column label="手机号" width="150">
              <template #default="{ row }">{{ row.phone_masked || '—' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <span class="aap-badge" :class="`aap-badge--${ADMIN_USER_STATUS[row.status]?.tone || 'muted'}`">
                  {{ ADMIN_USER_STATUS[row.status]?.label || row.status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="最近登录" width="170">
              <template #default="{ row }">{{ row.last_login_at || '从未登录' }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }">{{ row.created_at || '—' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'ACTIVE'"
                  size="small" type="danger" link
                  :data-testid="`au-suspend-${row.id}`"
                  @click="onSuspend(row)"
                >停用</el-button>
                <el-button
                  v-else
                  size="small" type="primary" link
                  :data-testid="`au-resume-${row.id}`"
                  @click="onResume(row)"
                >恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
          <p v-if="error" class="au__err" data-testid="au-error">{{ error }}</p>
        </div>
      </div>
    </template>

    <!-- 开通账号（ADM-AUTH03） -->
    <el-dialog v-model="createOpen" title="开通运营账号" width="460px" data-testid="create-dialog">
      <el-form label-width="90px">
        <el-form-item label="账号">
          <el-input v-model="draft.username" placeholder="登录账号（唯一，如 ops-zhang）" data-testid="new-username" />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="draft.displayName" placeholder="如 张运营" data-testid="new-display" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="draft.role" style="width: 100%" data-testid="new-role">
            <el-option v-for="(label, k) in ADMIN_ROLE_LABEL" :key="k" :label="label" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="draft.phone" placeholder="11 位手机号（即短信登录名，唯一）" maxlength="11" data-testid="new-phone" />
        </el-form-item>
      </el-form>
      <p class="au__hint">提示：手机号是短信验证码登录的唯一凭据，务必填本人可收码的号码；开号后该账号立即可登录（无需审核）。</p>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" data-testid="new-submit" @click="onCreate">开通</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  adminUserApi, ADMIN_ROLE_LABEL, ADMIN_USER_STATUS, type AdminUserRow
} from '@/api/admin/adminUsers';
import { ROLE_LABEL, type AdminRole } from '@/config/nav';
import { useSession } from '@/composables/useSession';

const { role } = useSession();
/** 建号/停用属提权操作（PRD 13 §1）：前端只做渲染过滤，后端另有二次校验 */
const isSuperAdmin = computed(() => role.value === 'SUPER_ADMIN');
const roleLabel = computed(() => ROLE_LABEL[role.value as AdminRole] ?? role.value);

const rows = ref<AdminUserRow[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');
const filters = reactive({ keyword: '', role: '', status: '' });

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const res = await adminUserApi.list({
      page: 1,
      pageSize: 50,
      keyword: filters.keyword || undefined,
      role: filters.role || undefined,
      status: filters.status || undefined
    });
    rows.value = res?.items ?? [];
    total.value = res?.total ?? rows.value.length;
  } catch (e) {
    // 403 说明后端也拦住了（前端隐藏不是安全边界）—— 如实展示，不吞
    error.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}

const createOpen = ref(false);
const creating = ref(false);
const draft = reactive({ username: '', displayName: '', role: 'BIZ_OPERATOR', phone: '' });

function openCreate() {
  draft.username = '';
  draft.displayName = '';
  draft.role = 'BIZ_OPERATOR';
  draft.phone = '';
  createOpen.value = true;
}

async function onCreate() {
  if (!draft.username.trim()) return ElMessage.warning('请填账号');
  if (!/^1\d{10}$/.test(draft.phone.trim())) return ElMessage.warning('手机号需为 11 位（1 开头）');
  creating.value = true;
  try {
    const created = await adminUserApi.create({
      username: draft.username.trim(),
      display_name: draft.displayName.trim() || null,
      role: draft.role,
      phone: draft.phone.trim()
    });
    ElMessage.success(`已开通：${created.username}（${ADMIN_ROLE_LABEL[created.role] || created.role}）`);
    createOpen.value = false;
    await load();
  } catch (e) {
    ElMessage.error((e as Error).message); // 手机号/账号重复 → 后端 E-1001
  } finally {
    creating.value = false;
  }
}

async function onSuspend(row: AdminUserRow) {
  try {
    const { value } = await ElMessageBox.prompt(
      `停用「${row.display_name || row.username}」后该账号**立即无法登录**，理由必填：`,
      '停用运营账号',
      { inputPlaceholder: '如：已离职', inputValidator: (v: string) => (v && v.trim() ? true : '理由必填') }
    );
    await adminUserApi.suspend(row.id, value.trim());
    ElMessage.success('已停用');
    await load();
  } catch (e) {
    // 取消是字符串（不报错）；「不可停用自己」「不可停用最后一个超管」由后端 409 拦下
    if (e instanceof Error) ElMessage.error(e.message);
  }
}

async function onResume(row: AdminUserRow) {
  try {
    await ElMessageBox.confirm(`恢复「${row.display_name || row.username}」的登录权限？`, '确认恢复', { type: 'warning' });
    await adminUserApi.resume(row.id);
    ElMessage.success('已恢复');
    await load();
  } catch (e) {
    if (e instanceof Error) ElMessage.error(e.message);
  }
}

// 角色是**异步**回填的（AdminLayout 挂载时调 /auth/me 恢复会话），所以不能用 onMounted 里的一次性判断：
// 挂载瞬间 role 还是默认值 BIZ_OPERATOR → 会误判为「无权」而永不加载（实测：表格恒「共 0 个」）。
watch(isSuperAdmin, (ok) => { if (ok) load(); }, { immediate: true });

defineExpose({ load });
</script>

<style scoped>
/* 注意：本项目视图一律用**纯 CSS** —— 用 lang="scss" 会因缺 sass-embedded 让整个组件 500（2026-09-23 实测） */
.au__note { margin-bottom: 12px; }
.au__bar { display: flex; align-items: center; gap: 10px; padding: 12px 16px; margin-bottom: 12px; }
.au__spacer { flex: 1; }
.au__err { color: var(--c-danger, #d03050); font-size: var(--fs-sm); margin: 8px 0 0; }
.au__hint { color: var(--c-text-muted); font-size: var(--fs-sm); margin: 0; line-height: 1.6; }
</style>
