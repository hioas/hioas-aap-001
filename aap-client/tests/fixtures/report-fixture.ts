/**
 * 序号 6【检测验真】大模型检测报告 · 多维度专业版（page-6）测试夹具
 *
 * ⚠️ 本文件是**从设计稿逐字抄录的示例态数据**，作为「文案一致性」的客观依据：
 *   设计真源：.calicat/raw/pages/page-6/design.tree.json（430 宽）
 *   顶部 b362b5a2 · 结论封面卡 4e855266 · 关键指标卡 c13761bd · 维度总览卡 7530b31a
 *   明细卡 7806d174（分组 A 92166f19 / B a77ed01e / C 6a70da17 / D 25882465 / E 4f599bdc / F 379f61e0 / G 72e4291c）
 *   风险发现卡 658a45d1 · 原始证据卡 9844215a · 免责声明卡 30918987 · 底部操作条 e096bd63
 * 字段名取自 15-数据模型ER与数据字典 aap_report / aap_report_section（18-API 只列路径，无字段级 schema → missing-prd）。
 */

const item = (code: string, name: string, metric: string, score: number | null, extra: Record<string, unknown> = {}) => ({
  code,
  name,
  metric,
  score,
  ...extra
})

export const DESIGN_REPORT = {
  report_no: 'DR-20240613-0758',
  channel_name: '华东主线路 · GPT 通道',
  total_score: 92,
  result: 'PASS',
  confidence: 'HIGH',
  pass_count: 7,
  item_total: 8,
  unmeasurable_count: 1,
  veto_triggered: false,
  verdict: '未发现与宣称模型不一致的迹象（置信度：较高）。接口连通稳定、鉴权有效、模型指纹吻合，可进入报价流程。',
  provider_name: '星辰云科技',
  provider_code: 'P-2041',
  api_key_masked: 'sk-••••••••••••••••4f2a',
  model_list: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
  detected_at: '2026-07-10 15:32',
  trigger_type: '提交凭证自动',
  duration_text: '12 分 46 秒',
  cost_estimate_usd: 1.86,
  cost_actual_usd: 1.72,
  key_metrics: [
    { key: 'FINGERPRINT', label: '模型指纹相似度', value: '0.93', unit: '余弦', sub: '高于告警线 0.70', tone: 'success' },
    { key: 'TTFT', label: 'TTFT 首 token（P50）', value: '268', unit: 'ms', sub: 'P90 620 ms' },
    { key: 'RPM', label: 'RPM 实测 / 申报', value: '52', unit: '/ 60', sub: '达成 87%' },
    { key: 'TPM', label: 'TPM 实测', value: '1.24', unit: 'M/min', sub: '窗口内主动降速' },
    { key: 'CACHE', label: 'Prompt 缓存', value: '命中', unit: '78%', sub: 'cached_tokens 字段可用' },
    { key: 'AVAILABILITY', label: '服务可用性', value: '99.9', unit: '%', sub: '30 分钟观测窗口' }
  ],
  sections: [
    {
      code: 'A',
      name: '时延与性能',
      avg: 86,
      scored: true,
      items: [
        item('A1', 'TTFT 首 token 延迟', 'P50 268 ms', 92),
        item('A2', 'TTFT 尾延迟', 'P90 620 ms', 88),
        item('A3', 'TTFT 抖动', '标准差 ±74 ms', 86),
        item('A4', '端到端延迟', 'P50 3.1 s（500 / 256）', 90),
        item('A5', '输出吞吐 TPS', '62 tok/s', 87),
        item('A6', '首字节时间 TTFB', '210 ms', 91),
        item('A7', '长上下文时延', '128K 输入 9.4 s', 78),
        item('A8', '高并发时延', 'P95 @30 并发 8.9 s', 74),
        item('A9', '时延稳定性', '变异系数 CV 0.11', 85)
      ]
    },
    {
      code: 'B',
      name: '吞吐与限速',
      avg: 84,
      scored: true,
      items: [
        item('B1', 'RPM 实测', '52 / 申报 60', 87),
        item('B2', 'TPM 实测', '1.24 M / min', 90),
        item('B3', '并发上限', '实测 48 并发', 82),
        item('B4', '429 触发阈值', '57 req/s', 85),
        item('B5', '限速恢复时间', '1.8 s', 84),
        item('B6', '突发容忍', '1.4× 基线', 80),
        item('B7', '队列等待', 'P50 320 ms', 83),
        item('B8', '每日配额', '上游未返回配额字段', null, { status: 'NOT_DECLARED' })
      ]
    },
    {
      code: 'C',
      name: '一致性与可靠性',
      avg: 92,
      scored: true,
      items: [
        item('C1', '确定性一致性', 'temp=0，8/8 完全一致', 96),
        item('C2', '响应文本相似度', '0.998', 95),
        item('C3', '服务错误率', '5xx 0.12%', 93),
        item('C4', '请求超时率', '0.30%', 90),
        item('C5', '自动重试成功率', '99.6%', 91),
        item('C6', '流式截断率', '0.40%', 88),
        item('C7', '服务可用性', '30 分钟窗口 99.9%', 94),
        item('C8', '长连接稳定性', '零中断 / 零重连', 92)
      ]
    },
    {
      code: 'D',
      name: '模型指纹（核心项）',
      avg: 90,
      scored: true,
      items: [
        item('D1', '行为指纹相似度', '题库回归 0.93 · 权重 0.35', 93),
        item('D2', 'Tokenizer 指纹', '偏离 +0.8% · 权重 0.25', 95),
        item('D3', '自我认知一致性', '身份/开发商吻合 · 0.15', 90),
        item('D4', '概率指纹', 'logprobs KL 0.14 · 0.15', 86),
        item('D5', '上下文能力边界', '实测 128K 吻合 · 0.10', 92),
        item('D6', '知识截止一致性', '2023-10 吻合', 82),
        item('D7', '多语言能力画像', '多语文本集偏移 +1.2%', 88),
        item('D8', '指令遵循一致性', '0.96', 91)
      ]
    },
    {
      code: 'E',
      name: '计量与缓存计费',
      avg: 94,
      scored: true,
      items: [
        item('E1', 'Prompt 缓存命中', '已观测命中', 100),
        item('E2', '缓存写入识别', '5m / 1h TTL 字段可读', 96),
        item('E3', '缓存命中率', '连续两次同 prompt 78%', 90),
        item('E4', 'usage 字段一致性', '与协议标准完全一致', 98),
        item('E5', '流式用量计数', '偏差 ±0.2%', 95),
        item('E6', '输入 / 输出单价', '与申报一致 · 无 ratio 转换', 94),
        item('E7', '倍率 / 计费口径', '样例向量模拟求值通过', 92),
        item('E8', '预扣与结算一致性', '预扣 / 实扣无偏差', 90)
      ]
    },
    {
      code: 'F',
      name: '安全与合规',
      avg: 92,
      scored: true,
      items: [
        item('F1', 'TLS 证书有效性', 'SAN 与端点一致 · 有效期 82 天', 95),
        item('F2', '证书签发机构', '仅作证据，不计入总分', null, { status: 'EVIDENCE_ONLY' }),
        item('F3', '出站 SSRF 防护', '内网 / 环回 / 元数据地址被拒', 96),
        item('F4', '端点归属校验', 'challenge 签名通过', 92),
        item('F5', '响应头指纹', 'server / x-request-id 与基线一致', 89),
        item('F6', '错误格式指纹', 'OpenAI 标准 error 结构', 90),
        item('F7', '数据留存声明', '上游未返回留存字段', null, { status: 'NOT_MEASURABLE' }),
        item('F8', '内容安全策略', '抽样 200 条 · 0 命中', 91)
      ]
    },
    {
      code: 'G',
      name: '真实源证据（不计分）',
      avg: null,
      scored: false,
      items: [
        item('G1', '出口 IP / ASN', '网络归属', null, { value: '20.42.xx.xx · AS8075 Azure' }),
        item('G2', 'TLS Subject / SAN', '证书主体', null, { value: 'CN=*.openai.com' }),
        item('G3', '/v1/models 清单', '能力清单一致性', null, { value: '3 个模型与申报一致' }),
        item('G4', '时间 / 语言特征', '响应本地化特征', null, { value: 'UTC · en-US' }),
        item('G5', 'x-request-id 前缀', '请求追踪格式', null, { value: 'req_（OpenAI 格式）' }),
        item('G6', '边缘节点标识', 'CDN / 边缘指纹', null, { value: '未检出 cf-ray' })
      ]
    }
  ],
  findings: [
    {
      title: '模型指纹与宣称一致',
      body: '行为指纹 0.93、Tokenizer 偏离 +0.8%、上下文 128K 吻合，未发现降级迹象。',
      tone: 'success'
    },
    {
      title: '长上下文时延偏高（A7 78）',
      body: '128K 输入下 P50 9.4 s，低于同类中位；建议对超长上下文场景设置超时与降级策略。',
      tone: 'warning'
    },
    {
      title: '高并发能力受限（A8 74 / B3 82）',
      body: '30 并发下 P95 8.9 s，实测并发上限 48；建议对外承诺不超过 20 并发。',
      tone: 'warning'
    },
    {
      title: '数据留存声明缺失（不可测）',
      body: '上游未返回数据留存相关字段，该项不计入总分，建议在合同中单独约定。',
      tone: 'info'
    }
  ],
  evidence: [
    { key: 'DNS / ASN', value: 'api.example-llm.com → 20.42.xx.xx（AS8075 · Microsoft Azure）' },
    { key: 'TLS 证书', value: "CN=*.openai.com · Issuer Let's Encrypt R3 · 有效期 82 天" },
    { key: '响应头', value: 'server: cloudflare · x-request-id: req_8f2a…c4 · openai-organization 存在' },
    { key: 'Tokenizer', value: 'cl100k_base 命中率 99.2%（基线 ±2% 容差内）' },
    { key: '缓存字段', value: 'usage.prompt_tokens_details.cached_tokens = 1560' },
    { key: '错误样本', value: '429 · Retry-After: 2 · error.type=rate_limit_exceeded' }
  ],
  disclaimer:
    '本引擎输出的是证据与置信度，不是"真 / 假"判决，请勿理解为"已验证该模型为正品"。检测结论仅代表检测时点状态，不构成对上游长期稳定性与合规性的担保。报告有效期 30 天，异常可申请复测。',
  veto_note:
    '一票否决项：行为指纹相似度 < 0.70 将直接判定不通过。本项得分按 5 条子证据线加权（行为 0.35 / Tokenizer 0.25 / 自我认知 0.15 / 概率 0.15 / 上下文 0.10）。',
  weight_note:
    '总分 = Σ(检测项得分 × 权重)；默认权重：指纹 0.35、P50 0.15、TTFT/一致性/RPM/TPM/缓存各 0.10；真实源仅证据不计分。置信度：可测子项 ≥4 且一致 → 高。'
}

/** 设计稿全部 55 项明细的项名（顺序即设计稿顺序），用于「文案逐条一致」断言 */
export const DESIGN_ITEM_LABELS: string[] = (DESIGN_REPORT.sections as { items: { code: string; name: string }[] }[])
  .flatMap((s) => s.items.map((i) => `${i.code} ${i.name}`))

export const DESIGN_GROUP_TITLES = ['A · 时延与性能', 'B · 吞吐与限速', 'C · 一致性与可靠性', 'D · 模型指纹（核心项）', 'E · 计量与缓存计费', 'F · 安全与合规', 'G · 真实源证据（不计分）']
