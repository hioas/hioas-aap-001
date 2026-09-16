#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""队列 0（目录改名）加一条「cron 任务 prompt 与人类决策冲突」的处置说明。

背景：本 job 的 prompt 仍写着「每轮开工先试一次 git mv aap-client hioas-aap-client」，
而人类 2026-09-16 的决策台账 D6 明确「不重命名、勿再重试」。冲突时以人类决策为准
（prompt 里也要求「若两者冲突…并在本轮顺手把状态文件改成一致后再继续」）。
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aap-tdd-state.md")
NOTE = (
    "  - ⚠️ **cron 任务 prompt 里仍写着「每轮先试一次 `git mv`」——该条已被决策 D6 取代，勿再执行**："
    "人类 2026-09-16 在 `aap-decisions.md` D6 明确「不重命名（`hioas-*` 是仓库名约定，不是模块目录约定），勿再重试」，"
    "凡 prompt 与本文件/决策台账冲突，一律以人类决策为准（本文件即此记录）。\n"
)
ANCHOR = "不再重试**。"

with io.open(P, "r", encoding="utf-8", newline="") as fh:
    text = fh.read()

if NOTE.strip().splitlines()[0] in text:
    print("already present")
    sys.exit(0)

idx = text.find(ANCHOR)
if idx < 0:
    print("anchor not found")
    sys.exit(1)
line_end = text.find("\n", idx)
if line_end < 0:
    print("line end not found")
    sys.exit(1)
idx = line_end + 1
text = text[:idx] + NOTE + text[idx:]

with io.open(P, "w", encoding="utf-8", newline="") as fh:
    fh.write(text)
print("queue-0 note added")
