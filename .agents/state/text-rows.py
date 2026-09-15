#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按行统计「深色墨迹像素数」—— 一把列出整页所有文本行的 y 区间（设计截图对账用）。

用法: python .agents/state/text-rows.py <png> <x0> <x1> [thresh] [minCount] [from] [to]
"""
import sys

from PIL import Image


def main():
    path, x0, x1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    th = int(sys.argv[4]) if len(sys.argv) > 4 else 190
    min_count = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    lo = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    hi = int(sys.argv[7]) if len(sys.argv) > 7 else 10 ** 6
    im = Image.open(path).convert('RGB')
    px = im.load()
    W, H = im.size
    rows = []
    for y in range(H):
        c = 0
        for x in range(x0, min(x1, W)):
            p = px[x, y]
            if min(p) < th:
                c += 1
        rows.append(c)
    segs = []
    cur = None
    for y, c in enumerate(rows):
        if c >= min_count:
            if cur is None:
                cur = [y, y]
            else:
                cur[1] = y
        else:
            if cur is not None:
                segs.append((cur[0], cur[1], max(rows[cur[0]:cur[1] + 1])))
                cur = None
    if cur is not None:
        segs.append((cur[0], cur[1], max(rows[cur[0]:cur[1] + 1])))
    print(f'PNG {W}x{H} x[{x0},{x1}) thresh<{th} minCount={min_count}')
    for a, b, m in segs:
        if b < lo or a > hi:
            continue
        print(f'  text {a}..{b} h={b - a + 1} maxDark={m}')


main()
