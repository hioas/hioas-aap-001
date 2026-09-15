/**
 * 序号 15【合同与通知】合同签署 2（page-15-2）— 视图模型（TDD 切片 1，先红）
 *
 * 状态机真源：10-PRD §4.2「CREATED→PENDING_SIGN→SUPPLIER_SIGNED→SIGNED→ARCHIVED；可 VOIDED 作废」
 * 设计真源：.calicat/raw/pages/page-15-2/design.tree.json（430 宽 · 7 卡 + 底栏 · 46 文本图层）
 *
 * ⚠️ 设计/PRD 冲突（已记台账序号 15，不静默解决）：
 *   设计帧「电子签章 / 短信验证码签署」 vs 10-PRD §4.2 与 17-spec R-41「合同线下 sign_channel=OFFLINE、线上电子签一期不做」。
 */
import { describe, expect, it } from 'vitest'
import {
  BTN_PDF,
  BTN_SIGN,
  CARD_BASIC,
  CARD_FEE,
  CARD_RECORDS,
  CARD_SIGN,
  CARD_TERMS,
  CONTRACT_ID_KEY,
  LABEL_CURRENCY,
  LABEL_FEE_RATE,
  LABEL_MIN_AMOUNT,
  LABEL_MODE,
  LABEL_PHONE,
  LABEL_SETTLE,
  LABEL_SIGNER,
  LABEL_SIGN_METHOD,
  LABEL_SUPPLIER,
  LABEL_VALID,
  PAGE_TITLE,
  TIP_TEXT,
  TONE_DOT,
  buildContractView,
  deadlineText,
  maskPhone,
  navNoText,
  numberClauses,
  recordTone,
  statusChip,
  validRangeText
} from '@/utils/contract-model'
import { CONTRACT_DESIGN } from '../fixtures/contract-fixture'

const EMPTY = '—'

describe('序号 15 · 设计常量（逐字取自 page-15-2 design.tree.json）', () => {
  it('顶栏与卡片标题、按钮、提示条文案与设计稿一致', () => {
    expect(PAGE_TITLE).toBe('合同签署')
    expect(CARD_BASIC).toBe('合同基本信息')
    expect(CARD_FEE).toBe('费用与分成')
    expect(CARD_TERMS).toBe('关键条款')
    expect(CARD_SIGN).toBe('签署信息')
    expect(CARD_RECORDS).toBe('签署记录')
    expect(BTN_PDF).toBe('PDF')
    expect(BTN_SIGN).toBe('去签署')
    expect(TIP_TEXT).toBe('本合同采用电子签章，签署后即时生效并具备法律效力。')
  })

  it('字段标签 10 个与设计稿一致', () => {
    expect([
      LABEL_SUPPLIER,
      LABEL_MODE,
      LABEL_VALID,
      LABEL_SETTLE,
      LABEL_FEE_RATE,
      LABEL_CURRENCY,
      LABEL_MIN_AMOUNT,
      LABEL_SIGNER,
      LABEL_PHONE,
      LABEL_SIGN_METHOD
    ]).toEqual([
      '供应商',
      '合作模式',
      '生效期',
      '结算账期',
      '平台服务费率',
      '结算币种',
      '最低结算额',
      '签署人',
      '手机号',
      '签署方式'
    ])
  })

  it('页面入参 storage 键沿用同族命名', () => {
    expect(CONTRACT_ID_KEY).toBe('aap_contract_id')
  })
})

describe('序号 15 · 纯函数', () => {
  it('navNoText 保留设计稿的「编号 」前缀（设计是单个文本图层，含前缀）', () => {
    expect(navNoText('CT-2024-0613-008')).toBe('编号 CT-2024-0613-008')
    expect(navNoText('')).toBe('')
  })

  it('deadlineText 按设计稿句式拼日期，无日期不编造', () => {
    expect(deadlineText('2024-06-20')).toBe('请在 2024-06-20 前完成签署，逾期将自动作废')
    expect(deadlineText('')).toBe('')
  })

  it('maskPhone 按设计帧格式脱敏（138 **** 6621）', () => {
    expect(maskPhone('13800006621')).toBe('138 **** 6621')
    expect(maskPhone('138 **** 6621')).toBe('138 **** 6621')
    expect(maskPhone('')).toBe('')
  })

  it('numberClauses 按 index 生成序号，已带序号的原文不重复加号', () => {
    expect(numberClauses(['供应商须保证上游接口的合法来源与稳定可用。'])).toEqual([
      '1. 供应商须保证上游接口的合法来源与稳定可用。'
    ])
    expect(numberClauses(['1. 已带序号'])).toEqual(['1. 已带序号'])
    expect(numberClauses([])).toEqual([])
  })

  it('validRangeText 拼接生效期', () => {
    expect(validRangeText('2024-07-01', '2025-06-30')).toBe('2024-07-01 至 2025-06-30')
    expect(validRangeText('2024-07-01', '')).toBe('2024-07-01')
    expect(validRangeText('', '')).toBe(EMPTY)
  })

  it('recordTone 未知值退 pending（不猜成已完成）', () => {
    expect(recordTone('success')).toBe('success')
    expect(recordTone('pending')).toBe('pending')
    expect(recordTone('void')).toBe('void')
    expect(recordTone('WEIRD')).toBe('pending')
    expect(recordTone(undefined)).toBe('pending')
  })

  it('TONE_DOT 三色取自设计帧（记录点 11x10 r5）', () => {
    expect(TONE_DOT.success).toBe('#16a34a')
    expect(TONE_DOT.pending).toBe('#f59e0b')
    expect(TONE_DOT.void).toBe('#94a3b8')
  })
})

describe('序号 15 · 合同状态胶囊（10-PRD §4.2 状态机 + 设计帧「待签署」配色）', () => {
  it('PENDING_SIGN → 待签署（设计帧 #FFFBEB / #B45309）', () => {
    expect(statusChip('PENDING_SIGN')).toEqual({ label: '待签署', bg: '#fffbeb', text: '#b45309' })
  })

  it('CREATED 同落「待签署」，SUPPLIER_SIGNED 走「待确认」', () => {
    expect(statusChip('CREATED').label).toBe('待签署')
    expect(statusChip('SUPPLIER_SIGNED').label).toBe('待确认')
  })

  it('SIGNED / ARCHIVED / VOIDED 三态', () => {
    expect(statusChip('SIGNED')).toEqual({ label: '已签署', bg: '#ecfdf5', text: '#15803d' })
    expect(statusChip('ARCHIVED')).toEqual({ label: '已归档', bg: '#f1f5f9', text: '#64748b' })
    expect(statusChip('VOIDED')).toEqual({ label: '已作废', bg: '#f1f5f9', text: '#64748b' })
  })

  it('未知状态原样直显（中性灰），不编造中文标签', () => {
    expect(statusChip('WEIRD')).toEqual({ label: 'WEIRD', bg: '#f1f5f9', text: '#64748b' })
    expect(statusChip('')).toEqual({ label: '', bg: '#f1f5f9', text: '#64748b' })
  })
})

describe('序号 15 · buildContractView（设计帧样例 → 视图）', () => {
  it('空数据：文案标签仍在，值一律占位，不照抄设计样例值', () => {
    const view = buildContractView(null)
    expect(view.navNo).toBe('')
    expect(view.title).toBe('')
    expect(view.hasStatus).toBe(false)
    expect(view.deadline).toBe('')
    expect(view.basicRows.map((r) => r.value)).toEqual([EMPTY, EMPTY, EMPTY, EMPTY])
    expect(view.feeRows.map((r) => r.value)).toEqual([EMPTY, EMPTY, EMPTY])
    expect(view.signRows.map((r) => r.value)).toEqual([EMPTY, EMPTY, EMPTY])
    expect(view.clauses).toEqual([])
    expect(view.records).toEqual([])
  })

  it('设计帧样例：四张信息卡的行标签与值逐字一致', () => {
    const view = buildContractView(CONTRACT_DESIGN)
    expect(view.navNo).toBe('编号 CT-2024-0613-008')
    expect(view.title).toBe('API 接入服务合同')
    expect(view.status).toEqual({ label: '待签署', bg: '#fffbeb', text: '#b45309' })
    expect(view.hasStatus).toBe(true)
    expect(view.deadline).toBe('请在 2024-06-20 前完成签署，逾期将自动作废')
    expect(view.basicRows).toEqual([
      { key: 'supplier', label: '供应商', value: '云智科技有限公司' },
      { key: 'mode', label: '合作模式', value: 'API 转售（非独家）' },
      { key: 'valid', label: '生效期', value: '2024-07-01 至 2025-06-30' },
      { key: 'settle', label: '结算账期', value: '月结 · 次月 15 日' }
    ])
    expect(view.feeRows).toEqual([
      { key: 'feeRate', label: '平台服务费率', value: '8%' },
      { key: 'currency', label: '结算币种', value: 'CNY' },
      { key: 'minAmount', label: '最低结算额', value: '¥1,000.00' }
    ])
    expect(view.signRows).toEqual([
      { key: 'signer', label: '签署人', value: '李明（商务负责人）' },
      { key: 'phone', label: '手机号', value: '138 **** 6621' },
      { key: 'method', label: '签署方式', value: '短信验证码签署' }
    ])
    expect(view.clauses).toEqual([
      '1. 供应商须保证上游接口的合法来源与稳定可用。',
      '2. 平台按实际用量结算，价格以审核通过的报价单为准。',
      '3. 若月度可用率低于 99%，平台有权下调报价或终止合作。',
      '4. 合同期内价格调整需双方确认后生效。'
    ])
    expect(view.records).toEqual([
      { key: 'r0', title: '平台方已盖章', time: '2024-06-13 09:12', tone: 'success', dot: '#16a34a' },
      { key: 'r1', title: '等待供应商签署', time: '请尽快完成，逾期作废', tone: 'pending', dot: '#f59e0b' }
    ])
  })

  it('字段名容错：company_name / mode / effective_from+effective_to / platform_fee_rate 等别名同样能读', () => {
    const view = buildContractView({
      contract_no: 'CT-1',
      name: '合同A',
      status: 'SIGNED',
      company_name: '别名科技',
      mode: '独家',
      effective_from: '2024-01-01',
      effective_to: '2024-12-31',
      settlement_terms: '季结',
      platform_fee_rate: '5%',
      settlement_currency: 'USD',
      min_amount: '$200.00',
      signer: '张三',
      signer_phone: '13900001111',
      sign_channel: 'OFFLINE',
      clauses: ['条款一'],
      records: [{ title: '已签署', time: '2024-02-02 10:00' }]
    })
    expect(view.title).toBe('合同A')
    expect(view.status.label).toBe('已签署')
    expect(view.basicRows.map((r) => r.value)).toEqual(['别名科技', '独家', '2024-01-01 至 2024-12-31', '季结'])
    expect(view.feeRows.map((r) => r.value)).toEqual(['5%', 'USD', '$200.00'])
    expect(view.signRows.map((r) => r.value)).toEqual(['张三', '139 **** 1111', 'OFFLINE'])
    expect(view.clauses).toEqual(['1. 条款一'])
    // 记录缺 tone → 退 pending（不猜成 success）
    expect(view.records).toEqual([{ key: 'r0', title: '已签署', time: '2024-02-02 10:00', tone: 'pending', dot: '#f59e0b' }])
  })

  it('脱敏手机号优先用服务端 signer_phone_masked；无号码不留空串占位而是「—」', () => {
    expect(buildContractView({ signer_phone_masked: '138 **** 6621', signer_phone: '13800006621' }).signRows[1].value).toBe(
      '138 **** 6621'
    )
    expect(buildContractView({}).signRows[1].value).toBe(EMPTY)
  })

  it('无 status 字段 → hasStatus false（页面不渲染状态胶囊）', () => {
    expect(buildContractView({ title: 'X' }).hasStatus).toBe(false)
  })
})
