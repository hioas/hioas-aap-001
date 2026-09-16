# -*- coding: utf-8 -*-
"""设计树：某文本叶子（按 id 前缀）的祖先链声明值。

用法:
  python .agents/state/design-ancestors.py <page-id> <leafIdPrefix> [--depth 8]

打印从根到该叶子的每一级：id8 | name | type | layout/gap/align | padding | w/h | fills | stroke | effects | fs/fam/lh | text
用途：判「这个盒子的高/间距是设计哪一级声明出来的」（例如 notice 条目的行盒与条目间距）。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS = ('layout', 'gap', 'alignItems', 'justifyContent', 'padding', 'width', 'height',
        'cornerRadius', 'fills', 'stroke', 'effects', 'fontSize', 'fontFamily',
        'lineHeight', 'textAlign', 'textAlignVertical', 'visible')


def load(page_id):
    p = os.path.join(ROOT, '.calicat', 'raw', 'pages', page_id, 'design.tree.json')
    with open(p, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def roots(tree):
    for entry in tree if isinstance(tree, list) else [tree]:
        yield entry.get('layer_data', entry) if isinstance(entry, dict) else entry


def find_path(node, prefix, path):
    nid = str(node.get('id', ''))
    path = path + [node]
    if nid.startswith(prefix):
        return path
    for k in node.get('children') or node.get('kids') or []:
        r = find_path(k, prefix, path)
        if r:
            return r
    return None


def fmt(node):
    nid = str(node.get('id', ''))[:8]
    name = node.get('name') or node.get('layer_name') or ''
    typ = node.get('type') or node.get('layer_type') or ''
    parts = ['id=%s' % nid, 'name=%s' % name, 'type=%s' % typ]
    for k in KEYS:
        v = node.get(k)
        if v in (None, [], {}, ''):
            continue
        if k == 'text':
            continue
        parts.append('%s=%s' % (k, json.dumps(v, ensure_ascii=False)))
    txt = node.get('content') or node.get('text') or node.get('characters')
    if txt:
        parts.append('text=%r' % (str(txt)[:40]))
    return ' | '.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page_id')
    ap.add_argument('prefix')
    ap.add_argument('--depth', type=int, default=8)
    args = ap.parse_args()
    tree = load(args.page_id)
    for r in roots(tree):
        p = find_path(r, args.prefix, [])
        if p:
            print('ancestor chain for id prefix %s (%d levels)' % (args.prefix, len(p)))
            for i, n in enumerate(p):
                print('  %s%s' % ('  ' * i, fmt(n)))
            return
    print('not found: %s' % args.prefix)


main()
