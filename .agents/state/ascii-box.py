# -*- coding: utf-8 -*-
"""把 PNG 的一个矩形区域渲染成 ASCII（按亮度），用于人眼判字形/结构。

用法: python .agents/state/ascii-box.py <png> <x0> <y0> <x1> <y1> [--thresh 200]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

_png = import_module('png-cardmap')

CH = ' .:-=+*#%@'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('png')
    ap.add_argument('x0', type=int)
    ap.add_argument('y0', type=int)
    ap.add_argument('x1', type=int)
    ap.add_argument('y1', type=int)
    ap.add_argument('--thresh', type=int, default=235)
    a = ap.parse_args()
    w, h, rows = _png.read_png(a.png)
    a.x1 = min(a.x1, w)
    a.y1 = min(a.y1, h)
    print('%s  x=%d..%d y=%d..%d' % (os.path.basename(a.png), a.x0, a.x1, a.y0, a.y1))
    print('     ' + ''.join(str((a.x0 + i) // 100 % 10) for i in range(a.x1 - a.x0)))
    print('     ' + ''.join(str((a.x0 + i) // 10 % 10) for i in range(a.x1 - a.x0)))
    for y in range(a.y0, a.y1):
        row = rows[y]
        line = []
        for x in range(a.x0, a.x1):
            r, g, b = row[x * 4], row[x * 4 + 1], row[x * 4 + 2]
            lum = (r * 299 + g * 587 + b * 114) // 1000
            if lum >= a.thresh:
                line.append(' ')
            else:
                idx = int((a.thresh - lum) / (a.thresh / 9.0))
                line.append(CH[min(9, max(1, 9 - idx))])
        print('%4d %s' % (y, ''.join(line)))


main()
