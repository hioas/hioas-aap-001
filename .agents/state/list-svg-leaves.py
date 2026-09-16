# -*- coding: utf-8 -*-
"""列出 page-22-2 设计树里「未渲染」类叶子（含内联 SVG 图形）的 id / 类型 / 尺寸 / 内容首段。

用法: python .agents/state/list-svg-leaves.py page-22-2 [--svg-only]
"""
import io
import json
import os
import sys

REPO = r'E:/workspaces/hioas/hioas-aap-001'
pid = sys.argv[1] if len(sys.argv) > 1 else 'page-22-2'
svg_only = '--svg-only' in sys.argv

tree = json.load(io.open(os.path.join(REPO, '.calicat', 'raw', 'pages', pid, 'design.tree.json'), encoding='utf-8'))


def walk(node, depth=0):
    yield node, depth
    for ch in (node.get('children') or []):
        for x in walk(ch, depth + 1):
            yield x


svg = 0
other = 0
for node, depth in walk(tree):
    content = node.get('content')
    name = node.get('name') or ''
    typ = node.get('type') or ''
    kids = node.get('children') or []
    if kids:
        continue
    if content is None:
        continue
    c = str(content)
    is_svg = '<svg' in c
    if is_svg:
        svg += 1
    else:
        other += 1
    if svg_only and not is_svg:
        continue
    print('%-16s depth=%d type=%-10s w=%s h=%s %s' % (node.get('id', '')[:12], depth, typ,
                                                      repr(node.get('width'))[:12], repr(node.get('height'))[:12], name[:24]))
    print('    content[:160] = %r' % c[:160])
print('---- svg leaves %d · text leaves %d ----' % (svg, other))
