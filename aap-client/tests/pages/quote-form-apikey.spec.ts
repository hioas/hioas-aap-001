/**
 * 序号 12-v2【报价管理】新增报价单-APIKey 下拉展开（page-apikey）— 页面渲染（TDD 切片 2，先红）
 *
 * 设计真源：.calicat/raw/pages/page-apikey/design.tree.json（430 宽 · 430x1129 · 无 TabBar）
 *   结构：顶部导航 → 内容区（基本信息卡〔含凭证选择框-展开态 + 下拉选项面板 + 凭证说明〕 + 模型列表卡〔待带出 + 空态〕）→ 底部操作条
 *   本帧**无步骤卡**、**无空态提示卡**（与 page-26 的差异按帧实现，已写台账，不静默统一）
 *   文案逐字抄自设计树（见 tests/unit/quote-form-variant.spec.ts 顶部清单）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuoteFormApikeyPage from '@/pages/quote-form/apikey.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 凭证列表 mock：逐字复刻设计帧的三行样例（字段名取 15-数据字典 / 17-spec；字段级 schema missing-prd） */
const CRED_LIST = {
  items: [
    {
      id: 'c1',
      alias: '生产环境密钥',
      api_key_mask: 'sk-prod-••••••••2f9a',
      is_primary: true,
      model_list: new Array(12).fill({ model_name: 'gpt-4o' })
    },
    {
      id: 'c2',
      alias: '测试环境密钥',
      api_key_mask: 'sk-test-••••••••7b31',
      env_tag: '沙箱',
      model_list: new Array(8).fill({})
    },
    {
      id: 'c3',
      alias: '数据标注专用',
      api_key_mask: 'sk-label-••••••••a4c8',
      env_tag: '专用',
      model_list: new Array(5).fill({})
    }
  ],
  total: 3
}

async function mountPage() {
  pushResponse(ok(CRED_LIST))
  const wrapper = mount(QuoteFormApikeyPage)
  await flushPromises()
  return wrapper
}

function requests() {
  return getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
}

function texts(wrapper: ReturnType<typeof mount>, sel: string) {
  return wrapper.findAll(sel).map((w) => w.text())
}

describe('序号 12-v2 · 页面骨架（帧级结构：无步骤卡 / 无空态提示卡）', () => {
  it('顶部导航与底部操作条与设计一致（同一页的两帧共用）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="nav-title"]').text()).toBe('新增报价单')
    expect(wrapper.find('[data-testid="nav-subtitle"]').text()).toBe('填写基本信息并设置模型报价')
    expect(wrapper.find('[data-testid="back"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="help"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="bar-hint"]').text()).toBe('保存成功后系统将自动生成报价单号')
    expect(wrapper.find('[data-testid="btn-draft"]').text()).toBe('存为草稿')
    expect(wrapper.find('[data-testid="btn-save"]').text()).toContain('保存并继续')
  })

  it('本帧设计稿无步骤卡 → 不渲染步骤卡（与 12-v1 帧的差异按帧实现）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="step-1"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="step-2"]').exists()).toBe(false)
  })

  it('本帧设计稿无空态提示卡 → 不渲染「带出的模型数量与凭证权限相关…」，空态说明用本帧文案', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="model-empty-tip"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="model-empty-desc"]').text()).toBe('选择凭证后将自动带出可用模型')
  })

  it('基本信息卡与本帧一致的字段与文案（名称占位 / 0/30 / 单号 / 凭证说明）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="card-basic-title"]').text()).toBe('基本信息')
    expect(wrapper.find('[data-testid="name-label"]').text()).toBe('报价单名称')
    expect(wrapper.find('[data-testid="name-count"]').text()).toBe('0/30')
    expect(wrapper.find('[data-testid="quote-no-tag"]').text()).toBe('系统生成')
    expect(wrapper.find('[data-testid="quote-no-text"]').text()).toBe('保存后自动生成')
    expect(wrapper.find('[data-testid="quote-no-sample"]').text()).toBe('QT-XXXXXXXX-XXXX')
    expect(wrapper.find('[data-testid="cred-label"]').text()).toBe('凭证名称')
    expect(wrapper.find('[data-testid="cred-hint"]').text()).toBe('选择凭证后，系统将自动带出该凭证下可用的模型列表')
  })

  it('本帧设计稿无「为必填项」标、无单号说明行、无填写须知卡（逐层比对两帧设计树）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="chip-required"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="quote-no-hint"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="card-notice"]').exists()).toBe(false)
  })
})

describe('序号 12-v2 · 凭证下拉展开态（api：GET /credentials，18-API Credential Tag）', () => {
  it('进页面即展开面板并发起 GET /credentials（分页参数走 uni.request 的 data：page=1&pageSize=20）', async () => {
    const wrapper = await mountPage()
    const reqs = requests().filter((r) => String(r.url).endsWith('/credentials'))
    expect(reqs).toHaveLength(1)
    expect(reqs[0].method).toBe('GET')
    expect(String(reqs[0].url)).toBe('/api/v1/credentials')
    // 查询串由 uni.request 在运行时拼到 url 上（H5 实测 `GET /api/v1/credentials?page=1&pageSize=20`，见台账证据链）
    expect(reqs[0].data).toEqual({ page: 1, pageSize: 20 })
    expect(wrapper.find('[data-testid="cred-panel"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="cred-select"]').attributes('data-open')).toBe('true')
  })

  it('未选中时选择框显示设计占位「请选择凭证」（本帧面板内的对勾是高亮态，由真实选择驱动）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="cred-value"]').text()).toBe('请选择凭证')
    expect(wrapper.find('[data-testid="cred-check-c1"]').exists()).toBe(false)
  })

  it('三行候选项：别名 + 脱敏 key · 模型数 + 环境标 / 推荐标（逐字对设计帧）', async () => {
    const wrapper = await mountPage()
    expect(texts(wrapper, '[data-testid^="cred-option-"]').filter((t) => t)).toHaveLength(3)
    expect(wrapper.find('[data-testid="cred-option-c1"]').text()).toContain('生产环境密钥')
    expect(wrapper.find('[data-testid="cred-option-c2"]').text()).toContain('测试环境密钥')
    expect(wrapper.find('[data-testid="cred-option-c3"]').text()).toContain('数据标注专用')
    const subs = texts(wrapper, '[data-testid^="cred-sub-"]')
    expect(subs).toEqual([
      'sk-prod-••••••••2f9a · 12 个模型',
      'sk-test-••••••••7b31 · 8 个模型',
      'sk-label-••••••••a4c8 · 5 个模型'
    ])
    expect(wrapper.find('[data-testid="cred-recommended-c1"]').text()).toBe('常用')
    expect(wrapper.find('[data-testid="cred-tag-c2"]').text()).toBe('沙箱')
    expect(wrapper.find('[data-testid="cred-tag-c3"]').text()).toBe('专用')
  })

  it('面板底部操作行 = 设计原文「前往「我的设置」新建凭证」（navigation）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="cred-create"]').text()).toBe('前往「我的设置」新建凭证')
  })

  it('模型列表卡：chip「待带出」+ 空态（尚未加载模型 / 本帧说明文案）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="chip-model"]').text()).toBe('待带出')
    expect(wrapper.find('[data-testid="model-empty-title"]').text()).toBe('尚未加载模型')
    expect(wrapper.find('[data-testid="model-empty"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(0)
  })

  it('列表接口失败 → toast 服务端 message 且面板为空（不编造候选项）', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-2001', message: '凭证列表获取失败' } })
    const wrapper = mount(QuoteFormApikeyPage)
    await flushPromises()
    expect(wrapper.find('[data-testid="cred-panel"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-testid^="cred-option-"]')).toHaveLength(0)
    const toasts = getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
    expect(toasts).toEqual(['凭证列表获取失败'])
  })
})
