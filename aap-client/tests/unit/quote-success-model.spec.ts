/**
 * 序号 12-v3【报价管理】新增报价单-保存成功（page-29）— 视图模型（TDD 切片 1，先红）
 *
 * 设计真源：.calicat/raw/pages/page-29/design.tree.json（430 宽 · 设计帧 430x1018 · 无 TabBar）
 *   顶部导航「报价单已创建 / 报价单号已自动生成」· 成功头部卡「报价单创建成功 / 已保存基本信息并带出模型清单」+ 单号展示条「报价单号 / QT-… / 复制」
 *   结果摘要卡 5 行（报价单名称 / 凭证名称〔环境小标 + 脱敏 key〕/ 参与报价模型〔已勾选 N 个〕/ 报价单号〔绿勾 + 蓝字〕/ 当前状态〔灰点 + 草稿〕）
 *   已带出模型卡（共 M 个 / 勾选 N 个 + 5 个模型标签，勾选蓝底 / 未勾选灰底）· 下一步提示卡 · 底部「继续设置模型报价 / 返回报价单列表」
 *
 * 接口真源：.calicat/prd/18-API设计OpenAPI.md「Quote」→ /quotes/{quoteId}（详情，含明细行）·
 *   「Credential」→ /credentials/{id}（凭证详情，含 model_list）；前缀 /api/v1。
 *   18-API 只列路径未列方法与字段级 schema → 方法（GET）与字段名为 REST 语义推断（missing-prd，不臆造）。
 * 状态真源：17-spec QuoteStatus + 10-PRD §4.1（新建报价单初始 DRAFT）；设计 5 态胶囊复用序号 8 的 STATUS_META。
 */
import { describe, expect, it } from 'vitest'
import {
  BTN_PRIMARY,
  BTN_SECONDARY,
  CARD_MODELS,
  COPY_TEXT,
  CREDENTIAL_ID_KEY,
  MODEL_PRICING_PAGE,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  QUOTES_LIST_PAGE,
  QUOTE_ID_KEY,
  QUOTE_NO_LABEL,
  ROW_CRED,
  ROW_MODELS,
  ROW_NAME,
  ROW_STATUS,
  SUCCESS_DESC,
  SUCCESS_TITLE,
  SUMMARY_TITLE,
  TIP_TEXT,
  buildModelTags,
  buildSuccessView,
  modelTotalText,
  resolveStatus,
  selectedCountText
} from '@/utils/quote-success-model'

/* ---------- 设计稿原文（逐字取自 page-29 design.tree.json） ---------- */

describe('序号 12-v3 · 文案与路由常量（设计稿逐字）', () => {
  it('顶栏与成功头部卡文案', () => {
    expect(PAGE_TITLE).toBe('报价单已创建')
    expect(PAGE_SUBTITLE).toBe('报价单号已自动生成')
    expect(SUCCESS_TITLE).toBe('报价单创建成功')
    expect(SUCCESS_DESC).toBe('已保存基本信息并带出模型清单')
  })

  it('结果摘要卡与模型卡文案', () => {
    expect(SUMMARY_TITLE).toBe('结果摘要')
    expect(ROW_NAME).toBe('报价单名称')
    expect(ROW_CRED).toBe('凭证名称')
    expect(ROW_MODELS).toBe('参与报价模型')
    expect(ROW_STATUS).toBe('当前状态')
    expect(QUOTE_NO_LABEL).toBe('报价单号')
    expect(CARD_MODELS).toBe('已带出模型')
    expect(COPY_TEXT).toBe('复制')
  })

  it('提示卡与底部按钮文案', () => {
    expect(TIP_TEXT).toBe('下一步可为勾选模型设置输入/输出单价，设置完成即可提交审核。')
    expect(BTN_PRIMARY).toBe('继续设置模型报价')
    expect(BTN_SECONDARY).toBe('返回报价单列表')
  })

  it('路由与入参 storage 键：模型定价页复用序号 11 目标，键名与既有页面一致', () => {
    expect(MODEL_PRICING_PAGE).toBe('/pages/model-pricing/index')
    expect(QUOTES_LIST_PAGE).toBe('/pages/quotes/index')
    expect(QUOTE_ID_KEY).toBe('aap_quote_id')
    expect(CREDENTIAL_ID_KEY).toBe('aap_credential_id')
  })
})

/* ---------- 计数文案 ---------- */

describe('序号 12-v3 · 计数文案（设计原文格式）', () => {
  it('「已勾选 N 个」按真实勾选数渲染', () => {
    expect(selectedCountText(3)).toBe('已勾选 3 个')
    expect(selectedCountText(0)).toBe('已勾选 0 个')
  })

  it('「共 M 个 / 勾选 N 个」按真实总数与勾选数渲染（不照抄设计样例 5/3）', () => {
    expect(modelTotalText(5, 3)).toBe('共 5 个 / 勾选 3 个')
    expect(modelTotalText(2, 0)).toBe('共 2 个 / 勾选 0 个')
  })
})

/* ---------- 模型标签 ---------- */

const MODELS = [
  { model_name: 'gpt-4o', vendor: 'OpenAI', selected: true },
  { model_name: 'gpt-4o-mini', vendor: 'OpenAI', selected: false },
  { model_name: 'claude-3-5', vendor: 'Anthropic', selected: true },
  { model_name: 'gemini-1.5-pro', vendor: 'Google', selected: false },
  { model_name: 'deepseek-chat', vendor: 'DeepSeek', selected: true }
]

describe('序号 12-v3 · 已带出模型标签', () => {
  it('报价单明细行（items）优先判定勾选态，顺序沿用凭证 model_list', () => {
    const tags = buildModelTags(MODELS, ['gpt-4o', 'claude-3-5', 'deepseek-chat'])
    expect(tags.map((t) => t.name)).toEqual(['gpt-4o', 'gpt-4o-mini', 'claude-3-5', 'gemini-1.5-pro', 'deepseek-chat'])
    expect(tags.filter((t) => t.selected).map((t) => t.name)).toEqual(['gpt-4o', 'claude-3-5', 'deepseek-chat'])
  })

  it('报价单无明细行时回退凭证 model_list 的 selected 标记', () => {
    const tags = buildModelTags(MODELS, [])
    expect(tags.filter((t) => t.selected).map((t) => t.name)).toEqual(['gpt-4o', 'claude-3-5', 'deepseek-chat'])
  })

  it('同名校验用 key 去重、无名项丢弃、非数组返回空（不编造模型）', () => {
    const tags = buildModelTags(
      [{ model_name: 'gpt-4o' }, { model_name: 'gpt-4o' }, { vendor: 'OpenAI' }],
      ['gpt-4o']
    )
    expect(tags).toHaveLength(1)
    expect(tags[0]).toEqual({ key: 'gpt-4o', name: 'gpt-4o', selected: true })
    // 凭证清单缺失但报价单有明细行 → 仍按明细行出标签（不丢数据，见下一条）
    expect(buildModelTags(undefined, ['gpt-4o'])).toEqual([{ key: 'gpt-4o', name: 'gpt-4o', selected: true }])
    // 两边都没有 → 空（不编造模型）
    expect(buildModelTags(null, [])).toEqual([])
    expect(buildModelTags([{ vendor: 'OpenAI' }], [])).toEqual([])
  })

  it('明细行含未在 model_list 中的模型 → 追加到末尾（不丢数据）', () => {
    const tags = buildModelTags([{ model_name: 'gpt-4o' }], ['gpt-4o', 'o1-preview'])
    expect(tags.map((t) => t.name)).toEqual(['gpt-4o', 'o1-preview'])
    expect(tags.every((t) => t.selected)).toBe(true)
  })
})

/* ---------- 状态胶囊 ---------- */

describe('序号 12-v3 · 当前状态胶囊（复用序号 8 STATUS_META）', () => {
  it('DRAFT → 设计稿 5 态里的「草稿」灰底', () => {
    expect(resolveStatus('DRAFT')).toEqual({ key: 'draft', label: '草稿', bg: '#f1f5f9', dot: '#94a3b8', text: '#64748b' })
  })

  it('服务端未给状态 → 按 10-PRD §4.1「新建报价单初始 DRAFT」取草稿', () => {
    expect(resolveStatus(undefined).label).toBe('草稿')
    expect(resolveStatus('').label).toBe('草稿')
  })

  it('已映射状态走映射（SUBMITTED → 已提交）', () => {
    expect(resolveStatus('SUBMITTED')).toEqual({ key: 'submitted', label: '已提交', bg: '#eff6ff', dot: '#2563eb', text: '#2563eb' })
  })

  it('设计稿外且未映射的状态 → 中性灰原样直显（不臆造映射）', () => {
    expect(resolveStatus('FROZEN')).toEqual({ key: 'unknown', label: 'FROZEN', bg: '#f1f5f9', dot: '#94a3b8', text: '#64748b' })
  })

  it('VOID（10-PRD §4.1 作废）→ 中性灰 + 中文态名，不借设计 5 态配色', () => {
    expect(resolveStatus('VOID')).toEqual({ key: 'void', label: '作废', bg: '#f1f5f9', dot: '#94a3b8', text: '#64748b' })
  })
})

/* ---------- 页面视图模型 ---------- */

const QUOTE = {
  quote_id: 'q9',
  quote_no: 'QT-20240615-0007',
  status: 'DRAFT',
  name: '2024Q3 主线路报价',
  credential_id: 'c1',
  items: [{ model_name: 'gpt-4o' }, { model_name: 'claude-3-5' }, { model_name: 'deepseek-chat' }]
}

const CRED = {
  id: 'c1',
  alias: '生产环境密钥',
  api_key_mask: 'sk-prod-••2f9a',
  env_tag: '生产环境',
  model_list: MODELS
}

describe('序号 12-v3 · buildSuccessView（取数 → 视图）', () => {
  it('报价单详情 + 凭证明细 → 摘要 5 行与模型卡计数全部落位', () => {
    const view = buildSuccessView({ quote: QUOTE, credential: CRED, fallbackCredentialId: '' })
    expect(view.quoteNo).toBe('QT-20240615-0007')
    expect(view.hasQuoteNo).toBe(true)
    expect(view.quoteName).toBe('2024Q3 主线路报价')
    expect(view.credAlias).toBe('生产环境密钥')
    expect(view.credMask).toBe('sk-prod-••2f9a')
    expect(view.credEnvTag).toBe('生产环境')
    expect(view.selectedCount).toBe(3)
    expect(view.selectedCountText).toBe('已勾选 3 个')
    expect(view.modelTotalText).toBe('共 5 个 / 勾选 3 个')
    expect(view.status.label).toBe('草稿')
    expect(view.models).toHaveLength(5)
  })

  it('环境标与脱敏 key 缺失 → 空串（页面不渲染该段，不猜环境、不本地二次脱敏）', () => {
    const view = buildSuccessView({ quote: QUOTE, credential: { id: 'c1', alias: '生产环境密钥' }, fallbackCredentialId: '' })
    expect(view.credEnvTag).toBe('')
    expect(view.credMask).toBe('')
    expect(view.credAlias).toBe('生产环境密钥')
  })

  it('凭证明细未取到 → 名称/脱敏回退报价单响应字段，模型退报价单明细行', () => {
    const view = buildSuccessView({
      quote: { ...QUOTE, credential_alias: '备用密钥', api_key_mask: 'sk-bak-••1234' },
      credential: null,
      fallbackCredentialId: 'c1'
    })
    expect(view.credAlias).toBe('备用密钥')
    expect(view.credMask).toBe('sk-bak-••1234')
    expect(view.models.map((m) => m.name)).toEqual(['gpt-4o', 'claude-3-5', 'deepseek-chat'])
    expect(view.modelTotalText).toBe('共 3 个 / 勾选 3 个')
    expect(view.selectedCount).toBe(3)
  })

  it('字段名容错：quote_no / quote_no_text、name / title / quote_name 都认（字段级 schema missing-prd）', () => {
    const view = buildSuccessView({
      quote: { id: 'q9', quote_no_text: 'QT-20240615-0008', title: '国产模型报价', items: [] },
      credential: null,
      fallbackCredentialId: ''
    })
    expect(view.quoteNo).toBe('QT-20240615-0008')
    expect(view.quoteName).toBe('国产模型报价')
  })

  it('无报价单数据 → 占位「—」且 hasQuoteNo=false（不照抄设计样例单号）', () => {
    const view = buildSuccessView({ quote: null, credential: null, fallbackCredentialId: '' })
    expect(view.quoteNo).toBe('')
    expect(view.hasQuoteNo).toBe(false)
    expect(view.quoteName).toBe('—')
    expect(view.credAlias).toBe('—')
    expect(view.credEnvTag).toBe('')
    expect(view.models).toEqual([])
    expect(view.selectedCountText).toBe('已勾选 0 个')
    expect(view.modelTotalText).toBe('共 0 个 / 勾选 0 个')
    expect(view.status.label).toBe('草稿')
  })
})
