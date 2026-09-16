# -*- coding: utf-8 -*-
"""诊断：打印台账某行的字段边界（最后 300 字符）。用法: python diag-ledger-row.py <序号>"""
import sys
from pathlib import Path

P = Path('.agents/state/aap-feature-status.csv')
text = P.read_text(encoding='utf-8')
rows = text.split('\n')
want = sys.argv[1] if len(sys.argv) > 1 else '6'
for i, ln in enumerate(rows):
    if ln.startswith(want + ','):
        print('line index', i, 'len', len(ln), 'endswith_quote', ln.endswith('"'))
        print('--- tail 200 (repr) ---')
        print(repr(ln[-200:]))
        break
