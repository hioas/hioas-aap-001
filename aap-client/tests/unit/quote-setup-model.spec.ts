/**
 * 序号 9【报价管理】模型报价设置（page-9）视图模型 — 纯逻辑用例
 *
 * 设计真源：.calicat/raw/pages/page-9/design.tree.json（430 宽 · 设计总高 1211）
 *   文案逐字取自设计树（.agents/state/page-9-nodes.txt）：
 *     顶部 672c8036「新增报价单」/ 307dd47e「填写基本信息并设置模型报价」
 *     卡1 报价主体 caf33d0e 右侧 chip「去新增」/ 说明 84580e5c「下拉选择主体公司，可在我的公司中新增」
 *     卡2 基本信息 829d6574「已完善」/ 名称 13/30 · 凭证说明「已自动带出该凭证下 5 个可用模型」
 *     卡3 模型列表 / f73af6cd「已选 3 / 5」/ 工具栏「全选模型」「按凭证实时带出」
 *       行文案模板 595d9b82「输入 $2.50 / 输出 $10.00 / 1M token」· 状态标 20018a68「已选」/ 1391570b「可选」
 *       底部 0e98f68a「价格均以 $/1M token 计价，勾选后可在下一步设置单价」
 *     提示卡 150c8da1「模型列表随凭证变化自动刷新，切换凭证将重置当前勾选状态，\n请确认后再保存。」
 *     底栏 6e0463ba「存为草稿」/ d3c55d1d「保存」
 *
 * 业务真源：10-报价与合同结算PRD §3.2 QuoteItem（model_name/model_alias/input_price/output_price…）
 *   §4.1 状态机（DRAFT 可编辑/暂存/提交）· §5.1 V1「明细行≥1」在**提交**时校验（A2 草稿无限暂存）
 *   15-数据字典 aap_quote / aap_quote_item（唯一 (quote_id, model_name)）
 *   17-spec E-1602 未通过检测不可报价（服务端判定，前端只展示 message）
 *   凭证模型清单：17-spec 名词表「凭证（base_url+api_key+model_list）」
 */
import { describe, expect, it } from 'vitest'
import {
  BTN_DRAFT,
  BTN_SAVE,
  CARD_BASIC,
  CARD_MODELS,
  CARD_SUBJECT,
  CHIP_DONE,
  CHIP_GO_ADD,
  COUNT_TEMPLATE_ZERO,
  CRED_HINT_TEMPLATE,
  MODEL_LIST_NOTE,
  MODEL_STATUS_OPTIONAL,
  MODEL_STATUS_SELECTED,
  NAME_LABEL,
  NAME_MAX,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  SELECT_ALL_TEXT,
  SOURCE_HINT,
  SUBJECT_HINT,
  TIP_TEXT,
  allSelected,
  buildItemsPayload,
  buildModelRows,
  buildQuotePayload,
  countText,
  credentialHintText,
  nameCountText,
  nameError,
  priceText,
  selectedCount,
  selectedNames,
  setAllSelected,
  toggleModel,
  validateForDraft,
  validateForSave
} from '@/utils/quote-setup-model'

const CATALOG = [
  { model_name: 'gpt-4o', vendor: 'OpenAI', input_price: 2.5, output_price: 10, selected: true },
  { model_name: 'gpt-4o-mini', vendor: 'OpenAI', input_price: 0.15, output_price: 0.6, selected: true },
  { model_name: 'claude-3-5-sonnet', vendor: 'Anthropic', input_price: 3, output_price: 15, selected: true },
  { model_name: 'gemini-1.5-pro', vendor: 'Google', input_price: 1.25, output_price: 5, selected: false },
  { model_name: 'deepseek-chat', vendor: 'DeepSeek', input_price: 0.14, output_price: 0.28, selected: false }
]

describe('序号 9 页面文案（必须与设计稿逐字一致）', () => {
  it('顶部与卡片标题、按钮、提示文案取自设计稿原文', () => {
    expect(PAGE_TITLE).toBe('新增报价单')
    expect(PAGE_SUBTITLE).toBe('填写基本信息并设置模型报价')
    expect(CARD_SUBJECT).toBe('报价主体')
    expect(CHIP_GO_ADD).toBe('去新增')
    expect(SUBJECT_HINT).toBe('下拉选择主体公司，可在我的公司中新增')
    expect(CARD_BASIC).toBe('基本信息')
    expect(CHIP_DONE).toBe('已完善')
    expect(NAME_LABEL).toBe('报价单名称')
    expect(CARD_MODELS).toBe('模型列表')
    expect(SELECT_ALL_TEXT).toBe('全选模型')
    expect(SOURCE_HINT).toBe('按凭证实时带出')
    expect(MODEL_STATUS_SELECTED).toBe('已选')
    expect(MODEL_STATUS_OPTIONAL).toBe('可选')
    expect(MODEL_LIST_NOTE).toBe('价格均以 $/1M token 计价，勾选后可在下一步设置单价')
    expect(TIP_TEXT).toBe('模型列表随凭证变化自动刷新，切换凭证将重置当前勾选状态，\n请确认后再保存。')
    expect(BTN_DRAFT).toBe('存为草稿')
    expect(BTN_SAVE).toBe('保存')
  })

  it('计数/带出/字数提示模板与设计稿一致', () => {
    expect(COUNT_TEMPLATE_ZERO).toBe('已选 0 / 0')
    expect(credentialHintText(5)).toBe('已自动带出该凭证下 5 个可用模型')
    expect(nameCountText('2024Q3 主线路报价')).toBe('12/30')
    expect(NAME_MAX).toBe(30)
  })
})

describe('模型行构建（按凭证实时带出）', () => {
  it('5 个模型 → 名称/厂商/价格文案/勾选态逐条对齐设计稿', () => {
    const rows = buildModelRows(CATALOG)
    expect(rows).toHaveLength(5)
    expect(rows.map((r) => r.name)).toEqual([
      'gpt-4o',
      'gpt-4o-mini',
      'claude-3-5-sonnet',
      'gemini-1.5-pro',
      'deepseek-chat'
    ])
    expect(rows.map((r) => r.vendor)).toEqual(['OpenAI', 'OpenAI', 'Anthropic', 'Google', 'DeepSeek'])
    expect(rows[0].priceText).toBe('输入 $2.50 / 输出 $10.00 / 1M token')
    expect(rows[1].priceText).toBe('输入 $0.15 / 输出 $0.60 / 1M token')
    expect(rows[2].priceText).toBe('输入 $3.00 / 输出 $15.00 / 1M token')
    expect(rows[3].priceText).toBe('输入 $1.25 / 输出 $5.00 / 1M token')
    expect(rows[4].priceText).toBe('输入 $0.14 / 输出 $0.28 / 1M token')
    expect(rows.map((r) => r.selected)).toEqual([true, true, true, false, false])
  })

  it('价格缺失时不编造价格行（返回空串，页面不渲染该行）', () => {
    expect(priceText(undefined, 5)).toBe('')
    expect(priceText(2.5, undefined)).toBe('')
    expect(priceText(undefined, undefined)).toBe('')
    expect(priceText(0.5, 1)).toBe('输入 $0.50 / 输出 $1.00 / 1M token')
  })

  it('空/缺失目录 → 空行（不伪造模型）', () => {
    expect(buildModelRows(undefined)).toEqual([])
    expect(buildModelRows([])).toEqual([])
  })

  it('同行 model_name 重复时 key 唯一（15-数据字典 C3/(quote_id, model_name) 唯一）', () => {
    const rows = buildModelRows([
      { model_name: 'gpt-4o', input_price: 1, output_price: 2 },
      { model_name: 'gpt-4o', input_price: 1, output_price: 2 }
    ])
    expect(new Set(rows.map((r) => r.key)).size).toBe(2)
  })

  it('缺名的行被丢弃（不渲染无名模型行）', () => {
    expect(buildModelRows([{ vendor: 'OpenAI' }, { model_name: 'gpt-4o' }])).toHaveLength(1)
  })
})

describe('勾选 / 全选 / 计数', () => {
  it('点单行 → 该行切换，其它行不动', () => {
    const rows = buildModelRows(CATALOG)
    const after = toggleModel(rows, rows[3].key)
    expect(after[3].selected).toBe(true)
    expect(after.map((r) => r.selected)).toEqual([true, true, true, true, false])
    // 纯函数：不改原数组
    expect(rows[3].selected).toBe(false)
  })

  it('全选 → 全部勾选；取消全选 → 全部取消', () => {
    const rows = buildModelRows(CATALOG)
    const all = setAllSelected(rows, true)
    expect(all.every((r) => r.selected)).toBe(true)
    expect(allSelected(all)).toBe(true)
    expect(setAllSelected(all, false).some((r) => r.selected)).toBe(false)
    expect(allSelected(rows)).toBe(false)
  })

  it('计数文案「已选 N / M」与设计一致', () => {
    const rows = buildModelRows(CATALOG)
    expect(selectedCount(rows)).toBe(3)
    expect(countText(rows)).toBe('已选 3 / 5')
    expect(countText(setAllSelected(rows, true))).toBe('已选 5 / 5')
    expect(countText([])).toBe('已选 0 / 0')
  })

  it('selectedNames 只给出已选模型名（提交明细行用）', () => {
    expect(selectedNames(buildModelRows(CATALOG))).toEqual(['gpt-4o', 'gpt-4o-mini', 'claude-3-5-sonnet'])
  })
})

describe('校验（PRD 10 §5.1 V1 明细行≥1 · A2 草稿无限暂存）', () => {
  const base = {
    name: '2024Q3 主线路报价',
    providerId: 'p1',
    credentialId: 'c1',
    rows: buildModelRows(CATALOG)
  }

  it('名称必填 / 超 30 字拦截', () => {
    expect(nameError('')).toBe('请输入报价单名称')
    expect(nameError('   ')).toBe('请输入报价单名称')
    expect(nameError('a'.repeat(31))).toBe('报价单名称最多 30 字')
    expect(nameError('2024Q3 主线路报价')).toBe('')
  })

  it('保存：缺主体 / 缺凭证 / 未选模型 各自拦截（顺序固定）', () => {
    expect(validateForSave({ ...base, providerId: '' })).toEqual(['请选择报价主体'])
    expect(validateForSave({ ...base, credentialId: '' })).toEqual(['请选择凭证'])
    expect(validateForSave({ ...base, rows: setAllSelected(base.rows, false) })).toEqual(['请至少选择一个模型'])
    expect(validateForSave({ ...base, name: '' })).toEqual(['请输入报价单名称'])
    expect(validateForSave(base)).toEqual([])
  })

  it('存为草稿：允许不完整（A2 草稿无限暂存），不做必填拦截', () => {
    expect(validateForDraft({ name: '', providerId: '', credentialId: '', rows: [] })).toEqual([])
  })
})

describe('提交体构造（不臆造字段：只发有依据的键）', () => {
  it('报价单主体 → POST /quotes 的请求体（字段依据 15-数据字典 aap_quote）', () => {
    expect(
      buildQuotePayload({ name: '2024Q3 主线路报价', providerId: 'p1', credentialId: 'c1', rows: [] })
    ).toEqual({
      name: '2024Q3 主线路报价',
      provider_id: 'p1',
      credential_id: 'c1'
    })
  })

  it('空值键不出现（避免把空串写进服务端）', () => {
    expect(buildQuotePayload({ name: '', providerId: '', credentialId: '', rows: [] })).toEqual({})
  })

  it('明细行 → 只带 model_name（单价在设计稿里属「下一步」，PRD 10 §5.1 V3 在提交时校验）', () => {
    expect(buildItemsPayload(buildModelRows(CATALOG))).toEqual({
      items: [{ model_name: 'gpt-4o' }, { model_name: 'gpt-4o-mini' }, { model_name: 'claude-3-5-sonnet' }]
    })
  })

  it('未勾选任何模型 → 不发 items 请求（返回空数组）', () => {
    expect(buildItemsPayload(setAllSelected(buildModelRows(CATALOG), false))).toEqual({ items: [] })
    expect(buildItemsPayload([])).toEqual({ items: [] })
  })
})
