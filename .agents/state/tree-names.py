"""打印某一帧设计树（从指定节点名开始）的名称层级，用于帧间结构对账。

用法：python .agents/state/tree-names.py <page-id> [起始节点名] [最大深度]
（节点名走 argv，中文参数在本机 MSYS 下可能被转码 → 建议传 ASCII 或省略）
"""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page = sys.argv[1]
start = sys.argv[2] if len(sys.argv) > 2 else None
maxdepth = int(sys.argv[3]) if len(sys.argv) > 3 else 99
tree = json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'design.tree.json'), encoding='utf-8'))


def find(n, name):
    if n.get('name') == name:
        return n
    for c in n.get('children') or []:
        r = find(c, name)
        if r:
            return r
    return None


def dump(n, d=0):
    print('%s%s%s' % ('  ' * d, n.get('name'), '' if d == 0 else ''))
    if d >= maxdepth:
        return
    for c in n.get('children') or []:
        dump(c, d + 1)


node = find(tree, start) if start else tree
if not node:
    print('NOT FOUND')
else:
    dump(node)
