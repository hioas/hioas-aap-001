#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在台账指定序号行的「用例(证据)」/「备注」列**追加**一段文字（不覆盖原内容）。

用法:
  python .agents/state/append-ledger-note.py <序号> [--case <文本>] [--note <文本>]
分隔符统一用 " ｜ "，便于人类阅读。
"""
import csv
import sys
from pathlib import Path

path = Path(".agents/state/aap-feature-status.csv")
args = sys.argv[1:]
seq = args[0]
case = note = None
i = 1
while i < len(args):
    if args[i] == "--case":
        case = args[i + 1]
        i += 2
    elif args[i] == "--note":
        note = args[i + 1]
        i += 2
    else:
        i += 1

raw = path.open(encoding="utf-8", newline="").read()
rows = list(csv.DictReader(raw.splitlines()))
fields = list(rows[0].keys())

hit = 0
for r in rows:
    if r["序号"] == seq:
        if case:
            r["用例(证据)"] = (r["用例(证据)"] or "") + " ｜ " + case
        if note:
            r["备注"] = (r["备注"] or "") + " ｜ " + note
        hit += 1

with path.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)

print("追加 %d 行 · 序号 %s" % (hit, seq))
if case:
    print("  用例 += %s" % case)
if note:
    print("  备注 += %s" % note)
