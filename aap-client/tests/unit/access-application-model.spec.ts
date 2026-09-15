/**
 * 序号 4-v1「接入凭证-表单」（page-24，准入表单变体）— 视图模型与校验单测
 *
 * 文案真源：.calicat/raw/pages/page-24/design.tree.json（430 宽）
 * 字段真源：.calicat/prd/15-数据模型ER与数据字典.md §aap_provider
 *   （provider_no / company_name / unified_social_credit_code（唯一）/ industry_category /
 *     contact_name / contact_phone_cipher·contact_phone_mask / status / …）
 *            .calicat/prd/17-零歧义执行规格spec.md §3 Provider(… qualification_files …)
 * 规则真源：17-spec §5 R-01 手机号 ^1[3-9]\d{9}$（复用 src/utils/validators.isPhone）
 *
 * ⚠️ missing-prd（不臆造，已在台账与状态文件登记）：
 *   1) 「基础检测 / 深度检测 / 合规检测」三值在 22 份 PRD 中 **零命中**，18-API 亦无入参
 *      → 只作 UI 选中态（client-only）保留，**不拼进提交体**（本文件有专门用例把这条钉死）。
 *   2) 「备注」在 15-数据字典 aap_provider 中无对应字段 → 同样只作 UI 态，不进提交体。
 *   3) 文件类型/尺寸（jpg/png/pdf、≤10MB）取自设计文案；18-API 无上传接口。
 *   4) 统一社会信用代码字符集（GB 32100-2015）PRD 未定义 → 只校验「18 位字母数字」。
 */
import { describe, expect, it } from 'vitest'
import {
  ACCEPT_EXTENSIONS,
  DEFAULT_DETECTION_TYPE,
  DETECTION_TYPES,
  ERR_COMPANY_REQUIRED,
  ERR_FILE_SIZE,
  ERR_FILE_TYPE,
  ERR_PHONE,
  ERR_USCC_FORMAT,
  ERR_USCC_REQUIRED,
  LABEL_COMPANY,
  LABEL_CONTACT,
  LABEL_PHONE,
  LABEL_USCC,
  MAX_FILE_BYTES,
  PAGE_SUBTITLE,
  PAGE_TITLE,
  PLACEHOLDER_COMPANY,
  PLACEHOLDER_CONTACT,
  PLACEHOLDER_PHONE,
  PLACEHOLDER_REMARK,
  PLACEHOLDER_USCC,
  SECTION_BASIC,
  SECTION_DETECTION,
  SECTION_FILES,
  SECTION_REMARK,
  SUBMIT_FOOTNOTE,
  SUBMIT_LABEL,
  UPLOAD_LIMIT,
  UPLOAD_MAIN,
  UPLOAD_TIP,
  addFile,
  buildAccessApplicationPayload,
  emptyAccessApplicationForm,
  fileExtension,
  formatFileSize,
  isAcceptedFile,
  isUscc,
  normalizeUscc,
  removeFileAt,
  toggleDetectionType,
  validateAccessApplication,
  validateFile
} from '@/utils/access-application-model'

const MB = 1024 * 1024

describe('文案常量 === 设计稿原文（不得改写）', () => {
  it('顶部栏：标题与副标题', () => {
    expect(PAGE_TITLE).toBe('接入凭证')
    expect(PAGE_SUBTITLE).toBe('填写客户信息并提交检测')
  })

  it('四个区块标题', () => {
    expect(SECTION_BASIC).toBe('基本信息')
    expect(SECTION_DETECTION).toBe('检测类型')
    expect(SECTION_FILES).toBe('凭证资料')
    expect(SECTION_REMARK).toBe('备注')
  })

  it('四个字段标签', () => {
    expect(LABEL_COMPANY).toBe('客户名称')
    expect(LABEL_USCC).toBe('统一社会信用代码')
    expect(LABEL_CONTACT).toBe('联系人')
    expect(LABEL_PHONE).toBe('联系电话')
  })

  it('占位提示：信用代码/联系人/联系电话/备注 为设计原文', () => {
    expect(PLACEHOLDER_USCC).toBe('请输入 18 位统一社会信用代码')
    expect(PLACEHOLDER_CONTACT).toBe('请输入联系人姓名')
    expect(PLACEHOLDER_PHONE).toBe('请输入手机号')
    expect(PLACEHOLDER_REMARK).toBe('补充说明，例如客户所属行业、检测用途等')
  })

  it('客户名称占位为推断（设计稿该框是已填值「深圳市恒信科技有限公司」，无占位文案）', () => {
    expect(PLACEHOLDER_COMPANY).toBe('请输入客户名称')
  })

  it('上传区与提交区文案 === 设计原文', () => {
    expect(UPLOAD_TIP).toBe('支持 jpg / png / pdf')
    expect(UPLOAD_MAIN).toBe('点击上传凭证文件')
    expect(UPLOAD_LIMIT).toBe('单个文件不超过 10MB')
    expect(SUBMIT_LABEL).toBe('提交接入')
    expect(SUBMIT_FOOTNOTE).toBe('提交后系统将自动发起检测，预计 5 分钟内完成')
  })
})

describe('检测类型（UI 选中态；枚举无 PRD 依据 → 不进提交体）', () => {
  it('三项与顺序 === 设计稿原文', () => {
    expect(DETECTION_TYPES).toEqual(['基础检测', '深度检测', '合规检测'])
  })

  it('默认选中 = 设计稿选中态「基础检测」', () => {
    expect(DEFAULT_DETECTION_TYPE).toBe('基础检测')
    expect(DETECTION_TYPES).toContain(DEFAULT_DETECTION_TYPE)
  })

  it('toggleDetectionType 单选：切换到合法项生效', () => {
    expect(toggleDetectionType('基础检测', '深度检测')).toBe('深度检测')
    expect(toggleDetectionType('深度检测', '合规检测')).toBe('合规检测')
  })

  it('toggleDetectionType 拒绝枚举外的值（不臆造新类型）', () => {
    expect(toggleDetectionType('基础检测', '超级检测')).toBe('基础检测')
    expect(toggleDetectionType('基础检测', '')).toBe('基础检测')
  })
})

describe('文件校验（设计：支持 jpg / png / pdf；单个文件不超过 10MB）', () => {
  it('扩展名白名单含 jpg/jpeg/png/pdf', () => {
    expect(ACCEPT_EXTENSIONS).toEqual(['jpg', 'jpeg', 'png', 'pdf'])
    expect(MAX_FILE_BYTES).toBe(10 * 1024 * 1024)
  })

  it('fileExtension 取末段扩展名并小写（无扩展名返回空串）', () => {
    expect(fileExtension('营业执照扫描件.PDF')).toBe('pdf')
    expect(fileExtension('a.b.c.png')).toBe('png')
    expect(fileExtension('noext')).toBe('')
  })

  it('isAcceptedFile 大小写不敏感', () => {
    expect(isAcceptedFile('x.JPG')).toBe(true)
    expect(isAcceptedFile('x.pdf')).toBe(true)
    expect(isAcceptedFile('x.txt')).toBe(false)
    expect(isAcceptedFile('x.exe')).toBe(false)
  })

  it('非法格式 → ERR_FILE_TYPE', () => {
    expect(validateFile({ name: '合同.txt', size: 1024 })).toBe(ERR_FILE_TYPE)
  })

  it('超过 10MB → ERR_FILE_SIZE；恰好 10MB 允许（边界）', () => {
    expect(validateFile({ name: 'big.pdf', size: 10 * MB + 1 })).toBe(ERR_FILE_SIZE)
    expect(validateFile({ name: 'ok.pdf', size: 10 * MB })).toBeNull()
  })

  it('合法文件 → null', () => {
    expect(validateFile({ name: '营业执照扫描件.pdf', size: 2516582 })).toBeNull()
  })

  it('formatFileSize：2.4 MB / KB / B 三档', () => {
    expect(formatFileSize(2516582)).toBe('2.4 MB')
    expect(formatFileSize(2 * MB)).toBe('2.0 MB')
    expect(formatFileSize(1536)).toBe('2 KB')
    expect(formatFileSize(512)).toBe('512 B')
  })

  it('addFile：合法则追加；非法则返回错误且列表不变', () => {
    const empty = emptyAccessApplicationForm()
    const ok = addFile(empty.files, { name: '营业执照扫描件.pdf', size: 2516582 })
    expect(ok.error).toBeNull()
    expect(ok.files.map((f) => f.name)).toEqual(['营业执照扫描件.pdf'])

    const bad = addFile(ok.files, { name: 'virus.exe', size: 10 })
    expect(bad.error).toBe(ERR_FILE_TYPE)
    expect(bad.files).toHaveLength(1)
  })

  it('removeFileAt：按下标删除，不存在的下标不报错', () => {
    const files = [
      { name: 'a.pdf', size: 1 },
      { name: 'b.png', size: 2 }
    ]
    expect(removeFileAt(files, 0).map((f) => f.name)).toEqual(['b.png'])
    expect(removeFileAt(files, 9).map((f) => f.name)).toEqual(['a.pdf', 'b.png'])
  })
})

describe('统一社会信用代码校验（设计占位「18 位」；PRD 未定义字符集）', () => {
  it('normalizeUscc 去空白并转大写', () => {
    expect(normalizeUscc(' 91440300ma5dajqh6x ')).toBe('91440300MA5DAJQH6X')
  })

  it('18 位字母数字通过；17/19 位或含符号不通过', () => {
    expect(isUscc('91440300MA5DAJQH6X')).toBe(true)
    expect(isUscc('91440300MA5DAJQH6')).toBe(false)
    expect(isUscc('91440300MA5DAJQH6XX')).toBe(false)
    expect(isUscc('91440300MA5DAJQH6-')).toBe(false)
  })
})

describe('表单校验（必填只看设计稿星号：客户名称 / 统一社会信用代码）', () => {
  const valid = () => ({
    ...emptyAccessApplicationForm(),
    companyName: '深圳市恒信科技有限公司',
    uscc: '91440300MA5DAJQH6X'
  })

  it('客户名称为空 → ERR_COMPANY_REQUIRED', () => {
    expect(validateAccessApplication({ ...valid(), companyName: '  ' })).toBe(ERR_COMPANY_REQUIRED)
  })

  it('信用代码为空 → ERR_USCC_REQUIRED', () => {
    expect(validateAccessApplication({ ...valid(), uscc: '' })).toBe(ERR_USCC_REQUIRED)
  })

  it('信用代码长度/字符非法 → ERR_USCC_FORMAT', () => {
    expect(validateAccessApplication({ ...valid(), uscc: '91440300MA5DAJQH6' })).toBe(ERR_USCC_FORMAT)
  })

  it('联系电话为选填（设计稿无星号）：留空放行', () => {
    expect(validateAccessApplication({ ...valid(), contactPhone: '' })).toBeNull()
  })

  it('联系电话填了但非法 → ERR_PHONE', () => {
    expect(validateAccessApplication({ ...valid(), contactPhone: '12345' })).toBe(ERR_PHONE)
  })

  it('完整合法 → null（含合法手机号）', () => {
    expect(
      validateAccessApplication({
        ...valid(),
        contactName: '张伟',
        contactPhone: '13800138000',
        remark: '补充说明'
      })
    ).toBeNull()
  })
})

describe('提交体：只含有据字段（防臆造）', () => {
  it('字段名取 15-数据字典 aap_provider', () => {
    const payload = buildAccessApplicationPayload({
      ...emptyAccessApplicationForm(),
      companyName: ' 深圳市恒信科技有限公司 ',
      uscc: ' 91440300ma5dajqh6x ',
      contactName: '张伟',
      contactPhone: '13800138000',
      files: [{ name: '营业执照扫描件.pdf', size: 2516582 }]
    })
    expect(payload).toEqual({
      company_name: '深圳市恒信科技有限公司',
      unified_social_credit_code: '91440300MA5DAJQH6X',
      contact_name: '张伟',
      contact_phone: '13800138000',
      qualification_files: [{ file_name: '营业执照扫描件.pdf', file_size: 2516582 }]
    })
  })

  it('未填的选填项被省略，而不是发空串', () => {
    const payload = buildAccessApplicationPayload({
      ...emptyAccessApplicationForm(),
      companyName: '深圳市恒信科技有限公司',
      uscc: '91440300MA5DAJQH6X'
    })
    expect(Object.keys(payload).sort()).toEqual(['company_name', 'unified_social_credit_code'])
  })

  it('不臆造检测类型字段（枚举无 PRD 依据 → 前端不发明字段名）', () => {
    const payload = buildAccessApplicationPayload({
      ...emptyAccessApplicationForm(),
      companyName: '深圳市恒信科技有限公司',
      uscc: '91440300MA5DAJQH6X',
      detectionType: '深度检测'
    })
    expect(payload).not.toHaveProperty('detection_type')
    expect(payload).not.toHaveProperty('detectionType')
    expect(JSON.stringify(payload)).not.toContain('深度检测')
  })

  it('不臆造备注字段（15-数据字典 aap_provider 无对应列）', () => {
    const payload = buildAccessApplicationPayload({
      ...emptyAccessApplicationForm(),
      companyName: '深圳市恒信科技有限公司',
      uscc: '91440300MA5DAJQH6X',
      remark: '检测用途：模型验真'
    })
    expect(payload).not.toHaveProperty('remark')
    expect(JSON.stringify(payload)).not.toContain('模型验真')
  })
})
