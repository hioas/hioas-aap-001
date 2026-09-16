#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Print raw lines of a dumped DOM around a keyword (for probing uni-app H5 rendered markup).

Usage: dom-around.py <dumped.html> <keyword> [before] [after] [maxHits]
"""
import io
import sys

path = sys.argv[1]
kw = sys.argv[2]
before = int(sys.argv[3]) if len(sys.argv) > 3 else 2
after = int(sys.argv[4]) if len(sys.argv) > 4 else 6
maxhits = int(sys.argv[5]) if len(sys.argv) > 5 else 3

lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
hits = 0
for i, line in enumerate(lines):
    if kw in line:
        hits += 1
        if hits > maxhits:
            break
        print("---- hit %d at line %d" % (hits, i + 1))
        for j in range(max(0, i - before), min(len(lines), i + after)):
            print("%5d| %s" % (j + 1, lines[j][:400]))
