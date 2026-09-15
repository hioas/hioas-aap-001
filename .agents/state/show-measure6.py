# -*- coding: utf-8 -*-
"""打印 measure JSON 的关键字段（page-6）。用法: python .agents/state/show-measure6.py <file.json> [phase]"""
import io
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else ".agents/state/evidence/measure-序号6-430宽.json"
phase = sys.argv[2] if len(sys.argv) > 2 else "phase2"
data = json.load(io.open(path, encoding="utf-8"))
p = data.get(phase, data)
keys = sys.argv[3:] if len(sys.argv) > 3 else None
for k, v in p.items():
    if keys and k not in keys:
        continue
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False)
        print("%-22s = %s" % (k, s if len(s) < 900 else s[:900] + u" …(%d)" % len(s)))
    else:
        print("%-22s = %r" % (k, v))
print("--- phases:", sorted(data.keys()))
