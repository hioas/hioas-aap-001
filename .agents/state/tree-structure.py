"""探查 design.tree.json 的结构（顶层键、节点键名、kids 键名）。

用法：python .agents/state/tree-structure.py <page-id>
"""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page = sys.argv[1]
tree = json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'design.tree.json'), encoding='utf-8'))
print('top type:', type(tree).__name__)
if isinstance(tree, dict):
    print('top keys:', list(tree.keys())[:20])
node = tree['root'] if isinstance(tree, dict) and 'root' in tree else tree
print('node keys:', list(node.keys()))


def child_key(n):
    for k in n:
        if isinstance(n[k], list) and n[k] and isinstance(n[k][0], dict):
            return k
    return None


k = child_key(node)
print('child key:', k)
if k:
    print('child0 keys:', list(node[k][0].keys()))
    print('child0 sample:', json.dumps({kk: node[k][0][kk] for kk in list(node[k][0].keys())[:25]}, ensure_ascii=False)[:600])
