# -*- coding: utf-8 -*-
"""比较两次独立测量的同一 phase（H5 版「连跑两轮一致」）。

用法: python .agents/state/cmp-measure-runs.py <a.json> <b.json> <phase>
"""
import io
import json
import sys

a = json.load(io.open(sys.argv[1], encoding="utf-8"))
b = json.load(io.open(sys.argv[2], encoding="utf-8"))
ph = sys.argv[3]

ka, kb = a[ph], b[ph]
keys = sorted(set(ka) | set(kb))
same, diff = [], []
for k in keys:
    if k in ("userAgent", "iframeHeightForShot"):
        continue
    x, y = ka.get(k, "<MISSING>"), kb.get(k, "<MISSING>")
    (same if x == y else diff).append(k if x == y else (k, x, y))

print("phase=%s · 全等字段 %d 个" % (ph, len(same)))
print("全等: %s" % ", ".join(same))
print("不一致 %d 个:" % len(diff))
for item in diff:
    if isinstance(item, tuple):
        k, x, y = item
        print("  %s:\n    A=%s\n    B=%s" % (k, json.dumps(x, ensure_ascii=False)[:200], json.dumps(y, ensure_ascii=False)[:200]))
    else:
        print("  %s" % item)
