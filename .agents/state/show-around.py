#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打印文本文件里含某个锚的子串（默认打印锚前后各 N 字符），用于精确取「要替换的片段」。

用法: python .agents/state/show-around.py <文件> <锚> [前后字符数] [行号=1]
"""
import io
import sys

path, needle = sys.argv[1], sys.argv[2]
pad = int(sys.argv[3]) if len(sys.argv) > 3 else 200
idx = int(sys.argv[4]) if len(sys.argv) > 4 else 1

with io.open(path, encoding="utf-8", newline="") as fh:
    text = fh.read().replace("\r\n", "\n").replace("\r", "\n")
lines = text.split("\n")
line = lines[idx - 1]
pos = line.find(needle)
print("行号 %d · 行长 %d · 锚位置 %d" % (idx, len(line), pos))
if pos >= 0:
    print("---前 %d 字符---" % pad)
    print(repr(line[max(0, pos - pad):pos]))
    print("---锚及其后 %d 字符---" % pad)
    print(repr(line[pos:pos + pad]))
else:
    print("锚不存在；该行前 300 字符：")
    print(repr(line[:300]))
