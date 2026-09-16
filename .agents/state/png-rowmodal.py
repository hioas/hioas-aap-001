# -*- coding: utf-8 -*-
"""逐行打印 x 区间内的主色与「等于白色的像素占比」——判卡片行/间隙行的辅助工具。

用法: python .agents/state/png-rowmodal.py <png> [--x0 40] [--x1 400] [--from 0] [--to 1211] [--step 1]
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

spec = importlib.util.spec_from_file_location(
    'pngcm', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'png-cardmap.py'))
pngcm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pngcm)

ap = argparse.ArgumentParser()
ap.add_argument('png')
ap.add_argument('--x0', type=int, default=40)
ap.add_argument('--x1', type=int, default=400)
ap.add_argument('--from', dest='frm', type=int, default=0)
ap.add_argument('--to', type=int, default=0)
ap.add_argument('--step', type=int, default=1)
ap.add_argument('--runs', action='store_true')
a = ap.parse_args()
last_kind = None
start = 0

w, h, px = pngcm.read_png(a.png)
if not a.to:
    a.to = h

for y in range(a.frm, min(a.to, h), a.step):
    row = [tuple(px[y][x * 4:x * 4 + 4]) for x in range(a.x0, min(a.x1, w))]
    cnt = collections.Counter([tuple(p[:3]) for p in row])
    modal, mc = cnt.most_common(1)[0]
    white = cnt.get((255, 255, 255), 0)
    if a.runs:
        kind = 'CARD' if modal == (255, 255, 255) else 'gap'
        if last_kind is None or kind != last_kind:
            if last_kind is not None:
                print('%-4s %4d..%4d  len=%d' % (last_kind, start, y - 1, y - start))
            last_kind, start = kind, y
        continue
    print('y=%-5d modal=#%02X%02X%02X %5.2f  white %5.2f  uniq=%d' % (
        y, modal[0], modal[1], modal[2], mc / len(row), white / len(row), len(cnt)))
if a.runs and last_kind is not None:
    print('%-4s %4d..%4d  len=%d' % (last_kind, start, min(a.to, h) - 1, min(a.to, h) - start))
