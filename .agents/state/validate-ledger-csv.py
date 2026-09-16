# -*- coding: utf-8 -*-
"""校验台账 CSV：逐行打印字段数，标出 != 表头字段数的行。
用法: python .agents/state/validate-ledger-csv.py <file>
"""
import csv
import sys
from pathlib import Path

p = Path(sys.argv[1])
text = p.read_text(encoding='utf-8')
rows = list(csv.reader(text.splitlines()))
head = rows[0]
print('header fields =', len(head))
bad = 0
for i, r in enumerate(rows[1:], start=2):
    if len(r) != len(head):
        bad += 1
        print('line %d: fields=%d  first=%r' % (i, len(r), r[0][:40]))
print('rows =', len(rows) - 1, 'bad =', bad)
