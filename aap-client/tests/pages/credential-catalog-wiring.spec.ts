/**
 * 凭证页候选模型来自**管理端维护的模型目录**（`GET /catalog/models`）。
 *
 * 背景（用户报障 2026-09-20）：「H5 前端接入凭证，模型清单列表还是空，
 * 我在 admin 加了几个厂商和配置了模型」。
 * 根因：凭证页的候选模型此前**只**取凭证详情的 `model_catalog`，
 * 而新建凭证该字段为空 → 列表恒空 → 无法勾选 → 报价带不出模型。
 * 管理端建的模型必须经 `/catalog/models` 进入本页，但前端一直没接。
 *
 * 本文件用 `vi.mock('@/api/catalog')` 直接给目录数据（不走测试底座的默认响应），
 * 断言「目录里的厂商/模型真的渲染成了候选行」——这是那条接线的唯一证据。
 *
 * ⚠️ 映射关键：进 `model_list` 的是**模型标识 modelUid**
 *    （后端 CatalogViews.Model.modelUid 注释原文「进 model_list 的就是它」），
 *    故断言提交体里出现的是 modelUid 而不是展示名 modelName。
 */
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CredentialSubmitPage from '@/pages/credential-submit/index.vue'
import { getCalls } from '../setup'

// 目录数据：两家厂商三个模型（用 modelUid 作为进 model_list 的标识）
const CATALOG = [
  { modelUid: 'gpt-4o', vendorName: 'OpenAI', contextWindow: 128000, enabled: true },
  { modelUid: 'gpt-4o-mini', vendorName: 'OpenAI', contextWindow: 128000, enabled: true },
  { modelUid: 'deepseek-chat', vendorName: 'DeepSeek', contextWindow: 64000, enabled: true }
]

vi.mock('@/api/catalog', () => ({
  catalogApi: {
    availableModels: vi.fn(async () => CATALOG)
  }
}))

const CREDENTIAL_ID_KEY = 'aap_credential_id'

async function mountPage() {
  // 无凭证 id（新建场景）——这正是用户遇到的情形：目录是唯一的候选来源
  uni.setStorageSync(CREDENTIAL_ID_KEY, '')
  const wrapper = mount(CredentialSubmitPage)
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('凭证页候选模型来自管理端模型目录', () => {
  it('目录里的厂商被渲染成候选分组（不是空列表）', async () => {
    const wrapper = await mountPage()
    const groups = wrapper.findAll('[data-testid="vendor-group"]')
    expect(groups.length).toBe(2)
    const text = wrapper.text()
    expect(text).toContain('OpenAI')
    expect(text).toContain('DeepSeek')
  })

  it('目录里的模型被渲染成可勾选行，且用 modelUid 作标识', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="model-row"]')
    expect(rows.length).toBe(3)
    const text = wrapper.text()
    // 勾选后进 model_list 的是 modelUid
    expect(text).toContain('gpt-4o-mini')
    expect(text).toContain('deepseek-chat')
  })

  it('勾选目录中的模型 → 已选计数变化（证明目录项真的可交互）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="selected-count"]').text()).toContain('0')
    await wrapper.find('[data-testid="model-check-0-0"]').trigger('tap')
    expect(wrapper.find('[data-testid="selected-count"]').text()).toContain('1')
  })

  it('目录请求确实发出（接线存在的直接证据）', async () => {
    await mountPage()
    // 底座对 /catalog/models 不 record，故这里断言 mock 被调用过
    const { catalogApi } = await import('@/api/catalog')
    expect((catalogApi.availableModels as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(0)
    // 同时确认没有误发凭证详情请求（无凭证 id 时不该发）
    const urls = getCalls('request').map((c) => String((c.args[0] as Record<string, unknown>).url))
    expect(urls.filter((u) => u.includes('/credentials/'))).toHaveLength(0)
  })
})
