#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把台账 CSV 的行尾统一成 LF（append-*.py 写的是 CRLF，会让 git 把整文件当成改动）。

⚠️ 2026-09-16 修：旧版直接以 "w" 打开目标文件再逐行写 → 一旦中途解析/格式报错（例如某行因
   多出 ASCII 引号/逗号而被拆列），**已写入的前几行会把原文件截断**（实测把 22 行写成 6 行）。
   现改为：先在内存里生成完整文本并用 csv 复解析校验，全部通过后才落盘。
"""
import csv
import io
from pathlib import Path

p = Path(".agents/state/aap-feature-status.csv")
text = io.open(p, encoding="utf-8", newline="").read()

rows = list(csv.DictReader(io.StringIO(text)))
if not rows:
    raise SystemExit("台账为空，拒绝写入")
fields = list(rows[0].keys())
if None in fields:
    raise SystemExit("表头解析异常：%r" % (fields,))

buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
w.writeheader()
for i, r in enumerate(rows, start=2):
    if None in r or len(r) != len(fields):
        raise SystemExit("第 %d 行字段数异常（%d != %d）→ 拒绝写入" % (i, len(r), len(fields)))
    w.writerow(r)
out = buf.getvalue()

# 复解析校验：写出去的内容必须还能被 csv 读回同样的行数
again = list(csv.DictReader(io.StringIO(out)))
if len(again) != len(rows):
    raise SystemExit("复解析行数不一致（%d != %d）→ 拒绝写入" % (len(again), len(rows)))

io.open(p, "w", encoding="utf-8", newline="").write(out)
print("normalized %d rows to LF" % len(again))
