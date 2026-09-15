/**
 * 序号 7【检测验真】检测未通过报告 2（page-7-2）测试夹具
 *
 * 真源：.calicat/raw/pages/page-7-2/design.tree.json（430 宽，逐字抄录）
 *   · 封面卡 07b82bea：报告编号 DR-20240614-0312 · 华南备线路 · 备用通道 · 综合分 54 · 「未通过」
 *   · 一票否决条 c93a930a：命中一票否决项：D2 鉴权在检测期间返回 401，模型清单存在 1 项无法调用。
 *   · 结论措辞 d5ad8ecf：请核对 APIKey 有效期与模型开放范围后重新提交检测；已通过项无需重复准备。
 *   · 分项评分总览卡 35a1df87：D1 连通性 89 / D2 鉴权 12 / D3 模型一致性 55 / D4 上下文 82 /
 *     D5 稳定性 61 / D6 计费口径 66 / D7 合规安全 58 / D8 并发压测 0
 *   · D2详情卡 09ddc4ca：D2 鉴权有效性 · 详情 / 12 分 / 四行「现象·依据·影响·建议」
 *   · 免责声明卡 1b0391c3：本报告基于抽样检测生成 / 未通过结论仅代表检测时点状态，修正后重新检测即可更新结论。
 *
 * ⚠️ 页面文案一律取自设计稿；此夹具只用于单测与 H5 取数，不代表服务端字段级 schema（18-API 未定义 → missing-prd）。
 */
export const DESIGN_REPORT_FAILED = {
  report_no: 'DR-20240614-0312',
  channel_name: '华南备线路 · 备用通道',
  total_score: 54,
  result: 'FAIL',
  veto_triggered: true,
  veto_note: '命中一票否决项：D2 鉴权在检测期间返回 401，模型清单存在 1 项无法调用。',
  verdict: '请核对 APIKey 有效期与模型开放范围后重新提交检测；已通过项无需重复准备。',
  credential_id: 'c1',
  dims: [
    { code: 'D1', name: '连通性', score: 89 },
    { code: 'D2', name: '鉴权', score: 12 },
    { code: 'D3', name: '模型一致性', score: 55 },
    { code: 'D4', name: '上下文', score: 82 },
    { code: 'D5', name: '稳定性', score: 61 },
    { code: 'D6', name: '计费口径', score: 66 },
    { code: 'D7', name: '合规安全', score: 58 },
    { code: 'D8', name: '并发压测', score: 0 }
  ],
  detail: {
    code: 'D2',
    title: 'D2 鉴权有效性 · 详情',
    score: 12,
    lines: [
      '· 现象：第 3 次探测返回 401 Unauthorized。',
      '· 依据：APIKey 与 BaseURL 不匹配，或密钥已轮换失效。',
      '· 影响：无法建立稳定转发链路，暂不可承接业务。',
      '· 建议：更新 APIKey 后重新提交检测。'
    ]
  },
  disclaimer: '未通过结论仅代表检测时点状态，修正后重新检测即可更新结论。'
}

/** 重新提交检测成功后的服务端返回（18-API Detection Tag /detection-jobs） */
export const DESIGN_RESUBMIT_RESULT = { job_id: 'j9', job_no: 'DJ-20260916-0009' }
