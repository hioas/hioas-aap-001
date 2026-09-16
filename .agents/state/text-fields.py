# -*- coding: utf-8 -*-
"""列出设计树里所有「文本叶子」的全字段（字号/字体/字色/尺寸/文案/行高）。

用法: python .agents/state/text-fields.py <page-id>
     python .agents/state/text-fields.py <page-id> --grep 报价单号   # 只打印路径或文案命中的行

用途：判「声明值」——字重由 fontFamily 后缀决定（Bold→700 / SemiBold→600 / Medium→500 / Regular→400），
字色取 fontFill（不是 fills；fills 在文本节点上常为空）。这是载体页 chk(k, got, want) 里 want 的第一来源。
"""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page = sys.argv[1]
grep = None
if '--grep' in sys.argv:
    grep = sys.argv[sys.argv.index('--grep') + 1]

tree = json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'design.tree.json'), encoding='utf-8'))

WEIGHT = {'Bold': '700', 'SemiBold': '600', 'Medium': '500', 'Regular': '400', 'Black': '900', 'ExtraBold': '800'}
rows = []


def walk(node, path):
    if not isinstance(node, dict):
        return
    name = node.get('name', '')
    content = node.get('content')
    kids = node.get('children') or []
    if isinstance(content, str) and content.strip() and not kids:
        fam = str(node.get('fontFamily') or '')
        suffix = fam.split('-')[-1] if '-' in fam else ''
        rows.append({
            'path': ' / '.join(path + [name]),
            'content': content,
            'fs': node.get('fontSize'),
            'fam': fam,
            'fw': WEIGHT.get(suffix, ''),
            'color': node.get('fontFill'),
            'w': node.get('width'),
            'h': node.get('height'),
            'id': str(node.get('id', ''))[:8],
        })
    for k in kids:
        walk(k, path + [name])


walk(tree, [])
print('total text leaves = %d' % len(rows))
for r in rows:
    line = '%-46s | %-22s | fs=%-5s w=%-4s h=%-11s fw=%-3s %-24s %s' % (
        r['id'], (r['content'] or '')[:20], r['fs'], r['w'], r['h'], r['fw'], r['color'], r['path'][-60:])
    if grep and grep not in line:
        continue
    print(line)
