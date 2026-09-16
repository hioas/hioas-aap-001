# -*- coding: utf-8 -*-
"""逐行统计「接近网格色」的像素数（容忍 AA），用于定死 4 条网格线的 y 行。

用法: python .agents/state/grid-rows-22.py <design.png> <impl.png> [y0 y1] [mincount]
"""
import os
import sys
from importlib import import_module

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
png = import_module('png-cardmap')

design, impl = sys.argv[1], sys.argv[2]
y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 415
y1 = int(sys.argv[4]) if len(sys.argv) > 4 else 540
minc = int(sys.argv[5]) if len(sys.argv) > 5 else 60
COLORS = [(241, 245, 249), (226, 232, 240)]


def rowcount(path, y, x0=40, x1=400, tol=8):
    w, h, rows = png.read_png(path)
    row = rows[y]
    n = 0
    for x in range(x0, min(x1, w)):
        px = (row[x * 4], row[x * 4 + 1], row[x * 4 + 2])
        if any(all(abs(a - b) <= tol for a, b in zip(px, c)) for c in COLORS):
            n += 1
    return n


for label, path in (('DESIGN', design), ('IMPL', impl)):
    print('=== %s' % label)
    for y in range(y0, y1):
        n = rowcount(path, y)
        if n >= minc:
            print('  y=%d n=%d' % (y, n))
