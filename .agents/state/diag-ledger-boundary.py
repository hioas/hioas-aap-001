# -*- coding: utf-8 -*-
"""诊断：定位台账某行「状态」列边界（打印 ',部分,' / ',已验证,' 附近的原始字符）。
用法: python .agents/state/diag-ledger-boundary.py <序号>
"""
import sys
from pathlib import Path

P = Path('.agents/state/aap-feature-status.csv')
rows = P.read_text(encoding='utf-8').split('\n')
want = sys.argv[1] if len(sys.argv) > 1 else '6'
for ln in rows:
    if ln.startswith(want + ','):
        for m in [',部分,', ',已验证,', ',阻塞,']:
            i = ln.find(m)
            if i != -1:
                print('marker %r at %d' % (m, i))
                print('  context:', repr(ln[i - 40:i + 40]))
        break
