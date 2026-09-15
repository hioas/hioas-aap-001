#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""沿列/行找「白色卡片带」/「页面底色带」，用阈值而非精确同色（设计截图常有抗锯齿模糊）。

用法:
  python .agents/state/white-runs.py <png> v <x> [--white] [--from Y] [--to Y] [--th 252]
  python .agents/state/white-runs.py <png> h <y> [--white] [--from X] [--to X] [--th 252]

--white（默认）: 打印像素 >= 阈值（纯白卡片底）的连续段
--bg          : 打印像素 <= 阈值-1（更暗：页面底色/描边/文字）的连续段
每段打印 (start..end len) 与段首末颜色，便于反推盒子边界（精确到 1px）。
"""
import sys

from PIL import Image


def runs(vals, pred):
    out = []
    cur = None
    for i, v in enumerate(vals):
        if pred(v):
            if cur is None:
                cur = [i, i]
            else:
                cur[1] = i
        else:
            if cur is not None:
                out.append(tuple(cur))
                cur = None
    if cur is not None:
        out.append(tuple(cur))
    return out


def main():
    path = sys.argv[1]
    axis = sys.argv[2]
    idx = int(sys.argv[3])
    white = '--bg' not in sys.argv
    th = 252
    if '--th' in sys.argv:
        th = int(sys.argv[sys.argv.index('--th') + 1])
    lo, hi = 0, None
    if '--from' in sys.argv:
        lo = int(sys.argv[sys.argv.index('--from') + 1])
    if '--to' in sys.argv:
        hi = int(sys.argv[sys.argv.index('--to') + 1])

    im = Image.open(path).convert('RGB')
    W, H = im.size
    px = im.load()
    if axis == 'v':
        n = H
        vals = [px[idx, y] for y in range(H)]
    else:
        n = W
        vals = [px[x, idx] for x in range(W)]
    hi = n if hi is None else min(hi, n)

    def pred(c):
        m = min(c)
        return m >= th if white else m < th

    segs = [s for s in runs(vals, pred) if s[0] >= lo and s[1] < hi]
    print(f'PNG {W}x{H} axis={axis} idx={idx} mode={"white>=%d" % th if white else "dark<%d" % th}')
    for a, b in segs:
        print(f'  {a}..{b} len={b - a + 1}  first={vals[a]} last={vals[b]}')


main()
