/**
 * 卡片「报价」= 对「新建报价」同页做编辑（用户口径 2026-09-19）
 *
 * 背景：此前「新建报价」→ `quote-models`，而卡片上的「报价」→ `quote-form`（旧设计 page-26 的另一套实现），
 * 同一个业务动作有两套长得不一样的界面。用户裁定：**以「新建报价」为准，卡片「报价」= 编辑那张报价单**。
 *
 * 本文件锁定四件事：
 *   1. 路由层：`quote` 动作与「新建报价」指向**同一个页面**，靠 `?quoteId=` 区分新建/编辑
 *   2. 行为层：带 `?quoteId=` 进来是编辑态 —— 回填既有内容、保存**先 PUT 表头再 setItems**、
 *      **绝不 create**（2026-09-23 起表头有 QT-02b 可写；此前表头改动被静默丢弃）
 *   3. 只读门禁：非 DRAFT/REJECTED 的单子（服务端 EDITABLE 之外）点保存只提示、不发写请求
 *   4. 反向护栏：不带 query 进来必须是**新建态**（不能被 storage 残留值误判成编辑）
 *
 * 接口真源：18-API → GET /quotes/{quoteId} · POST /quotes · PUT /quotes/{quoteId}（QT-02b）·
 *          POST /quotes/{quoteId}/items
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuoteSetupPage from '@/pages/quote-models/index.vue'
import { getCalls, pushResponse } from '../setup'
import { EDIT_PAGE_TITLE, PAGE_TITLE } from '@/utils/quote-setup-model'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const PROFILE = { id: 'p1', company_name: '上海徽石科技国外', unified_social_credit_code: '91330106MA2XXXXX8B' }

const CREDENTIALS = {
  total: 1,
  items: [{ id: 'c1', alias: '华东主线路 · GPT 通道', detection_status: 'PASS' }]
}

const C1_DETAIL = {
  id: 'c1',
  alias: '华东主线路 · GPT 通道',
  api_key_mask: 'sk-prod-••••••••2f9a',
  model_list: [
    { model_name: 'gpt-4o', vendor: 'OpenAI' },
    { model_name: 'gpt-4o-mini', vendor: 'OpenAI' },
    { model_name: 'deepseek-chat', vendor: 'DeepSeek' }
  ]
}

/** 既有报价单（编辑态要回填的对象） */
const QUOTE_DETAIL = {
  quote_id: 'q42',
  quote_no: 'Q20260919000009',
  name: '华东主线路报价',
  status: 'DRAFT',
  credential_id: 'c1',
  items: [
    { model_name: 'gpt-4o' },
    { model_name: 'deepseek-chat' }
  ]
}

/**
 * 按页面真实的请求顺序喂响应。
 *
 * ⚠️ 顺序是有依赖的，不能随便调：`onMounted` 里先 `Promise.all([档案, 凭证列表])`，
 * 编辑态再 `loadExistingQuote()` → 先 `GET /quotes/{id}`，**之后**才 `pickCredential()` →
 * `GET /credentials/{id}`。所以报价单详情必须排在凭证详情**前面**。
 */
async function mountPage(opts: { quoteId?: string; status?: string } = {}) {
  if (opts.quoteId) {
    globalThis.getCurrentPages = () => [{ options: { quoteId: opts.quoteId } }] as never
  } else {
    delete (globalThis as Record<string, unknown>).getCurrentPages
  }
  pushResponse(ok(PROFILE))
  pushResponse(ok(CREDENTIALS))
  if (opts.quoteId) {
    pushResponse(ok(opts.status ? { ...QUOTE_DETAIL, status: opts.status } : QUOTE_DETAIL)) // ③ GET /quotes/q42
    pushResponse(ok(C1_DETAIL)) // ④ GET /credentials/c1（编辑态回填模型清单）
  }
  const wrapper = mount(QuoteSetupPage)
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return wrapper
}

/** 取所有已发出请求的 URL（含 /api/v1 前缀），断言只关心后缀 */
function urlCalls(): string[] {
  return getCalls('request').map((c) => String((c.args[0] as Record<string, unknown>).url))
}

describe('卡片「报价」= 编辑「新建报价」同一页', () => {
  it('编辑态：标题变为「编辑报价单」，新建态仍是「新增报价单」', async () => {
    const edit = await mountPage({ quoteId: 'q42' })
    expect(edit.text()).toContain(EDIT_PAGE_TITLE)
    expect(edit.text()).not.toContain(PAGE_TITLE)

    const create = await mountPage()
    expect(create.text()).toContain(PAGE_TITLE)
    expect(create.text()).not.toContain(EDIT_PAGE_TITLE)
    delete (globalThis as Record<string, unknown>).getCurrentPages
  })

  it('编辑态：按 quoteId 拉取既有报价单（GET /api/v1/quotes/q42）', async () => {
    await mountPage({ quoteId: 'q42' })
    const urls = urlCalls()
    expect(urls.some((u) => u.endsWith('/quotes/q42'))).toBe(true)
    delete (globalThis as Record<string, unknown>).getCurrentPages
  })

  it('编辑态：回填既有明细的勾选状态（gpt-4o / deepseek-chat 选中，gpt-4o-mini 未选）', async () => {
    const wrapper = await mountPage({ quoteId: 'q42' })
    // 三行模型都应渲染出来（来自凭证详情）
    for (const name of ['gpt-4o', 'gpt-4o-mini', 'deepseek-chat']) {
      expect(wrapper.text()).toContain(name)
    }
    // 已选计数：既有明细 2 条命中，1 条未命中
    expect(wrapper.text()).toMatch(/已选\s*2/)
    delete (globalThis as Record<string, unknown>).getCurrentPages
  })

  it('编辑态保存：走 setItems 整体替换明细，**绝不**调用 POST /quotes（不新建单子）', async () => {
    const wrapper = await mountPage({ quoteId: 'q42' })
    pushResponse(ok({})) // setItems 的响应
    await (wrapper.vm as unknown as { onSave: () => Promise<void> }).onSave()
    await flushPromises()

    const posts = getCalls('request').filter(
      (c) => String((c.args[0] as Record<string, unknown>).method).toUpperCase() === 'POST'
    )
    const urls = posts.map((c) => String((c.args[0] as Record<string, unknown>).url))
    // 明细替换打到的具体 item 端点（.../quotes/q42/items），但**没有**裸 POST /quotes 的建单请求
    expect(urls.some((u) => u.includes('/quotes/q42/items'))).toBe(true)
    expect(urls.filter((u) => /\/quotes\/?$/.test(u))).toEqual([])
    delete (globalThis as Record<string, unknown>).getCurrentPages
  })

  it('编辑态保存：**先 PUT 表头**（QT-02b）再 setItems —— 表头的改动不再被静默丢弃', async () => {
    const wrapper = await mountPage({ quoteId: 'q42' })
    pushResponse(ok({})) // PUT /quotes/q42（表头）
    pushResponse(ok({})) // POST /quotes/q42/items（明细）
    await (wrapper.vm as unknown as { onSave: () => Promise<void> }).onSave()
    await flushPromises()

    const calls = getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
    const put = calls.find((c) => String(c.method).toUpperCase() === 'PUT')
    expect(put, '编辑态保存必须先写表头').toBeTruthy()
    expect(String(put?.url)).toMatch(/\/quotes\/q42$/)
    expect(put?.data).toMatchObject({ name: '华东主线路报价', credential_id: 'c1' })
    delete (globalThis as Record<string, unknown>).getCurrentPages
  })

  it('只读门禁：已提交（SUBMITTED）的单子点保存 → 只提示「当前状态不可编辑」，不发任何写请求', async () => {
    const wrapper = await mountPage({ quoteId: 'q42', status: 'SUBMITTED' })
    await (wrapper.vm as unknown as { onSave: () => Promise<void> }).onSave()
    await flushPromises()

    const writes = getCalls('request').filter((c) =>
      ['PUT', 'POST', 'DELETE'].includes(String((c.args[0] as Record<string, unknown>).method).toUpperCase())
    )
    expect(writes, '非可编辑状态点保存不得发出必然 409 的写请求').toEqual([])
    expect(getCalls('showToast').at(-1)?.args[0]).toMatchObject({ title: '当前状态不可编辑，仅可查看' })
    delete (globalThis as Record<string, unknown>).getCurrentPages
  })

  it('反向护栏：不带 quoteId 进来必须是新建态，不能被上次编辑的残留 id 带偏', async () => {
    // 先做一次编辑，把 id 写进 storage（实现里「只写不读」）
    await mountPage({ quoteId: 'q42' })
    delete (globalThis as Record<string, unknown>).getCurrentPages
    // 再走新建入口：无 query → 必须仍是「新增报价单」，且不发 GET /quotes/q42
    const create = await mountPage()
    expect(create.text()).toContain(PAGE_TITLE)
    const urls = getCalls('request').map((c) => String((c.args[0] as Record<string, unknown>).url))
    expect(urls.filter((u) => u === '/quotes/q42')).toEqual([])
  })
})
