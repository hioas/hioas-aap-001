# -*- coding: utf-8 -*-
"""打印某设计叶子的**祖先链**声明值（name/id/宽高/padding/layout/gap），用于判「盒高由谁决定」。

用法: python .agents/state/ancestors-of.py <page-id> <leaf-id-prefix>
"""
import io
import json
import sys

page, want = sys.argv[1], sys.argv[2]
root = json.load(io.open('.calicat/raw/pages/%s/design.tree.json' % page, encoding='utf-8'))
path = []


def walk(n, chain):
    if not isinstance(n, dict):
        return False
    nid = str(n.get('id') or '')
    ch = chain + [n]
    if nid.startswith(want):
        for i, a in enumerate(ch):
            print('%s%-2d %-28s id=%s type=%-9s w=%-12s h=%-12s pad=%-16s lay=%-9s gap=%-5s fs=%-5s lh=%-5s C=%r' % (
                '  ' * i, i, (a.get('name') or '')[:26], str(a.get('id') or '')[:8], a.get('type'),
                a.get('width'), a.get('height'), a.get('padding'), a.get('layout'), a.get('gap'),
                a.get('fontSize'), a.get('lineHeight'), str(a.get('content'))[:24]))
        return True
    for c in n.get('children') or []:
        if walk(c, ch):
            return True
    return False


walk(root, [])
