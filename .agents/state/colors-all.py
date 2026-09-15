# -*- coding: utf-8 -*-
"""列出设计树里出现过的**全部**颜色（fills + fontFill + stroke.fills），并标注 tokens.scss 是否已覆盖。
用法: python .agents/state/colors-all.py <design.tree.json> [tokens.scss]
"""
import json
import re
import sys
from collections import Counter

tree_path = sys.argv[1]
tokens_path = sys.argv[2] if len(sys.argv) > 2 else 'aap-client/src/styles/tokens.scss'


def rgba_to_hex(text):
    m = re.match(r'rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)', str(text))
    if not m:
        return None
    r, g, b = (int(round(float(m.group(i)))) for i in (1, 2, 3))
    return '#%02X%02X%02X' % (min(r, 255), min(g, 255), min(b, 255))


counter = Counter()
where = {}


def walk(node, path):
    for key in ('fills', 'fontFill'):
        hx = rgba_to_hex(node.get(key))
        if hx:
            counter[hx] += 1
            where.setdefault(hx, '%s.%s' % (node.get('name'), key))
    stroke = node.get('stroke')
    if isinstance(stroke, dict):
        hx = rgba_to_hex(stroke.get('fills'))
        if hx:
            counter[hx] += 1
            where.setdefault(hx, '%s.stroke' % node.get('name'))
    for child in node.get('children') or []:
        walk(child, path)


tree = json.load(open(tree_path, encoding='utf-8'))
walk(tree, '')

try:
    tokens = open(tokens_path, encoding='utf-8').read().lower()
except OSError:
    tokens = ''

print('颜色数: %d' % len(counter))
for hx, n in counter.most_common():
    hit = 'OK ' if hx.lower() in tokens else 'NEW'
    var = ''
    if hit == 'OK ':
        m = re.search(r'(\$[\w-]+):\s*' + hx.lower(), tokens)
        var = m.group(1) if m else ''
    print('  %s %s x%-3d %-28s %s' % (hit, hx, n, where.get(hx, ''), var))
