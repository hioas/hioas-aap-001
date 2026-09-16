# -*- coding: utf-8 -*-
"""转储 page-22-2 设计树里内联 SVG 图形叶子（折线/网格/面积/数据点）的样式声明。

用法: python .agents/state/svg-leaves-22.py
"""
import io
import json
import os
import re

REPO = r'E:/workspaces/hioas/hioas-aap-001'
p = os.path.join(REPO, '.calicat', 'raw', 'pages', 'page-22-2', 'design.tree.json')
t = json.load(io.open(p, encoding='utf-8'))


def walk(n, d=0):
    yield n, d
    for c in (n.get('children') or []):
        yield from walk(c, d + 1)


for n, d in walk(t):
    c = n.get('content')
    if not isinstance(c, str) or '<svg' not in c or (n.get('children') or []):
        continue
    pairs = re.findall(r'(stroke|fill)="([^"]*)"|(stroke|fill): ([^;"]+);', c)
    styles = [b or d2 for a, b, c2, d2 in pairs if (b or d2)]
    sw = re.search(r'stroke-width: ([0-9.]+)', c)
    r = re.search(r'cx="([-0-9.]+)" cy="([-0-9.]+)" r="([0-9.]+)"', c)
    op = re.search(r'opacity: ([0-9.]+)', c)
    dpath = re.search(r' d="(M [^"]{0,60})', c)
    print('%-12s type=%-9s w=%-8s h=%-8s styles=%s sw=%s circle=%s op=%s d=%r'
          % (n['id'][:12], n.get('type'), n.get('width'), n.get('height'),
             styles, sw and sw.group(1), r and r.groups(), op and op.group(1), dpath and dpath.group(1)))
