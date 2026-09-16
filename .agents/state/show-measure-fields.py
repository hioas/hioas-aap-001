#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""并排打印两份测量 JSON 中指定 phase 的若干字段（复核定位用）。

用法: python .agents/state/show-measure-fields.py <a.json> <b.json> <phase> <k1> [k2 ...]
"""
import io
import json
import sys

a = json.load(io.open(sys.argv[1], encoding="utf-8"))
b = json.load(io.open(sys.argv[2], encoding="utf-8"))
ph = sys.argv[3]
keys = sys.argv[4:]
ka, kb = a.get(ph, a), b.get(ph, b)
for k in keys:
    print("### %s" % k)
    print("  A(%s) = %s" % (sys.argv[1].split("/")[-1], json.dumps(ka.get(k, "<MISSING>"), ensure_ascii=False)))
    print("  B(%s) = %s" % (sys.argv[2].split("/")[-1], json.dumps(kb.get(k, "<MISSING>"), ensure_ascii=False)))
