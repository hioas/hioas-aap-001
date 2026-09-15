# -*- coding: utf-8 -*-
"""生成序号 21（我的页）H5 验收用 mock 集：.agents/state/h5-measure/api-21/v1/**
数据与设计帧逐字一致（企业名 / 三金额 / 各入口计数），便于像素与文案对账。
"""
import json
import os

ROOT = os.path.join('.agents', 'state', 'h5-measure', 'api-21', 'v1')


def put(rel, data):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({'code': '0', 'message': 'ok', 'data': data}, fh, ensure_ascii=False, indent=2)
    print('wrote', path)


put('provider/profile', {
    'id': 'p1',
    'company_name': '云智科技有限公司',
    'companyName': '云智科技有限公司',
    'unified_social_credit_code': '91330106MA2XXXXX8B',
    'industry_category': 'RESELLER',
    'verified': True,
    'status': 'PUBLISHED',
    'completeness': 100
})
put('payments', {
    'available_balance': 12860,
    'pending_settlement': 3240,
    'total_settled': 86420,
    'total': 3,
    'items': []
})
put('quotes/index', {'total': 3, 'items': []})
put('reports/index', {'total': 2, 'items': []})
put('contracts/index', {'total': 1, 'items': []})
put('credentials/index', {'total': 3, 'items': []})
put('notifications/index', {'total': 3, 'items': []})
print('api-21 mock set ready')
