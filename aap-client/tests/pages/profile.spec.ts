/**
 * 序号 10.1【档案与凭证】供应商档案（page-10-1-2 / 主体档案）— 页面单测
 *
 * 文案真源：.calicat/raw/pages/page-10-1-2/design.tree.json（430 宽 · 设计总高 1414 · 无 TabBar）
 *   断言里的中文一律**手抄自设计树**（不引用实现常量，避免自证）。
 * 几何真源（像素量尺 + DOM 实测对账）：顶栏 96 · 卡1 158 · 卡2 413 · 卡3 279 · 卡4 319 · 底栏 84 · 页高 1414
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD + 设计稿控件语义
 * 接口真源：GET/PUT /api/v1/provider/profile · GET /api/v1/provider/qualifications
 *          （18-API 只列路径未列方法 → 方法为 REST 语义推断）
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ProfilePage from '@/pages/profile/index.vue'
import { getCalls, pushResponse, resetUniMock } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

/** 设计稿示例档案（逐字抄自 design.tree.json；本帧是「已认证」的已填态） */
const PROFILE = {
  provider_id: 'p1',
  company_name: '云智科技有限公司',
  unified_social_credit_code: '91330106MA2XXXXX8B',
  industry_category: 'RESELLER',
  province: '浙江',
  city: '杭州',
  address: '西湖区文三路 199 号 A 座 18F',
  website: 'www.yunzhi-tech.com',
  contact_name: '李明',
  contact_title: '商务负责人',
  contact_phone: '13800006621',
  contact_email: 'liming@yunzhi.com',
  company_intro: '专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。',
  completeness: 72
}

/** 设计稿第 1 行是已上传态（「已上传 · 2024-06-10」+ 绿色「已通过」） */
const QUALS = {
  items: [
    {
      id: 'q1',
      category: 'BUSINESS_LICENSE',
      file_name: '营业执照-云智科技.jpg',
      uploaded_at: '2024-06-10T09:30:00Z'
    }
  ]
}

async function mountPage(profile: Record<string, unknown> = PROFILE, quals: unknown = QUALS) {
  pushResponse(ok(profile))
  pushResponse(ok(quals))
  const wrapper = mount(ProfilePage)
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

function text(wrapper: ReturnType<typeof mount>, testid: string) {
  return wrapper.find(`[data-testid="${testid}"]`).text()
}

describe('序号 10.1 · 结构与设计稿文案一致', () => {
  beforeEach(() => resetUniMock())

  it('顶部导航：标题「主体档案」+ 完整度胶囊「完整度 72%」（值取自服务端）', async () => {
    const wrapper = await mountPage()
    expect(text(wrapper, 'page-title')).toBe('主体档案')
    expect(text(wrapper, 'completeness-pill')).toBe('完整度 72%')
  })

  it('四张卡标题（逐字，顺序与设计稿一致）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('.card__title').map((t) => t.text())).toEqual([
      '档案完整度',
      '主体信息',
      '联系信息',
      '资质文件'
    ])
  })

  it('完整度卡：标题行「72%」+ 进度条填充宽度 + 闸门提示逐字', async () => {
    const wrapper = await mountPage()
    expect(text(wrapper, 'completeness-percent')).toBe('72%')
    expect(wrapper.find('[data-testid="completeness-bar"]').attributes('style')).toContain('width: 72%')
    expect(text(wrapper, 'gate-hint')).toBe('档案完整度达到 100% 后，才可发起报价审核。当前还缺 2 项资质文件。')
  })

  it('11 个字段标签逐字且顺序一致', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('[data-testid="field-label"]').map((t) => t.text())).toEqual([
      '企业名称',
      '统一社会信用代码',
      '供应商类型',
      '所在地区',
      '详细地址',
      '官网',
      '联系人',
      '职务',
      '手机号',
      '邮箱',
      '公司简介'
    ])
  })

  it('主体信息卡：值逐字 + 供应商类型为蓝色 chip（设计稿选中「渠道商」）', async () => {
    const wrapper = await mountPage()
    expect(text(wrapper, 'v-company')).toBe('云智科技有限公司')
    expect(text(wrapper, 'v-uscc')).toBe('91330106MA2XXXXX8B')
    expect(text(wrapper, 'v-industry')).toBe('渠道商')
    expect(wrapper.find('[data-testid="v-industry"]').attributes('data-tone')).toBe('chip')
    expect(text(wrapper, 'v-region')).toBe('浙江 · 杭州')
    expect(text(wrapper, 'v-address')).toBe('西湖区文三路 199 号 A 座 18F')
    expect(text(wrapper, 'v-website')).toBe('www.yunzhi-tech.com')
    /* 设计稿官网文字为蓝色 #2563EB、其它值为 #0F172A → 用色调标记钉死 */
    expect(wrapper.find('[data-testid="v-website"]').attributes('data-tone')).toBe('link')
    expect(wrapper.find('[data-testid="v-company"]').attributes('data-tone')).toBe('text')
  })

  it('主体信息卡的锁定角标与锁定提示逐字', async () => {
    const wrapper = await mountPage()
    expect(text(wrapper, 'lock-badge')).toBe('已认证 · 不可编辑')
    expect(text(wrapper, 'note-basic')).toBe('主体信息已完成企业认证，如需修改请联系平台运营。')
  })

  it('联系信息卡：四个值 + 简介逐字，右上「编辑」', async () => {
    const wrapper = await mountPage()
    expect(text(wrapper, 'v-contact')).toBe('李明')
    expect(text(wrapper, 'v-title')).toBe('商务负责人')
    /* 设计稿手机号为空格三段式「138 **** 6621」（与 R-05 的 138****8888 口径不同 → 按设计稿） */
    expect(text(wrapper, 'v-phone')).toBe('138 **** 6621')
    expect(text(wrapper, 'v-email')).toBe('liming@yunzhi.com')
    expect(text(wrapper, 'v-intro')).toBe('专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。')
    expect(text(wrapper, 'action-edit')).toBe('编辑')
  })

  it('资质三行：名称 / 副标题 / 角标逐字（第 1 行已上传 + 已通过，第 2 行未上传 + 条件必传）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('[data-testid="qual-name"]').map((t) => t.text())).toEqual([
      '营业执照',
      '上游授权书',
      '增值电信业务许可证'
    ])
    expect(wrapper.findAll('[data-testid="qual-subtitle"]').map((t) => t.text())).toEqual([
      '已上传 · 2024-06-10',
      '未上传',
      '选传 · 可后续补充'
    ])
    expect(wrapper.findAll('[data-testid="qual-badge"]').map((t) => t.text())).toEqual(['已通过', '条件必传'])
    expect(wrapper.findAll('[data-testid="qual-badge"]').map((t) => t.attributes('data-tone'))).toEqual([
      'success',
      'warning'
    ])
    expect(text(wrapper, 'action-manage')).toBe('管理')
  })

  it('单测快照式核对：底部三个操作按钮逐字', async () => {
    const wrapper = await mountPage()
    expect(text(wrapper, 'btn-upload')).toBe('上传新资质')
    expect(text(wrapper, 'btn-save')).toBe('保存')
    expect(text(wrapper, 'btn-complete')).toBe('去补全资质')
  })

  it('第 3 行是唯一的 chevron 行（设计稿资质3 末尾箭头）', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('[data-testid="qual-chevron"]').length).toBe(1)
    expect(
      wrapper.findAll('[data-testid="qual-row"]')[2].find('[data-testid="qual-chevron"]').exists()
    ).toBe(true)
  })

  it('本页是只读视图：不含任何输入控件', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('input').length).toBe(0)
    expect(wrapper.findAll('textarea').length).toBe(0)
  })
})

describe('序号 10.1 · 首屏取数（GET /provider/profile + GET /provider/qualifications）', () => {
  beforeEach(() => resetUniMock())

  it('挂载即拉档案与资质两条请求，路径正确', async () => {
    const wrapper = await mountPage()
    expect(requests().map((r) => `${r.method ?? 'GET'} ${r.url}`)).toEqual([
      'GET /api/v1/provider/profile',
      'GET /api/v1/provider/qualifications'
    ])
    expect(wrapper.findAll('[data-testid="qual-row"]').length).toBe(3)
  })

  it('服务端给了服务端脱敏字段时以服务端为准（不二次脱敏）', async () => {
    const wrapper = await mountPage({ ...PROFILE, contact_phone_mask: '138****8888' })
    expect(text(wrapper, 'v-phone')).toBe('138****8888')
  })

  it('档案为空 → 值渲染占位符（不显示 undefined），仍渲染设计稿文案', async () => {
    const wrapper = await mountPage({})
    expect(text(wrapper, 'v-company')).toBe('—')
    expect(text(wrapper, 'v-uscc')).toBe('—')
    expect(text(wrapper, 'v-region')).toBe('—')
    expect(text(wrapper, 'v-phone')).toBe('—')
    expect(text(wrapper, 'gate-hint')).toBe('档案完整度达到 100% 后，才可发起报价审核。当前还缺 2 项资质文件。')
  })

  it('完整度缺失 → 胶囊不渲染，进度条 0%', async () => {
    const wrapper = await mountPage({ company_name: '云智科技有限公司' })
    expect(wrapper.find('[data-testid="completeness-pill"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="completeness-bar"]').attributes('style')).toContain('width: 0%')
  })

  it('档案接口失败 → toast 服务端 message，页面不白屏', async () => {
    pushResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务异常', data: null } })
    pushResponse(ok(QUALS))
    const wrapper = mount(ProfilePage)
    await flushPromises()
    expect(lastToast()).toBe('服务异常')
    expect(text(wrapper, 'page-title')).toBe('主体档案')
  })

  it('资质接口失败 → 三行回落设计稿空态（不白屏、不臆造数据）', async () => {
    pushResponse(ok(PROFILE))
    pushResponse({ statusCode: 500, data: { code: 'E-2001', message: '服务异常', data: null } })
    const wrapper = mount(ProfilePage)
    await flushPromises()
    expect(wrapper.findAll('[data-testid="qual-subtitle"]').map((t) => t.text())).toEqual([
      '',
      '未上传',
      '选传 · 可后续补充'
    ])
  })

  it('资质返回裸数组也兼容', async () => {
    const wrapper = await mountPage(PROFILE, [
      { id: 'q1', category: 'BUSINESS_LICENSE', file_name: 'a.jpg', uploaded_at: '2024-06-10' }
    ])
    expect(wrapper.findAll('[data-testid="qual-subtitle"]')[0].text()).toBe('已上传 · 2024-06-10')
  })
})

describe('序号 10.1 · 页面交互（navigation / api 分类）', () => {
  beforeEach(() => resetUniMock())

  it('返回 → navigateBack delta 1', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'back-btn')
    expect(getCalls('navigateBack').length).toBe(1)
  })

  it('「编辑」（联系信息）→ navigateTo 序号 10 编辑页', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'action-edit')
    const navs = getCalls('navigateTo')
    expect(navs.length).toBe(1)
    expect((navs[0].args[0] as { url?: string }).url).toBe('/pages/profile-edit/index')
  })

  it('「管理」（资质）→ navigateTo 序号 10 编辑页', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'action-manage')
    const navs = getCalls('navigateTo')
    expect(navs.length).toBe(1)
    expect((navs[0].args[0] as { url?: string }).url).toBe('/pages/profile-edit/index')
  })

  it('「上传新资质」→ 落编辑页（本页固定三行、无新增行位；分类码全 PRD 无定义 → 不臆造 POST）', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'btn-upload')
    const navs = getCalls('navigateTo')
    expect(navs.length).toBe(1)
    expect((navs[0].args[0] as { url?: string }).url).toBe('/pages/profile-edit/index')
    expect(requests().filter((r) => r.method === 'POST').length).toBe(0)
  })

  it('「去补全资质」→ navigateTo 序号 10 编辑页', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'btn-complete')
    const navs = getCalls('navigateTo')
    expect(navs.length).toBe(1)
    expect((navs[0].args[0] as { url?: string }).url).toBe('/pages/profile-edit/index')
  })

  it('点击只读字段不产生任何跳转与写请求', async () => {
    const wrapper = await mountPage()
    await tap(wrapper, 'v-company')
    await tap(wrapper, 'v-website')
    expect(getCalls('navigateTo').length).toBe(0)
    expect(requests().length).toBe(2)
  })
})

describe('序号 10.1 · 「保存」（PUT /provider/profile）', () => {
  beforeEach(() => resetUniMock())

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
      province: '浙江',
      city: '杭州',
      address: '西湖区文三路 199 号 A 座 18F',
      website: 'www.yunzhi-tech.com',
      contact_name: '李明',
      contact_title: '商务负责人',
      contact_phone: '13800006621',
      contact_email: 'liming@yunzhi.com',
      company_intro: '专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。'
    })
    expect(lastToast()).toBe('保存成功')
  })

  it('保存失败 → toast 服务端 message，不跳转', async () => {
    const wrapper = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-1601', message: '状态非法流转', data: null } })
    await tap(wrapper, 'btn-save')
    expect(lastToast()).toBe('状态非法流转')
    expect(getCalls('navigateTo').length).toBe(0)
  })

  it('保存成功且响应带完整度时刷新展示值', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ completeness: 78 }))
    await tap(wrapper, 'btn-save')
    expect(text(wrapper, 'completeness-pill')).toBe('完整度 78%')
    expect(wrapper.find('[data-testid="completeness-bar"]').attributes('style')).toContain('width: 78%')
  })
})
