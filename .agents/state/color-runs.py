#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按颜色特征沿列/行找连续色段 —— 用来从设计截图反推「标签块 / 提示块 / 卡片」的精确边界。

用法:
  python .agents/state/color-runs.py <png> v <x> [mode] [--from N] [--to N]
  python .agents/state/color-runs.py <png> h <y> [mode] [--from N] [--to N]

mode:
  white  纯白（卡片底）        min>=253
  bg     非纯白（页面底色/描边/文本）  min<253
  blue   偏蓝底（#EFF6FF 等）  B-R>=8 且 B>=240
  green  偏绿底（#ECFDF5 等）  G-R>=8 且 G>=240
  amber  偏黄底（#FFFBEB 等）  R-B>=8 且 R>=240
  gray   浅灰底（#F1F5F9 等）  245<=min 且 min<253
  ink    深色墨迹（文字/图标）  min<200
段打印 (start..end len) 与段首末颜色。
"""
import sys

from PIL import Image

MODES = {
    'white': lambda c: min(c) >= 253,
    'bg': lambda c: min(c) < 253,
    'blue': lambda c: c[2] - c[0] >= 8 and c[2] >= 240,
    'green': lambda c: c[1] - c[0] >= 8 and c[1] >= 240,
    'amber': lambda c: c[0] - c[2] >= 8 and c[0] >= 240,
    'gray': lambda c: 245 <= min(c) < 253,
    'ink': lambda c: min(c) < 200,
}


def main():
    path = sys.argv[1]
    axis = sys.argv[2]
    idx = int(sys.argv[3])
    mode = 'bg'
    for a in sys.argv[4:]:
        if a in MODES:
            mode = a
    lo, hi = 0, None
    if '--from' in sys.argv:
        lo = int(sys.argv[sys.argv.index('--from') + 1])
    if '--to' in sys.argv:
        hi = int(sys.argv[sys.argv.index('--to') + 1])

    im = Image.open(path).convert('RGB')
    W, H = im.size
    px = im.load()
    if axis == 'v':
        n, vals = H, [px[idx, y] for y in range(H)]
    else:
        n, vals = W, [px[x, idx] for x in range(W)]
    hi = n if hi is None else min(hi, n)

    pred = MODES[mode]
    segs = []
    cur = None
    for i, v in enumerate(vals):
        if pred(v):
            if cur is None:
                cur = [i, i]
            else:
                cur[1] = i
        else:
            if cur is not None:
                segs.append(tuple(cur))
                cur = None
    if cur is not None:
        segs.append(tuple(cur))

    print(f'PNG {W}x{H} axis={axis} idx={idx} mode={mode}')
    for a, b in segs:
        if a < lo or b >= hi:
            continue
        print(f'  {a}..{b} len={b - a + 1}  first={vals[a]} last={vals[b]}')


main()
