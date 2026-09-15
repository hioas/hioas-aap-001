/**
 * 页面 1【账号接入】登录注册 — 校验规则单测
 * 依据：17-零歧义执行规格spec R-01/R-02/R-05 + 21-验收标准 AC-02/AC-03
 */
import { describe, expect, it } from 'vitest'
import { isPhone, isSmsCode, isCaptcha, maskPhone } from '@/utils/validators'

describe('R-01 手机号校验 ^1[3-9]\\d{9}$', () => {
  it.each([
    ['13800138000', true],
    ['19912345678', true],
    ['12800138000', false], // 第二位不能是 2
    ['1380013800', false], // 10 位
    ['138001380000', false], // 12 位
    ['1380013800a', false],
    ['+8613800138000', false],
    ['', false]
  ])('isPhone(%s) === %s', (input, expected) => {
    expect(isPhone(input)).toBe(expected)
  })
})

describe('R-02 验证码格式：短信 6 位数字', () => {
  it.each([
    ['123456', true],
    ['000000', true],
    ['12345', false],
    ['1234567', false],
    ['12345a', false],
    ['', false]
  ])('isSmsCode(%s) === %s', (input, expected) => {
    expect(isSmsCode(input)).toBe(expected)
  })
})

describe('图形验证码：4 位字母数字（设计稿示例 A7K9）', () => {
  it.each([
    ['A7K9', true],
    ['a7k9', true],
    ['1234', true],
    ['A7K', false],
    ['A7K99', false],
    ['A7-9', false]
  ])('isCaptcha(%s) === %s', (input, expected) => {
    expect(isCaptcha(input)).toBe(expected)
  })
})

describe('R-48 手机号脱敏 前3****后4', () => {
  it('13800138000 -> 138****8000', () => {
    expect(maskPhone('13800138000')).toBe('138****8000')
  })
  it('非 11 位原样返回', () => {
    expect(maskPhone('123')).toBe('123')
  })
})
