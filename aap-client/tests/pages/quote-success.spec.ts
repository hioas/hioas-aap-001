/**
 * 序号 12-v3【报价管理】新增报价单-保存成功（page-29）— 页面取数与渲染（TDD 切片 2，先红）
 *
 * 页面入参：quoteId 优先页面栈 query（H5/mini 的 ?quoteId=），其次 storage 键 aap_quote_id（单测/刷新兜底）；
 *   凭证 id 同族取 aap_credential_id（报价单响应自带 credential_id 时优先用它）。
 * 接口真源：18-API「Quote」/quotes/{quoteId} + 「Credential」/credentials/{id}（前缀 /api/v1；方法为 REST 推断）。
 * 设计基线：430 宽 · 设计帧 430x1018（四卡 + 底栏，见 .agents/state/h5-measure/__measure-quote-success.html）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuoteSuccessPage from '@/pages/quote-form/success.vue'
import { getCalls, pushResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const QUOTE = {
  quote_id: 'q9',
  quote_no: 'QT-20240615-0007',
  status: 'DRAFT',
  name: '2024Q3 主线路报价',
  credential_id: 'c1',
  items: [{ model_name: 'gpt-4o' }, { model_name: 'gpt-4o-mini' }, { model_name: 'claude-3-5' }]
}

/** 凭证 model_list 与设计帧的 5 个标签逐字一致（前 3 个勾选、后 2 个未勾选） */
const CRED = {
  id: 'c1',
  alias: '生产环境密钥',
  api_key_mask: 'sk-prod-••2f9a',
  env_tag: '生产环境',
  model_list: [
    { model_name: 'gpt-4o', vendor: 'OpenAI', selected: true },
    { model_name: 'gpt-4o-mini', vendor: 'OpenAI', selected: true },
    { model_name: 'claude-3-5', vendor: 'Anthropic', selected: true },
    { model_name: 'gemini-1.5-pro', vendor: 'Google', selected: false },
    { model_name: 'deepseek-chat', vendor: 'DeepSeek', selected: false }
  ]
}

function requests() {
  return getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
}

function urls() {
  return requests().map((r) => String(r.url))
}

function toasts() {
  return getCalls('showToast').map((c) => String((c.args[0] as Record<string, unknown>).title))
}

function text(wrapper: ReturnType<typeof mount>, testid: string) {
  const el = wrapper.find(`[data-testid="${testid}"]`)
  return el.exists() ? el.text() : ''
}

/** 正常链路：报价单详情 + 凭证明细 */
async function mountLoaded() {
  storage.set('aap_quote_id', 'q9')
  storage.set('aap_credential_id', 'c1')
  pushResponse(ok(QUOTE))
  pushResponse(ok(CRED))
  const wrapper = mount(QuoteSuccessPage)
  await flushPromises()
  return wrapper
}

describe('序号 12-v3 · 取数（api）', () => {
  it('有 quoteId → GET /api/v1/quotes/q9，再按 credential_id 拉 GET /api/v1/credentials/c1', async () => {
    await mountLoaded()
    expect(urls()).toEqual(['/api/v1/quotes/q9', '/api/v1/credentials/c1'])
    expect(requests().every((r) => r.method === 'GET')).toBe(true)
  })

  it('无 quoteId → 不发任何请求，页面显示占位「—」与 0 计数（不照抄设计样例值）', async () => {
    const wrapper = mount(QuoteSuccessPage)
    await flushPromises()
    expect(urls()).toEqual([])
    expect(text(wrapper, 'quote-no-value')).toBe('')
    expect(text(wrapper, 'row-name')).toContain('—')
    expect(text(wrapper, 'row-cred')).toContain('—')
    expect(text(wrapper, 'model-count')).toBe('共 0 个 / 勾选 0 个')
    expect(wrapper.findAll('[data-testid^="model-tag-"]')).toHaveLength(0)
  })

  it('报价单响应自带 credential_id → 即使 storage 没有凭证 id 也会拉凭证明细', async () => {
    storage.set('aap_quote_id', 'q9')
    pushResponse(ok(QUOTE))
    pushResponse(ok(CRED))
    mount(QuoteSuccessPage)
    await flushPromises()
    expect(urls()).toEqual(['/api/v1/quotes/q9', '/api/v1/credentials/c1'])
  })

  it('报价单详情失败 → toast 服务端 message，页面保持占位（不编造单号/名称）', async () => {
    storage.set('aap_quote_id', 'q9')
    pushResponse({ statusCode: 200, data: { code: 'E-1404', message: '报价单不存在' } })
    const wrapper = mount(QuoteSuccessPage)
    await flushPromises()
    expect(toasts()).toEqual(['报价单不存在'])
    expect(text(wrapper, 'quote-no-value')).toBe('')
    expect(text(wrapper, 'row-name')).toContain('—')
    expect(wrapper.findAll('[data-testid^="model-tag-"]')).toHaveLength(0)
  })

  it('凭证明细失败 → 摘要仍用报价单侧数据，环境标与脱敏不渲染（不猜）', async () => {
    storage.set('aap_quote_id', 'q9')
    pushResponse(ok(QUOTE))
    pushResponse({ statusCode: 200, data: { code: 'E-2001', message: '凭证明细获取失败' } })
    const wrapper = mount(QuoteSuccessPage)
    await flushPromises()
    expect(toasts()).toEqual(['凭证明细获取失败'])
    expect(text(wrapper, 'quote-no-value')).toBe('QT-20240615-0007')
    expect(wrapper.find('[data-testid="cred-env-tag"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="cred-mask"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid^="model-tag-"]').map((t) => t.text())).toEqual([
      'gpt-4o',
      'gpt-4o-mini',
      'claude-3-5'
    ])
    expect(text(wrapper, 'model-count')).toBe('共 3 个 / 勾选 3 个')
  })
})

describe('序号 12-v3 · 渲染（设计稿文案与结构）', () => {
  it('顶栏与成功头部卡逐字渲染', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'nav-title')).toBe('报价单已创建')
    expect(text(wrapper, 'nav-subtitle')).toBe('报价单号已自动生成')
    expect(text(wrapper, 'success-title')).toBe('报价单创建成功')
    expect(text(wrapper, 'success-desc')).toBe('已保存基本信息并带出模型清单')
    expect(text(wrapper, 'quote-no-value')).toBe('QT-20240615-0007')
    expect(text(wrapper, 'quote-no-label')).toBe('报价单号')
    expect(text(wrapper, 'copy')).toContain('复制')
  })

  it('结果摘要 5 行：名称 / 凭证（环境标 + 脱敏）/ 模型数 / 单号 / 状态', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'summary-title')).toBe('结果摘要')
    expect(text(wrapper, 'row-name')).toContain('报价单名称')
    expect(text(wrapper, 'row-name')).toContain('2024Q3 主线路报价')
    expect(text(wrapper, 'row-cred')).toContain('凭证名称')
    expect(text(wrapper, 'cred-env-tag')).toBe('生产环境')
    expect(text(wrapper, 'cred-mask')).toBe('sk-prod-••2f9a')
    expect(text(wrapper, 'row-models')).toContain('参与报价模型')
    expect(text(wrapper, 'row-models')).toContain('已勾选 3 个')
    expect(text(wrapper, 'row-no')).toContain('QT-20240615-0007')
    expect(text(wrapper, 'row-status')).toContain('当前状态')
    expect(text(wrapper, 'status-chip')).toBe('草稿')
  })

  it('已带出模型卡：计数文案 + 5 个标签，勾选 3 个（data-selected）', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'model-card-title')).toBe('已带出模型')
    expect(text(wrapper, 'model-count')).toBe('共 5 个 / 勾选 3 个')
    const tags = wrapper.findAll('[data-testid^="model-tag-"]')
    expect(tags.map((t) => t.text())).toEqual([
      'gpt-4o',
      'gpt-4o-mini',
      'claude-3-5',
      'gemini-1.5-pro',
      'deepseek-chat'
    ])
    // 设计帧把标签分成两行：勾选在前（蓝底）、未勾选在后（灰底）
    expect(tags.map((t) => t.attributes('data-selected'))).toEqual(['true', 'true', 'true', 'false', 'false'])
  })

  it('提示卡与底部按钮逐字渲染', async () => {
    const wrapper = await mountLoaded()
    expect(text(wrapper, 'tip')).toBe('下一步可为勾选模型设置输入/输出单价，设置完成即可提交审核。')
    expect(text(wrapper, 'btn-primary')).toBe('继续设置模型报价')
    expect(text(wrapper, 'btn-secondary')).toBe('返回报价单列表')
  })
})
