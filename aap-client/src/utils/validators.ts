/**
 * 校验规则 — 依据 17-零歧义执行规格spec §5（R-01/R-02/R-05/R-48）
 *
 * 注意：uni-app 的 <input type="number"> 在 H5 下 v-model 得到 **number**，
 * 小程序下是 string。所有校验与请求体一律先经 normalize() 归一，避免 trim is not a function。
 */

/** R-01 手机号 ^1[3-9]\d{9}$ */
export const PHONE_RE = /^1[3-9]\d{9}$/
/** R-02 短信验证码 6 位数字；300s 有效、60s 频控、连续 5 次错锁 15 分钟 */
export const SMS_CODE_RE = /^\d{6}$/
/** 图形验证码 4 位字母数字（design 示例 A7K9） */
export const CAPTCHA_RE = /^[A-Za-z0-9]{4}$/

/** 归一为去空白的字符串（number/undefined/null 全部兜住） */
export function normalize(v: unknown): string {
  return String(v ?? '').trim()
}

export function isPhone(v: unknown): boolean {
  return PHONE_RE.test(normalize(v))
}

export function isSmsCode(v: unknown): boolean {
  return SMS_CODE_RE.test(normalize(v))
}

export function isCaptcha(v: unknown): boolean {
  return CAPTCHA_RE.test(normalize(v))
}

/** R-48 手机号脱敏：前 3 + **** + 后 4 */
export function maskPhone(v: unknown): string {
  const s = normalize(v)
  if (!PHONE_RE.test(s)) return s
  return `${s.slice(0, 3)}****${s.slice(7)}`
}
