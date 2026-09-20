/**
 * 页面 4【检测验真】提交接入凭证 2（序号 4 / page-4-2）— 页面单测
 *
 * 文案与结构真源：.calicat/raw/pages/page-4-2/design.tree.json（430 宽）
 *   顶部导航(返回/「接入凭证」/主凭证 chip) · 凭证名称卡片 · BaseURL 卡片(含安全提示) ·
 *   APIKey 卡片(已配置标签 + 脱敏框 + 编辑图标) · 模型清单卡片(2 厂商 5 模型 + 已选计数 + 底部提示) ·
 *   底部固定操作条(保存草稿 + 提交检测)
 * 交互真源：page-4-2 interaction.json =「不存在图层交互数据」→ 退 PRD 17-spec / 18-API + 画布 30 页清单
 * 接口：GET/PUT /api/v1/credentials/{id}、POST /api/v1/credentials/{id}/precheck（18-API Credential Tag）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CredentialSubmitPage from '@/pages/credential-submit/index.vue'
import { getCalls, pushResponse, setNextResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 与设计稿 page-4-2 逐条一致的详情响应 */
const DETAIL = {
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

const CREDENTIAL_ID_KEY = 'aap_credential_id'

async function mountPage(detail: unknown = DETAIL) {
  uni.setStorageSync(CREDENTIAL_ID_KEY, 'c1')
  pushResponse(ok(detail))
  const wrapper = mount(CredentialSubmitPage)
  await flushPromises()
  return wrapper
}

const toastTitles = () => getCalls('showToast').map((c) => String((c.args[0] as { title?: string }).title ?? ''))

describe('页面 4 · 渲染：文案与 page-4-2 设计稿逐条一致', () => {
  it('顶部导航：标题「接入凭证」+ 主凭证 chip（design id=0fa01a4a / 62c388f2）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('接入凭证')
    expect(wrapper.find('[data-testid="primary-chip"]').text()).toBe('主凭证')
    expect(wrapper.find('[data-testid="back-btn"]').exists()).toBe(true)
  })

  it('凭证名称卡片：标签 + 值 + 「建议 6–24 字」提示', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('凭证名称')
    expect((wrapper.find('[data-testid="alias-input"]').element as HTMLInputElement).value).toBe(
      '华东主线路 · GPT 通道'
    )
    expect(wrapper.text()).toContain('建议 6–24 字')
  })

  it('BaseURL 卡片：标签 + 值；按设计稿**不含**安全说明', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('BaseURL')
    expect((wrapper.find('[data-testid="baseurl-input"]').element as HTMLInputElement).value).toBe(
      'https://api.example-llm.com/v1'
    )
    // 设计稿（calicat 2100004969199824896 / node ed742274）**没有**安全说明文案；
    // 该 note 是原实现的额外添加。用户要求「按设计稿调整」→ 断言改为「不存在」。
    expect(wrapper.find('[data-testid="security-note"]').exists()).toBe(false)
  })

  it('APIKey 卡片：标签 + 「已配置」标签 + 脱敏值 + 轮换提示', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('APIKey')
    expect(wrapper.find('[data-testid="configured-chip"]').text()).toBe('已配置')
    expect(wrapper.find('[data-testid="apikey-mask"]').text()).toBe('sk-••••••••••••••••4f2a')
    expect(wrapper.text()).toContain('如已轮换密钥，请在此更新后重新检测')
  })

  it('模型清单卡片：标题 / 已选 3 个 / 说明行 / 2 厂商 5 模型与规格 / 底部提示', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('模型清单')
    expect(wrapper.find('[data-testid="selected-count"]').text()).toBe('已选 3 个')
    expect(wrapper.text()).toContain('按厂商勾选，自动生成本次接入检测清单')
    expect(wrapper.findAll('[data-testid="vendor-group"]')).toHaveLength(2)
    expect(wrapper.findAll('[data-testid="model-row"]')).toHaveLength(5)
    expect(wrapper.find('[data-testid="model-name-0-0"]').text()).toBe('gpt-4o')
    expect(wrapper.find('[data-testid="model-spec-0-0"]').text()).toBe('128K · 500 RPM')
    expect(wrapper.find('[data-testid="model-name-1-0"]').text()).toBe('claude-3-5-sonnet')
    expect(wrapper.find('[data-testid="model-spec-1-0"]').text()).toBe('200K · 300 RPM')
    expect(wrapper.find('[data-testid="catalog-more"]').text()).toBe('仅展示 2 个厂商，查看更多厂商 ›')
  })

  it('勾选态与设计稿一致：gpt-4o/gpt-4o-mini/claude-3-5-sonnet 已勾选', async () => {
    const wrapper = await mountPage()
    const checked = (i: number, j: number) =>
      wrapper.find(`[data-testid="model-check-${i}-${j}"]`).classes().includes('model-row__box--checked')
    expect(checked(0, 0)).toBe(true)
    expect(checked(0, 1)).toBe(true)
    expect(checked(0, 2)).toBe(false)
    expect(checked(1, 0)).toBe(true)
    expect(checked(1, 1)).toBe(false)
  })

  it('底部固定操作条：保存草稿 + 提交检测', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="save-btn"]').text()).toBe('保存草稿')
    expect(wrapper.find('[data-testid="submit-btn"]').text()).toContain('提交检测')
  })
})

describe('页面 4 · 数据加载', () => {
  it('按 storage 里的凭证 id 拉取详情：GET /api/v1/credentials/c1', async () => {
    await mountPage()
    const calls = getCalls('request')
    expect(calls).toHaveLength(1)
    expect((calls[0].args[0] as { url: string }).url).toBe('/api/v1/credentials/c1')
  })

  it('无凭证 id → 不发请求，页面仍渲染标题与操作条（不崩）', async () => {
    uni.setStorageSync(CREDENTIAL_ID_KEY, '')
    const wrapper = mount(CredentialSubmitPage)
    await flushPromises()
    expect(getCalls('request')).toHaveLength(0)
    expect(wrapper.text()).toContain('接入凭证')
    expect(wrapper.find('[data-testid="submit-btn"]').exists()).toBe(true)
  })

  it('详情加载失败 → 提示且不崩', async () => {
    uni.setStorageSync(CREDENTIAL_ID_KEY, 'c1')
    setNextResponse({ statusCode: 200, data: { code: 'E-2001', message: '内部错误' } })
    const wrapper = mount(CredentialSubmitPage)
    await flushPromises()
    expect(wrapper.text()).toContain('接入凭证')
    expect(toastTitles().join()).toContain('内部错误')
  })
})

describe('页面 4 · 交互（勾选联动 / 客户端私有交互）', () => {
  it('点未勾选模型 → 已选 3 → 4；再点同一行 → 回到 3', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="model-check-0-2"]').trigger('tap')
    expect(wrapper.find('[data-testid="selected-count"]').text()).toBe('已选 4 个')
    await wrapper.find('[data-testid="model-check-0-2"]').trigger('tap')
    expect(wrapper.find('[data-testid="selected-count"]').text()).toBe('已选 3 个')
  })

  it('取消已勾选模型 → 已选 2 个，且该行变未勾选', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="model-check-0-1"]').trigger('tap')
    expect(wrapper.find('[data-testid="selected-count"]').text()).toBe('已选 2 个')
    expect(wrapper.find('[data-testid="model-check-0-1"]').classes()).not.toContain('model-row__box--checked')
  })

  it('「查看更多厂商 ›」= client-only（画布 30 页无厂商目录页 → 不臆造路由）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="catalog-more"]').trigger('tap')
    await flushPromises()
    expect(getCalls('navigateTo')).toHaveLength(0)
    expect(toastTitles()).toHaveLength(1)
  })

  it('APIKey 编辑图标 → 出现输入框；输入后保存请求体带 api_key', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="apikey-input"]').exists()).toBe(false)
    await wrapper.find('[data-testid="apikey-edit"]').trigger('tap')
    await wrapper.find('[data-testid="apikey-input"]').setValue('sk-new-9999')
    pushResponse(ok({ id: 'c1' }))
    await wrapper.find('[data-testid="save-btn"]').trigger('tap')
    await flushPromises()
    const reqs = getCalls('request')
    const put = reqs[reqs.length - 1].args[0] as { method: string; data: Record<string, unknown> }
    expect(put.method).toBe('PUT')
    expect(put.data.api_key).toBe('sk-new-9999')
  })

  it('primary_flag=false → 不渲染主凭证 chip', async () => {
    const wrapper = await mountPage({ ...DETAIL, primary_flag: false })
    expect(wrapper.find('[data-testid="primary-chip"]').exists()).toBe(false)
  })

  it('脱敏框内不再有与脱敏值争抢 flex 的 spacer（否则 430 宽下脱敏值被压成两行）', async () => {
    const wrapper = await mountPage()
    const mask = wrapper.find('[data-testid="apikey-mask"]')
    const box = mask.element.parentElement as HTMLElement
    expect(box.querySelectorAll('.input-box__spacer')).toHaveLength(0)
    // 编辑图标必须仍在脱敏框内（设计稿 id=236156ed，靠右）
    expect(box.querySelector('[data-testid="apikey-edit"]')).not.toBeNull()
  })

  it('返回按钮 → navigateBack', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="back-btn"]').trigger('tap')
    expect(getCalls('navigateBack')).toHaveLength(1)
  })
})

describe('页面 4 · 保存草稿（PUT /credentials/{id}）', () => {
  it('请求体：alias + 规范化 base_url + 已勾选 model_list，未改密钥则不带 api_key；不跳转', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="baseurl-input"]').setValue('https://api.example-llm.com/v1/')
    pushResponse(ok({ id: 'c1' }))
    await wrapper.find('[data-testid="save-btn"]').trigger('tap')
    await flushPromises()

    const reqs = getCalls('request')
    const put = reqs[reqs.length - 1].args[0] as { url: string; method: string; data: Record<string, unknown> }
    expect(put.url).toBe('/api/v1/credentials/c1')
    expect(put.method).toBe('PUT')
    expect(put.data).toEqual({
      alias: '华东主线路 · GPT 通道',
      base_url: 'https://api.example-llm.com/v1',
      model_list: [{ model_name: 'gpt-4o' }, { model_name: 'gpt-4o-mini' }, { model_name: 'claude-3-5-sonnet' }]
    })
    expect(getCalls('navigateTo')).toHaveLength(0)
  })

  it('服务端业务错误（E-1104 重复凭证）→ 原文提示，不跳转', async () => {
    const wrapper = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-1104', message: '该凭证已存在，请勿重复接入' } })
    await wrapper.find('[data-testid="save-btn"]').trigger('tap')
    await flushPromises()
    expect(toastTitles().join()).toContain('该凭证已存在，请勿重复接入')
    expect(getCalls('navigateTo')).toHaveLength(0)
  })
})

describe('页面 4 · 提交检测（保存 + POST /precheck → 检测进行中页）', () => {
  it('先 PUT 保存，再 POST /credentials/c1/precheck，成功后跳序号 5 检测进行中页', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ id: 'c1' })) // PUT
    pushResponse(ok({ job_id: 'j1' })) // precheck
    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    const reqs = getCalls('request').map((c) => c.args[0] as { url: string; method: string })
    expect(reqs).toHaveLength(3) // 1 次详情 + PUT + precheck
    expect(reqs[1]).toMatchObject({ url: '/api/v1/credentials/c1', method: 'PUT' })
    expect(reqs[2]).toMatchObject({ url: '/api/v1/credentials/c1/precheck', method: 'POST' })

    const nav = getCalls('navigateTo')
    expect(nav).toHaveLength(1)
    expect((nav[0].args[0] as { url: string }).url).toContain('/pages/detecting/index')
    expect((nav[0].args[0] as { url: string }).url).toContain('jobId=j1')
  })

  it('凭证名称为空 → 只提示，不发任何写请求（E-1001 前端前置校验）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="alias-input"]').setValue('   ')
    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()
    expect(getCalls('request')).toHaveLength(1) // 仅详情
    expect(toastTitles().join()).toContain('请输入凭证名称')
  })

  it('BaseURL 非 http(s) → 只提示，不发写请求', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="baseurl-input"]').setValue('api.example-llm.com/v1')
    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()
    expect(getCalls('request')).toHaveLength(1)
    expect(toastTitles().join()).toContain('http')
  })

  it('检测互斥（E-1301）→ 展示服务端原文，不跳转', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ id: 'c1' }))
    pushResponse({ statusCode: 200, data: { code: 'E-1301', message: '该凭证已有检测任务进行中' } })
    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()
    expect(toastTitles().join()).toContain('该凭证已有检测任务进行中')
    expect(getCalls('navigateTo')).toHaveLength(0)
  })
})
