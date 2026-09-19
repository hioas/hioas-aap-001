/**
 * 序号 4【检测验真】提交接入凭证 2（page-4-2）— 视图模型与校验单测
 *
 * 设计真源：.calicat/raw/pages/page-4-2/design.tree.json（430 宽；顶部导航/凭证名称卡片/
 *   BaseURL 卡片(含安全提示)/APIKey 卡片(含已配置标签与脱敏框)/模型清单卡片(厂商分组+勾选)/底部固定操作条）
 * 字段依据：.calicat/prd/15-数据模型ER与数据字典.md「aap_credential」
 *   （alias / base_url / api_key_mask `sk-****abcd` / primary_flag / model_list / declared_vendor /
 *     declared_rpm / declared_context_window）——字段级 schema 未在 18-API 卡片定义，台账记 missing-prd
 * 业务规则：17-零歧义执行规格spec.md R-04（base_url 规范化去尾斜杠保留 /v1）、R-05（脱敏）、
 *   R-07（SSRF 出站防护 E-1201，服务端判定）、AC-08/AC-10/AC-11（21-验收标准）
 * 接口依据：.calicat/prd/18-API设计OpenAPI.md「Credential」Tag → /credentials/{id}、/{id}/precheck
 */
import { describe, expect, it } from 'vitest'
import {
  ALIAS_HINT,
  ANCHOR_NOTE,
  CATALOG_MORE_TEXT,
  MODEL_SECTION_NOTE,
  buildCredentialForm,
  buildSavePayload,
  countSelected,
  formatModelSpec,
  isAliasInSuggestedRange,
  normalizeBaseUrl,
  toggleModel,
  validateBaseUrl,
  type CredentialDetailRaw
} from '@/utils/credential-form-model'

/** 与设计稿 page-4-2 逐条一致的凭证详情响应（名称/BaseURL/脱敏 Key/模型清单分组） */
const RAW: CredentialDetailRaw = {
  id: 'c1',
  alias: '华东主线路 · GPT 通道',
  base_url: 'https://api.example-llm.com/v1',
  api_key_mask: 'sk-••••••••••••••••4f2a',
  primary_flag: true,
  model_list: [{ model_name: 'gpt-4o' }, { model_name: 'gpt-4o-mini' }, { model_name: 'claude-3-5-sonnet' }],
  model_catalog: [
    {
      vendor: 'OpenAI',
      models: [
        { model_name: 'gpt-4o', context_window: 128000, rpm: 500 },
        { model_name: 'gpt-4o-mini', context_window: 128000, rpm: 500 },
        { model_name: 'gpt-3.5-turbo', context_window: 16000, rpm: 200 }
      ]
    },
    {
      vendor: 'Anthropic',
      models: [
        { model_name: 'claude-3-5-sonnet', context_window: 200000, rpm: 300 },
        { model_name: 'claude-3-opus', context_window: 200000, rpm: 120 }
      ]
    }
  ]
}

describe('formatModelSpec · 「128K · 500 RPM」规格文案', () => {
  it('context_window 按千位显示 K（128000/128 都算 128K）', () => {
    expect(formatModelSpec(128000, 500)).toBe('128K · 500 RPM')
    expect(formatModelSpec(128, 500)).toBe('128K · 500 RPM')
    expect(formatModelSpec(16000, 200)).toBe('16K · 200 RPM')
    expect(formatModelSpec(200000, 120)).toBe('200K · 120 RPM')
  })

  it('非整千保留一位小数；缺失字段不编造（缺 RPM 只显示上下文）', () => {
    expect(formatModelSpec(1500, 300)).toBe('1.5K · 300 RPM')
    expect(formatModelSpec(128000, undefined)).toBe('128K')
    expect(formatModelSpec(undefined, undefined)).toBe('')
  })
})

describe('buildCredentialForm · 视图模型对齐设计稿', () => {
  const form = buildCredentialForm(RAW)

  it('凭证名称/BaseURL/脱敏 Key 原样取自接口（不改写文案）', () => {
    expect(form.alias).toBe('华东主线路 · GPT 通道')
    expect(form.baseUrl).toBe('https://api.example-llm.com/v1')
    expect(form.apiKeyMask).toBe('sk-••••••••••••••••4f2a')
  })

  it('主凭证标记取自 primary_flag（设计稿右上 chip）', () => {
    expect(form.isPrimary).toBe(true)
    expect(buildCredentialForm({ ...RAW, primary_flag: false }).isPrimary).toBe(false)
  })

  it('模型清单按厂商分组，顺序与设计稿一致（OpenAI 3 行 / Anthropic 2 行）', () => {
    expect(form.vendors.map((v) => v.vendor)).toEqual(['OpenAI', 'Anthropic'])
    expect(form.vendors[0].models.map((m) => m.name)).toEqual(['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'])
    expect(form.vendors[1].models.map((m) => m.name)).toEqual(['claude-3-5-sonnet', 'claude-3-opus'])
    expect(form.vendors[0].models.map((m) => m.specText)).toEqual(['128K · 500 RPM', '128K · 500 RPM', '16K · 200 RPM'])
    expect(form.vendors[1].models.map((m) => m.specText)).toEqual(['200K · 300 RPM', '200K · 120 RPM'])
  })

  it('勾选态来自 model_list，且「已选 N 个」与勾选数一致（设计稿 3 个）', () => {
    expect(form.vendors[0].models.map((m) => m.checked)).toEqual([true, true, false])
    expect(form.vendors[1].models.map((m) => m.checked)).toEqual([true, false])
    expect(form.selectedCount).toBe(3)
    expect(form.selectedCountText).toBe('已选 3 个')
  })

  it('每个可选模型都有稳定 key（厂商::模型名）', () => {
    expect(form.vendors[0].models[0].key).toBe('OpenAI::gpt-4o')
    expect(form.vendors[1].models[0].key).toBe('Anthropic::claude-3-5-sonnet')
  })

  it('底部提示按实际厂商数生成（设计稿 2 个厂商 → 文案与设计一致）', () => {
    expect(form.catalogMoreText).toBe(CATALOG_MORE_TEXT)
    expect(form.catalogMoreText).toBe('仅展示 2 个厂商，查看更多厂商 ›')
    expect(buildCredentialForm({ model_catalog: [RAW.model_catalog![0]] }).catalogMoreText).toBe(
      '仅展示 1 个厂商，查看更多厂商 ›'
    )
  })
})

describe('buildCredentialForm · 缺数据不崩且不编造', () => {
  it('空响应 → 空名称/空 URL/无分组/已选 0 个，不出现 NaN/undefined 文案', () => {
    const form = buildCredentialForm({})
    expect(form.alias).toBe('')
    expect(form.baseUrl).toBe('')
    expect(form.apiKeyMask).toBe('')
    expect(form.vendors).toEqual([])
    expect(form.selectedCount).toBe(0)
    expect(form.selectedCountText).toBe('已选 0 个')
    expect(JSON.stringify(form)).not.toContain('NaN')
  })

  it('null/undefined 入参同样安全', () => {
    expect(buildCredentialForm(undefined).vendors).toEqual([])
    expect(buildCredentialForm(null).selectedCount).toBe(0)
  })

  it('无目录时退化为用 model_list + declared_vendor 单分组展示（不丢已选模型）', () => {
    const form = buildCredentialForm({
      alias: 'A',
      declared_vendor: 'OpenAI',
      model_list: [{ model_name: 'gpt-4o' }]
    })
    expect(form.vendors.map((v) => v.vendor)).toEqual(['OpenAI'])
    expect(form.vendors[0].models.map((m) => m.name)).toEqual(['gpt-4o'])
    expect(form.selectedCount).toBe(1)
  })

  it('model_list 与目录都缺失 → 只有无厂商分组，不伪造模型', () => {
    const form = buildCredentialForm({ alias: 'A', model_list: [{ model_name: 'x' }] })
    expect(form.vendors).toHaveLength(1)
    expect(form.vendors[0].vendor).toBe('')
    expect(countSelected(form.vendors)).toBe(1)
  })
})

describe('toggleModel · 勾选联动「已选 N 个」', () => {
  const form = buildCredentialForm(RAW)

  it('取消一个已勾选 → 该行变未勾选，计数 3 → 2', () => {
    const next = toggleModel(form.vendors, 'OpenAI::gpt-4o-mini')
    expect(countSelected(next)).toBe(2)
    expect(next[0].models[1].checked).toBe(false)
    expect(next[0].models[0].checked).toBe(true)
  })

  it('勾选一个未选中 → 计数 3 → 4', () => {
    const next = toggleModel(form.vendors, 'OpenAI::gpt-3.5-turbo')
    expect(countSelected(next)).toBe(4)
    expect(next[0].models[2].checked).toBe(true)
  })

  it('不修改原数组（返回新数组，避免视图共享同一引用）', () => {
    const next = toggleModel(form.vendors, 'OpenAI::gpt-4o')
    expect(form.vendors[0].models[0].checked).toBe(true)
    expect(next[0].models[0].checked).toBe(false)
  })

  it('未知 key 安全返回（不抛错、计数不变）', () => {
    const next = toggleModel(form.vendors, 'Nope::nope')
    expect(countSelected(next)).toBe(3)
  })
})

describe('normalizeBaseUrl · R-04 规范化去尾斜杠保留 /v1', () => {
  it('去掉尾部斜杠但保留 /v1', () => {
    expect(normalizeBaseUrl('https://api.example-llm.com/v1/')).toBe('https://api.example-llm.com/v1')
    expect(normalizeBaseUrl('https://api.example-llm.com/v1')).toBe('https://api.example-llm.com/v1')
    expect(normalizeBaseUrl('https://api.example-llm.com//')).toBe('https://api.example-llm.com')
  })

  it('去首尾空白；空串/缺省 → 空串', () => {
    expect(normalizeBaseUrl('  https://a.com/v1/  ')).toBe('https://a.com/v1')
    expect(normalizeBaseUrl('')).toBe('')
    expect(normalizeBaseUrl(undefined)).toBe('')
  })
})

describe('validateBaseUrl · 前端只做协议/主机前置校验（SSRF 由服务端 E-1201）', () => {
  it('合法 http(s) 地址通过', () => {
    expect(validateBaseUrl('https://api.example-llm.com/v1')).toBeNull()
    expect(validateBaseUrl('http://127.0.0.1:8080/v1')).toBeNull()
  })

  it('空 → 必填提示', () => {
    expect(validateBaseUrl('')).toBe('请输入 BaseURL')
  })

  it('非 http/https 协议 → 拦截', () => {
    expect(validateBaseUrl('ftp://api.example-llm.com/v1')).toContain('http')
    expect(validateBaseUrl('api.example-llm.com/v1')).toContain('http')
  })

  it('缺主机名 → 拦截', () => {
    expect(validateBaseUrl('https://')).toContain('BaseURL')
  })
})

describe('isAliasInSuggestedRange · 设计稿「建议 6–24 字」为建议而非硬校验', () => {
  it('设计稿文案原样导出', () => {
    expect(ALIAS_HINT).toBe('建议 6–24 字')
  })

  it('6–24 字为建议区间（含边界）', () => {
    expect(isAliasInSuggestedRange('华东主线路 · GPT 通道')).toBe(true)
    expect(isAliasInSuggestedRange('短名')).toBe(false)
    expect(isAliasInSuggestedRange('a'.repeat(25))).toBe(false)
    expect(isAliasInSuggestedRange('a'.repeat(6))).toBe(true)
    expect(isAliasInSuggestedRange('a'.repeat(24))).toBe(true)
  })
})

describe('buildSavePayload · 请求体（不臆造未填字段）', () => {
  it('未改密钥 → 请求体不含 api_key；base_url 已规范化；model_list 为已勾选模型（**对象数组**，缺陷 11）', () => {
    const payload = buildSavePayload({
      alias: '华东主线路 · GPT 通道',
      baseUrl: 'https://api.example-llm.com/v1/',
      vendors: buildCredentialForm(RAW).vendors
    })
    // 契约 credential-create.schema.json：model_list.items = $ref model-entry
    // 后端入参 List<Map<String,Object>>；发字符串数组会被拒（E-1001，实测）
    expect(payload).toEqual({
      alias: '华东主线路 · GPT 通道',
      base_url: 'https://api.example-llm.com/v1',
      model_list: [
        { model_name: 'gpt-4o' },
        { model_name: 'gpt-4o-mini' },
        { model_name: 'claude-3-5-sonnet' }
      ]
    })
    expect('api_key' in payload).toBe(false)
  })

  it('轮换了密钥 → 携带 api_key（且去掉首尾空白）', () => {
    const payload = buildSavePayload({
      alias: 'A',
      baseUrl: 'https://a.com/v1',
      apiKey: '  sk-new-1234  ',
      vendors: buildCredentialForm(RAW).vendors
    })
    expect(payload.api_key).toBe('sk-new-1234')
  })

  it('model_list 按厂商顺序展开并去重（对象数组，缺陷 11）', () => {
    const vendors = toggleModel(buildCredentialForm(RAW).vendors, 'OpenAI::gpt-3.5-turbo')
    const payload = buildSavePayload({ alias: 'A', baseUrl: 'https://a.com', vendors })
    expect(payload.model_list).toEqual([
      { model_name: 'gpt-4o' },
      { model_name: 'gpt-4o-mini' },
      { model_name: 'gpt-3.5-turbo' },
      { model_name: 'claude-3-5-sonnet' }
    ])
  })

  it('设计稿静态文案原样导出（供页面直接渲染，避免各页各写一套）', () => {
    expect(MODEL_SECTION_NOTE).toBe('按厂商勾选，自动生成本次接入检测清单')
    expect(CATALOG_MORE_TEXT).toBe('仅展示 2 个厂商，查看更多厂商 ›')
    expect(ANCHOR_NOTE).toBe('凭证仅用于平台检测与转发调用，全程加密存储，不会对外泄露。')
  })
})
