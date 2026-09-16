"""scan-row.py — 打印某一行（或 y 带内逐列众数）的颜色连续段，用于定位边框/胶囊/角标边界。

用法: python .agents/state/scan-row.py <png> <y> <x0> <x1> [tol]
"""
import sys
from collections import Counter

from PIL import Image

path, y, x0, x1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
tol = int(sys.argv[5]) if len(sys.argv) > 5 else 10
im = Image.open(path).convert('RGB')
px = im.load()
W, H = im.size
x1 = min(x1, W)


def close(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= tol


segs = []
cur = px[x0, y]
start = x0
for x in range(x0 + 1, x1):
    p = px[x, y]
    if not close(p, cur):
        segs.append((start, x - 1, cur))
        cur = p
        start = x
segs.append((start, x1 - 1, cur))
print('row y=%d x=%d..%d tol=%d segs=%d' % (y, x0, x1, tol, len(segs)))
for a, b, c in segs:
    print('  x=%d..%d w=%d rgb%s' % (a, b, b - a + 1, str(c)))
