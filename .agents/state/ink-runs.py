"""ink-runs.py — 在给定 y 带内（按列取并集）打印 x 方向的墨迹连续段（设计 PNG 量尺用）。

用法: python .agents/state/ink-runs.py <png> <x0> <x1> <y0> <y1> [bgTol] [minInk]
背景色取该带内出现最多的颜色；墨迹 = 与背景色曼哈顿距离 > bgTol 的像素。
"""
import sys
from collections import Counter

from PIL import Image

path, x0, x1, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
tol = int(sys.argv[6]) if len(sys.argv) > 6 else 30
min_ink = int(sys.argv[7]) if len(sys.argv) > 7 else 1

im = Image.open(path).convert('RGB')
px = im.load()
W, H = im.size
x1 = min(x1, W); y1 = min(y1, H)
bg = Counter()
for y in range(y0, y1):
    for x in range(x0, x1):
        bg[px[x, y]] += 1
bgc = bg.most_common(1)[0][0]

cols = []
for x in range(x0, x1):
    c = 0
    for y in range(y0, y1):
        p = px[x, y]
        if abs(p[0] - bgc[0]) + abs(p[1] - bgc[1]) + abs(p[2] - bgc[2]) > tol:
            c += 1
    cols.append(c)

segs = []
start = None
for i, c in enumerate(cols):
    if c >= min_ink and start is None:
        start = i
    elif c < min_ink and start is not None:
        segs.append((x0 + start, x0 + i - 1))
        start = None
if start is not None:
    segs.append((x0 + start, x0 + len(cols) - 1))

print('band y=%d..%d bg=%s runs=%d' % (y0, y1, str(bgc), len(segs)))
for a, b in segs:
    print('  x=%d..%d w=%d' % (a, b, b - a + 1))
