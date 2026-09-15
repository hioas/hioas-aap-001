#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按行列出墨迹（非白/非页面底色）的 x 区间 —— 一次拿到行内每个文本/图标的横向位置与宽度。

用法: python .agents/state/ink-x.py <png> <y> [x0] [x1] [thresh] [gap]
  thresh: 判定为墨迹的亮度上限（默认 235，覆盖浅灰文案）
  gap:    合并相邻墨迹段的空隙上限（默认 4，字符间距）
"""
import sys

from PIL import Image


def main():
    path = sys.argv[1]
    y = int(sys.argv[2])
    x0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    x1 = int(sys.argv[4]) if len(sys.argv) > 4 else None
    thresh = int(sys.argv[5]) if len(sys.argv) > 5 else 235
    gap = int(sys.argv[6]) if len(sys.argv) > 6 else 4
    im = Image.open(path).convert('RGB')
    w, h = im.size
    x1 = x1 if x1 is not None else w
    px = im.load()
    runs = []
    for x in range(x0, x1):
        r, g, b = px[x, y]
        if min(r, g, b) < thresh:
            if runs and x - runs[-1][1] <= gap:
                runs[-1][1] = x
            else:
                runs.append([x, x])
    print(f'PNG {w}x{h} row y={y} x={x0}..{x1} thresh<{thresh} gap<={gap}')
    for a, b in runs:
        print(f'  x {a}..{b}  w={b - a + 1}')


if __name__ == '__main__':
    main()
