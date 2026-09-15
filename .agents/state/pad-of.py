"""给某页面设计树里「凭证说明 / 单号说明 / 提示卡」等节点打印其父链上的 padding，
用来核对实现里的间距是否与设计一致（中文节点名通过 unicode 转义避免命令行编码坑）。

用法：python .agents/state/pad-of.py <page-id> <节点名unicode转义或原文>
"""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page = sys.argv[1]
target = sys.argv[2].encode().decode('unicode_escape') if '\\u' in sys.argv[2] else sys.argv[2]
tree = json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'design.tree.json'), encoding='utf-8'))


def walk(n, path):
    if n.get('name') == target:
        for i, anc in enumerate(path):
            print('%s%s padding=%s height=%s' % ('  ' * i, anc.get('name'), anc.get('padding'), anc.get('height')))
        print('  ' * len(path) + 'TARGET %s padding=%s height=%s' % (n.get('name'), n.get('padding'), n.get('height')))
    for c in n.get('children') or []:
        walk(c, path + [n])


walk(tree, [])
