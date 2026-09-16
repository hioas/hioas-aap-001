# -*- coding: utf-8 -*-
"""打印 design.json（原始，非 tree）里指定 id 前缀节点的完整 JSON。

用法: python .agents/state/raw-node.py <pageId> <idPrefix> [<idPrefix> ...]
"""
import io
import json
import sys

page = sys.argv[1]
ids = sys.argv[2:]
data = json.load(io.open('.calicat/raw/pages/%s/design.json' % page, encoding='utf-8'))
hits = []


def walk(node):
    if isinstance(node, list):
        for n in node:
            walk(n)
        return
    if not isinstance(node, dict):
        return
    nid = node.get('id') or node.get('layer_id')
    if nid and any(str(nid).startswith(p) for p in ids):
        hits.append(node)
    for k in ('children', 'kids', 'layer_data'):
        if k in node:
            walk(node[k])


walk(data)
for h in hits:
    print('==== %s | %s' % (h.get('id'), h.get('name')))
    print(json.dumps(h, ensure_ascii=False, indent=1)[:2500])
    print()
print('hits=%d' % len(hits))
