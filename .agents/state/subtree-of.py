# -*- coding: utf-8 -*-
"""打印某设计节点的**子树**（含每层 h/pad/lay/gap/fs/lh/文案），用于做卡高算术。

用法: python .agents/state/subtree-of.py <page-id> <id-prefix> [max-depth]
"""
import io
import json
import sys

page, want = sys.argv[1], sys.argv[2]
maxd = int(sys.argv[3]) if len(sys.argv) > 3 else 9
root = json.load(io.open('.calicat/raw/pages/%s/design.tree.json' % page, encoding='utf-8'))
found = []


def find(n, chain):
    if not isinstance(n, dict):
        return
    if str(n.get('id') or '').startswith(want):
        found.append(chain + [n])
    for c in n.get('children') or []:
        find(c, chain + [n])


find(root, [])
if not found:
    print('未找到 %s' % want)
    sys.exit(1)
base = found[0][-1]


def show(n, depth):
    if depth > maxd:
        return
    print('%s%-2d %-26s id=%s w=%-11s h=%-12s pad=%-15s lay=%-9s gap=%-4s fs=%-4s lh=%-4s C=%r' % (
        '  ' * depth, depth, (n.get('name') or '')[:24], str(n.get('id') or '')[:8], n.get('width'), n.get('height'),
        n.get('padding'), n.get('layout'), n.get('gap'), n.get('fontSize'), n.get('lineHeight'),
        str(n.get('content'))[:22]))
    for c in n.get('children') or []:
        show(c, depth + 1)


show(base, 0)
