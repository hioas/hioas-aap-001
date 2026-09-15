#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打印某列/行在指定区间内每个像素的 RGB —— 用于看清边界过渡（设计截图有抗锯齿模糊）。

用法: python .agents/state/pxdump.py <png> v|h <idx> <from> <to> [step]
"""
import sys

from PIL import Image


def main():
    path, axis, idx, lo, hi = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    step = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    im = Image.open(path).convert('RGB')
    px = im.load()
    for i in range(lo, hi + 1, step):
        c = px[idx, i] if axis == 'v' else px[i, idx]
        mark = ''
        if min(c) >= 254:
            mark = 'CARD'
        elif abs(c[0] - 248) <= 3 and abs(c[2] - 252) <= 3:
            mark = 'PAGEBG'
        print(f'{i:5d} {c} {mark}')


main()
