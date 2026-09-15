"""打印某页面设计树里某个节点（按 id 前缀匹配，避开中文参数编码坑）的原始 JSON 子树。

用法：python .agents/state/node-tree-raw.py <page-id> <id前缀> [maxdepth]
"""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page, prefix = sys.argv[1], sys.argv[2]
maxdepth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
tree = json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'design.tree.json'), encoding='utf-8'))

KEYS = ['id', 'type', 'width', 'height', 'heightMode', 'padding', 'gap', 'fontSize', 'lineHeight',
        'fontFamily', 'text', 'fills', 'fontFill', 'cornerRadius', 'layout', 'alignItems', 'justifyContent', 'visible']


def brief(n):
    return {k: n[k] for k in KEYS if k in n and n[k] is not None}


def dump(n, depth, maxdepth):
    pad = '  ' * depth
    print('%s%s' % (pad, json.dumps(brief(n), ensure_ascii=False)))
    if depth >= maxdepth:
        return
    for k in n.get('children') or []:
        dump(k, depth + 1, maxdepth)


def walk(n, depth=0):
    if str(n.get('id', '')).startswith(prefix):
        dump(n, 0, maxdepth)
        return True
    for k in n.get('children') or []:
        if walk(k, depth + 1):
            return True
    return False


if not walk(tree):
    print('NOT FOUND: %s' % prefix)
