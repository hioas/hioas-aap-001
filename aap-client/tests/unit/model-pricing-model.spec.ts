/**
 * 序号 11【报价管理】模型定价-详情（page-11）— 纯模型单测（TDD 切片 1）
 *
 * 文案真源：.calicat/raw/pages/page-11/design.tree.json（430 宽 · 设计总高 1541 · 无 TabBar）
 *   以下断言里的中文一律**手抄自设计树**（不引用实现常量，避免自证）：
 *     模型定价 / 保存 / 始终匹配（默认档位）· 输入 $2.50 输出 $10.00 / 1M token
 *     档位 / base / 按 token / 添加计费分支
 *     Token 价格 / $/1M token / 输入价格 / 输出价格 / 缓存读取价格 / 缓存写入价格 / 1 小时缓存写入价格 / 媒体定价
 *     图像输入价格 / 图片缓存输入价格 / 图像输出价格 / 音频输入价格 / 音频输出价格
 *     请求规则计费 / 条件满足时，最终价格乘以 X；多条命中的倍率会相乘；小于 1 的值为折扣。 / 规则组 #1
 *     时间 / 小时 / Asia/Shanghai / 大于等于 / 值 / 新增参数/Header / 新增时间条件 / 倍率 / 1.0
 *     匹配条件时，最终费用 = 基础费用 × 倍率 / 新增规则组 / 点击展开，配置计费请求规则 / 保存价格
 * 接口真源：18-API设计OpenAPI.md「Quote」/quotes、/{quoteId}/items、/items/{itemId}（路径原文；方法与字段级 schema 为推断）
 * 业务真源：06-报价模型与计费编译规则 §1.2 八大单价 / §1.3 时段价规则 / §4.2 边界冲突（单价为负、倍率 ≤0 → 拒绝）
 * 缺口（记 missing-prd，不臆造）：计价方式选项集合、请求规则条件枚举、档位分支语义、「启用」勾选字段
 */
import { describe, expect, it } from 'vitest'
import {
  ADD_BRANCH_TEXT,
  ADD_PARAM_TEXT,
  ADD_RULE_GROUP_TEXT,
  ADD_TIME_TEXT,
  BOTTOM_SAVE_TEXT,
  DEFAULT_MULTIPLIER,
  DEFAULT_RULE_FIELD,
  DEFAULT_RULE_GRANULARITY,
  DEFAULT_RULE_OP,
  DEFAULT_RULE_TZ,
  MEDIA_PRICE_FIELDS,
  MEDIA_TITLE,
  MODE_FALLBACK,
  MULTIPLIER_LABEL,
  MULTIPLIER_NOTE,
  NAV_SAVE_TEXT,
  PAGE_SUBTITLE,
  PRICE_UNIT_LABEL,
  RULE_CARD_TITLE,
  RULE_HINT,
  RULE_NOTE,
  TIER_LABEL,
  TOKEN_CARD_TITLE,
  TOKEN_PRICE_FIELDS,
  VALUE_PLACEHOLDER,
  addRuleGroup,
  buildItemPayload,
  buildItemViewModel,
  buildPriceFields,
  buildRuleGroups,
  formatPrice,
  removeRuleGroup,
  ruleGroupTitle,
  setPriceValue,
  setRuleValue,
  tierSummaryText,
  togglePriceField,
  validateItem,
  type PriceField,
  type RequestRuleGroup
} from '@/utils/model-pricing-model'

/** 设计稿样例（逐值抄自 design.tree.json：输入 2.50 / 输出 10.00 / 其余 0） */
const ITEM_RAW = {
  item_id: 'qi1',
  quote_id: 'q9',
  model_name: 'gpt-4o',
  tier: 'base',
  billing_mode: '按 token',
  input_price: 2.5,
  output_price: 10,
  cache_read_price: 0,
  cache_write_price: 0,
  cache_write_1h_price: 0,
  image_input_price: 0,
  image_cache_input_price: 0,
  image_output_price: 0,
  audio_input_price: 0,
  audio_output_price: 0,
  request_rules: [
    { tz: 'Asia/Shanghai', multiplier: 1.0, field: '时间', granularity: '小时', op: '大于等于', value: '' }
  ]
}

describe('序号 11 · 设计稿文案常量（逐字）', () => {
  it('顶栏 / 底部操作条文案与设计稿一致', () => {
    expect(PAGE_SUBTITLE).toBe('模型定价')
    expect(NAV_SAVE_TEXT).toBe('保存')
    expect(BOTTOM_SAVE_TEXT).toBe('保存价格')
  })

  it('卡2 / 卡3 / 卡4 标题与说明文案与设计稿一致', () => {
    expect(TIER_LABEL).toBe('档位')
    expect(MODE_FALLBACK).toBe('按 token')
    expect(ADD_BRANCH_TEXT).toBe('添加计费分支')
    expect(TOKEN_CARD_TITLE).toBe('Token 价格')
    expect(PRICE_UNIT_LABEL).toBe('$/1M token')
    expect(MEDIA_TITLE).toBe('媒体定价')
    expect(RULE_CARD_TITLE).toBe('请求规则计费')
    expect(RULE_NOTE).toBe('条件满足时，最终价格乘以 X；多条命中的倍率会相乘；小于 1 的值为折扣。')
    expect(MULTIPLIER_LABEL).toBe('倍率')
    expect(MULTIPLIER_NOTE).toBe('匹配条件时，最终费用 = 基础费用 × 倍率')
    expect(ADD_RULE_GROUP_TEXT).toBe('新增规则组')
    expect(ADD_PARAM_TEXT).toBe('新增参数/Header')
    expect(ADD_TIME_TEXT).toBe('新增时间条件')
    expect(RULE_HINT).toBe('点击展开，配置计费请求规则')
    expect(VALUE_PLACEHOLDER).toBe('值')
  })
})

describe('序号 11 · 单价字段清单（顺序与文案严格照设计稿）', () => {
  it('Token 价格 5 个字段按设计顺序 + 键名对齐 06-PRD §1.2', () => {
    expect(TOKEN_PRICE_FIELDS.map((f) => f.label)).toEqual([
      '输入价格',
      '输出价格',
      '缓存读取价格',
      '缓存写入价格',
      '1 小时缓存写入价格'
    ])
    expect(TOKEN_PRICE_FIELDS.map((f) => f.key)).toEqual([
      'input_price',
      'output_price',
      'cache_read_price',
      'cache_write_price',
      'cache_write_1h_price'
    ])
  })

  it('媒体定价 5 个字段按设计顺序（图像列 3 + 音频列 2）', () => {
    expect(MEDIA_PRICE_FIELDS.map((f) => f.label)).toEqual([
      '图像输入价格',
      '图片缓存输入价格',
      '图像输出价格',
      '音频输入价格',
      '音频输出价格'
    ])
  })
})

describe('序号 11 · 价格格式化与启用态（与设计稿样例逐值一致）', () => {
  it('formatPrice：0 → "0"，非 0 → 两位小数', () => {
    expect(formatPrice(0)).toBe('0')
    expect(formatPrice(2.5)).toBe('2.50')
    expect(formatPrice(10)).toBe('10.00')
    expect(formatPrice(undefined)).toBe('0')
    expect(formatPrice(null)).toBe('0')
    expect(formatPrice('')).toBe('0')
  })

  it('buildPriceFields：仅有值的字段为「已勾选」（设计稿只有输入/输出勾选）', () => {
    const fields = buildPriceFields(ITEM_RAW)
    expect(fields).toHaveLength(10)
    const on = fields.filter((f) => f.enabled).map((f) => f.label)
    expect(on).toEqual(['输入价格', '输出价格'])
    expect(fields.find((f) => f.label === '缓存读取价格')?.value).toBe('0')
  })

  it('buildPriceFields：两列顺序 —— Token 5 个后接媒体 5 个', () => {
    const fields = buildPriceFields(ITEM_RAW)
    expect(fields.map((f) => f.group)).toEqual([
      'token',
      'token',
      'token',
      'token',
      'token',
      'media',
      'media',
      'media',
      'media',
      'media'
    ])
  })

  it('togglePriceField：只翻转该字段的启用态，其余不动', () => {
    const fields = buildPriceFields(ITEM_RAW)
    const next = togglePriceField(fields, 'cache_read_price')
    expect(next.find((f) => f.key === 'cache_read_price')?.enabled).toBe(true)
    expect(next.find((f) => f.key === 'input_price')?.enabled).toBe(true)
    expect(next.find((f) => f.key === 'output_price')?.enabled).toBe(true)
  })

  it('setPriceValue：写入原始输入串（不立刻格式化，避免打字被吞）', () => {
    const fields = setPriceValue(buildPriceFields(ITEM_RAW), 'input_price', '3.5')
    expect(fields.find((f) => f.key === 'input_price')?.value).toBe('3.5')
  })

  it('tierSummaryText：设计稿原文由「档位固定语 + 输入/输出价」拼出', () => {
    expect(tierSummaryText(buildPriceFields(ITEM_RAW))).toBe(
      '始终匹配（默认档位）· 输入 $2.50 输出 $10.00 / 1M token'
    )
  })
})

describe('序号 11 · 请求规则组（设计稿 1 组：时间/小时/Asia/Shanghai/大于等于/值/1.0）', () => {
  it('buildRuleGroups：缺字段时回落设计默认值，标题按序号生成', () => {
    const groups = buildRuleGroups({ request_rules: [{}] })
    expect(groups).toHaveLength(1)
    expect(ruleGroupTitle(groups[0])).toBe('规则组 #1')
    expect(groups[0].field).toBe(DEFAULT_RULE_FIELD)
    expect(groups[0].granularity).toBe(DEFAULT_RULE_GRANULARITY)
    expect(groups[0].tz).toBe(DEFAULT_RULE_TZ)
    expect(groups[0].op).toBe(DEFAULT_RULE_OP)
    expect(groups[0].multiplier).toBe(DEFAULT_MULTIPLIER)
  })

  it('设计默认值逐字：时间 / 小时 / Asia/Shanghai / 大于等于 / 1.0', () => {
    expect(DEFAULT_RULE_FIELD).toBe('时间')
    expect(DEFAULT_RULE_GRANULARITY).toBe('小时')
    expect(DEFAULT_RULE_TZ).toBe('Asia/Shanghai')
    expect(DEFAULT_RULE_OP).toBe('大于等于')
    expect(DEFAULT_MULTIPLIER).toBe('1.0')
  })

  it('buildRuleGroups：无 request_rules 时渲染设计稿那一组（缺省 1 组）', () => {
    expect(buildRuleGroups({}).length + buildRuleGroups(undefined).length).toBeGreaterThanOrEqual(0)
    const base = buildRuleGroups({})
    expect(base.length).toBe(1)
  })

  it('addRuleGroup：追加后序号连续（规则组 #1 / #2）', () => {
    const groups = addRuleGroup(buildRuleGroups({}))
    expect(groups).toHaveLength(2)
    expect(groups.map((g) => ruleGroupTitle(g))).toEqual(['规则组 #1', '规则组 #2'])
  })

  it('removeRuleGroup：删除后重新编号，且不会删到空数组', () => {
    const two = addRuleGroup(buildRuleGroups({}))
    const one = removeRuleGroup(two, 1)
    expect(one).toHaveLength(1)
    expect(ruleGroupTitle(one[0])).toBe('规则组 #1')
    expect(removeRuleGroup(one, 1)).toHaveLength(1)
  })

  it('setRuleValue：按字段写入单组（不改其它组）', () => {
    const two = addRuleGroup(buildRuleGroups({}))
    const next = setRuleValue(two, 2, 'multiplier', '1.5')
    expect(next[1].multiplier).toBe('1.5')
    expect(next[0].multiplier).toBe('1.0')
  })
})

describe('序号 11 · 校验（06-PRD §1.2 必填 + §4.2 边界冲突）', () => {
  const state = (over: Partial<{ priceFields: PriceField[]; ruleGroups: RequestRuleGroup[] }> = {}) => ({
    priceFields: over.priceFields ?? buildPriceFields(ITEM_RAW),
    ruleGroups: over.ruleGroups ?? buildRuleGroups(ITEM_RAW)
  })

  it('设计稿样例状态无错误', () => {
    expect(validateItem(state())).toEqual([])
  })

  it('必填的输入价格清空 → 报错（06-PRD §1.2 input_price 必填）', () => {
    const fields = setPriceValue(buildPriceFields(ITEM_RAW), 'input_price', '')
    expect(validateItem(state({ priceFields: fields }))[0]).toBe('请输入输入价格')
  })

  it('输出价格为负数 → 拒绝（06-PRD §4.2「单价为负 → 拒绝」）', () => {
    const fields = setPriceValue(buildPriceFields(ITEM_RAW), 'output_price', '-1')
    expect(validateItem(state({ priceFields: fields }))[0]).toBe('输出价格不能为负数')
  })

  it('输入价格非法数字 → 报错', () => {
    const fields = setPriceValue(buildPriceFields(ITEM_RAW), 'input_price', 'abc')
    expect(validateItem(state({ priceFields: fields }))[0]).toBe('请输入正确的输入价格')
  })

  it('未勾选的字段即使是 0 也不报错（可选价 06-PRD §1.2 ❌）', () => {
    const fields = setPriceValue(buildPriceFields(ITEM_RAW), 'cache_read_price', '')
    expect(validateItem(state({ priceFields: fields }))).toEqual([])
  })

  it('倍率为 0 → 拒绝（06-PRD §4.2「倍率 ≤0 → 拒绝」）', () => {
    const groups = setRuleValue(buildRuleGroups(ITEM_RAW), 1, 'multiplier', '0')
    expect(validateItem(state({ ruleGroups: groups }))[0]).toBe('倍率必须大于 0')
  })

  it('倍率非数字 → 拒绝', () => {
    const groups = setRuleValue(buildRuleGroups(ITEM_RAW), 1, 'multiplier', 'x')
    expect(validateItem(state({ ruleGroups: groups }))[0]).toBe('请输入正确的倍率')
  })
})

describe('序号 11 · 提交体（只带启用字段 + 规则组；不臆造未定义字段）', () => {
  it('buildItemPayload：启用的价格按数字提交，未启用的不出现', () => {
    const payload = buildItemPayload({
      priceFields: buildPriceFields(ITEM_RAW),
      ruleGroups: buildRuleGroups(ITEM_RAW)
    })
    expect(payload.input_price).toBe(2.5)
    expect(payload.output_price).toBe(10)
    expect('cache_read_price' in payload).toBe(false)
    expect('audio_output_price' in payload).toBe(false)
  })

  it('buildItemPayload：档位 / 计价方式 / 规则组一并提交', () => {
    const payload = buildItemPayload({
      priceFields: buildPriceFields(ITEM_RAW),
      ruleGroups: setRuleValue(buildRuleGroups(ITEM_RAW), 1, 'value', '9'),
      tier: 'base',
      billingMode: '按 token'
    })
    expect(payload.tier).toBe('base')
    expect(payload.billing_mode).toBe('按 token')
    expect(Array.isArray(payload.request_rules)).toBe(true)
    expect((payload.request_rules as RequestRuleGroup[])[0].value).toBe('9')
  })

  it('buildItemPayload：勾选但值为空的可选价按 0 提交（勾选 = 启用）', () => {
    const fields = togglePriceField(buildPriceFields(ITEM_RAW), 'cache_read_price')
    const payload = buildItemPayload({ priceFields: fields, ruleGroups: buildRuleGroups(ITEM_RAW) })
    expect(payload.cache_read_price).toBe(0)
  })
})

describe('序号 11 · 页面视图模型（接口响应 → 页面数据）', () => {
  it('buildItemViewModel：取到模型名 / 档位 / 计价方式 / 单价 / 规则组', () => {
    const vm = buildItemViewModel(ITEM_RAW)
    expect(vm.itemId).toBe('qi1')
    expect(vm.quoteId).toBe('q9')
    expect(vm.modelName).toBe('gpt-4o')
    expect(vm.tier).toBe('base')
    expect(vm.billingMode).toBe('按 token')
    expect(vm.priceFields).toHaveLength(10)
    expect(vm.ruleGroups).toHaveLength(1)
  })

  it('buildItemViewModel：字段缺失时给出安全回落（不崩、不臆造具体值）', () => {
    const vm = buildItemViewModel({ item_id: 'qi2', model_name: 'claude-3-5-sonnet' })
    expect(vm.itemId).toBe('qi2')
    expect(vm.modelName).toBe('claude-3-5-sonnet')
    expect(vm.tier).toBe('')
    expect(vm.billingMode).toBe(MODE_FALLBACK)
    expect(vm.priceFields.every((f) => f.enabled === false)).toBe(true)
  })
})
