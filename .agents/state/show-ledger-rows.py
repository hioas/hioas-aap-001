# -*- coding: utf-8 -*-
"""打印台账若干行的可见内容（cron 下不能用 heredoc，必须落盘再跑）。"""
import csv
import io
import sys

path = '.agents/state/aap-feature-status.csv'
rows = list(csv.reader(io.open(path, encoding='utf-8-sig')))
hdr = rows[0]
want = set(sys.argv[1:]) if len(sys.argv) > 1 else None
for r in rows[1:]:
    if not r:
        continue
    if want and r[0].strip() not in want:
        continue
    print('===== 序号 %s =====' % r[0].strip())
    for h, v in zip(hdr, r):
        v = v.replace('\r', ' ').replace('\n', ' | ')
        print('  %-14s %s' % (h, v[:1500]))
