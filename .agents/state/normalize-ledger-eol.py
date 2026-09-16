#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把台账 CSV 的行尾统一成 LF（append-ledger-note.py 写的是 CRLF，会让 git 把整文件当成改动）。"""
import csv
import io
from pathlib import Path

p = Path(".agents/state/aap-feature-status.csv")
text = io.open(p, encoding="utf-8", newline="").read()
rows = list(csv.DictReader(io.StringIO(text)))
fields = list(rows[0].keys())
with io.open(p, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print("normalized %d rows to LF" % len(rows))
