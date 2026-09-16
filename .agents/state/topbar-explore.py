"""探索：逐帧打印 design.tree.json 的「页面容器」前 3 个直接子节点（name/type/宽高/布局）。
用于确定各帧「顶部栏/导航区」节点的命名与位置口径。
用法：python .agents/state/topbar-explore.py [page-id ...]
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES = os.path.join(REPO, '.calicat', 'raw', 'pages')

ids = sys.argv[1:]
if not ids:
    ids = sorted(os.listdir(PAGES))

for pid in ids:
    f = os.path.join(PAGES, pid, 'design.tree.json')
    if not os.path.exists(f):
        print('MISSING', pid)
        continue
    root = json.load(open(f, encoding='utf-8'))
    print('== %s  %s  %sx%s' % (pid, root.get('name'), root.get('width'), root.get('height')))
    for c in root.get('children') or []:
        print('   容器: %-16s %-6s w=%-10s h=%-8s layout=%s' % (
            (c.get('name') or '')[:16], c.get('type'), c.get('width'), c.get('height'), c.get('layout')))
        for g in (c.get('children') or [])[:4]:
            print('      ├ %-28s %-6s w=%-10s h=%-8s layout=%s gap=%s' % (
                (g.get('name') or '')[:28], g.get('type'), g.get('width'), g.get('height'),
                g.get('layout'), g.get('gap')))
