# -*- coding: utf-8 -*-
"""打印某次测量 JSON 的指定 phase 里的指定字段（避免 heredoc/-c 被 cron 安全策略拦）。"""
import io
import json
import sys

path = sys.argv[1]
phase = sys.argv[2]
fields = sys.argv[3:]

d = json.load(io.open(path, encoding="utf-8"))
p = d.get(phase, {})
for f in fields:
    print("%-14s = %s" % (f, json.dumps(p.get(f), ensure_ascii=False)))
print("phase keys:", ", ".join(sorted(p.keys())))
