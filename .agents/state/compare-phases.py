# -*- coding: utf-8 -*-
"""比较 measure JSON 里两个 phase 的关键字段是否全等（「连跑两轮一致」的 H5 版本）。

用法: python .agents/state/compare-phases.py <measure.json> [phaseA] [phaseB]
"""
import io
import json
import sys

path = sys.argv[1]
a = sys.argv[2] if len(sys.argv) > 2 else "phase1"
b = sys.argv[3] if len(sys.argv) > 3 else "phase2"
data = json.load(io.open(path, encoding="utf-8"))
pa, pb = data.get(a, {}), data.get(b, {})

keys = sorted(set(pa.keys()) | set(pb.keys()))
keys = [k for k in keys if k not in ("userAgent",)]
diff = []
for k in keys:
    if pa.get(k) != pb.get(k):
        diff.append((k, pa.get(k), pb.get(k)))

print("%s vs %s : 比较 %d 个字段" % (a, b, len(keys)))
if diff:
    for k, va, vb in diff:
        print("  DIFF %-22s\n    %s\n    %s" % (k, json.dumps(va, ensure_ascii=False)[:180], json.dumps(vb, ensure_ascii=False)[:180]))
    print("结论：不一致 %d 个字段" % len(diff))
    sys.exit(1)
print("结论：全部相等 —— 两段测量一致（布局稳定，无轮询/异步抖动）")
