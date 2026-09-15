/**
 * 序号 10【档案与凭证】供应商档案编辑（page-10-2 / 编辑主体档案）— 视图模型与校验单测
 *
 * 文案真源：.calicat/raw/pages/page-10-2/design.tree.json（430 宽 · 设计总高 1409 · 无 TabBar）
 *   以下断言里的中文一律**手抄自设计树**（不引用实现常量，避免自证）。
 * 校验真源：.calicat/prd/17-零歧义执行规格spec.md R-01 手机号 ^1[3-9]\d{9}$
 *   统一社会信用代码 GB 32100-2015 未在 PRD 定义 → 只校验 18 位字母数字（与序号 4-v1 一致，记 missing-prd）
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md aap_provider
 *   （company_name / unified_social_credit_code / industry_category / contact_name / contact_phone / contact_email）
 *   ⚠️ 省市 / 详细地址 / 官网 / 职务 / 公司简介 / 完整度 在 22 份 PRD 与数据字典**零命中** → 前端按
 *   province/city/address/website/contact_title/company_intro/completeness 消费，字段名为推断（记 missing-prd）。
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD + 画布页码 + 设计稿控件语义。
 */
import { describe, expect, it } from 'vitest'
import {
  BADGE_CONDITIONAL,
  BADGE_REQUIRED,
  BADGE_UPLOADED,
  BTN_DRAFT,
  BTN_SAVE,
  FILES_TIP,
  INDUSTRY_OPTIONS,
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
  MAX_INTRO,
  PAGE_TITLE,
  PLACEHOLDER_WEBSITE,
  QUALIFICATION_ROWS,
  SECTION_CONTACT,
  SECTION_FILES,
  SECTION_BASIC,
  UPLOAD_HINT_SINGLE,
  bioCounter,
  buildProfilePayload,
  buildQualificationRows,
  completenessText,
  emptyProfileForm,
  industryLabel,
  mapProfileToForm,
  uploadPayload,
  validateProfileForm,
  type ProfileForm
} from '@/utils/profile-edit-model'

/** 设计稿示例值（逐字抄自 design.tree.json） */
const DESIGN_PROFILE = {
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

function filledForm(): ProfileForm {
  return mapProfileToForm(DESIGN_PROFILE)
}

describe('序号 10 · 文案常量与设计稿逐字一致', () => {
  it('页面标题 / 三张卡标题 / 按钮', () => {
    expect(PAGE_TITLE).toBe('编辑主体档案')
    expect([SECTION_BASIC, SECTION_CONTACT, SECTION_FILES]).toEqual(['主体信息', '联系信息', '资质文件'])
    expect(BTN_DRAFT).toBe('保存草稿')
    expect(BTN_SAVE).toBe('保存')
  })

  it('字段标签逐字一致（含设计稿里 * 前的空格）', () => {
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
  })

  it('官网占位文案与资质卡右上说明逐字一致', () => {
    expect(PLACEHOLDER_WEBSITE).toBe('请输入企业官网地址')
    expect(FILES_TIP).toBe('支持 JPG/PNG/PDF，≤10MB')
  })

  it('供应商类型三项与顺序逐字一致', () => {
    expect(INDUSTRY_OPTIONS.map((o) => o.label)).toEqual(['原厂', '渠道商', '中转商'])
  })

  it('资质三行（名称/角标/说明）逐字一致，顺序与设计稿相同', () => {
    expect(QUALIFICATION_ROWS.map((r) => r.name)).toEqual(['营业执照', '上游授权书', '其他选传资质'])
    expect(QUALIFICATION_ROWS[0].badge).toBe(BADGE_REQUIRED)
    expect(BADGE_REQUIRED).toBe('必传')
    expect(QUALIFICATION_ROWS[1].badge).toBe(BADGE_CONDITIONAL)
    expect(BADGE_CONDITIONAL).toBe('条件必传')
    expect(BADGE_UPLOADED).toBe('已上传')
    expect(QUALIFICATION_ROWS[1].hint).toBe(UPLOAD_HINT_SINGLE)
    expect(UPLOAD_HINT_SINGLE).toBe('点击上传，仅支持单个文件')
    expect(QUALIFICATION_ROWS[2].desc).toBe('增值电信业务许可证、等保备案等')
  })

  it('简介上限 = 设计稿计数的分母 200', () => {
    expect(MAX_INTRO).toBe(200)
  })
})

describe('序号 10 · 服务端档案 → 表单视图模型', () => {
  it('aap_provider 字段映射到表单（逐字段）', () => {
    const form = mapProfileToForm(DESIGN_PROFILE)
    expect(form.companyName).toBe('云智科技有限公司')
    expect(form.uscc).toBe('91330106MA2XXXXX8B')
    expect(form.industry).toBe('RESELLER')
    expect(form.province).toBe('浙江省')
    expect(form.city).toBe('杭州市')
    expect(form.address).toBe('西湖区文三路 199 号 A 座 18F')
    expect(form.contactName).toBe('李明')
    expect(form.contactTitle).toBe('商务负责人')
    expect(form.phone).toBe('13800006621')
    expect(form.email).toBe('liming@yunzhi.com')
    expect(form.intro).toBe('专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。')
  })

  it('空响应 / undefined → 全空表单，不产生 undefined（表单不显示 undefined）', () => {
    for (const input of [undefined, null, {}]) {
      const form = mapProfileToForm(input as never)
      expect(Object.values(form).every((v) => v === '')).toBe(true)
      expect(form).toEqual(emptyProfileForm())
    }
  })

  it('未知 industry_category 原样保留（不臆造映射），无值时为空串', () => {
    expect(mapProfileToForm({ industry_category: 'UNKNOWN_X' }).industry).toBe('UNKNOWN_X')
    expect(mapProfileToForm({}).industry).toBe('')
  })

  it('industryLabel：三项枚举可回显中文，其它值原样返回，空值返回空串', () => {
    expect(industryLabel('ORIGINAL')).toBe('原厂')
    expect(industryLabel('RESELLER')).toBe('渠道商')
    expect(industryLabel('AGGREGATOR')).toBe('中转商')
    expect(industryLabel('UNKNOWN_X')).toBe('UNKNOWN_X')
    expect(industryLabel('')).toBe('')
  })

  it('完整度标签：数字 → 「72%」，缺值 → 空串（PRD 无定义，不臆造公式）', () => {
    expect(completenessText(72)).toBe('72%')
    expect(completenessText(72.4)).toBe('72%')
    expect(completenessText(undefined)).toBe('')
    expect(completenessText(null)).toBe('')
    expect(completenessText('')).toBe('')
  })

  it('简介计数：按真实字数（设计稿 48/200 与 40 字示例不自洽 → 以真实长度为准）', () => {
    expect(bioCounter('专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。')).toBe('40/200')
    expect(bioCounter('')).toBe('0/200')
  })
})

describe('序号 10 · 表单 → 提交体', () => {
  it('按数据字典字段名组装（snake_case），并 trim', () => {
    const form = { ...filledForm(), companyName: ' 云智科技有限公司 ', intro: ' 简介 ' }
    expect(buildProfilePayload(form)).toEqual({
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
      company_intro: '简介'
    })
  })

  it('提交体不携带完整度（只读展示字段，服务端派生）', () => {
    expect(Object.keys(buildProfilePayload(filledForm()))).not.toContain('completeness')
  })
})

describe('序号 10 · 保存前校验（R-01 手机号 / 18 位统一社会信用代码）', () => {
  it('合法表单 → 通过', () => {
    expect(validateProfileForm(filledForm())).toBeUndefined()
  })

  it('空表单一 → 提示企业名称', () => {
    expect(validateProfileForm(emptyProfileForm())).toBe('请输入企业名称')
  })

  it('统一社会信用代码：非 18 位 / 含非字母数字 → 拦截', () => {
    expect(validateProfileForm({ ...filledForm(), uscc: '91330106MA2XXXXX8' })).toBe('请输入 18 位统一社会信用代码')
    expect(validateProfileForm({ ...filledForm(), uscc: '91330106MA2XXXXX8-' })).toBe('请输入 18 位统一社会信用代码')
    expect(validateProfileForm({ ...filledForm(), uscc: '91330106ma2xxxxx8b' })).toBeUndefined()
  })

  it('供应商类型必须选择', () => {
    expect(validateProfileForm({ ...filledForm(), industry: '' })).toBe('请选择供应商类型')
  })

  it('所在地区必须选择（省市都选）', () => {
    expect(validateProfileForm({ ...filledForm(), province: '' })).toBe('请选择所在地区')
    expect(validateProfileForm({ ...filledForm(), city: '' })).toBe('请选择所在地区')
  })

  it('详细地址 / 联系人必填', () => {
    expect(validateProfileForm({ ...filledForm(), address: '  ' })).toBe('请输入详细地址')
    expect(validateProfileForm({ ...filledForm(), contactName: '' })).toBe('请输入联系人')
  })

  it('手机号按 R-01 ^1[3-9]\\d{9}$ 校验', () => {
    expect(validateProfileForm({ ...filledForm(), phone: '' })).toBe('请输入手机号')
    expect(validateProfileForm({ ...filledForm(), phone: '23800006621' })).toBe('请输入正确的手机号')
    expect(validateProfileForm({ ...filledForm(), phone: '1380000662' })).toBe('请输入正确的手机号')
    expect(validateProfileForm({ ...filledForm(), phone: '13800006621' })).toBeUndefined()
  })

  it('邮箱选填：留空放行，填了就校验格式', () => {
    expect(validateProfileForm({ ...filledForm(), email: '' })).toBeUndefined()
    expect(validateProfileForm({ ...filledForm(), email: 'liming@yunzhi' })).toBe('请输入正确的邮箱')
    expect(validateProfileForm({ ...filledForm(), email: 'liming@yunzhi.com' })).toBeUndefined()
  })

  it('官网选填：留空放行；填了必须是 http/https 地址', () => {
    expect(validateProfileForm({ ...filledForm(), website: '' })).toBeUndefined()
    expect(validateProfileForm({ ...filledForm(), website: 'yunzhi.com' })).toBe('请输入正确的官网地址，需以 http:// 或 https:// 开头')
    expect(validateProfileForm({ ...filledForm(), website: 'https://www.yunzhi.com' })).toBeUndefined()
  })

  it('公司简介不超过 200 字', () => {
    expect(validateProfileForm({ ...filledForm(), intro: 'a'.repeat(200) })).toBeUndefined()
    expect(validateProfileForm({ ...filledForm(), intro: 'a'.repeat(201) })).toBe('公司简介不超过 200 字')
  })
})

describe('序号 10 · 资质行视图模型', () => {
  it('无服务端数据 → 三行均为空态（保留设计稿角标与说明）', () => {
    const rows = buildQualificationRows([])
    expect(rows.map((r) => r.name)).toEqual(['营业执照', '上游授权书', '其他选传资质'])
    expect(rows.every((r) => r.file === undefined)).toBe(true)
    expect(rows[0].badge).toBe('必传')
  })

  it('按 category 匹配：营业执照已上传 → 带上文件名与删除所需 id', () => {
    const rows = buildQualificationRows([
      { id: 'q1', category: 'BUSINESS_LICENSE', file_name: '营业执照-云智科技.jpg' }
    ])
    expect(rows[0].file).toEqual({ id: 'q1', fileName: '营业执照-云智科技.jpg' })
    expect(rows[1].file).toBeUndefined()
    expect(rows[2].file).toBeUndefined()
  })

  it('category 缺失时按 code / type 兜底匹配；完全不匹配的文件不硬塞进设计稿的行', () => {
    const byCode = buildQualificationRows([{ id: 'q2', code: 'UPSTREAM_AUTHORIZATION', file_name: '上游授权书.pdf' }])
    expect(byCode[1].file?.fileName).toBe('上游授权书.pdf')

    const unknown = buildQualificationRows([{ id: 'q3', file_name: '未知资质.png' }])
    expect(unknown.every((r) => r.file === undefined)).toBe(true)
  })

  it('上传提交体：只登记 category + 文件名 + 字节数（18-API 无文件上传接口）', () => {
    const rows = buildQualificationRows([])
    expect(uploadPayload(rows[2], { name: '许可.pdf', size: 2048 })).toEqual({
      category: 'OTHER',
      file_name: '许可.pdf',
      file_size: 2048
    })
  })

  it('空列表 / undefined 不抛错', () => {
    expect(buildQualificationRows(undefined).length).toBe(3)
  })
})
