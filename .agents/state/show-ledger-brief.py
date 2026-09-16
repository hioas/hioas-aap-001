# -*- coding: utf-8 -*-
"""打印台账 序号/页面ID/目标路由/状态/Mock 目录，供审计脚本取件。"""
import csv
import io
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows = list(csv.DictReader(io.open(os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv'), encoding='utf-8')))
print('cols:', list(rows[0].keys()))
for r in rows:
    print('%-7s | %-12s | %-38s | %s' % (r['序号'], r['页面ID'], r['目标路由'], r['状态']))
