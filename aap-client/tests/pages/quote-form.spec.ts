/**
 * 序号 12-v1【报价管理】新增报价单-初始态（page-26）— 页面结构与设计稿文案（TDD 切片 2，先红）
 *
 * 文案真源：.calicat/raw/pages/page-26/design.tree.json（430 宽 · 设计总高 1238 · 无 TabBar · 底栏随文档流）
 *   本切片只断言**渲染结构与文案**（交互见 quote-form-flow.spec.ts）。
 *   所有中文断言逐字手抄自设计树；同时断言本帧**没有**的元素不得凭空出现（不臆造）。
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import QuoteFormPage from '@/pages/quote-form/index.vue'

function mountPage() {
  return mount(QuoteFormPage)
}

function texts(wrapper: ReturnType<typeof mount>, testid: string) {
  return wrapper.findAll(`[data-testid="${testid}"]`).map((n) => n.text())
}

describe('序号 12-v1 · 顶部导航（设计 c36637be）', () => {
  it('标题与副标题按设计原文渲染', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="nav-title"]').text()).toBe('新增报价单')
    expect(wrapper.find('[data-testid="nav-subtitle"]').text()).toBe('填写基本信息并设置模型报价')
  })

  it('左右各有 36×36 圆形按钮（返回 / 帮助），无 TabBar', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="back"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="help"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tabbar"]').exists()).toBe(false)
  })
})

describe('序号 12-v1 · 步骤卡（设计 7acff570）', () => {
  it('两个步骤的标题与说明按设计原文，且初始态高亮步骤 1', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="step-1"]').text()).toContain('填写信息')
    expect(wrapper.find('[data-testid="step-1"]').text()).toContain('名称 / 密钥 / 单号')
    expect(wrapper.find('[data-testid="step-2"]').text()).toContain('设置报价')
    expect(wrapper.find('[data-testid="step-2"]').text()).toContain('模型定价')
    expect(wrapper.find('[data-testid="step-1"]').attributes('data-active')).toBe('true')
    expect(wrapper.find('[data-testid="step-2"]').attributes('data-active')).toBe('false')
  })
})

describe('序号 12-v1 · 基本信息卡（设计 82bbea2b）', () => {
  it('卡片标题与必填提示', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="card-basic-title"]').text()).toBe('基本信息')
    expect(wrapper.find('[data-testid="chip-required"]').text()).toBe('为必填项')
  })

  it('报价单名称：标签 + 必填星号 + 设计占位 + 字数 0/30', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="name-label"]').text()).toBe('报价单名称')
    expect(wrapper.find('[data-testid="name-star"]').text()).toBe('*')
    const input = wrapper.find('[data-testid="name-input"]')
    expect(input.attributes('placeholder')).toBe('请输入报价单名称，如：2024Q3 主线路报价')
    expect(wrapper.find('[data-testid="name-count"]').text()).toBe('0/30')
  })

  it('报价单号：标签 + 「系统生成」标 + 只读框占位与示例 + 说明行', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="quote-no-label"]').text()).toBe('报价单号')
    expect(wrapper.find('[data-testid="quote-no-tag"]').text()).toBe('系统生成')
    expect(wrapper.find('[data-testid="quote-no-text"]').text()).toBe('保存后自动生成')
    expect(wrapper.find('[data-testid="quote-no-sample"]').text()).toBe('QT-XXXXXXXX-XXXX')
    expect(wrapper.find('[data-testid="quote-no-hint"]').text()).toBe(
      '报价单号由系统按日期与序号规则自动生成，无需手动填写'
    )
    // 只读：设计为「系统生成」态，不提供输入控件
    expect(wrapper.find('[data-testid="quote-no-box"]').find('input').exists()).toBe(false)
  })

  it('凭证名称：标签 + 必填星号 + 占位 + 说明行', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="cred-label"]').text()).toBe('凭证名称')
    expect(wrapper.find('[data-testid="cred-star"]').text()).toBe('*')
    expect(wrapper.find('[data-testid="cred-value"]').text()).toBe('请选择凭证')
    expect(wrapper.find('[data-testid="cred-hint"]').text()).toBe(
      '选择凭证后，系统将自动带出该凭证下可用的模型列表'
    )
  })

  it('本帧设计无「报价主体」控件 → 契约不得凭空出现', () => {
    const wrapper = mountPage()
    expect(wrapper.text()).not.toContain('报价主体')
    expect(wrapper.text()).not.toContain('去新增')
  })
})

describe('序号 12-v1 · 模型列表卡（设计 9fabffe3）', () => {
  it('标题 + 「待带出」标 + 空态三行文案', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="card-models-title"]').text()).toBe('模型列表')
    expect(wrapper.find('[data-testid="chip-model"]').text()).toBe('待带出')
    expect(wrapper.find('[data-testid="model-empty-title"]').text()).toBe('尚未加载模型')
    expect(wrapper.find('[data-testid="model-empty-desc"]').text()).toBe(
      '请先在上方选择凭证，系统将自动带出可用模型列表'
    )
    expect(wrapper.find('[data-testid="model-empty-tip"]').text()).toBe(
      '带出的模型数量与凭证权限相关，可在「我的设置」中管理凭证权限范围。'
    )
  })

  it('初始态没有模型行（模型清单随凭证带出）', () => {
    const wrapper = mountPage()
    expect(wrapper.findAll('[data-testid^="model-row-"]')).toHaveLength(0)
  })

  it('本帧设计无模型行工具栏（「全选模型 / 按凭证实时带出」属序号 9 帧）→ 不臆造', () => {
    const wrapper = mountPage()
    expect(wrapper.text()).not.toContain('全选模型')
    expect(wrapper.text()).not.toContain('按凭证实时带出')
  })
})

describe('序号 12-v1 · 填写须知卡（设计 f4fab5a4）', () => {
  it('标题与三条须知按设计原文，序号点为 1/2/3', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="card-notice-title"]').text()).toBe('填写须知')
    expect(texts(wrapper, 'notice-index')).toEqual(['1', '2', '3'])
    expect(texts(wrapper, 'notice-text')).toEqual([
      '报价单名称建议包含季度或用途，便于后续在列表中检索。',
      '凭证决定可报价的模型范围，选择后模型列表自动刷新。',
      '首次保存成功后，系统将自动生成报价单号并进入设置报价环节。'
    ])
  })
})

describe('序号 12-v1 · 底部操作条（设计 0bf8e01d padding[12,16,28,16]）', () => {
  it('保存说明 + 两个按钮文案按设计原文', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="bar-hint"]').text()).toBe('保存成功后系统将自动生成报价单号')
    expect(wrapper.find('[data-testid="btn-draft"]').text()).toBe('存为草稿')
    expect(wrapper.find('[data-testid="btn-save"]').text()).toBe('保存并继续')
  })

  it('存为草稿为 128 宽幽灵按钮、保存并继续为主色按钮（类名可断言）', () => {
    const wrapper = mountPage()
    expect(wrapper.find('[data-testid="btn-draft"]').classes()).toContain('btn--ghost')
    expect(wrapper.find('[data-testid="btn-save"]').classes()).toContain('btn--primary')
  })
})
