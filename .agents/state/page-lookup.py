#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按关键字在 .calicat/raw/pages.json 里查页面，打印其 id / 图层 id / 名称。

用法: python .agents/state/page-lookup.py "提交接入凭证"
"""
import io, json, sys

pat = sys.argv[1] if len(sys.argv) > 1 else ""

with io.open(".calicat/raw/pages.json", encoding="utf-8") as f:
    d = json.load(f)

print("top-level type:", type(d).__name__)
if isinstance(d, dict):
    print("keys:", list(d.keys())[:30])

rows = []
def walk(o):
    if isinstance(o, dict):
        s = json.dumps(o, ensure_ascii=False)
        if pat and pat in s and any(k in o for k in ("id", "layer_id", "name", "title")):
            rows.append(o)
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
walk(d)

seen = set()
for r in rows:
    s = json.dumps(r, ensure_ascii=False)
    if s in seen:
        continue
    seen.add(s)
    print("---")
    print(s[:600])
