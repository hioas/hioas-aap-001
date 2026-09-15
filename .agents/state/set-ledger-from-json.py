#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按序号回写台账行，字段值从 JSON 文件读（避免 bash 里中文/逗号/$ 的引号地狱）。

用法：
    python .agents/state/set-ledger-from-json.py 4-v1 .agents/state/ledger-4v1.json
"""
import csv
import json
import sys
from pathlib import Path

path = Path(".agents/state/aap-feature-status.csv")
target = sys.argv[1]
fields = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
hit = 0
for r in rows:
    if r["序号"] == target:
        for k, v in fields.items():
            if k not in r:
                raise SystemExit(f"字段不存在: {k}（可选: {list(r.keys())}）")
            r[k] = v
        hit += 1

if not hit:
    raise SystemExit(f"台账里没有序号 {target}")

with path.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"更新 {hit} 行 · 序号 {target}")
for k, v in fields.items():
    print(f"  {k} = {v[:100]}{'…' if len(v) > 100 else ''}")
