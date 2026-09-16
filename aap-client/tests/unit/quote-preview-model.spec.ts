/**
 * 序号 12「报价预览与提交 2」（page-12-2）视图模型用例（TDD 切片 1，先红）
 *
 * 文案真源：.calicat/raw/pages/page-12-2/design.tree.json（430 宽 · 设计总高 1027 · 无 TabBar）
 *   本文件里的中文常量**逐字抄自设计树**（硬约束 5：不得改写设计原文）。
 * 业务真源：
 *   10-报价与合同结算PRD §3.1/§3.2（Quote/QuoteItem 字段）· §3.3 时段价 price_time_rules ·
 *     §3.4 阶梯价 price_tier_rules · §3.5 请求级加价 request_rules · §4.1 状态机 DRAFT→SUBMITTED ·
 *     §5.1 提交时校验 V1–V17（服务端闸门，前端只做「有明细/已确认」的本地门禁）
 *   06-报价模型与计费编译规则 §1.2（八大单价 $/1M tokens）· §1.3（时段）· §1.4（阶梯 tiers[].label）
 *   17-spec：错误码 E-1601 状态非法流转（服务端拒绝，前端透传 message）
 * 接口真源：18-API设计OpenAPI.md「Quote」→ /quotes/{quoteId}、/quotes/{quoteId}/submit（前缀 /api/v1）
 *
 * ⚠️ 记 missing-prd（不臆造，已同步台账）：字段级 schema/文案派生规则见 quote-preview-model.ts 顶部说明。
 */
import { describe, expect, it } from 'vitest'
import {
  CONFIRM_TEXT,
  HINT_TEXT,
  BACK_EDIT_TEXT,
  PAGE_TITLE,
  REQUEST_RULE_TEXT,
  SUBMIT_TEXT,
  buildPreviewItems,
  buildSubmitPayload,
  buildTag,
  formatPrice,
  previewRuleLines,
  ruleBlockClass,
  timeRuleText,
  tierRuleText,
  validateSubmit
} from '@/utils/quote-preview-model'

/** 设计稿三个模型的样例数据（逐字抄自 design.tree.json 的可见文本） */
const ITEM_MINI = {
  item_id: 'qi1',
  model_name: 'gpt-4o-mini',
  input_price: 1.2,
  output_price: 3.6,
  cache_read_price: 0.6,
  price_time_rules: {
    tz: 'Asia/Shanghai',
    weekday_scope: 'ALL',
    peak_ranges: [
      { start: '09:00', end: '12:00' },
      { start: '18:00', end: '22:00' }
    ],
    peak_multiplier: 1.2,
    offpeak_multiplier: 0.85
  },
  price_tier_rules: {
    tier_field: 'len',
    tiers: [
      { min: 0, max: 1000000, label: '0–100万' },
      { min: 1000000, max: 5000000, label: '100–500万' },
      { min: 5000000, max: null, label: '500万以上' }
    ]
  },
  request_rules: [{ when: "header('anthropic-beta') has 'fast-mode'", multiplier: 6 }]
}

const ITEM_SONNET = {
  item_id: 'qi2',
  model_name: 'claude-3-5-sonnet',
  input_price: 2,
  output_price: 8,
  cache_read_price: 0.2,
  price_tier_rules: {
    tier_field: 'len',
    tiers: [{ min: 0, max: null }, { min: 0, max: null }, { min: 0, max: null }]
  },
  request_rules: [{ multiplier: 2 }]
}

const ITEM_GPT4O = {
  item_id: 'qi3',
  model_name: 'gpt-4o',
  input_price: 4,
  output_price: 12,
  cache_write_price: 5,
  request_rules: [{ multiplier: 6 }]
}

describe('设计文案常量（逐字抄自 page-12-2 design.tree.json）', () => {
  it('顶栏标题 / 底栏两个按钮', () => {
    expect(PAGE_TITLE).toBe('报价预览')
    expect(BACK_EDIT_TEXT).toBe('返回编辑')
    expect(SUBMIT_TEXT).toBe('提交报价')
  })

  it('确认行与提示条原文', () => {
    expect(CONFIRM_TEXT).toBe('我确认以上价格真实有效，并同意《报价服务条款》')
    expect(HINT_TEXT).toBe('提交后进入运营审核，审核通过将自动编译计费表达式并同步渠道。')
  })

  it('请求规则行的固定说明（三张卡都出现，属设计常量）', () => {
    expect(REQUEST_RULE_TEXT).toBe('请求规则计费：命中条件时按倍率计费，多条命中相乘')
  })
})

describe('modelTag：右上角标签由「有哪些规则」派生', () => {
  it('时段价 + 阶梯价 → 蓝底 primary（卡1）', () => {
    expect(buildTag(ITEM_MINI)).toEqual({ text: '时段价 + 阶梯价', tone: 'primary' })
  })

  it('仅阶梯价 → 绿底 success（卡2）', () => {
    expect(buildTag(ITEM_SONNET)).toEqual({ text: '阶梯价', tone: 'success' })
  })

  it('无任何规则 → 灰底 neutral（卡3）', () => {
    expect(buildTag(ITEM_GPT4O)).toEqual({ text: '仅基础价', tone: 'neutral' })
  })

  it('仅时段价 → primary（设计无该样例，按同一派生规则）', () => {
    expect(buildTag({ ...ITEM_MINI, price_tier_rules: undefined })).toEqual({
      text: '时段价',
      tone: 'primary'
    })
  })
})

describe('价格列：输入/输出必填 + 第三列取缓存价', () => {
  it('数值格式与设计样例逐值一致（一位小数、¥ 前缀）', () => {
    expect(formatPrice(1.2)).toBe('¥1.2')
    expect(formatPrice(3.6)).toBe('¥3.6')
    expect(formatPrice(0.6)).toBe('¥0.6')
    expect(formatPrice(2)).toBe('¥2.0')
    expect(formatPrice(12)).toBe('¥12.0')
    expect(formatPrice(undefined)).toBe('¥0.0')
  })

  it('有 cache_read_price → 第三列「缓存读」（卡1/卡2 设计样例）', () => {
    const [card] = buildPreviewItems({ items: [ITEM_MINI] })
    expect(card.prices).toEqual([
      { label: '输入', value: '¥1.2' },
      { label: '输出', value: '¥3.6' },
      { label: '缓存读', value: '¥0.6' }
    ])
  })

  it('无 cache_read_price 但有 cache_write_price → 第三列「缓存写」（卡3 设计样例）', () => {
    const [card] = buildPreviewItems({ items: [ITEM_GPT4O] })
    expect(card.prices.map((p) => p.label)).toEqual(['输入', '输出', '缓存写'])
    expect(card.prices[2].value).toBe('¥5.0')
  })

  it('两种缓存价都没有 → 只有两列（不臆造第三列）', () => {
    const [card] = buildPreviewItems({
      items: [{ item_id: 'qi4', model_name: 'm', input_price: 1, output_price: 2 }]
    })
    expect(card.prices.map((p) => p.label)).toEqual(['输入', '输出'])
  })
})

describe('时段价行（06-PRD §1.3 peak_ranges + 倍率）', () => {
  it('按设计样例拼出原文：高峰 09:00–12:00 / 18:00–22:00 上浮 1.2 倍，其余时段 0.85 倍', () => {
    expect(timeRuleText(ITEM_MINI.price_time_rules)).toBe(
      '高峰 09:00–12:00 / 18:00–22:00 上浮 1.2 倍，其余时段 0.85 倍'
    )
  })

  it('无时段价规则 → 空串（该行不渲染）', () => {
    expect(timeRuleText(undefined)).toBe('')
    expect(timeRuleText({ peak_ranges: [] })).toBe('')
  })
})

describe('阶梯价行（06-PRD §1.4 tiers[].label）', () => {
  it('档位带 label →「N 档阶梯：label / label / label」', () => {
    expect(tierRuleText(ITEM_MINI.price_tier_rules)).toBe(
      '3 档阶梯：0–100万 / 100–500万 / 500万以上'
    )
  })

  it('档位无 label → 设计卡2 的措辞「N 档阶梯已启用，末档覆盖至不限量」', () => {
    expect(tierRuleText(ITEM_SONNET.price_tier_rules)).toBe('3 档阶梯已启用，末档覆盖至不限量')
  })

  it('无阶梯规则 → 空串', () => {
    expect(tierRuleText(undefined)).toBe('')
  })
})

describe('规则行集合：图标配色 + 渲染顺序（时段 → 阶梯 → 请求规则）', () => {
  it('卡1 三行，时段行琥珀色、其余蓝（设计树 icon fills）', () => {
    const lines = previewRuleLines(ITEM_MINI)
    expect(lines.map((l) => l.tone)).toEqual(['amber', 'primary', 'primary'])
    expect(lines.map((l) => l.text)).toEqual([
      '高峰 09:00–12:00 / 18:00–22:00 上浮 1.2 倍，其余时段 0.85 倍',
      '3 档阶梯：0–100万 / 100–500万 / 500万以上',
      REQUEST_RULE_TEXT
    ])
  })

  it('卡2 两行：阶梯 + 请求规则', () => {
    const lines = previewRuleLines(ITEM_SONNET)
    expect(lines).toHaveLength(2)
    expect(lines[0].tone).toBe('primary')
    expect(lines[1].text).toBe(REQUEST_RULE_TEXT)
  })

  it('卡3 只有请求规则一行（设计稿如此）', () => {
    expect(previewRuleLines(ITEM_GPT4O)).toEqual([{ kind: 'request', tone: 'primary', text: REQUEST_RULE_TEXT }])
  })

  it('没有任何规则 → 空数组', () => {
    expect(previewRuleLines({ item_id: 'x', model_name: 'm', input_price: 1, output_price: 2 })).toEqual([])
  })
})

describe('buildPreviewItems：整页视图模型', () => {
  it('三张卡顺序与模型名与设计稿一致', () => {
    const cards = buildPreviewItems({ items: [ITEM_MINI, ITEM_SONNET, ITEM_GPT4O] })
    expect(cards.map((c) => c.modelName)).toEqual(['gpt-4o-mini', 'claude-3-5-sonnet', 'gpt-4o'])
  })

  it('兼容 snake_case / camelCase 字段名（18-API 未定字段级 schema）', () => {
    const cards = buildPreviewItems({
      items: [{ itemId: 'qi9', modelName: 'm-9', input_price: 1, output_price: 2 }]
    })
    expect(cards[0].modelName).toBe('m-9')
    expect(cards[0].itemId).toBe('qi9')
  })

  it('空/缺失 items → 空数组（不抛异常）', () => {
    expect(buildPreviewItems(null)).toEqual([])
    expect(buildPreviewItems({ items: [] })).toEqual([])
  })
})

describe('validateSubmit：本地门禁（服务端 V1–V17 仍为准）', () => {
  it('未勾选确认 → 拦截', () => {
    expect(validateSubmit({ confirmed: false, itemCount: 3 })).toEqual(['请先确认报价条款'])
  })

  it('没有明细行 → 拦截（V1 明细行≥1）', () => {
    expect(validateSubmit({ confirmed: true, itemCount: 0 })).toEqual(['暂无模型报价，无法提交'])
  })

  it('已确认且有条目 → 放行', () => {
    expect(validateSubmit({ confirmed: true, itemCount: 3 })).toEqual([])
  })
})

describe('buildSubmitPayload：提交请求体', () => {
  it('18-API 无请求体 schema → 不发送任何字段（确认勾选仅前端门禁，记 missing-prd）', () => {
    expect(buildSubmitPayload({ confirmed: true, itemCount: 3 })).toEqual({})
  })
})

describe('ruleBlockClass：规则块间距（设计逐卡如此）', () => {
  it('多条规则 → 首个规则块 padding-top 12（卡1/卡2 设计如此）', () => {
    expect(ruleBlockClass(0, 3)).toBe('card__block--first')
    expect(ruleBlockClass(0, 2)).toBe('card__block--first')
  })

  it('多条规则 → 其后规则块 padding-top 8', () => {
    expect(ruleBlockClass(1, 3)).toBe('card__block--tight')
    expect(ruleBlockClass(2, 3)).toBe('card__block--tight')
  })

  it('只有一条规则 → 用 8（设计卡3 的唯一规则行 wrapper padding-top=8，与卡1/卡2 首个规则行 12 不一致）', () => {
    expect(ruleBlockClass(0, 1)).toBe('card__block--tight')
  })
})

describe('规则行 kind：请求规则行是紧凑行（设计 PNG 实测行高 40，峰谷/阶梯行 44）', () => {
  /* 设计树：请求规则行的图标图层 width=fit_content（其余为固定 18），
     对应 PNG 实测行高 —— 卡1 217..260(44) / 269..312(44) / 321..360(**40**)；
     卡2 501..544(44) / 553..592(**40**)；卡3 729..768(**40**)。
     行高 = padding 10 + 内容 + 10，内容 = max(图标盒, 文本行框)：
       · 峰谷/阶梯行 内容 24（图标盒 fs16×1.5=24）
       · 请求规则行 内容 20（同页实测，与图标图层 fit_content 自洽） */
  it('卡1 三行 kind = time / tier / request', () => {
    expect(previewRuleLines(ITEM_MINI).map((l) => l.kind)).toEqual(['time', 'tier', 'request'])
  })

  it('卡2 = tier / request；卡3 = request（设计稿各卡规则数 3 / 2 / 1）', () => {
    expect(previewRuleLines(ITEM_SONNET).map((l) => l.kind)).toEqual(['tier', 'request'])
    expect(previewRuleLines(ITEM_GPT4O).map((l) => l.kind)).toEqual(['request'])
  })

  it('无规则 → 空数组（不因为 kind 而多渲染空行）', () => {
    expect(previewRuleLines({ item_id: 'x', model_name: 'm' }).map((l) => l.kind)).toEqual([])
  })
})
