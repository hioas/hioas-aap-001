# -*- coding: utf-8 -*-
"""Extract pending/拍板/missing-prd items from ledger for queue-3 triage."""
import csv, re, sys

rows = list(csv.reader(open('.agents/state/aap-feature-status.csv', encoding='utf-8')))
hdr = rows[0]
idx = {h: i for i, h in enumerate(hdr)}
keys = ['拍板', 'missing-prd', '待确认', '待人类', '待定', '悬置', '不阻塞', '未实现']
for r in rows[1:]:
    seq = r[idx['序号']] if idx['序号'] < len(r) else ''
    page = r[idx['页面名']] if idx['页面名'] < len(r) else ''
    status = r[idx['状态']] if idx['状态'] < len(r) else ''
    if idx['备注'] >= len(r):
        continue
    note = r[idx['备注']]
    if not any(k in note for k in keys):
        continue
    flagged = []
    for seg in re.split(r'[；;\n]', note):
        if any(k in seg for k in keys):
            flagged.append(seg.strip()[:220])
    if flagged:
        print(f"== {seq} ({page[:30]}) status={status}")
        for f in flagged:
            print("   *", f)