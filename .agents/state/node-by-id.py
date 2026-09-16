"""node-by-id.py — 按 layer_id 打印设计树节点的声明字段（page-10-1-2 等）。

用法: python .agents/state/node-by-id.py <pageId> <layerId> [<layerId> ...]
"""
import io
import json
import sys

page = sys.argv[1]
ids = set(sys.argv[2:])
data = json.load(io.open('.calicat/raw/pages/%s/design.tree.json' % page, encoding='utf-8'))


def walk(node, path):
    if isinstance(node, list):
        for n in node:
            walk(n, path)
        return
    if not isinstance(node, dict):
        return
    nid = node.get('id') or node.get('layer_id')
    name = node.get('name') or node.get('layer_name') or ''
    hit = nid and any(nid.startswith(p) for p in ids)
    if hit:
        print('--- %s | %s' % (nid, name))
        for k in sorted(node.keys()):
            if k in ('children', 'kids'):
                continue
            v = node[k]
            if v in (None, '', [], {}):
                continue
            s = json.dumps(v, ensure_ascii=False)
            print('  %-16s %s' % (k, s[:220]))
        print()
    for key in ('children', 'kids', 'layer_data'):
        if key in node:
            walk(node[key], path + '/' + str(name))


walk(data, '')
