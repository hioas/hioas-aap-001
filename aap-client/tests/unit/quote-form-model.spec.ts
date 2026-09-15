/**
 * 序号 12-v1【报价管理】新增报价单-初始态（page-26）— 视图模型单测（TDD 切片 1，先红）
 *
 * 文案真源：.calicat/raw/pages/page-26/design.tree.json（430 宽 · 设计总高 1238 · 无 TabBar）
 *   断言里的中文**逐字手抄自设计树**（不引用实现常量，避免自证）：
 *     新增报价单 / 填写基本信息并设置模型报价 / 填写信息 / 名称 / 密钥 / 单号 / 设置报价 / 模型定价
 *     基本信息 / 为必填项 / 报价单名称 / 请输入报价单名称，如：2024Q3 主线路报价 / 0/30
 *     报价单号 / 系统生成 / 保存后自动生成 / QT-XXXXXXXX-XXXX
 *     报价单号由系统按日期与序号规则自动生成，无需手动填写
 *     凭证名称 / 请选择凭证 / 选择凭证后，系统将自动带出该凭证下可用的模型列表
 *     模型列表 / 待带出 / 尚未加载模型 / 请先在上方选择凭证，系统将自动带出可用模型列表
 *     带出的模型数量与凭证权限相关，可在「我的设置」中管理凭证权限范围。
 *     填写须知 / 报价单名称建议包含季度或用途，便于后续在列表中检索。
 *     凭证决定可报价的模型范围，选择后模型列表自动刷新。
 *     首次保存成功后，系统将自动生成报价单号并进入设置报价环节。
 *     保存成功后系统将自动生成报价单号 / 存为草稿 / 保存并继续
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 */
import { describe, expect, it } from 'vitest'
import {
  BAR_HINT,
  BTN_DRAFT,
  BTN_SAVE,
  CARD_BASIC,
  CARD_MODELS,
  CARD_NOTICE,
  CRED_HINT,
  CRED_LABEL,
  CRED_PLACEHOLDER,
  MODEL_CHIP_PENDING,
  MODEL_EMPTY_DESC,
  MODEL_EMPTY_TIP,
  MODEL_EMPTY_TITLE,
  MODEL_PRICING_PAGE,
  NAME_LABEL,
  NAME_MAX,
  NAME_PLACEHOLDER,
  NOTICES,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  QUOTE_NO_HINT,
  QUOTE_NO_LABEL,
  QUOTE_NO_PLACEHOLDER,
  QUOTE_NO_SAMPLE,
  QUOTE_NO_TAG,
  REQUIRED_HINT,
  STEP_ACTIVE,
  STEP_INACTIVE,
  buildFormPayload,
  buildQuoteNoBox,
  iconLineBox,
  modelChipText,
  nameCountText,
  stepsFor,
  textLineBox,
  validateForSave
} from '@/utils/quote-form-model'
import type { QuoteModelRow } from '@/utils/quote-setup-model'

function row(name: string, selected = false): QuoteModelRow {
  return { key: name, name, vendor: '', priceText: '', selected }
}

describe('序号 12-v1 · 设计稿原文逐字一致', () => {
  it('顶部导航与步骤条文案', () => {
    expect(PAGE_TITLE).toBe('新增报价单')
    expect(PAGE_SUBTITLE).toBe('填写基本信息并设置模型报价')
    expect(STEP_ACTIVE.title).toBe('填写信息')
    expect(STEP_ACTIVE.desc).toBe('名称 / 密钥 / 单号')
    expect(STEP_INACTIVE.title).toBe('设置报价')
    expect(STEP_INACTIVE.desc).toBe('模型定价')
  })

  it('基本信息卡文案（含必填提示与占位）', () => {
    expect(CARD_BASIC).toBe('基本信息')
    expect(REQUIRED_HINT).toBe('为必填项')
    expect(NAME_LABEL).toBe('报价单名称')
    expect(NAME_PLACEHOLDER).toBe('请输入报价单名称，如：2024Q3 主线路报价')
    expect(NAME_MAX).toBe(30)
    expect(nameCountText('')).toBe('0/30')
  })

  it('报价单号只读区文案与示例', () => {
    expect(QUOTE_NO_LABEL).toBe('报价单号')
    expect(QUOTE_NO_TAG).toBe('系统生成')
    expect(QUOTE_NO_PLACEHOLDER).toBe('保存后自动生成')
    expect(QUOTE_NO_SAMPLE).toBe('QT-XXXXXXXX-XXXX')
    expect(QUOTE_NO_HINT).toBe('报价单号由系统按日期与序号规则自动生成，无需手动填写')
  })

  it('凭证字段与说明文案', () => {
    expect(CRED_LABEL).toBe('凭证名称')
    expect(CRED_PLACEHOLDER).toBe('请选择凭证')
    expect(CRED_HINT).toBe('选择凭证后，系统将自动带出该凭证下可用的模型列表')
  })

  it('模型列表空态与提示文案', () => {
    expect(CARD_MODELS).toBe('模型列表')
    expect(MODEL_CHIP_PENDING).toBe('待带出')
    expect(MODEL_EMPTY_TITLE).toBe('尚未加载模型')
    expect(MODEL_EMPTY_DESC).toBe('请先在上方选择凭证，系统将自动带出可用模型列表')
    expect(MODEL_EMPTY_TIP).toBe('带出的模型数量与凭证权限相关，可在「我的设置」中管理凭证权限范围。')
  })

  it('填写须知三条与底栏文案', () => {
    expect(CARD_NOTICE).toBe('填写须知')
    expect(NOTICES).toEqual([
      '报价单名称建议包含季度或用途，便于后续在列表中检索。',
      '凭证决定可报价的模型范围，选择后模型列表自动刷新。',
      '首次保存成功后，系统将自动生成报价单号并进入设置报价环节。'
    ])
    expect(BAR_HINT).toBe('保存成功后系统将自动生成报价单号')
    expect(BTN_DRAFT).toBe('存为草稿')
    expect(BTN_SAVE).toBe('保存并继续')
  })
})

describe('序号 12-v1 · stepsFor 步骤条状态', () => {
  it('初始态：步骤 1 高亮、步骤 2 未激活，顺序与设计一致', () => {
    const steps = stepsFor(1)
    expect(steps.map((s) => s.no)).toEqual([1, 2])
    expect(steps.map((s) => s.active)).toEqual([true, false])
    expect(steps.map((s) => s.title)).toEqual(['填写信息', '设置报价'])
  })

  it('第二步态：步骤 2 高亮、步骤 1 已过（仍非激活色）', () => {
    const steps = stepsFor(2)
    expect(steps.map((s) => s.active)).toEqual([false, true])
  })
})

describe('序号 12-v1 · 名称计数与模型 chip', () => {
  it('字数提示按真实长度渲染并受 30 上限', () => {
    expect(nameCountText('2024Q3 主线路报价')).toBe('12/30')
    expect(nameCountText('a'.repeat(NAME_MAX))).toBe('30/30')
  })

  it('未选凭证 → chip 为设计原文「待带出」；已选 → 复用序号 9 的「已选 N / M」', () => {
    expect(modelChipText('', [])).toBe('待带出')
    expect(modelChipText('c1', [row('gpt-4o', true), row('gpt-4o-mini')])).toBe('已选 1 / 2')
    expect(modelChipText('c1', [])).toBe('已选 0 / 0')
  })

  it('已选凭证时单号只读区显示带出态文案（设计原文「保存后自动生成」）', () => {
    expect(buildQuoteNoBox('').text).toBe(QUOTE_NO_PLACEHOLDER)
    expect(buildQuoteNoBox('').sample).toBe(QUOTE_NO_SAMPLE)
    // 服务端返回单号时（本帧设计为「系统生成」态 → 无单号）
    expect(buildQuoteNoBox('QT-20240614-0007').text).toBe('QT-20240614-0007')
  })
})

describe('序号 12-v1 · 行盒规则（设计 tree 声明 lineHeight 1.2 + 图标行盒 = 字号×1.5）', () => {
  it('图标行盒 = 字号 × 1.5（page-10-1-2 实测规则；本页须知标题 18 → 27、底栏说明图标 13 → 19.5）', () => {
    expect(iconLineBox(18)).toBe(27)
    expect(iconLineBox(13)).toBe(19.5)
    expect(iconLineBox(15)).toBe(22.5)
  })

  it('文本行盒 = 字号 × 1.2（本页 design.tree.json 全部文本节点 lineHeight=1.2）', () => {
    expect(textLineBox(11)).toBeCloseTo(13.2, 5)
    expect(textLineBox(12)).toBeCloseTo(14.4, 5)
    expect(textLineBox(14)).toBeCloseTo(16.8, 5)
  })
})

describe('序号 12-v1 · 校验与请求体', () => {
  it('保存并继续：名称必填（设计标 *，顺序固定便于逐条 toast）', () => {
    expect(validateForSave({ name: '  ', credentialId: 'c1', rows: [row('a', true)] })).toEqual(['请输入报价单名称'])
  })

  it('保存并继续：凭证必填（设计标 *）', () => {
    expect(validateForSave({ name: '2024Q3 主线路报价', credentialId: '', rows: [] })).toEqual([
      '请选择凭证',
      '请至少选择一个模型'
    ])
  })

  it('保存并继续：需至少勾选一个模型（10-PRD §5.1 V1，同序号 9 口径）', () => {
    expect(validateForSave({ name: 'x', credentialId: 'c1', rows: [row('a'), row('b', true)] })).toEqual([])
  })

  it('超过 30 字报错', () => {
    expect(validateForSave({ name: 'a'.repeat(31), credentialId: 'c1', rows: [row('a', true)] })).toEqual([
      '报价单名称最多 30 字'
    ])
  })

  it('请求体只带设计稿确有的字段：name + credential_id（推断字段名，missing-prd）', () => {
    expect(buildFormPayload({ name: ' 2024Q3 主线路报价 ', credentialId: 'c1', rows: [row('a', true)] })).toEqual({
      name: '2024Q3 主线路报价',
      credential_id: 'c1'
    })
  })

  it('空值不进请求体（不臆造 provider_id：本帧设计无报价主体控件）', () => {
    expect(buildFormPayload({ name: '', credentialId: '', rows: [] })).toEqual({})
  })

  it('保存成功后进入「设置报价」→ 复用序号 11 的模型定价路由', () => {
    expect(MODEL_PRICING_PAGE).toBe('/pages/model-pricing/index')
  })
})
