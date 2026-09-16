# -*- coding: utf-8 -*-
"""打印测量 JSON 某 phase 的 checkFails（兼容扁平/多相两种结构，字段名容错）。"""
import io
import json
import sys

path = sys.argv[1]
phase = sys.argv[2] if len(sys.argv) > 2 else None

d = json.load(io.open(path, encoding="utf-8"))
p = d.get(phase) if phase else d
if not isinstance(p, dict):
    p = d
fails = p.get("checkFails") or p.get("fails") or []
print("checkCount =", p.get("checkCount"), "checkFailCount =", p.get("checkFailCount"), "printed =", len(fails))
for f in fails[:40]:
    if isinstance(f, dict):
        print("  FAIL %s: got %s want %s" % (f.get("k") or f.get("key"), f.get("got"), f.get("want")))
    else:
        print("  FAIL", f)
