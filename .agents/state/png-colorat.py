# -*- coding: utf-8 -*-
"""在某一行/列上找「接近指定颜色」的连续区间（判元素横向/纵向边界）。

用法: python .agents/state/png-colorat.py <png> h <y> <rrggbb> [tol=6] [minLen=2]
      python .agents/state/png-colorat.py <png> v <x> <rrggbb> [tol=6] [minLen=2]
"""
import importlib.util
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('pngcm', os.path.join(here, 'png-cardmap.py'))
pngcm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pngcm)

path, axis, idx, hexs = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
tol = int(sys.argv[5]) if len(sys.argv) > 5 else 6
minlen = int(sys.argv[6]) if len(sys.argv) > 6 else 2
want = tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))

w, h, px = pngcm.read_png(path)
n = w if axis == 'h' else h
runs = []
start = None
for i in range(n):
    p = px[idx][i * 4:i * 4 + 3] if axis == 'h' else px[i][idx * 4:idx * 4 + 3]
    ok = all(abs(p[c] - want[c]) <= tol for c in range(3))
    if ok and start is None:
        start = i
    elif not ok and start is not None:
        runs.append((start, i - 1))
        start = None
if start is not None:
    runs.append((start, n - 1))
print('PNG %dx%d axis=%s idx=%d want=#%s tol=%d' % (w, h, axis, idx, hexs.upper(), tol))
for a, b in runs:
    if b - a + 1 >= minlen:
        print('  %4d..%4d  len=%-4d' % (a, b, b - a + 1))
