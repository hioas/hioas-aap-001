/**
 * 序号 10.1【档案与凭证】供应商档案（page-10-1-2 / 主体档案）— 视图模型单测
 *
 * 文案真源：.calicat/raw/pages/page-10-1-2/design.tree.json（430 宽 · 设计总高 1414 · 无 TabBar）
 *   下列断言里的中文一律**手抄自设计树**（不引用实现常量，避免自证）：
 *     主体档案 / 完整度 72% / 档案完整度 / 72% /
 *     档案完整度达到 100% 后，才可发起报价审核。当前还缺 2 项资质文件。 /
 *     主体信息 / 已认证 · 不可编辑 / 企业名称 / 统一社会信用代码 / 供应商类型 / 所在地区 / 详细地址 / 官网 /
 *     主体信息已完成企业认证，如需修改请联系平台运营。 /
 *     联系信息 / 编辑 / 联系人 / 职务 / 手机号 / 邮箱 / 公司简介 /
 *     资质文件 / 管理 / 营业执照 / 已上传 · 2024-06-10 / 已通过 / 上游授权书 / 未上传 / 条件必传 /
 *     增值电信业务许可证 / 选传 · 可后续补充 / 上传新资质 / 保存 / 去补全资质
 * 几何真源（像素量尺见 .agents/state/design-shots/page-10-1-2.png）：
 *   顶栏 96 · 卡1 108..265(158) · 卡2 278..690(413) · 卡3 703..981(279) · 卡4 995..1313(319) ·
 *   底栏 1330..1413(84) · 页高 1414 · 卡间距 12 · 字段 = 标签 16 + 2 + 值 20
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD + 设计稿控件语义
 * 接口真源：18-API「Provider」→ GET /provider/profile、GET /provider/qualifications、PUT /provider/profile
 */
import { describe, expect, it } from 'vitest'
import {
  ACTION_EDIT,
  ACTION_MANAGE,
  BADGE_APPROVED,
  BADGE_CONDITIONAL,
  BADGE_LOCKED,
  BTN_COMPLETE,
  BTN_SAVE,
  BTN_UPLOAD,
  EMPTY_VALUE,
  GATE_HINT,
  LABEL_ADDRESS,
  LABEL_COMPANY,
  LABEL_CONTACT_NAME,
  LABEL_CONTACT_TITLE,
  LABEL_EMAIL,
  LABEL_INDUSTRY,
  LABEL_INTRO,
  LABEL_PHONE,
  LABEL_REGION,
  LABEL_USCC,
  LABEL_WEBSITE,
  NOTE_BASIC_LOCKED,
  PAGE_TITLE,
  SECTION_BASIC,
  SECTION_COMPLETENESS,
  SECTION_CONTACT,
  SECTION_FILES,
  completenessBarWidth,
  completenessPercent,
  completenessPillText,
  industryLabel,
  mapProfileView,
  maskPhone,
  qualificationViewRows,
  regionText,
  toQualificationItems
} from '@/utils/profile-model'

/** 设计稿示例档案（逐字抄自 design.tree.json：本帧就是「已认证」的已填态） */
const PROFILE = {
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

describe('序号 10.1 · 设计稿文案常量（逐字，禁改）', () => {
  it('页面标题 / 卡片标题 / 入口文案', () => {
    expect(PAGE_TITLE).toBe('主体档案')
    expect(SECTION_COMPLETENESS).toBe('档案完整度')
    expect(SECTION_BASIC).toBe('主体信息')
    expect(SECTION_CONTACT).toBe('联系信息')
    expect(SECTION_FILES).toBe('资质文件')
    expect(ACTION_EDIT).toBe('编辑')
    expect(ACTION_MANAGE).toBe('管理')
    expect(BTN_UPLOAD).toBe('上传新资质')
    expect(BTN_SAVE).toBe('保存')
    expect(BTN_COMPLETE).toBe('去补全资质')
  })

  it('角标与提示文案', () => {
    expect(BADGE_LOCKED).toBe('已认证 · 不可编辑')
    expect(BADGE_APPROVED).toBe('已通过')
    expect(BADGE_CONDITIONAL).toBe('条件必传')
    expect(NOTE_BASIC_LOCKED).toBe('主体信息已完成企业认证，如需修改请联系平台运营。')
    expect(GATE_HINT).toBe('档案完整度达到 100% 后，才可发起报价审核。当前还缺 2 项资质文件。')
  })

  it('11 个字段标签（逐字，顺序与设计树一致）', () => {
    expect([
      LABEL_COMPANY,
      LABEL_USCC,
      LABEL_INDUSTRY,
      LABEL_REGION,
      LABEL_ADDRESS,
      LABEL_WEBSITE,
      LABEL_CONTACT_NAME,
      LABEL_CONTACT_TITLE,
      LABEL_PHONE,
      LABEL_EMAIL,
      LABEL_INTRO
    ]).toEqual([
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
})

describe('序号 10.1 · 完整度（设计中 72% 出现在胶囊与卡片两处 + 进度条填充 259/358）', () => {
  it('百分比：取整并夹到 0..100', () => {
    expect(completenessPercent(72)).toBe(72)
    expect(completenessPercent(72.6)).toBe(73)
    expect(completenessPercent(0)).toBe(0)
    expect(completenessPercent(100)).toBe(100)
    expect(completenessPercent(120)).toBe(100)
    expect(completenessPercent(-5)).toBe(0)
  })

  it('非数字（含字符串）一律视为无值 —— 不臆造公式', () => {
    expect(completenessPercent(undefined)).toBeUndefined()
    expect(completenessPercent(null)).toBeUndefined()
    expect(completenessPercent('72')).toBeUndefined()
    expect(completenessPercent(Number.NaN)).toBeUndefined()
  })

  it('顶部胶囊文案「完整度 72%」；无值时整块不渲染（返回空串）', () => {
    expect(completenessPillText(72)).toBe('完整度 72%')
    expect(completenessPillText(100)).toBe('完整度 100%')
    expect(completenessPillText(undefined)).toBe('')
  })

  it('进度条填充宽度 = 百分比字符串；无值时为 0%', () => {
    expect(completenessBarWidth(72)).toBe('72%')
    expect(completenessBarWidth(0)).toBe('0%')
    expect(completenessBarWidth(undefined)).toBe('0%')
  })
})

describe('序号 10.1 · 显示值格式化', () => {
  it('地区按设计稿的「 · 」连接（浙江 · 杭州）', () => {
    expect(regionText('浙江', '杭州')).toBe('浙江 · 杭州')
    expect(regionText('浙江', '')).toBe('浙江')
    expect(regionText('', '杭州')).toBe('杭州')
    expect(regionText('', '')).toBe('')
  })

  it('手机号脱敏为设计稿格式「138 **** 6621」（三段式，含空格）', () => {
    expect(maskPhone('13800006621')).toBe('138 **** 6621')
    expect(maskPhone('18612345678')).toBe('186 **** 5678')
  })

  it('手机号非 11 位数字 / 已脱敏值：不猜测，原样或空', () => {
    expect(maskPhone('12345')).toBe('')
    expect(maskPhone('')).toBe('')
    expect(maskPhone(undefined)).toBe('')
    expect(maskPhone('138 **** 6621')).toBe('138 **** 6621')
    expect(maskPhone('138****6621')).toBe('138****6621')
  })

  it('供应商类型码 → 设计稿三项标签；未知码原样返回（不臆造映射）', () => {
    expect(industryLabel('RESELLER')).toBe('渠道商')
    expect(industryLabel('ORIGINAL')).toBe('原厂')
    expect(industryLabel('AGGREGATOR')).toBe('中转商')
    expect(industryLabel('SOMETHING')).toBe('SOMETHING')
    expect(industryLabel('')).toBe('')
  })
})

describe('序号 10.1 · mapProfileView（服务端档案 → 展示模型）', () => {
  it('设计稿示例档案逐字段还原（含地区拼接与手机号脱敏）', () => {
    const view = mapProfileView(PROFILE)
    expect(view).toEqual({
      company: '云智科技有限公司',
      uscc: '91330106MA2XXXXX8B',
      industryCode: 'RESELLER',
      industryLabel: '渠道商',
      region: '浙江 · 杭州',
      address: '西湖区文三路 199 号 A 座 18F',
      website: 'www.yunzhi-tech.com',
      contactName: '李明',
      contactTitle: '商务负责人',
      phone: '138 **** 6621',
      email: 'liming@yunzhi.com',
      intro: '专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。',
      completeness: 72
    })
  })

  it('服务端已给脱敏字段时以服务端为准（不二次脱敏）', () => {
    const view = mapProfileView({ ...PROFILE, contact_phone_mask: '138****8888', contact_phone: '13800006621' })
    expect(view.phone).toBe('138****8888')
  })

  it('缺字段一律渲染占位符（不显示 undefined / null，不编造内容）', () => {
    const view = mapProfileView({})
    expect(view.company).toBe(EMPTY_VALUE)
    expect(view.uscc).toBe(EMPTY_VALUE)
    expect(view.address).toBe(EMPTY_VALUE)
    expect(view.website).toBe(EMPTY_VALUE)
    expect(view.contactName).toBe(EMPTY_VALUE)
    expect(view.email).toBe(EMPTY_VALUE)
    expect(view.intro).toBe(EMPTY_VALUE)
    expect(view.phone).toBe(EMPTY_VALUE)
    expect(view.region).toBe(EMPTY_VALUE)
    expect(view.industryCode).toBe('')
    expect(view.industryLabel).toBe('')
    expect(view.completeness).toBeUndefined()
  })

  it('null / undefined 档案不抛错，等价于空档案', () => {
    expect(mapProfileView(null).company).toBe(EMPTY_VALUE)
    expect(mapProfileView(undefined).uscc).toBe(EMPTY_VALUE)
  })
})

describe('序号 10.1 · 资质三行（设计稿固定三行，逐行文案不同）', () => {
  it('toQualificationItems：兼容数组 / {items} / 非法负载', () => {
    expect(toQualificationItems([{ id: 'q1' }]).length).toBe(1)
    expect(toQualificationItems({ items: [{ id: 'q1' }, { id: 'q2' }] }).length).toBe(2)
    expect(toQualificationItems(null)).toEqual([])
    expect(toQualificationItems({ items: 'x' })).toEqual([])
    expect(toQualificationItems(undefined)).toEqual([])
  })

  it('无资质数据时三行是设计稿的空态文案（未上传 / 条件必传 / 选传 · 可后续补充）', () => {
    const rows = qualificationViewRows([])
    expect(rows.map((r) => r.name)).toEqual(['营业执照', '上游授权书', '增值电信业务许可证'])
    expect(rows.map((r) => r.subtitle)).toEqual(['', '未上传', '选传 · 可后续补充'])
    expect(rows.map((r) => r.badge)).toEqual(['', '条件必传', ''])
    expect(rows.map((r) => r.badgeTone)).toEqual(['', 'warning', ''])
    expect(rows.map((r) => r.chevron)).toEqual([false, false, true])
    expect(rows.map((r) => r.tone)).toEqual(['primary', 'primary', 'muted'])
  })

  it('第 1 行已上传（设计稿样例）→ 「已上传 · 2024-06-10」+ 绿色「已通过」，且不再显空态', () => {
    const rows = qualificationViewRows([
      { id: 'q1', category: 'BUSINESS_LICENSE', file_name: '营业执照-云智科技.jpg', uploaded_at: '2024-06-10T09:30:00Z' }
    ])
    expect(rows[0].subtitle).toBe('已上传 · 2024-06-10')
    expect(rows[0].badge).toBe('已通过')
    expect(rows[0].badgeTone).toBe('success')
    expect(rows[1].subtitle).toBe('未上传')
    expect(rows[2].subtitle).toBe('选传 · 可后续补充')
  })

  it('已上传但无日期 → 只写「已上传」（不编造日期）', () => {
    const rows = qualificationViewRows([{ id: 'q1', category: 'BUSINESS_LICENSE', file_name: 'a.jpg' }])
    expect(rows[0].subtitle).toBe('已上传')
  })

  it('三行分类码与序号 10 编辑页同槽位（BUSINESS_LICENSE / UPSTREAM_AUTHORIZATION / OTHER）', () => {
    const rows = qualificationViewRows([
      { id: 'q1', category: 'UPSTREAM_AUTHORIZATION', file_name: '上游授权书.pdf' },
      { id: 'q2', category: 'OTHER', file_name: '增值电信.pdf' }
    ])
    expect(rows[0].subtitle).toBe('') /* 营业执照无数据 → 设计稿无空态文案 */
    expect(rows[1].subtitle).toBe('已上传')
    expect(rows[2].subtitle).toBe('已上传')
  })

  it('行数恒为 3（设计稿固定三行，服务端多出的分类不硬塞）', () => {
    const rows = qualificationViewRows([
      { id: 'q1', category: 'BUSINESS_LICENSE', file_name: 'a.jpg' },
      { id: 'q2', category: 'UNKNOWN_CATEGORY', file_name: 'b.jpg' }
    ])
    expect(rows.length).toBe(3)
    expect(rows.map((r) => r.subtitle)).toEqual(['已上传', '未上传', '选传 · 可后续补充'])
  })
})
