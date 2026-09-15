/**
 * 序号 15【合同与通知】合同签署 2（page-15-2）— 设计帧样例数据
 *
 * 逐字抄自 `.calicat/raw/pages/page-15-2/design.tree.json`（46 个文本图层），
 * 用作「实现渲染文案 = 设计稿文案」的比对依据，以及 H5 mock 集（.agents/state/h5-measure/api-15）的真源。
 *
 * ⚠️ 设计帧与 PRD 的已知冲突（不静默解决，已记台账序号 15 备注）：
 *   设计帧写「本合同采用电子签章…」「签署方式：短信验证码签署」，
 *   而 10-PRD §4.2 / 17-spec R-41 明确「合同线下（sign_channel OFFLINE）、线上电子签一期不做」。
 */
export const CONTRACT_DESIGN = {
  contract_id: 'c1',
  contract_no: 'CT-2024-0613-008',
  title: 'API 接入服务合同',
  status: 'PENDING_SIGN',
  /** 设计帧原文：请在 2024-06-20 前完成签署，逾期将自动作废 */
  sign_deadline: '2024-06-20',
  supplier_name: '云智科技有限公司',
  cooperation_mode: 'API 转售（非独家）',
  valid_from: '2024-07-01',
  valid_to: '2025-06-30',
  settlement_cycle: '月结 · 次月 15 日',
  fee_rate: '8%',
  currency: 'CNY',
  min_settlement_amount: '¥1,000.00',
  signer_name: '李明（商务负责人）',
  signer_phone_masked: '138 **** 6621',
  sign_method: '短信验证码签署',
  /** 关键条款 4 条（设计帧原文，含序号由实现按 index 生成） */
  terms: [
    '供应商须保证上游接口的合法来源与稳定可用。',
    '平台按实际用量结算，价格以审核通过的报价单为准。',
    '若月度可用率低于 99%，平台有权下调报价或终止合作。',
    '合同期内价格调整需双方确认后生效。'
  ],
  /** 签署记录 2 条（设计帧原文；tone 为服务端字段，缺失时实现按 pending 处理） */
  records: [
    { title: '平台方已盖章', time: '2024-06-13 09:12', tone: 'success' },
    { title: '等待供应商签署', time: '请尽快完成，逾期作废', tone: 'pending' }
  ]
}
