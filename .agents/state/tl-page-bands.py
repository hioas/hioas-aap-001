# -*- coding: utf-8 -*-
"""设计 PNG vs 实现 PNG 的分区行墨迹带并排对账（一页多窗口）。

用法:
  python .agents/state/tl-page-bands.py <design.png> <impl.png> [--x0 30] [--x1 410] [--tol 2]

窗口由内置 REGIONS 给出（page-26 / 序号 12-v1 用）。
对每个窗口打印两图的 band 起点列表，并统计「设计起点在实现里 ±tol 内命中」的比例。
"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

_png = import_module('png-cardmap')

REGIONS = [
    ('nav 顶部栏', 0, 110),
    ('step-card 步骤卡', 110, 200),
    ('card1 基本信息 头', 200, 250),
    ('card1 字段 1 标签/框', 250, 350),
    ('card1 单号字段', 360, 500),
    ('card1 凭证字段', 500, 570),
    ('card1 提示行 blue', 570, 620),
    ('card2 模型列表卡', 620, 700),
    ('card2 空态', 700, 830),
    ('card2 提示条', 830, 940),
    ('notice 须知卡', 940, 1110),
    ('bar 底部操作条', 1110, 1241),
]


def bands(png, x0, x1, y0, y1, minink=2):
    w, h, rows = png
    x0, x1 = max(0, int(x0)), min(w, int(x1))
    y0, y1 = max(0, int(y0)), min(h, int(y1))
    out = []
    cur = None
    for y in range(y0, y1):
        row = rows[y]
        c = Counter()
        for x in range(x0, x1):
            c[(row[x * 4], row[x * 4 + 1], row[x * 4 + 2])] += 1
        _, n = c.most_common(1)[0]
        ink = (x1 - x0) - n
        if ink >= minink:
            if cur is None:
                cur = [y, y, ink]
            else:
                cur[1] = y
                cur[2] = max(cur[2], ink)
        else:
            if cur is not None:
                out.append(tuple(cur))
                cur = None
    if cur is not None:
        out.append(tuple(cur))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('design')
    ap.add_argument('impl')
    ap.add_argument('--x0', type=int, default=30)
    ap.add_argument('--x1', type=int, default=410)
    ap.add_argument('--tol', type=int, default=2)
    ap.add_argument('--minink', type=int, default=2)
    args = ap.parse_args()
    des = _png.read_png(args.design)
    imp = _png.read_png(args.impl)
    print('design %dx%d   impl %dx%d   x=%d..%d  minink=%d  tol=%d'
          % (des[0], des[1], imp[0], imp[1], args.x0, args.x1, args.minink, args.tol))
    tot = hit = 0
    for name, y0, y1 in REGIONS:
        db = bands(des, args.x0, args.x1, y0, y1, args.minink)
        ib = bands(imp, args.x0, args.x1, y0, y1, args.minink)
        istarts = [b[0] for b in ib]
        marks = []
        for b in db:
            ok = any(abs(b[0] - s) <= args.tol for s in istarts)
            tot += 1
            hit += 1 if ok else 0
            marks.append('%d%s' % (b[0], '' if ok else '!!'))
        print('\n== %-22s y=%d..%d   命中 %d/%d' % (name, y0, y1, sum(1 for m in marks if not m.endswith('!!')), len(db)))
        print('   design starts: %s' % ' '.join(marks))
        print('   impl   starts: %s' % ' '.join(str(s) for s in istarts))
        if any(m.endswith('!!') for m in marks):
            miss = [int(m[:-2]) for m in marks if m.endswith('!!')]
            print('   未命中设计起点: %s' % miss)
            print('     design bands: %s' % ' | '.join('%d..%d' % (b[0], b[1]) for b in db))
            print('     impl   bands: %s' % ' | '.join('%d..%d' % (b[0], b[1]) for b in ib))
    print('\n合计命中 %d/%d' % (hit, tot))


main()
