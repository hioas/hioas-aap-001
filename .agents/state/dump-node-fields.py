# -*- coding: utf-8 -*-
"""Dump the raw shape of a node in .calicat/raw/pages/<page>/design.json (keys + geometry fields)."""
import io
import json
import sys

page = sys.argv[1] if len(sys.argv) > 1 else 'page-4-2'
name_needle = sys.argv[2] if len(sys.argv) > 2 else '凭证名称'
data = json.load(io.open('.calicat/raw/pages/%s/design.json' % page, encoding='utf-8'))


def walk(node, depth=0):
    if not isinstance(node, dict):
        return
    name = node.get('name') or node.get('layer_name') or ''
    content = node.get('content') or ''
    hit = (isinstance(name, str) and name_needle in name) or (isinstance(content, str) and name_needle in content)
    if hit:
        print('--- node: %s (depth %d) ---' % (content or name, depth))
        for k in sorted(node.keys()):
            v = node[k]
            s = json.dumps(v, ensure_ascii=False)
            print('  %-22s %s' % (k, s[:300]))
        print()
    for key in ('children', 'kids'):
        for c in node.get(key) or []:
            walk(c, depth + 1)
    for key in ('layer_data', 'data'):
        v = node.get(key)
        if isinstance(v, dict):
            walk(v, depth)
        elif isinstance(v, list):
            for c in v:
                walk(c, depth)


if isinstance(data, list):
    for item in data:
        walk(item)
else:
    walk(data)
