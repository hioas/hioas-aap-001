#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打印设计树中某个节点（按 id 前缀匹配）的**完整原始 JSON**。

用法: python .agents/state/node-raw.py <design.tree.json> <nodeIdPrefix> [--limit N]

比 node-probe.py 更原始：会打印 padding / gap / stroke 等声明（node-probe 只挑部分字段）。
"""
import json
import sys


def walk(node, prefix, out):
    if isinstance(node, dict):
        nid = str(node.get('id', ''))
        if prefix and nid.startswith(prefix):
            out.append(node)
        for c in node.get('children') or []:
            walk(c, prefix, out)
    elif isinstance(node, list):
        for c in node:
            walk(c, prefix, out)


def main():
    path, prefix = sys.argv[1], sys.argv[2]
    limit = 1
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    tree = json.load(open(path, encoding='utf-8'))
    out = []
    walk(tree, prefix, out)
    if not out:
        print('not found:', prefix)
        return
    for node in out[:limit]:
        print(json.dumps(node, ensure_ascii=False, indent=1))


main()
