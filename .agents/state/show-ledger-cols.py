# -*- coding: utf-8 -*-
"""打印台账某行的各列下标与内容（写回写脚本前核对列位）。"""
import csv
from pathlib import Path

LEDGER = Path("E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-feature-status.csv")
with LEDGER.open(encoding="utf-8", newline="") as fh:
    rows = list(csv.reader(fh))
print("HEADER:", list(enumerate(rows[0])))
for r in rows:
    if r and r[0] == "12-v2":
        for i, c in enumerate(r):
            print(i, "|", (c[:160] + ("…(%d)" % len(c) if len(c) > 160 else "")))
