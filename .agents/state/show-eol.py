#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打印文件行尾统计（CRLF / LF / CR 各多少），用于回写前判断行尾风格。

用法: python .agents/state/show-eol.py <文件> [<文件> ...]
"""
import sys

for p in sys.argv[1:]:
    with open(p, "rb") as fh:
        d = fh.read()
    print("%s: bytes=%d CRLF=%d LF=%d CR=%d" % (p, len(d), d.count(b"\r\n"), d.count(b"\n"), d.count(b"\r")))
