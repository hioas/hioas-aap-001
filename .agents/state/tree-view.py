#!/usr/bin/env python
"""Compact design-tree view for a captured page: structure only (frames) by default.

Usage:
  python .agents/state/tree-view.py <page-id> [--types frame,text] [--min-depth N] [--max-depth N]
                                    [--match SUBSTR] [--text-max N]

Reads .calicat/raw/pages/<page-id>/design.tree.json and prints one line per node with
depth indentation, id, name, type, geometry, padding/radius/fills/stroke/layout and text.
Prints the raw declared values so a probe's `want` argument can be copied verbatim.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(page_id):
    p = os.path.join(ROOT, '.calicat', 'raw', 'pages', page_id, 'design.tree.json')
    if not os.path.exists(p):
        sys.exit('missing %s' % p)
    with open(p, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def nodes(tree):
    """design.tree.json is [{id, layer_data}] where layer_data is the node tree."""
    out = []
    stack = []
    for entry in tree if isinstance(tree, list) else [tree]:
        root = entry.get('layer_data', entry) if isinstance(entry, dict) else entry
        stack.append((0, root))
    while stack:
        depth, node = stack.pop()
        if not isinstance(node, dict):
            continue
        out.append((depth, node))
        kids = node.get('children') or node.get('kids') or []
        for kid in reversed(kids):
            stack.append((depth + 1, kid))
    return out


def fmt(depth, node, text_max):
    d = node.get('layer_data') if isinstance(node.get('layer_data'), dict) else node
    parts = ['%s%s' % ('  ' * depth, d.get('name') or '?')]
    if d.get('id'):
        parts.append('id=%s' % str(d['id'])[:8])
    t = d.get('type')
    if t:
        parts.append('type=%s' % t)
    for k in ('width', 'height'):
        if d.get(k) is not None:
            parts.append('%s=%s' % (k, d[k]))
    if d.get('padding') is not None:
        parts.append('padding=%s' % (d['padding'],))
    if d.get('cornerRadius') is not None:
        parts.append('r=%s' % d['cornerRadius'])
    if d.get('fills') is not None:
        parts.append('fills=%s' % json.dumps(d['fills'], ensure_ascii=False, separators=(',', ':')))
    if d.get('stroke') is not None:
        parts.append('stroke=%s' % json.dumps(d['stroke'], ensure_ascii=False, separators=(',', ':')))
    if d.get('effects') is not None:
        parts.append('effects=%s' % json.dumps(d['effects'], ensure_ascii=False, separators=(',', ':')))
    for k in ('layout', 'alignItems', 'justifyContent', 'fontSize', 'fontFamily', 'textAlignVertical'):
        if d.get(k) is not None:
            parts.append('%s=%s' % (k, d[k]))
    txt = d.get('text') or d.get('TEXT') or d.get('characters')
    if txt:
        s = str(txt)
        if len(s) > text_max:
            s = s[:text_max] + '…'
        parts.append('TEXT=%r' % s)
    return ' '.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page_id')
    ap.add_argument('--types', default='frame')
    ap.add_argument('--min-depth', type=int, default=0)
    ap.add_argument('--max-depth', type=int, default=99)
    ap.add_argument('--match', default=None)
    ap.add_argument('--text-max', type=int, default=28)
    args = ap.parse_args()
    want = None if args.types == 'all' else set(args.types.split(','))
    for depth, node in nodes(load(args.page_id)):
        d = node.get('layer_data') if isinstance(node.get('layer_data'), dict) else node
        if want is not None and d.get('type') not in want:
            continue
        if not (args.min_depth <= depth <= args.max_depth):
            continue
        line = fmt(depth, node, args.text_max)
        if args.match and args.match not in line:
            continue
        print(line)


if __name__ == '__main__':
    main()
