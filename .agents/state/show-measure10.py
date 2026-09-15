# -*- coding: utf-8 -*-
"""按 phase + 字段名取数（cmp 模式：逐字段比较两个 phase，做「连跑两轮一致」的 H5 版本）。

用法:
  python .agents/state/show-measure10.py <measure.json> <phase> [字段名...]
  python .agents/state/show-measure10.py <measure.json> cmp <phaseA> <phaseB> [字段名...]
"""
import io
import json
import sys

d = json.load(io.open(sys.argv[1], encoding="utf-8"))
mode = sys.argv[2]

if mode == "cmp":
    a, b = sys.argv[3], sys.argv[4]
    keys = sys.argv[5:] or sorted(set(d[a]) & set(d[b]))
    same, diff = [], []
    for k in keys:
        if k in ("userAgent",):
            continue
        if d[a][k] == d[b][k]:
            same.append(k)
        else:
            diff.append((k, d[a][k], d[b][k]))
    print("全等字段 %d 个: %s" % (len(same), ", ".join(same)))
    print("不一致字段 %d 个:" % len(diff))
    for k, x, y in diff:
        print("  %s: %s  !=  %s" % (k, json.dumps(x, ensure_ascii=False)[:160], json.dumps(y, ensure_ascii=False)[:160]))
    sys.exit(0)

ph = d[mode]
keys = sys.argv[3:] or list(ph.keys())
for k in keys:
    print("%s = %s" % (k, json.dumps(ph.get(k, "<MISSING>"), ensure_ascii=False)))
