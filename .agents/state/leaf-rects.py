# -*- coding: utf-8 -*-
"""从 textleaf-<tag>.json 里按类名取实现侧 rect / computed 值（判读用）。

用法: python .agents/state/leaf-rects.py <tag> <class> [<class> ...]
      class 用空格分隔表示「类链里同时包含这几段」，如 'metric__sub metric__sub--muted'。
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _r(v):
    if isinstance(v, (int, float)):
        return round(v, 1)
    return v


tag = sys.argv[1]
wanted = sys.argv[2:]
data = json.load(io.open(os.path.join(REPO, '.agents', 'state', 'evidence', 'textleaf-%s.json' % tag),
                         encoding='utf-8'))
leafs = data.get('leafs') or []
for w in wanted:
    parts = w.split()
    hits = [l for l in leafs if all(p in (l.get('ac') or '') for p in parts)]
    print('== %s  n=%d' % (w, len(hits)))
    for l in hits[:10]:
        print('   x=%-7s r=%-7s top=%-8s bot=%-8s w=%-6s h=%-6s fs=%-7s lh=%-8s fw=%-4s %s' % (
            _r(l.get('left')), _r((l.get('left') or 0) + (l.get('w') or 0)), _r(l.get('top')),
            _r((l.get('top') or 0) + (l.get('h') or 0)), _r(l.get('w')), _r(l.get('h')),
            l.get('fs'), l.get('lh'), l.get('fw'), (l.get('t') or '')[:24]))
