# -*- coding: utf-8 -*-
"""打印每个页面「顶部栏/导航」CSS 规则块（含其上一条注释），供跨页同族位置核对。

用法: python .agents/state/nav-source-dump.py [--grep 关键子串]
"""
import glob
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'aap-client', 'src')
RULE = re.compile(r'^\s*\.([A-Za-z0-9_-]*(?:__nav|__topbar|__header))\s*\{')
grep = sys.argv[sys.argv.index('--grep') + 1] if '--grep' in sys.argv else None

for f in sorted(glob.glob(os.path.join(SRC, 'pages', '**', '*.vue'), recursive=True) +
                glob.glob(os.path.join(SRC, 'components', '**', '*.vue'), recursive=True)):
    lines = io.open(f, encoding='utf-8').read().split('\n')
    hits = [i for i, l in enumerate(lines) if RULE.match(l)]
    if not hits:
        continue
    print('===== %s' % os.path.relpath(f, SRC))
    for i in hits:
        j = i
        depth = 0
        while j < len(lines):
            depth += lines[j].count('{') - lines[j].count('}')
            print('  %4d %s' % (j + 1, lines[j]))
            if depth <= 0 and j > i:
                break
            j += 1
    print()
