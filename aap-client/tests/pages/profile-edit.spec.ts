/**
 * 序号 10【档案与凭证】供应商档案编辑（page-10-2 / 编辑主体档案）— 页面单测
 *
 * 文案真源：.calicat/raw/pages/page-10-2/design.tree.json（430 宽 · 设计总高 1409 · 无 TabBar）
 *   以下断言里的中文一律**手抄自设计树**（不引用实现常量，避免自证）：
 *     编辑主体档案 / 72% / 主体信息 / 企业名称 * / 统一社会信用代码 * / 供应商类型 * / 所在地区 * /
 *     详细地址 * / 官网 / 请输入企业官网地址 / 联系信息 / 联系人 * / 职务 / 手机号 * / 邮箱 / 公司简介 /
 *     资质文件 / 支持 JPG/PNG/PDF，≤10MB / 营业执照 / 必传 / 已上传 / 上游授权书 / 条件必传 /
 *     点击上传，仅支持单个文件 / 其他选传资质 / 增值电信业务许可证、等保备案等 / 保存草稿 / 保存
 * 几何真源（用于后续 DOM 实测对账）：顶栏 96 · 卡 padding20 r18 描边 #EEF2F7 · 输入框 44 r12 ·
 *   卡间距 12 · 底栏 padding[12,16,24,16] · 按钮 156×48 / 自适应×48
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD + 设计稿控件语义
 * 接口真源：GET/PUT /api/v1/provider/profile · GET/POST /api/v1/provider/qualifications ·
 *          DELETE /api/v1/provider/qualifications/{id}（18-API 只列路径未列方法 → 方法为推断）
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ProfileEditPage from '@/pages/profile-edit/index.vue'
import { getCalls, pushResponse, resetUniMock, setModalAnswer, storage } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 设计稿示例值（逐字抄自 design.tree.json：卡片就是「已填态」） */
const PROFILE = {
  provider_id: 'p1',
  company_name: '云智科技有限公司',
  unified_social_credit_code: '91330106MA2XXXXX8B',
  industry_category: 'RESELLER',
  province: '浙江省',
  city: '杭州市',
  address: '西湖区文三路 199 号 A 座 18F',
  contact_name: '李明',
  contact_title: '商务负责人',
  contact_phone: '13800006621',
  contact_email: 'liming@yunzhi.com',
  company_intro: '专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。',
  completeness: 72
}

const QUALS = {
  items: [{ id: 'q1', category: 'BUSINESS_LICENSE', file_name: '营业执照-云智科技.jpg' }]
}

async function mountPage(profile: Record<string, unknown> = PROFILE, quals: unknown = QUALS) {
  pushResponse(ok(profile))
  pushResponse(ok(quals))
  const wrapper = mount(ProfileEditPage)
  await flushPromises()
  return wrapper
}

async function tap(wrapper: ReturnType<typeof mount>, testid: string) {
  await wrapper.find(`[data-testid="${testid}"]`).trigger('tap')
  await flushPromises()
}

function requests() {
  return getCalls('request').map((c) => c.args[0] as Record<string, unknown>)
}

function lastToast() {
  const toasts = getCalls('showToast')
  return (toasts.at(-1)?.args[0] as { title?: string } | undefined)?.title
}

describe('序号 10 · 结构与设计稿文案一致', () => {
  beforeEach(() => resetUniMock())

  it('顶部导航：标题 + 完整度标签（值来自服务端，渲染为 72%）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="page-title"]').text()).toBe('编辑主体档案')
    expect(wrapper.find('[data-testid="completeness-chip"]').text()).toBe('72%')
  })

  it('三张卡标题（逐字，顺序与设计稿一致）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('.card__title').map((t) => t.text())).toEqual(['主体信息', '联系信息', '资质文件'])
  })

  it('主体信息卡：6 个字段标签逐字一致，官网用设计稿占位文案', async () => {
    const wrapper = await mountPage()
    const labels = wrapper.findAll('.field__label').map((t) => t.text())
    expect(labels).toEqual([
      '企业名称 *',
      '统一社会信用代码 *',
      '供应商类型 *',
      '所在地区 *',
      '详细地址 *',
      '官网',
      '联系人 *',
      '职务',
      '手机号 *',
      '邮箱',
      '公司简介'
    ])
    expect(wrapper.find('[data-testid="website-input"]').attributes('placeholder')).toBe('请输入企业官网地址')
  })

  it('供应商类型三项与选中态（设计稿选中「渠道商」）', async () => {
    const wrapper = await mountPage()
    const chips = wrapper.findAll('[data-testid="industry-chip"]')
    expect(chips.map((c) => c.text())).toEqual(['原厂', '渠道商', '中转商'])
    expect(chips.map((c) => c.attributes('data-checked'))).toEqual(['false', 'true', 'false'])
  })

  it('资质卡：右上说明 + 三行名称/角标/说明/已上传文件名（逐字）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="files-tip"]').text()).toBe('支持 JPG/PNG/PDF，≤10MB')
    expect(wrapper.findAll('[data-testid="qual-name"]').map((n) => n.text())).toEqual([
      '营业执照',
      '上游授权书',
      '其他选传资质'
    ])
    /* 设计稿第 1 行是**两个独立角标**（必传 = 红底 x156..191；已上传 = 绿底 x201..261），不是一个合并角标 */
    expect(wrapper.findAll('[data-testid="qual-badge"]').map((b) => b.text())).toEqual([
      '必传',
      '已上传',
      '条件必传'
    ])
    expect(wrapper.findAll('[data-testid="qual-badge"]').map((b) => b.attributes('data-badge'))).toEqual([
      'required',
      'uploaded',
      'conditional'
    ])
    expect(wrapper.find('[data-testid="qual-file"]').text()).toBe('营业执照-云智科技.jpg')
    expect(wrapper.find('[data-testid="qual-hint"]').text()).toBe('点击上传，仅支持单个文件')
    expect(wrapper.find('[data-testid="qual-desc"]').text()).toBe('增值电信业务许可证、等保备案等')
  })

  it('底部操作条两个按钮逐字一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="btn-draft"]').text()).toBe('保存草稿')
    expect(wrapper.find('[data-testid="btn-save"]').text()).toContain('保存')
  })

  it('公司简介计数按真实字数（设计稿 48/200 与 40 字示例不自洽 → 以真实长度为准）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="intro-counter"]').text()).toBe('40/200')
  })
})

describe('序号 10 · 首屏取数（GET /provider/profile + GET /provider/qualifications）', () => {
  beforeEach(() => resetUniMock())

  it('挂载即拉档案与资质两条请求，且路径正确', async () => {
    const wrapper = await mountPage()
    const paths = requests().map((r) => `${r.method ?? 'GET'} ${r.url}`)
    expect(paths).toEqual(['GET /api/v1/provider/profile', 'GET /api/v1/provider/qualifications'])
    expect(wrapper.findAll('[data-testid="qual-row"]').length).toBe(3)
  })

  it('服务端值回填到表单与地区选择框（不显示 undefined）', async () => {
    const wrapper = await mountPage()
    const val = (testid: string) => (wrapper.find(`[data-testid="${testid}"]`).element as HTMLInputElement).value
    expect(val('company-input')).toBe('云智科技有限公司')
    expect(val('uscc-input')).toBe('91330106MA2XXXXX8B')
    expect(wrapper.find('[data-testid="province-value"]').text()).toBe('浙江省')
    expect(wrapper.find('[data-testid="city-value"]').text()).toBe('杭州市')
    expect(val('contact-input')).toBe('李明')
    expect(val('title-input')).toBe('商务负责人')
    expect(val('phone-input')).toBe('13800006621')
    expect(val('email-input')).toBe('liming@yunzhi.com')
  })

  it('档案接口失败 → toast 错误提示，页面仍渲染设计稿文案（不白屏）', async () => {
    pushResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务异常', data: null } })
    pushResponse(ok(QUALS))
    const wrapper = mount(ProfileEditPage)
    await flushPromises()
    expect(lastToast()).toBe('服务异常')
    expect(wrapper.find('[data-testid="page-title"]').text()).toBe('编辑主体档案')
  })

  it('本地草稿存在时优先回填（保存草稿的恢复路径）', async () => {
    storage.set('aap_provider_profile_draft', JSON.stringify({ company_name: '草稿公司', province: '江苏省' }))
    const wrapper = await mountPage()
    const company = wrapper.find('[data-testid="company-input"]').element as HTMLInputElement
    expect(company.value).toBe('草稿公司')
    expect(wrapper.find('[data-testid="province-value"]').text()).toBe('江苏省')
  })
})

describe('序号 10 · 页面交互（client-only）', () => {
  beforeEach(() => resetUniMock())

  it('点「原厂」→ 选中态切换，且没有产生写请求', async () => {
    const wrapper = await mountPage()
    const chips = wrapper.findAll('[data-testid="industry-chip"]')
    await chips[0].trigger('tap')
    await flushPromises()
    const after = wrapper.findAll('[data-testid="industry-chip"]')
    expect(after.map((c) => c.attributes('data-checked'))).toEqual(['true', 'false', 'false'])
    expect(requests().length).toBe(2)
  })

  it('地区选择器选省市 → 两个框同步显示', async () => {
    const wrapper = await mountPage()
    await wrapper
      .find('[data-testid="region-picker"]')
      .trigger('change', { detail: { value: ['广东省', '深圳市', '南山区'] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="province-value"]').text()).toBe('广东省')
    expect(wrapper.find('[data-testid="city-value"]').text()).toBe('深圳市')
  })

  it('简介输入 → 计数实时更新', async () => {
    const wrapper = await mountPage()
    const intro = wrapper.find('[data-testid="intro-input"]')
    await intro.setValue('专注大模型')
    await flushPromises()
    expect(wrapper.find('[data-testid="intro-counter"]').text()).toBe('5/200')
  })

  it('统一社会信用代码合法时显示通过标记（设计稿绿勾），清空后消失', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="uscc-ok"]').exists()).toBe(true)
    await wrapper.find('[data-testid="uscc-input"]').setValue('91330106MA2XXXXX8')
    await flushPromises()
    expect(wrapper.find('[data-testid="uscc-ok"]').exists()).toBe(false)
  })

  it('返回 → navigateBack delta 1', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'back-btn')
    expect(getCalls('navigateBack').length).toBe(1)
  })
})

describe('序号 10 · 保存与草稿', () => {
  beforeEach(() => resetUniMock())

  it('表单非法（清空企业名称）→ toast「请输入企业名称」且不发写请求', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="company-input"]').setValue('')
    await flushPromises()
    await tap(wrapper, 'btn-save')
    expect(lastToast()).toBe('请输入企业名称')
    expect(requests().filter((r) => r.method === 'PUT').length).toBe(0)
  })

  it('手机号不合法 → R-01 拦截，不发写请求', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="phone-input"]').setValue('23800006621')
    await flushPromises()
    await tap(wrapper, 'btn-save')
    expect(lastToast()).toBe('请输入正确的手机号')
    expect(requests().filter((r) => r.method === 'PUT').length).toBe(0)
  })

  it('保存 → PUT /api/v1/provider/profile，提交体为数据字典字段名', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ provider_id: 'p1' }))
    await tap(wrapper, 'btn-save')
    const put = requests().filter((r) => r.method === 'PUT')
    expect(put.length).toBe(1)
    expect(put[0].url).toBe('/api/v1/provider/profile')
    expect(put[0].data).toEqual({
      company_name: '云智科技有限公司',
      unified_social_credit_code: '91330106MA2XXXXX8B',
      industry_category: 'RESELLER',
      province: '浙江省',
      city: '杭州市',
      address: '西湖区文三路 199 号 A 座 18F',
      website: '',
      contact_name: '李明',
      contact_title: '商务负责人',
      contact_phone: '13800006621',
      contact_email: 'liming@yunzhi.com',
      company_intro: '专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。'
    })
    expect(lastToast()).toBe('保存成功')
  })

  it('保存失败（服务端 E-1104）→ toast 服务端 message，不跳转', async () => {
    const wrapper = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-1104', message: '统一社会信用代码已存在', data: null } })
    await tap(wrapper, 'btn-save')
    expect(lastToast()).toBe('统一社会信用代码已存在')
    expect(getCalls('navigateTo').length).toBe(0)
  })

  it('保存草稿 → 只写本地草稿（storage），不发写请求', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'btn-draft')
    expect(requests().filter((r) => r.method === 'PUT' || r.method === 'POST').length).toBe(0)
    expect(JSON.parse(storage.get('aap_provider_profile_draft') as string).company_name).toBe('云智科技有限公司')
    expect(lastToast()).toBe('已存为草稿')
  })
})

describe('序号 10 · 资质文件交互', () => {
  beforeEach(() => resetUniMock())

  it('删除已上传资质：二次确认 → DELETE /api/v1/provider/qualifications/q1 → 刷新列表', async () => {
    const wrapper = await mountPage()
    setModalAnswer(true)
    pushResponse(ok({})) // DELETE
    pushResponse(ok({ items: [] })) // 刷新
    await tap(wrapper, 'qual-del-0')
    const deletes = requests().filter((r) => r.method === 'DELETE')
    expect(deletes.length).toBe(1)
    expect(deletes[0].url).toBe('/api/v1/provider/qualifications/q1')
    expect(getCalls('showModal').length).toBe(1)
    expect(wrapper.find('[data-testid="qual-file"]').exists()).toBe(false)
  })

  it('取消删除 → 不发 DELETE，文件名仍在', async () => {
    const wrapper = await mountPage()
    setModalAnswer(false)
    await tap(wrapper, 'qual-del-0')
    expect(requests().filter((r) => r.method === 'DELETE').length).toBe(0)
    expect(wrapper.find('[data-testid="qual-file"]').text()).toBe('营业执照-云智科技.jpg')
  })

  it('点空态行（上游授权书）→ 选文件后 POST /api/v1/provider/qualifications 只带元数据', async () => {
    const wrapper = await mountPage()
    // uni.chooseFile 桩：模拟选择「上游授权书.pdf」
    const chooseFile = (options: Record<string, unknown>) =>
      (options.success as (r: unknown) => void)({
        tempFiles: [{ name: '上游授权书.pdf', size: 1024 }]
      })
    ;(globalThis.uni as unknown as Record<string, unknown>).chooseFile = chooseFile
    pushResponse(ok({ id: 'q2' })) // POST
    pushResponse(ok({ items: [{ id: 'q2', category: 'UPSTREAM_AUTHORIZATION', file_name: '上游授权书.pdf' }] }))
    // 设计稿里空态行**没有**尾部图标（PNG y=1198 该区间无 ink）→ 上传入口是整行点击
    await wrapper.findAll('[data-testid="qual-row"]')[1].trigger('tap')
    await flushPromises()
    const posts = requests().filter((r) => r.method === 'POST')
    expect(posts.length).toBe(1)
    expect(posts[0].url).toBe('/api/v1/provider/qualifications')
    expect(posts[0].data).toEqual({ category: 'UPSTREAM_AUTHORIZATION', file_name: '上游授权书.pdf', file_size: 1024 })
    expect(lastToast()).toBe('已上传')
    delete (globalThis.uni as unknown as Record<string, unknown>).chooseFile
  })

  it('尾部图标只出现在已上传行（设计稿：删除 + 查看两枚；空态行 0 枚）', async () => {
    const wrapper = await mountPage()
    const rows = wrapper.findAll('[data-testid="qual-row"]')
    expect(rows.length).toBe(3)
    expect(rows[0].findAll('.icon-tap').length).toBe(2)
    expect(rows[1].findAll('.icon-tap').length).toBe(0)
    expect(rows[2].findAll('.icon-tap').length).toBe(0)
    expect(wrapper.find('[data-testid="qual-upload-1"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="qual-upload-2"]').exists()).toBe(false)
  })

  it('已上传行的「查看」箭头 = client-only（18-API 无文件查看接口 → 不臆造路由）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'qual-view-0')
    expect(getCalls('navigateTo').length).toBe(0)
    expect(lastToast()).toBeTruthy()
  })
})
