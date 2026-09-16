# -*- coding: utf-8 -*-
"""打印 design.tree.json / design.json 的顶层结构（类型 + 片段）。"""
import io
import json
import os
import sys

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
rel = sys.argv[1] if len(sys.argv) > 1 else ".calicat/raw/pages/page-12-2/design.tree.json"
p = os.path.join(ROOT, rel)
data = json.load(io.open(p, encoding="utf-8"))
print("type:", type(data).__name__)
if isinstance(data, dict):
    for k, v in data.items():
        print("  key=%-16s type=%s len=%s" % (k, type(v).__name__, (len(v) if hasattr(v, "__len__") else "-")))
        print("     ", json.dumps(v, ensure_ascii=False)[:300])
elif isinstance(data, list):
    print("len:", len(data))
    print(json.dumps(data[0], ensure_ascii=False)[:600])
    print("---- second ----")
    print(json.dumps(data[1], ensure_ascii=False)[:300])
