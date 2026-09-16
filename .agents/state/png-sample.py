#!/usr/bin/env python
"""Sample raw RGBA pixels along a column or row of a PNG (alpha included).

Usage:
  python .agents/state/png-sample.py <png> --x 8 --step 100 [--from 0] [--to 99999]
  python .agents/state/png-sample.py <png> --y 300 --x0 0 --x1 430 --step 10
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

_png = import_module('png-cardmap')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('png')
    ap.add_argument('--x', type=int)
    ap.add_argument('--y', type=int)
    ap.add_argument('--x0', type=int, default=0)
    ap.add_argument('--x1', type=int, default=10 ** 9)
    ap.add_argument('--step', type=int, default=25)
    ap.add_argument('--frm', type=int, default=0)
    ap.add_argument('--to', type=int, default=10 ** 9)
    args = ap.parse_args()
    w, h, rows = _png.read_png(args.png)
    print('PNG %dx%d' % (w, h))
    if args.x is not None:
        y = args.frm
        while y < min(args.to, h):
            px = rows[y][args.x * 4:args.x * 4 + 4]
            print('y=%-5d %s a=%d' % (y, '#%02X%02X%02X' % tuple(px[:3]), px[3]))
            y += args.step
    else:
        x = args.x0
        while x < min(args.x1, w):
            px = rows[args.y][x * 4:x * 4 + 4]
            print('x=%-5d %s a=%d' % (x, '#%02X%02X%02X' % tuple(px[:3]), px[3]))
            x += args.step


if __name__ == '__main__':
    main()
