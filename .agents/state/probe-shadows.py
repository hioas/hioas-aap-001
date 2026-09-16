# -*- coding: utf-8 -*-
"""列出 page-3 design.json 里所有 effect/shadow 相关声明（判断实现里的 box-shadow 是否有设计依据）。"""
import io, json, re, sys

page = sys.argv[1] if len(sys.argv) > 1 else 'page-3'
raw = io.open('.calicat/raw/pages/%s/design.json' % page, encoding='utf-8').read()
# 找出所有 keys 里含 shadow/effect/opacity 的片段
hits = {}
for m in re.finditer(r'"(effect[A-Za-z]*|shadow[A-Za-z]*|shadows|blur|offsetX|offsetY|spread)"\s*:\s*([^,}\]]+)', raw):
    hits.setdefault(m.group(1), []).append(m.group(2).strip())
for k, v in hits.items():
    print(k, 'x%d' % len(v), v[:6])
print('---- 含 shadow 关键字的节点名 ----')
for m in re.finditer(r'"name"\s*:\s*"([^"]*)"', raw):
    n = m.group(1)
    if 'shadow' in n.lower() or '投影' in n:
        print('node name:', n)
print('---- 关键词出现次数 ----')
for kw in ['effect', 'shadow', 'blur', 'drop']:
    print(kw, raw.count(kw))
