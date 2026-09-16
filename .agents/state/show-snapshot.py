# -*- coding: utf-8 -*-
"""打印一次 430 宽 DOM 实测 JSON 的关键字段（复核用）。

用法: python .agents/state/show-snapshot.py <run.json> [key ...]
"""
import io
import json
import sys

path = sys.argv[1]
data = json.load(io.open(path, encoding='utf-8'))
phase = data
if 'phases' in data:
    for p in data['phases']:
        if p.get('ok'):
            phase = p
            break
else:
    for k in ('phases',):
        pass

want = sys.argv[2:]
default = ['innerWidth', 'docScrollWidth', 'docScrollHeight', 'overflowingCount', 'missingTexts',
           'checkCount', 'checkFailCount', 'cardRects', 'topbarRect', 'cardCount', 'vendorGroupCount',
           'modelRowCount', 'checkedCount', 'selectedCountText', 'apikeyMaskText', 'apikeyMaskHeight',
           'primaryChipText', 'configuredChipText', 'catalogMoreText', 'barPinned', 'barTop', 'barHeight',
           'ghostBtn', 'submitBtnRect', 'atBottom', 'scrollYMax', 'emojiInText', 'knownMockConflicts']
for k in (want or default):
    if k in phase:
        print('%-20s %s' % (k, json.dumps(phase[k], ensure_ascii=False)))
    else:
        print('%-20s <absent>' % k)
