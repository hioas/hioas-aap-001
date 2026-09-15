"""按字段特征在设计树里搜节点（避开中文参数编码坑）。

用法：python .agents/state/find-node.py <page-id> <key>=<value> [maxdepth]
例：python .agents/state/find-node.py page-26 fills=rgba(250,252,255,1)
"""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page, cond = sys.argv[1], sys.argv[2]
maxdepth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
key, _, val = cond.partition('=')
tree = json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'design.tree.json'), encoding='utf-8'))

KEYS = ['id', 'name', 'type', 'width', 'height', 'padding', 'gap', 'fontSize', 'lineHeight', 'fontFamily',
        'text', 'fills', 'fontFill', 'cornerRadius', 'layout', 'alignItems', 'visible']


def brief(n):
    return {k: n[k] for k in KEYS if k in n and n[k] is not None}


def dump(n, depth, maxdepth):
    print('%s%s' % ('  ' * depth, json.dumps(brief(n), ensure_ascii=False)))
    if depth >= maxdepth:
        return
    for c in n.get('children') or []:
        dump(c, depth + 1, maxdepth)


def walk(n):
    if str(n.get(key)) == val:
        dump(n, 0, maxdepth)
        return True
    for c in n.get('children') or []:
        if walk(c):
            return True
    return False


if not walk(tree):
    print('NOT FOUND: %s' % cond)
