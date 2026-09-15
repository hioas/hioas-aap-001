# -*- coding: utf-8 -*-
"""打印 PNG 宽高（无第三方依赖）。

用法: python .agents/state/png-size.py <a.png> [b.png ...]
"""
import struct
import sys

for path in sys.argv[1:]:
    with open(path, "rb") as fh:
        head = fh.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        print("%s NOT_PNG" % path)
        continue
    w, h = struct.unpack(">II", head[16:24])
    print("%s %dx%d" % (path, w, h))
