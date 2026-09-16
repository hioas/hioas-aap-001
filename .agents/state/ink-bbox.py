"""ink-bbox.py — 打印若干矩形区域内的「非背景墨迹」包围盒（设计 PNG 量尺用）。

用法: python .agents/state/ink-bbox.py <png> <x0,y0,x1,y1> [<x0,y0,x1,y1> ...]
每个区域打印：区域、墨迹 bbox（含宽高）、墨迹像素数。背景色 = 该区域内出现最多的颜色。
"""
import sys
from collections import Counter

from PIL import Image

im = Image.open(sys.argv[1]).convert('RGB')
px = im.load()
W, H = im.size
print('image', W, 'x', H)

for spec in sys.argv[2:]:
    x0, y0, x1, y1 = [int(v) for v in spec.split(',')]
    bg = Counter()
    for y in range(y0, min(y1, H)):
        for x in range(x0, min(x1, W)):
            bg[px[x, y]] += 1
    bgc = bg.most_common(1)[0][0]
    minx, miny, maxx, maxy, n = 10 ** 6, 10 ** 6, -1, -1, 0
    for y in range(y0, min(y1, H)):
        for x in range(x0, min(x1, W)):
            p = px[x, y]
            if abs(p[0] - bgc[0]) + abs(p[1] - bgc[1]) + abs(p[2] - bgc[2]) > 30:
                n += 1
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    if n == 0:
        print('%-22s bbox=NONE bg=%s' % (spec, bgc))
    else:
        print('%-22s bg=%-16s bbox x=%d..%d y=%d..%d  w=%d h=%d  cx=%.1f cy=%.1f  ink=%d'
              % (spec, str(bgc), minx, maxx, miny, maxy, maxx - minx + 1, maxy - miny + 1,
                 (minx + maxx) / 2, (miny + maxy) / 2, n))
