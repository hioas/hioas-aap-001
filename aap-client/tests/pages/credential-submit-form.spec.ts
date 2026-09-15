/**
 * 页面 4-v1「接入凭证-表单」（序号 4-v1 / page-24）— 页面单测
 *
 * 设计真源：.calicat/raw/pages/page-24/design.tree.json（430 宽）
 *   顶部栏(返回按钮 36 圆 + 标题块 + 扫描按钮 36 圆) ·
 *   基本信息卡(客户名称* / 统一社会信用代码* / 联系人 / 联系电话，输入框 44 高) ·
 *   检测类型卡(基础检测选中 / 深度检测 / 合规检测) ·
 *   凭证资料卡(上传区虚线框 + 已上传文件行) · 备注卡 · 提交按钮(48 高) + 提交提示
 * 接口：18-API Provider Tag → POST /api/v1/provider/qualifications（见 src/api/access-application.ts 头部说明）
 * 交互分类：返回=navigation；扫描按钮=client-only（画布 30 页无对应页，不臆造路由）；
 *   四个输入框/检测类型/上传/删文件=client-only；提交接入=api + navigation(/pages/detecting/index)。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import FormPage from '@/pages/credential-submit/form.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const uniAny = globalThis.uni as unknown as Record<string, unknown>

/** 给 uni.chooseFile 打桩（H5 路径）；小程序路径 uni.chooseMessageFile 由用例单独覆盖 */
function stubChooseFile(result: { name: string; size: number } | 'fail') {
  uniAny.chooseFile = (options: Record<string, unknown>) => {
    const success = options.success as ((r: unknown) => void) | undefined
    const fail = options.fail as ((r: unknown) => void) | undefined
    Promise.resolve().then(() => {
      if (result === 'fail') fail?.({ errMsg: 'chooseFile:fail cancel' })
      else success?.({ tempFiles: [{ path: result.name, name: result.name, size: result.size }] })
    })
    return {}
  }
}

function deleteChooseFile() {
  delete uniAny.chooseFile
  delete uniAny.chooseMessageFile
}

const mountPage = () => mount(FormPage)

/** 填到「可提交」状态 */
async function fillValid(wrapper: ReturnType<typeof mount>) {
  await wrapper.find('[data-testid="company-input"]').setValue('深圳市恒信科技有限公司')
  await wrapper.find('[data-testid="uscc-input"]').setValue('91440300MA5DAJQH6X')
}

beforeEach(() => {
  deleteChooseFile()
})

describe('结构：文案与元素逐条对齐设计稿', () => {
  it('顶部栏：标题「接入凭证」+ 副标题「填写客户信息并提交检测」+ 返回/扫描按钮', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="page-title"]').text()).toBe('接入凭证')
    expect(wrapper.find('[data-testid="page-subtitle"]').text()).toBe('填写客户信息并提交检测')
    expect(wrapper.find('[data-testid="back-btn"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="scan-btn"]').exists()).toBe(true)
  })

  it('四个区块标题（基本信息 / 检测类型 / 凭证资料 / 备注）', () => {
    const wrapper = mountPage()
    const titles = wrapper.findAll('[data-testid="section-title"]').map((n) => n.text())
    expect(titles).toEqual(['基本信息', '检测类型', '凭证资料', '备注'])
  })

  it('四个字段标签 + 仅两处必填星号（客户名称 / 统一社会信用代码）', () => {
    const wrapper = mountPage()
    const labels = wrapper.findAll('[data-testid="field-label"]').map((n) => n.text())
    expect(labels).toEqual(['客户名称', '统一社会信用代码', '联系人', '联系电话'])
    expect(wrapper.findAll('[data-testid="field-star"]')).toHaveLength(2)
  })

  it('三个输入占位文案 === 设计原文', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="uscc-input"]').attributes('placeholder')).toBe(
      '请输入 18 位统一社会信用代码'
    )
    expect(wrapper.find('[data-testid="contact-input"]').attributes('placeholder')).toBe('请输入联系人姓名')
    expect(wrapper.find('[data-testid="phone-input"]').attributes('placeholder')).toBe('请输入手机号')
    expect(wrapper.find('[data-testid="remark-input"]').attributes('placeholder')).toBe(
      '补充说明，例如客户所属行业、检测用途等'
    )
  })

  it('上传区三段文案 + 提交按钮与脚注文案', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="upload-tip"]').text()).toBe('支持 jpg / png / pdf')
    expect(wrapper.find('[data-testid="upload-main"]').text()).toBe('点击上传凭证文件')
    expect(wrapper.find('[data-testid="upload-limit"]').text()).toBe('单个文件不超过 10MB')
    expect(wrapper.find('[data-testid="submit-btn"]').text()).toContain('提交接入')
    expect(wrapper.find('[data-testid="submit-footnote"]').text()).toBe(
      '提交后系统将自动发起检测，预计 5 分钟内完成'
    )
  })
})

describe('检测类型：单选 chip', () => {
  it('三项文案与顺序 === 设计稿，默认选中「基础检测」（设计稿选中态）', () => {
    const wrapper = mountPage()
    const chips = wrapper.findAll('[data-testid="type-chip"]')
    expect(chips.map((c) => c.text())).toEqual(['基础检测', '深度检测', '合规检测'])
    expect(chips[0].attributes('data-checked')).toBe('true')
    expect(chips[1].attributes('data-checked')).toBe('false')
    expect(chips[2].attributes('data-checked')).toBe('false')
  })

  it('点「深度检测」→ 单选切换，另外两个取消选中', async () => {
    const wrapper = mountPage()
    await wrapper.findAll('[data-testid="type-chip"]')[1].trigger('tap')

    const chips = wrapper.findAll('[data-testid="type-chip"]')
    expect(chips[0].attributes('data-checked')).toBe('false')
    expect(chips[1].attributes('data-checked')).toBe('true')
    expect(chips[2].attributes('data-checked')).toBe('false')
  })

  it('切换类型不发请求（无接口依据 → 纯 UI 态）', async () => {
    const wrapper = mountPage()
    await wrapper.findAll('[data-testid="type-chip"]')[2].trigger('tap')
    expect(getCalls('request')).toHaveLength(0)
  })
})

describe('凭证资料上传', () => {
  it('点击上传区 → 调 uni.chooseFile，合法文件进入已上传列表并显示大小', async () => {
    stubChooseFile({ name: '营业执照扫描件.pdf', size: 2516582 })
    const wrapper = mountPage()

    await wrapper.find('[data-testid="upload-box"]').trigger('tap')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="file-row"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="file-name"]').text()).toBe('营业执照扫描件.pdf')
    expect(wrapper.find('[data-testid="file-size"]').text()).toBe('2.4 MB')
    expect(getCalls('request')).toHaveLength(0)
  })

  it('非法格式 → toast 提示且不进入列表', async () => {
    stubChooseFile({ name: '合同.txt', size: 1024 })
    const wrapper = mountPage()

    await wrapper.find('[data-testid="upload-box"]').trigger('tap')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="file-row"]')).toHaveLength(0)
    const toast = getCalls('showToast').pop()
    expect((toast?.args[0] as { title?: string }).title).toBe('仅支持 jpg / png / pdf 格式')
  })

  it('超过 10MB → toast 提示且不进入列表', async () => {
    stubChooseFile({ name: 'big.pdf', size: 11 * 1024 * 1024 })
    const wrapper = mountPage()

    await wrapper.find('[data-testid="upload-box"]').trigger('tap')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="file-row"]')).toHaveLength(0)
    expect((getCalls('showToast').pop()?.args[0] as { title?: string }).title).toBe('单个文件不超过 10MB')
  })

  it('用户取消选择 → 静默，不弹提示', async () => {
    stubChooseFile('fail')
    const wrapper = mountPage()

    await wrapper.find('[data-testid="upload-box"]').trigger('tap')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="file-row"]')).toHaveLength(0)
    expect(getCalls('showToast')).toHaveLength(0)
  })

  it('小程序路径（无 uni.chooseFile 时）退 uni.chooseMessageFile', async () => {
    uniAny.chooseMessageFile = (options: Record<string, unknown>) => {
      const success = options.success as ((r: unknown) => void) | undefined
      Promise.resolve().then(() =>
        success?.({ tempFiles: [{ path: '营业执照扫描件.pdf', name: '营业执照扫描件.pdf', size: 2516582 }] })
      )
      return {}
    }
    const wrapper = mountPage()

    await wrapper.find('[data-testid="upload-box"]').trigger('tap')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="file-row"]')).toHaveLength(1)
    expect(getCalls('request')).toHaveLength(0)
  })

  it('点删除图标 → 该行移除', async () => {
    stubChooseFile({ name: '营业执照扫描件.pdf', size: 2516582 })
    const wrapper = mountPage()
    await wrapper.find('[data-testid="upload-box"]').trigger('tap')
    await flushPromises()

    await wrapper.find('[data-testid="file-del-0"]').trigger('tap')

    expect(wrapper.findAll('[data-testid="file-row"]')).toHaveLength(0)
  })
})

describe('提交接入', () => {
  it('客户名称为空 → 本地拦截，不发请求', async () => {
    const wrapper = mountPage()
    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    expect((getCalls('showToast').pop()?.args[0] as { title?: string }).title).toBe('请输入客户名称')
    expect(getCalls('request')).toHaveLength(0)
  })

  it('信用代码非法 → 本地拦截，不发请求', async () => {
    const wrapper = mountPage()
    await wrapper.find('[data-testid="company-input"]').setValue('深圳市恒信科技有限公司')
    await wrapper.find('[data-testid="uscc-input"]').setValue('91440300MA5DAJQH6')
    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    expect((getCalls('showToast').pop()?.args[0] as { title?: string }).title).toBe(
      '统一社会信用代码需为 18 位字母数字'
    )
    expect(getCalls('request')).toHaveLength(0)
  })

  it('合法 → POST /api/v1/provider/qualifications（有据字段 + 资质文件）', async () => {
    stubChooseFile({ name: '营业执照扫描件.pdf', size: 2516582 })
    pushResponse(ok({ id: 'q1', detection_job_id: 'J-20260916-001' }))
    const wrapper = mountPage()

    await fillValid(wrapper)
    await wrapper.find('[data-testid="remark-input"]').setValue('检测用途：模型验真')
    await wrapper.find('[data-testid="upload-box"]').trigger('tap')
    await flushPromises()
    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    const req = getCalls('request')[0].args[0] as Record<string, unknown>
    expect(req.url).toBe('/api/v1/provider/qualifications')
    expect(req.method).toBe('POST')
    expect(req.data).toEqual({
      company_name: '深圳市恒信科技有限公司',
      unified_social_credit_code: '91440300MA5DAJQH6X',
      qualification_files: [{ file_name: '营业执照扫描件.pdf', file_size: 2516582 }]
    })
  })

  it('提交成功 → 跳检测进行中页并带上检测任务号', async () => {
    pushResponse(ok({ id: 'q1', detection_job_id: 'J-20260916-001' }))
    const wrapper = mountPage()
    await fillValid(wrapper)

    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    const nav = getCalls('navigateTo').pop()
    expect((nav?.args[0] as { url?: string }).url).toBe('/pages/detecting/index?jobId=J-20260916-001')
  })

  it('响应无任务号 → 仍跳检测进行中页（设计脚注：提交后自动发起检测）', async () => {
    pushResponse(ok({ id: 'q1' }))
    const wrapper = mountPage()
    await fillValid(wrapper)

    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    expect((getCalls('navigateTo').pop()?.args[0] as { url?: string }).url).toBe('/pages/detecting/index')
  })

  it('服务端拒绝（E-1104）→ 用服务端 message 提示，不跳转', async () => {
    pushResponse({ statusCode: 200, data: { code: 'E-1104', message: '该企业已提交过接入申请' } })
    const wrapper = mountPage()
    await fillValid(wrapper)

    await wrapper.find('[data-testid="submit-btn"]').trigger('tap')
    await flushPromises()

    expect((getCalls('showToast').pop()?.args[0] as { title?: string }).title).toBe('该企业已提交过接入申请')
    expect(getCalls('navigateTo')).toHaveLength(0)
  })
})

describe('其余交互', () => {
  it('返回按钮 → navigateBack delta 1', async () => {
    const wrapper = mountPage()
    await wrapper.find('[data-testid="back-btn"]').trigger('tap')
    expect((getCalls('navigateBack').pop()?.args[0] as { delta?: number }).delta).toBe(1)
  })

  it('扫描按钮 → client-only toast（画布无对应页面，不臆造路由）', async () => {
    const wrapper = mountPage()
    await wrapper.find('[data-testid="scan-btn"]').trigger('tap')

    expect(getCalls('navigateTo')).toHaveLength(0)
    expect(getCalls('showToast')).toHaveLength(1)
  })
})
