# -*- coding: utf-8 -*-
"""按台账「状态」列列出尚未标 已验证 的行（队列 8 取件用）。"""
import csv
from pathlib import Path

LEDGER = Path("E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-feature-status.csv")
with LEDGER.open(encoding="utf-8", newline="") as fh:
    rows = list(csv.reader(fh))
for r in rows[1:]:
    if len(r) > 9 and r[9] != "已验证":
        print("%-7s %-14s %-34s %-28s %s" % (r[0], r[1], r[2][:32], r[4], r[9]))
