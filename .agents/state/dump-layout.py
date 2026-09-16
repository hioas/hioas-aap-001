#!/usr/bin/env python
"""Full-field compact dump of one captured page's design tree (declaration values only).

Usage:
  python .agents/state/dump-layout.py <page-id> [--match SUBSTR] [--depth N] [--text-max N]

Prints one line per node: depth, name, id8, type, layout/gap/align, padding, w/h, radius,
fills, stroke, effects, fontSize/fontFamily/lineHeight, content, visible.

Why: tree-view.py omits `gap` and `lineHeight`; dump-node-fields.py prints one node at a
time with truncation; raw-node.py prints raw JSON (too verbose for a whole page).
This is the single entry point for "what did the design declare, verbatim".
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS = (
    'layout', 'gap', 'alignItems', 'justifyContent', 'padding', 'width', 'height',
    'cornerRadius', 'fills', 'stroke', 'effects', 'fontSize', 'fontFamily',
    'lineHeight', 'letterSpacing', 'textAlign', 'textAlignVertical', 'visible',
)


def load(page_id):
    p = os.path.join(ROOT, '.calicat', 'raw', 'pages', page_id, 'design.tree.json')
    if not os.path.exists(p):
        sys.exit('missing %s' % p)
    with open(p, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def walk(tree):
    out, stack = [], []
    for entry in tree if isinstance(tree, list) else [tree]:
        root = entry.get('layer_data', entry) if isinstance(entry, dict) else entry
        stack.append((0, root))
    while stack:
        depth, node = stack.pop()
        if not isinstance(node, dict):
            continue
        d = node.get('layer_data') if isinstance(node.get('layer_data'), dict) else node
        out.append((depth, d))
        for kid in reversed(d.get('children') or d.get('kids') or []):
            stack.append((depth + 1, kid))
    return out


def fmt(depth, d, text_max):
    parts = ['%s%s' % ('  ' * depth, d.get('name') or '?'), 'id=%s' % str(d.get('id'))[:8],
             'type=%s' % d.get('type')]
    for k in KEYS:
        v = d.get(k)
        if v is None or v is False:
            continue
        if k in ('fills', 'stroke', 'effects'):
            parts.append('%s=%s' % (k, json.dumps(v, ensure_ascii=False, separators=(',', ':'))))
        else:
            parts.append('%s=%s' % (k, v))
    txt = d.get('content') or d.get('text') or d.get('characters')
    if txt:
        s = str(txt)
        parts.append('C=%r' % (s[:text_max] + '…' if len(s) > text_max else s))
    return ' '.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page_id')
    ap.add_argument('--match', default=None)
    ap.add_argument('--depth', type=int, default=99)
    ap.add_argument('--text-max', type=int, default=40)
    args = ap.parse_args()
    for depth, d in walk(load(args.page_id)):
        if depth > args.depth:
            continue
        line = fmt(depth, d, args.text_max)
        if args.match and args.match not in line:
            continue
        print(line)


if __name__ == '__main__':
    main()
