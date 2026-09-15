<template>
  <view class="login-page">
    <!-- 品牌头部 -->
    <view class="brand">
      <view class="brand__logo">
        <view class="brand__logo-mark" />
      </view>
      <text class="brand__name">云算接入</text>
      <text class="brand__en">SUPPLIER ONBOARDING</text>
      <text class="brand__title">API 供应商一站式接入</text>
      <text class="brand__subtitle">注册即开通，检测 · 报价 · 结算全流程线上化</text>
    </view>

    <!-- 表单卡片 -->
    <view class="card">
      <view class="card__head">
        <text class="card__title">手机号登录 / 注册</text>
        <text class="card__hint">未注册的手机号将自动创建账号</text>
      </view>

      <view class="field" data-test="phone">
        <text class="field__label">手机号</text>
        <view class="field__box">
          <view class="field__mark field__mark--phone" />
          <text class="field__prefix">+86</text>
          <view class="field__divider" />
          <input
            v-model="form.phone"
            class="field__input"
            type="number"
            maxlength="11"
            placeholder="请输入手机号"
            placeholder-class="field__placeholder"
          />
        </view>
      </view>

      <view class="field" data-test="captcha">
        <text class="field__label">图形验证码</text>
        <view class="field__box">
          <view class="field__mark field__mark--shield" />
          <input
            v-model="form.captcha"
            class="field__input"
            maxlength="4"
            placeholder="请输入验证码"
            placeholder-class="field__placeholder"
          />
          <view class="captcha" @tap="refreshCaptcha">
            <text class="captcha__text">{{ captchaText }}</text>
          </view>
        </view>
      </view>

      <view class="field" data-test="smsCode">
        <text class="field__label">短信验证码</text>
        <view class="field__box">
          <view class="field__mark field__mark--lock" />
          <input
            v-model="form.smsCode"
            class="field__input"
            type="number"
            maxlength="6"
            placeholder="请输入短信验证码"
            placeholder-class="field__placeholder"
          />
          <view
            class="sms-btn"
            :class="{ 'sms-btn--disabled': cooldown.active.value }"
            data-test="btn-send-sms"
            @tap="onSendSms"
          >
            <text class="sms-btn__text">{{ cooldown.label('获取验证码') }}</text>
          </view>
        </view>
        <view class="field__tip">
          <view class="field__tip-mark" />
          <text class="field__tip-text">验证码 5 分钟内有效，请注意查收</text>
        </view>
      </view>

      <view class="submit" data-test="btn-login" @tap="onLogin">
        <text class="submit__text">登录 / 注册</text>
      </view>

      <view class="divider">
        <view class="divider__line" />
        <text class="divider__text">其他登录方式</text>
        <view class="divider__line" />
      </view>

      <view class="wechat" data-test="btn-wechat" @tap="onWechatLogin">
        <view class="wechat__mark" />
        <text class="wechat__text">微信一键登录</text>
      </view>

      <view class="agree" data-test="agree">
        <view class="agree__row">
          <view
            class="agree__box"
            :class="{ 'agree__box--checked': agreed }"
            data-test="agree-box"
            @tap="agreed = !agreed"
          >
            <text v-if="agreed" class="agree__tick">✓</text>
          </view>
          <text class="agree__text">
            我已阅读并同意<text class="agree__link">《服务协议》</text>与<text class="agree__link">《隐私政策》</text>
          </text>
        </view>
      </view>
    </view>

    <!-- 免责与合规说明 -->
    <view class="disclaimer">
      <view class="disclaimer__head">
        <view class="disclaimer__mark" />
        <text class="disclaimer__title">免责与合规说明</text>
      </view>
      <text class="disclaimer__body">本平台仅提供 API 接入检测与报价撮合服务，不对供应商上游资源合法性及稳定性作担保，请如实提交资料。</text>
    </view>

    <view class="footer">
      <text class="footer__text">登录即代表您已满 18 周岁</text>
      <text class="footer__text">© 2024 云算接入平台 · 保留所有权利</text>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 页面 1 ·【账号接入】登录注册（Calicat page-1-2）
 * 依据：01-PRD总览 §4、17-spec R-01/R-02/R-48、18-API设计OpenAPI Auth、21-验收标准 AC-01~05
 * 交互真源：interaction.json 返回「不存在图层交互数据」→ 退到 PRD（见台账备注）
 */
import { reactive, ref } from 'vue'
import { authApi } from '@/api/auth'
import { ApiError, setToken } from '@/api/http'
import { createCooldown } from '@/utils/cooldown'
import { isCaptcha, isPhone, isSmsCode, normalize } from '@/utils/validators'

const form = reactive({ phone: '', captcha: '', smsCode: '' })
const agreed = ref(false)
const captchaText = ref('A7K9')
const cooldown = createCooldown(60)

function toast(title: string, icon: 'none' | 'success' = 'none') {
  uni.showToast({ title, icon, duration: 2000 })
}

function refreshCaptcha() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  captchaText.value = Array.from({ length: 4 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
}

async function onSendSms() {
  if (cooldown.active.value) return
  if (!isPhone(form.phone)) {
    toast('请输入正确的手机号')
    return
  }
  if (!isCaptcha(form.captcha)) {
    toast('请输入 4 位图形验证码')
    return
  }
  try {
    await authApi.sendSms({ phone: normalize(form.phone), captcha: normalize(form.captcha) })
    cooldown.start()
    toast('验证码已发送')
  } catch (e) {
    toast(e instanceof ApiError ? e.message : '发送失败，请稍后重试')
  }
}

/** 登录成功后的统一落地：写 token + 进工作台 */
function afterLogin(token: string) {
  setToken(token)
  toast('登录成功', 'success')
  uni.navigateTo({ url: '/pages/workbench/index' })
}

async function onLogin() {
  if (!isPhone(form.phone)) {
    toast('请输入正确的手机号')
    return
  }
  if (!isSmsCode(form.smsCode)) {
    toast('请输入 6 位短信验证码')
    return
  }
  if (!agreed.value) {
    toast('请先阅读并同意服务协议与隐私政策')
    return
  }
  try {
    const res = await authApi.login({ phone: normalize(form.phone), smsCode: normalize(form.smsCode) })
    afterLogin(res.token)
  } catch (e) {
    toast(e instanceof ApiError ? e.message : '登录失败，请稍后重试')
  }
}

function onWechatLogin() {
  if (!agreed.value) {
    toast('请先阅读并同意服务协议与隐私政策')
    return
  }
  uni.login({
    provider: 'weixin',
    success: async (r: { code?: string }) => {
      try {
        const res = await authApi.wechatLogin({ code: r.code ?? '' })
        afterLogin(res.token)
      } catch (e) {
        toast(e instanceof ApiError ? e.message : '微信登录失败，请稍后重试')
      }
    },
    fail: () => toast('微信授权已取消')
  })
}
</script>

<style lang="scss" scoped>
@use '@/styles/tokens.scss' as *;

.login-page {
  min-height: 100vh;
  width: 100%;
  box-sizing: border-box;
  background: $color-bg-page;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

.brand {
  background: $color-brand;
  padding: 56px 24px 64px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  box-sizing: border-box;

  &__logo {
    width: 48px;
    height: 48px;
    border-radius: $radius-md;
    background: $color-bg-card;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* 图标占位：设计稿为白色圆角块内的蓝色闪电，禁用 emoji（PRD 08） */
  &__logo-mark {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    background: $color-brand;
    transform: rotate(45deg);
  }

  &__name {
    margin-top: $gap-lg;
    font-size: $font-2xl;
    line-height: 1.2;
    color: $color-bg-card;
  }

  &__en {
    margin-top: $gap-xs;
    font-size: $font-xs;
    line-height: 1.2;
    letter-spacing: 1px;
    color: rgba(255, 255, 255, 0.75);
  }

  &__title {
    margin-top: $gap-lg;
    font-size: $font-title;
    line-height: 1.25;
    color: $color-bg-card;
  }

  &__subtitle {
    margin-top: $gap-sm;
    font-size: $font-base;
    line-height: 1.4;
    color: rgba(255, 255, 255, 0.85);
  }
}

.card {
  margin: -32px 16px 0;
  padding: 24px 20px;
  background: $color-bg-card;
  border-radius: $radius-lg;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;

  &__head {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  &__title {
    font-size: $font-2xl;
    line-height: 1.3;
    color: $color-text-primary;
  }

  &__hint {
    margin-top: $gap-xs;
    font-size: $font-xs;
    line-height: 1.3;
    color: $color-text-secondary;
  }
}

.field {
  margin-top: $gap-lg;
  display: flex;
  flex-direction: column;

  &__label {
    font-size: $font-sm;
    line-height: 1.3;
    color: $color-text-secondary;
  }

  &__box {
    margin-top: $gap-sm;
    height: $tap-min;
    padding: 0 $gap-md;
    border: 1px solid $color-border;
    border-radius: $radius-md;
    display: flex;
    flex-direction: row;
    align-items: center;
    box-sizing: border-box;
    overflow: hidden;
  }

  /* 图标占位（设计稿为矢量图标，禁用 emoji） */
  &__mark {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    margin-right: $gap-sm;
    border-radius: 4px;
    background: $color-primary-weak-2;

    &--phone {
      background: $color-primary-weak;
    }

    &--shield {
      border-radius: 50%;
      background: $color-primary-weak;
    }

    &--lock {
      background: $color-primary-weak;
    }
  }

  &__prefix {
    font-size: $font-base;
    color: $color-text-primary;
    flex-shrink: 0;
  }

  &__divider {
    width: 1px;
    height: 20px;
    margin: 0 $gap-md;
    background: $color-border;
    flex-shrink: 0;
  }

  &__input {
    flex: 1;
    min-width: 0;
    width: 100%;
    font-size: $font-base;
    color: $color-text-primary;
  }

  &__placeholder {
    color: $color-text-placeholder;
    font-size: $font-base;
  }

  &__tip {
    margin-top: $gap-sm;
    display: flex;
    flex-direction: row;
    align-items: center;
  }

  &__tip-mark {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: $color-primary;
    margin-right: $gap-xs;
    flex-shrink: 0;
  }

  &__tip-text {
    flex: 1;
    min-width: 0;
    font-size: $font-xs;
    line-height: 1.3;
    color: $color-text-secondary;
  }
}

.captcha {
  width: 72px;
  height: 32px;
  flex-shrink: 0;
  border-radius: $radius-sm;
  background: $color-primary-weak-2;
  display: flex;
  align-items: center;
  justify-content: center;

  &__text {
    font-size: $font-lg;
    letter-spacing: 2px;
    color: $color-brand;
  }
}

.sms-btn {
  padding: 0 $gap-md;
  height: 32px;
  flex-shrink: 0;
  border-radius: $radius-sm;
  background: $color-primary-weak;
  display: flex;
  align-items: center;
  justify-content: center;

  &--disabled {
    opacity: 0.6;
  }

  &__text {
    font-size: $font-sm;
    color: $color-primary;
    white-space: nowrap;
  }
}

.submit {
  margin-top: 24px;
  height: 48px;
  border-radius: $radius-md;
  background: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;

  &__text {
    font-size: $font-lg;
    color: $color-bg-card;
  }
}

.divider {
  margin-top: 24px;
  display: flex;
  align-items: center;

  &__line {
    flex: 1;
    height: 1px;
    background: $color-border;
  }

  &__text {
    margin: 0 $gap-md;
    font-size: $font-xs;
    color: $color-text-placeholder;
  }
}

.wechat {
  margin-top: $gap-lg;
  height: 48px;
  border-radius: $radius-md;
  background: $color-wechat-weak;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;

  &__mark {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: $color-wechat;
    margin-right: $gap-sm;
    flex-shrink: 0;
  }

  &__text {
    font-size: $font-md;
    color: $color-wechat;
  }
}

.agree {
  margin-top: $gap-lg;

  &__row {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
  }

  &__box {
    width: 16px;
    height: 16px;
    margin-right: $gap-sm;
    margin-top: 2px;
    flex-shrink: 0;
    border: 1px solid $color-border;
    border-radius: 3px;
    background: $color-bg-card;
    display: flex;
    align-items: center;
    justify-content: center;

    &--checked {
      background: $color-primary;
      border-color: $color-primary;
    }
  }

  &__tick {
    font-size: 12px;
    line-height: 1;
    color: $color-bg-card;
  }

  &__text {
    flex: 1;
    min-width: 0;
    font-size: $font-xs;
    line-height: 1.5;
    color: $color-text-secondary;
  }

  &__link {
    color: $color-primary;
  }
}

.disclaimer {
  margin: 24px 20px 0;
  display: flex;
  flex-direction: column;

  &__head {
    display: flex;
    flex-direction: row;
    align-items: center;
  }

  &__mark {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 1px solid $color-text-placeholder;
    margin-right: $gap-xs;
    flex-shrink: 0;
  }

  &__title {
    font-size: $font-base;
    color: $color-text-primary;
  }

  &__body {
    margin-top: $gap-sm;
    font-size: $font-xs;
    line-height: 1.6;
    color: $color-text-secondary;
  }
}

.footer {
  margin: 24px 0 32px;
  display: flex;
  flex-direction: column;
  align-items: center;

  &__text {
    font-size: $font-2xs;
    line-height: 1.8;
    color: $color-text-placeholder;
  }
}
</style>
