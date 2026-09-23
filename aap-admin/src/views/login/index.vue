<template>
  <div class="login">
    <div class="login__card aap-card">
      <div class="login__brand">
        <div class="login__logo">云</div>
        <div>
          <div class="login__name">云算接入</div>
          <div class="login__sub">运营管理端</div>
        </div>
      </div>

      <h1 class="login__title">登录</h1>
      <p class="login__hint">仅限运营商务 / 技术运营 / 超级管理员</p>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" maxlength="11" placeholder="请输入手机号" data-testid="phone" />
        </el-form-item>
        <el-form-item label="图形验证码">
          <div class="login__captcha">
            <el-input v-model="form.captcha" maxlength="4" placeholder="请输入验证码" data-testid="captcha" />
            <div class="login__captcha-box" data-testid="captcha-text" @click="refreshCaptcha">{{ captchaText }}</div>
          </div>
        </el-form-item>
        <el-form-item label="短信验证码">
          <div class="login__captcha">
            <el-input v-model="form.smsCode" maxlength="6" placeholder="请输入短信验证码" data-testid="sms-code" />
            <el-button :disabled="cooldown > 0" data-testid="sms-btn" @click="onSendSms">
              {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <p v-if="devCode" class="login__dev" data-testid="dev-code">dev 回显验证码：{{ devCode }}</p>
        <el-alert v-if="error" type="error" :closable="false" show-icon class="login__err" data-testid="login-error">{{ error }}</el-alert>
        <el-button type="primary" class="login__submit" :loading="loading" data-testid="submit" @click="onSubmit">登录</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { request, tokenStore } from '@/api/http';
import { useSession } from '@/composables/useSession';
import type { AdminRole } from '@/config/nav';

const router = useRouter();
const route = useRoute();
const session = useSession();

const form = reactive({ phone: '', captcha: '', smsCode: '' });
const captchaText = ref('');
const cooldown = ref(0);
const devCode = ref('');
const error = ref('');
const loading = ref(false);

function refreshCaptcha() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  captchaText.value = Array.from({ length: 4 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
}
refreshCaptcha();

async function onSendSms() {
  error.value = '';
  try {
    const r = await request<{ dev_code?: string; ttl?: number }>('/auth/sms/send', {
      method: 'POST',
      body: { phone: form.phone, captcha: form.captcha },
      skipAuthRedirect: true
    });
    // dev 环境后端会回显验证码（AAP_SMS_EXPOSE_CODE=true）；生产不回显
    devCode.value = r?.dev_code ?? '';
    cooldown.value = 60;
    const t = setInterval(() => {
      cooldown.value -= 1;
      if (cooldown.value <= 0) clearInterval(t);
    }, 1000);
  } catch (e) {
    error.value = (e as Error).message;
  }
}

async function onSubmit() {
  error.value = '';
  loading.value = true;
  try {
    // ⚠️ 管理端**必须**走 `/admin/auth/sms/login`（2026-09-23 新增）。
    //    旧写法 `('/auth/sms/login'` 是供应商登录：后端固定签发 subjectType=PROVIDER+role=SUPPLIER，
    //    于是登录「成功」但之后所有 /api/v1/admin/** 全是 403 E-1901 —— 管理端等于不可用。
    //    `/auth/sms/send` 两边共用（同一套频控与锁定）。
    const r = await request<{ token: string; refresh_token?: string; refreshToken?: string }>('/admin/auth/sms/login', {
      method: 'POST',
      body: { phone: form.phone, smsCode: form.smsCode },
      skipAuthRedirect: true
    });
    if (!r?.token) throw new Error('登录响应缺少 token');
    tokenStore.set(r.token, r.refresh_token ?? r.refreshToken);

    // 取当前用户 → 角色（PRD 13 §1 RBAC；后端二次校验）
    const me = await request<{ name?: string; nickname?: string; phone?: string; role?: string }>('/auth/me');
    const role = (me?.role ?? 'BIZ_OPERATOR') as AdminRole;
    session.set(me?.name ?? me?.nickname ?? me?.phone ?? '管理员', role);

    ElMessage.success('登录成功');
    router.push((route.query.redirect as string) || '/dashboard');
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--c-page); }
.login__card { width: 400px; padding: 28px 30px 30px; }
.login__brand { display: flex; align-items: center; gap: 10px; margin-bottom: 22px; }
.login__logo {
  width: 40px; height: 40px; border-radius: var(--r-lg); background: var(--c-primary);
  color: #fff; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 600;
}
.login__name { font-size: var(--fs-xl); font-weight: 600; }
.login__sub { font-size: var(--fs-xs); color: var(--c-text-sub); margin-top: 2px; }
.login__title { font-size: var(--fs-2xl); margin: 0 0 4px; }
.login__hint { font-size: var(--fs-base); color: var(--c-text-muted); margin: 0 0 18px; }
.login__captcha { display: flex; gap: 10px; width: 100%; }
.login__captcha-box {
  flex: 0 0 96px; height: 32px; display: flex; align-items: center; justify-content: center;
  background: var(--c-surface-alt); border: 1px solid var(--c-border); border-radius: var(--r-md);
  font-weight: 600; letter-spacing: 3px; cursor: pointer; user-select: none;
}
.login__dev { font-size: var(--fs-sm); color: var(--c-warn-strong); margin: 0 0 10px; }
.login__err { margin-bottom: 12px; }
.login__submit { width: 100%; margin-top: 6px; }
</style>
