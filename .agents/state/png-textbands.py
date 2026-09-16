#!/usr/bin/env python
"""Row ink bands of a design/impl PNG box: which rows carry ink and how they group.

Usage:
  python .agents/state/png-textbands.py <png> <x0> <y0> <x1> <y1> [--minink 2] [--gap 1]
                                          [--dominant auto|RRGGBB]

Prints one line per contiguous band of rows whose ink count (pixels differing from the box's
modal colour) is >= minink: `<y0>..<y1> len=N ink=<max ink in band>`. A blank line separates
bands that are more than `--gap` rows apart, so item rows and the spacing between them are both
visible as numbers (this is the tool for reading fit_content row heights / row spacing).
"""
import argparse
from collections import Counter

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

_png = import_module('png-cardmap')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('png')
    ap.add_argument('x0', type=int)
    ap.add_argument('y0', type=int)
    ap.add_argument('x1', type=int)
    ap.add_argument('y1', type=int)
    ap.add_argument('--minink', type=int, default=2)
    ap.add_argument('--gap', type=int, default=1)
    args = ap.parse_args()
    w, h, rows = _png.read_png(args.png)
    x0, x1 = max(0, args.x0), min(w, args.x1)
    y0, y1 = max(0, args.y0), min(h, args.y1)
    counts = []
    modal = Counter()
    for y in range(y0, y1):
        row = rows[y]
        c = Counter()
        for x in range(x0, x1):
            c[(row[x * 4], row[x * 4 + 1], row[x * 4 + 2])] += 1
        top, n = c.most_common(1)[0]
        modal[top] += n
        counts.append((y, len(range(x1 - x0)) - n, top))
    print('PNG %dx%d box x=%d..%d y=%d..%d modal=%s' % (w, h, x0, x1, y0, y1, modal.most_common(1)[0][0]))
    band = []
    last_ink = None
    for y, ink, _top in counts:
        if ink >= args.minink:
            if band and last_ink is not None and y - last_ink > args.gap + 1:
                flush(band)
                band = []
            band.append((y, ink))
            last_ink = y
        else:
            last_ink = last_ink if last_ink is not None else None
    if band:
        flush(band)


def flush(band):
    print('%5d..%-5d len=%-4d maxink=%d' % (band[0][0], band[-1][0], band[-1][0] - band[0][0] + 1,
                                            max(i for _y, i in band)))


if __name__ == '__main__':
    main()
