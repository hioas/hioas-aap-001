# -*- coding: utf-8 -*-
"""逐帧打印「顶部栏/导航区」子树内的**文本叶子声明值**（fs / fontFamily / lineHeight / 显式 height / 宽 / 文案）。

用途：跨页同族位置（导航标题、编号、副标题）的行盒口径核对——同一视觉位置在不同帧里
是否声明一致、实现是否逐帧落到同一声明值上。want 取 .calicat/raw/pages/<page-id>/design.tree.json。

用法: python .agents/state/nav-title-decl.py [page-id ...]
"""
import csv
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES = os.path.join(REPO, '.calicat', 'raw', 'pages')
LEDGER = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')
TOPBAR_RE = re.compile(r'顶部栏|顶部导航|顶部|用户头部')


def find_bar(root):
    for c in root.get('children') or []:
        for g in c.get('children') or []:
            if TOPBAR_RE.search(g.get('name') or ''):
                return g
    return None


def leaves(node, out, depth=0, path=''):
    txt = node.get('content') or node.get('text')
    if txt is not None:
        out.append((node, depth, path))
    for i, ch in enumerate(node.get('children') or []):
        leaves(ch, out, depth + 1, '%s.%d' % (path, i))


ids = sys.argv[1:] or [r['页面ID'] for r in csv.DictReader(io.open(LEDGER, encoding='utf-8'))]
for pid in ids:
    f = os.path.join(PAGES, pid, 'design.tree.json')
    if not os.path.exists(f):
        continue
    root = json.load(io.open(f, encoding='utf-8'))
    bar = find_bar(root)
    if bar is None:
        print('== %-12s （无顶部栏节点）' % pid)
        continue
    out = []
    leaves(bar, out)
    print('== %-12s 顶部栏=%s（data 子节点 %d 个文本叶子）' % (pid, bar.get('name'), len(out)))
    for node, depth, path in out:
        print('   %-4s %-20s fs=%-5s fam=%-22s lh=%-6s h=%-12s w=%-7s %r' % (
            (node.get('id') or '')[:4], (node.get('name') or '')[:20], node.get('fontSize'),
            node.get('fontFamily'), node.get('lineHeight'), node.get('height'), node.get('width'),
            str(node.get('content') or node.get('text'))[:34]))
