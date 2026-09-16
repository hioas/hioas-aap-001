<template>
  <view class="login-page">
    <!-- 品牌头部（设计 品牌头部 = Logo行[Logo方块 54x54 + spacer 12 + 品牌名块] + spacer 28 + 定位语块） -->
    <view class="brand">
      <view class="brand__row">
        <view class="brand__logo">
          <view class="brand__logo-mark" />
        </view>
        <view class="brand__id">
          <text class="brand__name">云算接入</text>
          <text class="brand__en">SUPPLIER ONBOARDING</text>
        </view>
      </view>
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

    <!-- 免责与合规说明（设计：container padding 0/16 里的一张白卡） -->
    <view class="disclaimer-wrap">
      <view class="disclaimer">
        <view class="disclaimer__head">
          <view class="disclaimer__mark" />
          <text class="disclaimer__title">免责与合规说明</text>
        </view>
        <text class="disclaimer__body">本平台仅提供 API 接入检测与报价撮合服务，不对供应商上游资源合法性及稳定性作担保，请如实提交资料。</text>
      </view>
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

  /* Logo行：Logo方块 + spacer 12 + 品牌名块（设计 layout=horizontal alignItems=center） */
  &__row {
    display: flex;
    flex-direction: row;
    align-items: center;
  }

  &__logo {
    width: 54px;
    height: 54px;
    border-radius: 16px;
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

  /* 品牌名块：名称 / 英文行竖排（设计 品牌名块 宽 137，字号 20/12） */
  &__id {
    margin-left: $gap-md;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  &__name {
    font-weight: 700;
    font-size: $font-2xl;
    line-height: 28px; /* 设计 2774910e h=28（fs20） */
    color: $color-bg-card;
  }

  &__en {
    font-size: $font-xs;
    line-height: 20px; /* 设计 425a7e1c h=20（fs12） */
    letter-spacing: 1px;
    color: $color-brand-en;
  }

  /* 定位语块：Logo行 之后 spacer 28 */
  &__title {
    margin-top: 28px;
    font-weight: 700;
    font-size: $font-title;
    line-height: 36px; /* 设计 15a710ce h=36（fs26） */
    color: $color-bg-card;
  }

  &__subtitle {
    margin-top: 6px;
    font-size: $font-base;
    line-height: 24px; /* 设计 b96e4f92 h=24（fs14） */
    color: $color-brand-subtitle;
  }
}

.card {
  /* 设计：表单卡片紧接品牌头部之下（无负外边距），container padding 0/16 */
  margin: 0 16px;
  padding: 24px 20px;
  background: $color-bg-card;
  border-radius: 20px;
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
    line-height: 28px; /* 设计 c127cbae h=28（fs20） */
    font-weight: 700;
    color: $color-text-primary;
  }

  &__hint {
    margin-top: $gap-xs;
    font-size: $font-xs;
    line-height: 20px; /* 设计 d6c0472f h=20（fs12） */
    color: $color-text-muted;
  }
}

.field {
  margin-top: $gap-lg;
  display: flex;
  flex-direction: column;

  &__label {
    font-weight: 500;
    font-size: $font-sm;
    line-height: 18px; /* 设计 125de7eb 等 3 处 h=18（fs13） */
    color: $color-text-secondary-2;
  }

  /* 设计：输入框 h48 / r12 / 底 rgba(248,250,252,1) / 描边 rgba(226,232,240,1) / padding 0 12 */
  &__box {
    margin-top: $gap-sm;
    height: 48px;
    padding: 0 $gap-md;
    background: $color-bg-page;
    border: 1px solid $color-border;
    border-radius: 12px;
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
    color: $color-text-secondary-2;
    font-weight: 500;
    flex-shrink: 0;
  }

  /* 设计：竖分隔 2x18，色 rgba(226,232,240,1) */
  &__divider {
    width: 2px;
    height: 18px;
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
    line-height: 16.8px; /* 设计 3d537892 fs14×lh1.2 = 16.8（无显式 h） */
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
    line-height: 14.4px; /* 设计 345fa279 fs12×lh1.2 = 14.4（无显式 h） */
    color: $color-text-placeholder;
  }
}

/* 设计：图形验证码图 112x48 r12 底 rgba(238,242,255,1) 描边 rgba(224,231,255,1) 文字 rgba(79,70,229,1) */
.captcha {
  width: 112px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 12px;
  background: $color-primary-weak-2;
  border: 1px solid $color-captcha-border;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;

  &__text {
    font-size: $font-lg;
    letter-spacing: 2px;
    font-weight: 700;
    color: $color-captcha-text;
  }
}

/* 设计：获取验证码按钮 112x48 r12 底 rgba(239,246,255,1) 描边 rgba(191,219,254,1) 文字 13 rgba(37,99,235,1) */
.sms-btn {
  width: 112px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 12px;
  background: $color-primary-weak;
  border: 1px solid $color-brand-en;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;

  &--disabled {
    opacity: 0.6;
  }

  &__text {
    font-size: $font-sm;
    color: $color-primary;
    font-weight: 500;
    white-space: nowrap;
  }
}

/* 设计：主按钮 h50 r14（距上 24） */
.submit {
  margin-top: 24px;
  height: 50px;
  border-radius: 14px;
  background: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;

  &__text {
    font-size: $font-lg;
    color: $color-bg-card;
    font-weight: 600;
  }
}

/* 设计：主按钮之后 spacer 20 */
.divider {
  margin-top: 20px;
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

/* 设计：微信登录按钮 h50 r14 底 rgba(240,253,244,1) 描边 rgba(187,247,208,1)，距上 20 */
.wechat {
  margin-top: 20px;
  height: 50px;
  border-radius: 14px;
  background: $color-wechat-weak;
  border: 1px solid $color-wechat-border;
  box-sizing: border-box;
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
    color: $color-wechat-text;
    font-weight: 500;
  }
}

.agree {
  margin-top: 20px;

  &__row {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
  }

  /* 设计：勾选框 18x18 r6（含 1px 描边的外框尺寸） */
  &__box {
    width: 18px;
    height: 18px;
    margin-right: $gap-sm;
    margin-top: 2px;
    flex-shrink: 0;
    border: 1px solid $color-border;
    border-radius: 6px;
    background: $color-bg-card;
    box-sizing: border-box;
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
    color: $color-text-muted;
  }

  &__link {
    color: $color-primary;
  }
}

/* 设计：免责说明 = container(padding 0/16) 内一张白卡，卡 padding 16/20 r16 描边 rgba(238,242,247,1)，距表单卡片 16 */
.disclaimer-wrap {
  margin-top: $gap-lg;
  padding: 0 16px;
  box-sizing: border-box;
}

.disclaimer {
  padding: 16px 20px;
  background: $color-bg-card;
  border: 1px solid $color-border-chip;
  border-radius: 16px;
  box-sizing: border-box;
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
    margin-right: 6px;
    flex-shrink: 0;
  }

  &__title {
    font-weight: 600;
    font-size: $font-base;
    color: $color-text-primary;
  }

  &__body {
    margin-top: $gap-sm;
    font-size: $font-xs;
    line-height: 1.6;
    color: $color-text-muted;
  }
}

/* 设计：底部说明 padding 32/0/32/0 */
.footer {
  padding: 32px 0;
  display: flex;
  flex-direction: column;
  align-items: center;

  &__text {
    font-size: $font-2xs;
    line-height: 18px; /* 设计 页脚说明 h=18（fs11） */
    color: $color-text-placeholder;
  }
}
</style>
