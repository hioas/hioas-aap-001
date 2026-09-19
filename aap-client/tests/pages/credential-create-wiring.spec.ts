/**
 * 缺陷 4 · `POST /credentials` 前端未接线 —— 先红后绿
 *
 * 现状（联调实测）：`src/api/credential.ts` 只有 list/detail/PUT/precheck，
 * 页面 id 靠 query/storage 传入，取不到就 toast「缺少凭证标识，无法保存/提交」。
 * 后果：**小程序内用户无法新建凭证** → 凭证列表恒空 → 检测/报告/报价/合同/打款全链路不可达。
 * 而后端契约里 `POST /api/v1/credentials` 是存在的（credential-create.schema.json，
 * required = [api_key, base_url]）。
 *
 * 期望：页面在**无凭证标识时就地新建**，拿到 id 后继续原有保存/预检流程。
 */
import { describe, expect, it, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CredentialSubmitPage from '@/pages/credential-submit/index.vue'
import { getCalls, pushResponse, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })
const fail = (code: string, message: string) => ({
  statusCode: 200,
  data: { code, message, data: {} }
})

/** 页面最小可用输入：名称 + BaseURL + APIKey（APIKey 需先点编辑图标才出现输入框） */
async function fillForm(wrapper: ReturnType<typeof mount>) {
  await wrapper.find('[data-testid="alias-input"]').setValue('联调新凭证')
  await wrapper.find('[data-testid="baseurl-input"]').setValue('https://api.example-llm.com/v1')
  await wrapper.find('[data-testid="apikey-edit"]').trigger('tap')
  await wrapper.find('[data-testid="apikey-input"]').setValue('sk-e2e-abcdef0123456789')
  await flushPromises()
}

const urls = () => getCalls('request').map((c) => (c.args[0] as Record<string, any>).url)

describe('缺陷4 · 无凭证标识时就地新建', () => {
  beforeEach(() => {
    storage.clear()
  })

  it('保存草稿：先 POST /credentials 新建，再用返回的 id 走 PUT 保存', async () => {
    const wrapper = mount(CredentialSubmitPage)
    await flushPromises()
    await fillForm(wrapper)

    pushResponse(ok({ id: 'c-new-1' })) // POST /credentials
    pushResponse(ok({ id: 'c-new-1' })) // PUT /credentials/c-new-1

    await wrapper.find('[data-testid="save-btn"]').trigger('tap')
    await flushPromises()

    expect(urls()).toEqual(['/api/v1/credentials', '/api/v1/credentials/c-new-1'])
    const post = getCalls('request')[0].args[0] as Record<string, any>
    expect(post.method).toBe('POST')
    expect(post.data.base_url).toBe('https://api.example-llm.com/v1')
    expect(post.data.api_key).toBe('sk-e2e-abcdef0123456789')
    expect(getCalls('request')[1].args[0]).toMatchObject({ method: 'PUT' })
    // 新 id 应落盘，供后续页面复用
    expect(storage.get('aap_credential_id')).toBe('c-new-1')
  })

  it('提交检测：新建 → 保存 → 预检 → 跳检测页并带 jobId', async () => {
    const wrapper = mount(CredentialSubmitPage)
    await flushPromises()
    await fillForm(wrapper)

    pushResponse(ok({ id: 'c-new-2' })) // POST
    pushResponse(ok({ id: 'c-new-2' })) // PUT
    pushResponse(ok({ job_id: 'job-9' })) // precheck

    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    expect(urls()).toEqual([
      '/api/v1/credentials',
      '/api/v1/credentials/c-new-2',
      '/api/v1/credentials/c-new-2/precheck'
    ])
    const nav = getCalls('navigateTo')
    expect(nav.length).toBeGreaterThan(0)
    expect(String((nav[nav.length - 1].args[0] as Record<string, any>).url)).toContain('jobId=job-9')
  })

  it('已有凭证标识时不重复新建（只走 PUT）', async () => {
    storage.set('aap_credential_id', 'c-existing')
    pushResponse(ok({})) // GET detail（onMounted 回填）
    const wrapper = mount(CredentialSubmitPage)
    await flushPromises()
    await fillForm(wrapper)

    pushResponse(ok({ id: 'c-existing' })) // PUT

    await wrapper.find('[data-testid="save-btn"]').trigger('tap')
    await flushPromises()

    expect(urls()).not.toContain('/api/v1/credentials')
    expect(urls().some((u) => u === '/api/v1/credentials/c-existing')).toBe(true)
  })

  it('新建失败：如实透传服务端错误，不继续后续调用', async () => {
    const wrapper = mount(CredentialSubmitPage)
    await flushPromises()
    await fillForm(wrapper)

    pushResponse(fail('E-1104', '该 APIKey 已提交过（指纹重复）'))

    await wrapper.find('[data-testid="save-btn"]').trigger('tap')
    await flushPromises()

    expect(urls()).toEqual(['/api/v1/credentials'])
    const toast = getCalls('showToast').map((c) => (c.args[0] as Record<string, any>).title)
    // 项目约定：业务错误一律透传服务端 message，不臆造文案（见台账序号4 备注⑦）
    expect(toast.join(' ')).toContain('指纹重复')
  })

  it('无凭证标识且未填 APIKey：客户端就拦下（后端 api_key 必填）', async () => {
    const wrapper = mount(CredentialSubmitPage)
    await flushPromises()
    await wrapper.find('[data-testid="alias-input"]').setValue('联调新凭证')
    await wrapper.find('[data-testid="baseurl-input"]').setValue('https://api.example-llm.com/v1')
    await flushPromises()

    await wrapper.find('[data-testid="save-btn"]').trigger('tap')
    await flushPromises()

    expect(urls()).toEqual([])
    const toast = getCalls('showToast').map((c) => (c.args[0] as Record<string, any>).title)
    expect(toast.join(' ')).toContain('APIKey')
  })
})
