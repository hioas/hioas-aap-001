# -*- coding: utf-8 -*-
"""设计树：按 id 前缀列某节点的直接子节点（含孙节点）声明值。

用法:
  python .agents/state/design-children.py <page-id> <idPrefix> [--depth 2]
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS = ('layout', 'gap', 'alignItems', 'justifyContent', 'padding', 'width', 'height',
        'cornerRadius', 'fills', 'stroke', 'effects', 'fontSize', 'fontFamily',
        'lineHeight', 'textAlign', 'textAlignVertical', 'visible')


def load(page_id):
    with open(os.path.join(ROOT, '.calicat', 'raw', 'pages', page_id, 'design.tree.json'),
              'r', encoding='utf-8') as fh:
        return json.load(fh)


def roots(tree):
    for entry in tree if isinstance(tree, list) else [tree]:
        yield entry.get('layer_data', entry) if isinstance(entry, dict) else entry


def find(node, prefix):
    if str(node.get('id', '')).startswith(prefix):
        return node
    for k in node.get('children') or node.get('kids') or []:
        r = find(k, prefix)
        if r:
            return r
    return None


def fmt(node):
    parts = ['id=%s' % str(node.get('id', ''))[:8], 'name=%s' % (node.get('name') or ''),
             'type=%s' % (node.get('type') or '')]
    for k in KEYS:
        v = node.get(k)
        if v in (None, [], {}, ''):
            continue
        parts.append('%s=%s' % (k, json.dumps(v, ensure_ascii=False)))
    txt = node.get('content') or node.get('text') or node.get('characters')
    if txt:
        parts.append('text=%r' % (str(txt)[:34]))
    return ' | '.join(parts)


def walk(node, depth, maxd):
    print('%s%s' % ('  ' * depth, fmt(node)))
    if depth >= maxd:
        return
    for k in node.get('children') or node.get('kids') or []:
        walk(k, depth + 1, maxd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page_id')
    ap.add_argument('prefix')
    ap.add_argument('--depth', type=int, default=2)
    a = ap.parse_args()
    tree = load(a.page_id)
    for r in roots(tree):
        n = find(r, a.prefix)
        if n:
            walk(n, 0, a.depth)
            return
    print('not found: %s' % a.prefix)


main()
