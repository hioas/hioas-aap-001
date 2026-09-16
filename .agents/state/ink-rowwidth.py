"""ink-rowwidth.py — 打印区域内每一行的墨迹 x 段（判断图标字形形状：圆 / 圆角矩形 / 尖底）。

用法: python .agents/state/ink-rowwidth.py <png> <x0,y0,x1,y1> [...]
"""
import sys
from collections import Counter

from PIL import Image

im = Image.open(sys.argv[1]).convert('RGB')
px = im.load()
for spec in sys.argv[2:]:
    x0, y0, x1, y1 = [int(v) for v in spec.split(',')]
    bg = Counter()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            bg[px[x, y]] += 1
    bgc = bg.most_common(1)[0][0]
    print('--- region %s bg=%s' % (spec, bgc))
    for y in range(y0, y1 + 1):
        xs = [x for x in range(x0, x1 + 1)
              if abs(px[x, y][0] - bgc[0]) + abs(px[x, y][1] - bgc[1]) + abs(px[x, y][2] - bgc[2]) > 30]
        if xs:
            segs = []
            s = xs[0]
            p = xs[0]
            for x in xs[1:]:
                if x != p + 1:
                    segs.append((s, p))
                    s = x
                p = x
            segs.append((s, p))
            print('  y=%d  %s' % (y, ' '.join('%d..%d(%d)' % (a, b, b - a + 1) for a, b in segs)))
