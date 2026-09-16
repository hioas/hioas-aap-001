"""scan-col.py — 打印某一列（或 x 带内逐行众数）的颜色连续段，用于定位卡片/盒子的上下边界。

用法: python .agents/state/scan-col.py <png> <x> <y0> <y1> [tol]
"""
import sys

from PIL import Image

path, x, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
tol = int(sys.argv[5]) if len(sys.argv) > 5 else 6
im = Image.open(path).convert('RGB')
px = im.load()
W, H = im.size
y1 = min(y1, H)


def close(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= tol


segs = []
cur = px[x, y0]
start = y0
for y in range(y0 + 1, y1):
    p = px[x, y]
    if not close(p, cur):
        segs.append((start, y - 1, cur))
        cur = p
        start = y
segs.append((start, y1 - 1, cur))
print('col x=%d y=%d..%d tol=%d segs=%d' % (x, y0, y1, tol, len(segs)))
for a, b, c in segs:
    if b - a + 1 >= 2:
        print('  y=%d..%d h=%d rgb%s' % (a, b, b - a + 1, str(c)))
