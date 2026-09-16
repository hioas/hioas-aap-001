#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对比两张 PNG 的 text-rows.py 输出（设计 vs 实现），逐行报「完全相同 / 起点差」。

用法: python .agents/state/cmp-textrows.py <design.txt> <impl.txt>
"""
import io
import re
import sys


def parse(path):
    rows = []
    for ln in io.open(path, encoding="utf-8"):
        m = re.match(r"\s*text (\d+)\.\.(\d+)", ln)
        if m:
            rows.append((int(m.group(1)), int(m.group(2))))
    return rows


d = parse(sys.argv[1])
i = parse(sys.argv[2])
print("design rows", len(d), "impl rows", len(i))
zero = 0
diffs = []
for a, b in zip(d, i):
    if b[0] - a[0] == 0 and b[1] == a[1]:
        zero += 1
    else:
        diffs.append((a, b, b[0] - a[0]))
print("完全相同的行: %d / %d" % (zero, len(d)))
for a, b, dd in diffs:
    print("  设计 %s 实现 %s 起点差 %+d" % (a, b, dd))
