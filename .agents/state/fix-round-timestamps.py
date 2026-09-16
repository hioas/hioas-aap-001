#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修正本轮回写里手写的时间戳（写成了 09:35 / 09:38 等未来时间）。

真实时间（可核）：D3 提交 `3612f41` = 2026-09-16 09:25:49；状态/决策回写提交 `c001d70` = 09:26:10。
规则（状态文件 §0）：时间一律用 `date "+%Y-%m-%d %H:%M:%S"` 读，禁止手写/推测。
本脚本做纯文本替换，把未来时间改成真实提交时间，并把「09:35/09:38」字样清零。
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REAL = "2026-09-16 09:26"
JOBS = [
    (os.path.join(BASE, "aap-decisions.md"), [
        ("`已完成 2026-09-16 09:35`", "`已完成 2026-09-16 09:26`"),
        ("**已落地 2026-09-16 09:38（cron 轮 `aap-tdd-run-20260916-0910`）**", "**已落地 2026-09-16 09:26（cron 轮 `aap-tdd-run-20260916-0910`）**"),
        ("- ✅ **已落库 2026-09-16 09:38**", "- ✅ **已落库 2026-09-16 09:26**"),
    ]),
    (os.path.join(BASE, "aap-tdd-state.md"), [
        ("已完成 2026-09-16 09:35", "已完成 2026-09-16 09:26"),
        ("已完成 2026-09-16 09:38", "已完成 2026-09-16 09:26"),
        ("已执行完 2026-09-16 09:35", "已执行完 2026-09-16 09:26"),
        ("小改已完成 2026-09-16 09:38", "小改已完成 2026-09-16 09:26"),
        ("- 2026-09-16 09:38（cron 轮 `aap-tdd-run-20260916-0910`）", "- 2026-09-16 09:26（cron 轮 `aap-tdd-run-20260916-0910`）"),
    ]),
]

changed = []
for path, pairs in JOBS:
    with io.open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    hits = 0
    for old, new in pairs:
        if old in text:
            hits += text.count(old)
            text = text.replace(old, new)
    if hits:
        with io.open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        changed.append("%s:%d" % (os.path.basename(path), hits))

# 事后体检：文件里不应再出现未来时间
bad = []
for path, _ in JOBS:
    with io.open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    for token in ("09:35", "09:38", "09:32（cron", "2026-09-16 09:3"):
        if token in text:
            bad.append("%s contains %s" % (os.path.basename(path), token))

print("replaced: %s" % ", ".join(changed) if changed else "nothing to replace")
if bad:
    print("STILL PRESENT:")
    for b in bad:
        print("  - %s" % b)
    sys.exit(1)
print("ok: no hand-written future timestamps remain (real=%s)" % REAL)
