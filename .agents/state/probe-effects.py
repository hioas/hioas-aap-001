# -*- coding: utf-8 -*-
"""遍历 page-N design.json，打印带 effects 的节点（名称 + offset/blur/颜色）与顶部栏/按钮节点的完整声明。"""
import io, json, sys

page = sys.argv[1] if len(sys.argv) > 1 else 'page-3'
data = json.load(io.open('.calicat/raw/pages/%s/design.json' % page, encoding='utf-8'))


def walk(node, path):
    if not isinstance(node, dict):
        return
    name = node.get('name') or node.get('layer_name') or '?'
    eff = node.get('effects') or node.get('style', {}).get('effects') if isinstance(node.get('style'), dict) else node.get('effects')
    if eff:
        print('EFFECT node=%s id=%s' % (name, node.get('id') or node.get('layer_id')))
        print('   ', json.dumps(eff, ensure_ascii=False))
    for key in ('children', 'kids'):
        for c in node.get(key) or []:
            walk(c, path + '/' + name)
    for key in ('layer_data', 'data'):
        v = node.get(key)
        if isinstance(v, dict):
            walk(v, path)
        elif isinstance(v, list):
            for c in v:
                walk(c, path)


if isinstance(data, list):
    for item in data:
        walk(item, '')
else:
    walk(data, '')
print('=== top-level type:', type(data).__name__, list(data.keys()) if isinstance(data, dict) else len(data))
