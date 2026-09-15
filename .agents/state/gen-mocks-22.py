# -*- coding: utf-8 -*-
"""序号 22 用量概览页的独立 H5 mock 集（不与 api/ 或 api-21 混用）。

设计帧 page-22-2 的样例数值逐值复刻：
  请求数 1.24M · Token 3.86B · 费用 ¥12,860 · 较上月节省 ¥2,140
  近 7 日 0.23 / 0.65 / 0.50 / 1.10 / 1.37 / 1.64 / 1.92 亿（设计帧折线 y 117.78..29.28，纵轴上限 2 亿）
  模型占比 42 / 31 / 21 / 6 % · 成本 输入 ¥4,120 / 输出 ¥8,240 / 平台服务费（8%）¥500 / 合计 ¥12,860
运行：python .agents/state/gen-mocks-22.py
"""
import io
import json
import os

ROOT = os.path.join('.agents', 'state', 'h5-measure', 'api-22', 'v1', 'usage')

DAILY = [
    ('2024-06-08', 23_000_000),
    ('2024-06-09', 65_000_000),
    ('2024-06-10', 50_000_000),
    ('2024-06-11', 110_000_000),
    ('2024-06-12', 137_000_000),
    ('2024-06-13', 164_000_000),
    ('2024-06-14', 192_000_000),
]

SUMMARY = {
    'code': '0',
    'message': 'ok',
    'data': {
        'month': '2024-06',
        'request_count': 1_240_000,
        'total_tokens': 3_860_000_000,
        'amount_total': 12_860,
        'mom_saved_amount': 2_140,
        'updated_at': '2024-06-14 16:20',
        'daily': [{'stat_date': d, 'total_tokens': t} for d, t in DAILY],
        'models': [
            {'model_name': 'gpt-4o-mini', 'share': 42},
            {'model_name': 'claude-3-5-sonnet', 'share': 31},
            {'model_name': 'gpt-4o', 'share': 21},
            {'model_name': '其他', 'share': 6},
        ],
        'cost': {
            'input': 4_120,
            'output': 8_240,
            'platform_fee': 500,
            'platform_fee_rate': 8,
            'total': 12_860,
        },
        # ⚠️ mock 是静态文件：切月份后服务端仍返回 6 月数据（与序号 20 同口径），
        #    「重新取数真的带上了新月份」以 serve.py 访问日志里的 ?month=YYYY-MM 为准。
    },
}

if not os.path.isdir(ROOT):
    os.makedirs(ROOT)

with io.open(os.path.join(ROOT, 'summary'), 'w', encoding='utf-8') as fh:
    json.dump(SUMMARY, fh, ensure_ascii=False, indent=2)

print('wrote', os.path.join(ROOT, 'summary'))
