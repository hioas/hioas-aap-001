#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在指定矩形内找「明显偏蓝（或偏绿/黄）的墨迹像素」，用于判断设计稿里某段文字是不是链接色。

用法: python .agents/state/find-tint.py <png> <x0> <y0> <x1> <y1> [blue|green|amber] [minDelta]
"""
import sys

from PIL import Image


def main():
    path = sys.argv[1]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6])
    tint = sys.argv[6] if len(sys.argv) > 6 else 'blue'
    delta = int(sys.argv[7]) if len(sys.argv) > 7 else 25
    im = Image.open(path).convert('RGB')
    px = im.load()
    hits = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            r, g, b = px[x, y]
            if min(r, g, b) > 220:
                continue
            d = (b - r) if tint == 'blue' else (g - r) if tint == 'green' else (r - b)
            if d >= delta:
                hits.append((x, y, (r, g, b), d))
    print(f'PNG {im.size} rect=({x0},{y0})-({x1},{y1}) tint={tint} delta>={delta} hits={len(hits)}')
    for h in hits[:40]:
        print('  ', h)
    if hits:
        xs = [h[0] for h in hits]
        ys = [h[1] for h in hits]
        print(f'  x range {min(xs)}..{max(xs)}  y range {min(ys)}..{max(ys)}')


main()
