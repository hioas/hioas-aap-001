# -*- coding: utf-8 -*-
"""打印设计树里指定 id 前缀文本叶子的**判读字段**（一行一条）。

用法: python .agents/state/decl-leaves.py <pageId> <idPrefix> [<idPrefix> ...]

字段: id | type | name | fs | fontFamily | lineHeight | w | h | fills | text(截断 24)
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
page = sys.argv[1]
ids = sys.argv[2:]
path = os.path.join(REPO, '.calicat', 'raw', 'pages', page, 'design.tree.json')
data = json.load(io.open(path, encoding='utf-8'))
hits = []


def walk(n):
    if isinstance(n, list):
        for x in n:
            walk(x)
        return
    if not isinstance(n, dict):
        return
    nid = n.get('id') or n.get('layer_id')
    if nid and any(str(nid).startswith(p) for p in ids):
        hits.append(n)
    for ch in n.get('children') or []:
        walk(ch)


walk(data)


def cut(s, n=26):
    s = str(s or '')
    return s if len(s) <= n else s[:n] + '…'


def fill(v):
    if isinstance(v, list) and v:
        v = v[0]
    if isinstance(v, dict):
        return v.get('color') or v.get('fills') or json.dumps(v, ensure_ascii=False)[:24]
    return v


for n in hits:
    print('%-9s %-10s %-16s fs=%-6s fam=%-26s lh=%-5s w=%-12s h=%-13s fill=%-22s %s' % (
        str(n.get('id'))[:8], n.get('type'), cut(n.get('name'), 16), n.get('fontSize'),
        cut(n.get('fontFamily'), 26), n.get('lineHeight'), n.get('width'), n.get('height'),
        cut(fill(n.get('fills')), 22), cut(n.get('text') or n.get('content'))))
print('-- %d 条' % len(hits))
