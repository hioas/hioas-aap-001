#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按设计树的 x/y/width/height 打印带绝对坐标的节点清单。

用法: python .agents/state/geom.py <design.tree.json> [minDepth] [maxDepth] [idPrefix]

设计树里每个节点都带 x/y（绝对坐标，单位 px，画布坐标）。本脚本把它转成
「相对页面左上角」的坐标打印，用于直接算出卡高/卡间距/元素 y —— 比像素量尺更快，
但**帧内坐标可能是相对坐标**，所以同时打印原始值供核对。
"""
import json
import sys


def walk(node, depth, out, prefix, parent_xy):
    if not isinstance(node, dict):
        return
    x = node.get('x')
    y = node.get('y')
    w = node.get('width')
    h = node.get('height')
    abs_x = None
    abs_y = None
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        abs_x = x
        abs_y = y
    out.append((depth, str(node.get('id', ''))[:8], str(node.get('name', '')), str(node.get('type', '')),
                x, y, w, h))
    for c in node.get('children') or []:
        walk(c, depth + 1, out, prefix, (abs_x, abs_y))


def main():
    path = sys.argv[1]
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else 99
    tree = json.load(open(path, encoding='utf-8'))
    out = []
    walk(tree, 0, out, '', (None, None))
    for depth, nid, name, typ, x, y, w, h in out:
        if depth < lo or depth > hi:
            continue
        print('  ' * depth + f'{nid} {name} [{typ}] x={x} y={y} w={w} h={h}')


main()
