# -*- coding: utf-8 -*-
"""找出「接近某色」的横向长条所在行（判卡片描边上下边 / 分隔线）。

用法: python .agents/state/stroke-rows.py <png> <rrggbb> [tol] [mincount] [x0] [x1] [y0] [y1]
"""
import importlib.util
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('pngcm', os.path.join(here, 'png-cardmap.py'))
pngcm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pngcm)

path = sys.argv[1]
want = tuple(int(sys.argv[2][i:i + 2], 16) for i in (0, 2, 4))
tol = int(sys.argv[3]) if len(sys.argv) > 3 else 5
mincount = int(sys.argv[4]) if len(sys.argv) > 4 else 100
x0 = int(sys.argv[5]) if len(sys.argv) > 5 else 20
x1 = int(sys.argv[6]) if len(sys.argv) > 6 else 410
y0 = int(sys.argv[7]) if len(sys.argv) > 7 else 0
y1 = int(sys.argv[8]) if len(sys.argv) > 8 else 100000

w, h, px = pngcm.read_png(path)
y1 = min(y1, h)
runs = []
start = None
for y in range(y0, y1):
    cnt = 0
    for x in range(x0, min(x1, w)):
        p = px[y][x * 4:x * 4 + 3]
        if all(abs(p[c] - want[c]) <= tol for c in range(3)):
            cnt += 1
    ok = cnt >= mincount
    if ok:
        if start is None:
            start = y
        last = cnt
    elif start is not None:
        runs.append((start, y - 1))
        start = None
if start is not None:
    runs.append((start, y1 - 1))
print("PNG %dx%d want=#%s tol=%d mincount=%d x=[%d,%d)" % (w, h, sys.argv[2], tol, mincount, x0, x1))
for a, b in runs:
    print("  rows %d..%d  len=%d" % (a, b, b - a + 1))
