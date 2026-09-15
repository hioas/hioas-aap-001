# -*- coding: utf-8 -*-
"""打印 __diag-usage-overflow.html 的取数结果（溢出元素到底是谁）。

用法: python .agents/state/show-diag.py .agents/state/evidence/diag-序号22-overflow.json
"""
import io
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else '.agents/state/evidence/diag-序号22-overflow.json'
data = json.load(io.open(path, encoding='utf-8'))
phase = data.get('phase1', {})
print('innerWidth', phase.get('innerWidth'), 'docScrollWidth', phase.get('docScrollWidth'), 'count', phase.get('count'))
for row in phase.get('rows', []):
    print('-', row.get('tag'), '|', row.get('cls'), '| testid', row.get('testid'),
          '| left', row.get('left'), 'w', row.get('w'),
          '| parent', row.get('parent'), 'overflow', row.get('parentOverflow'))
    print('   html:', (row.get('html') or '')[:150])
print('pickerHost:', (phase.get('pickerHostHtml') or '')[:300])
