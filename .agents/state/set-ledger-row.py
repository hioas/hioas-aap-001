"""按序号回写台账行（csv 安全）。

用法: python .agents/state/set-ledger-row.py <序号> <字段>=<值> [<字段>=<值> ...]
"""
import csv
import sys
from pathlib import Path

path = Path(".agents/state/aap-feature-status.csv")
rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
fields = [f.split("=", 1) for f in sys.argv[2:]]
target = sys.argv[1]

hit = 0
for r in rows:
    if r["序号"] == target:
        for k, v in fields:
            if k not in r:
                raise SystemExit(f"字段不存在: {k}（可选: {list(r.keys())}）")
            r[k] = v
        hit += 1

with path.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"更新 {hit} 行 · 序号 {target}")
for k, v in fields:
    print(f"  {k} = {v[:120]}")
