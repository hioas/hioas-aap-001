#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Set the LEASE line in .agents/state/aap-tdd-state.md.

用法:
  python .agents/state/lease-set.py <holder> <until>        # until = 'YYYY-MM-DD HH:MM'（时间戳）
  python .agents/state/lease-set.py <holder> --minutes 45   # 自动写「现在 + 45 分钟」（推荐）
  python .agents/state/lease-set.py free                    # 释放租约（写 'free until -'）

⚠️ 坑：第二个参数若是纯数字会被当成**分钟数**（旧版直接写进去，租约行变成「until 45」这种非法时间戳）。
"""
import io
import re
import sys
import datetime

path = ".agents/state/aap-tdd-state.md"
holder = sys.argv[1]

if holder == "free":
    line = "LEASE: free until -"
else:
    args = sys.argv[2:]
    if "--minutes" in args:
        mins = int(args[args.index("--minutes") + 1])
        until = (datetime.datetime.now() + datetime.timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M")
    elif args and args[0].isdigit():
        until = (datetime.datetime.now() + datetime.timedelta(minutes=int(args[0]))).strftime("%Y-%m-%d %H:%M")
    elif args:
        until = args[0]
    else:
        raise SystemExit("需要 until（时间戳 / --minutes N / 数字分钟数）")
    line = "LEASE: %s until %s" % (holder, until)

text = io.open(path, encoding="utf-8").read()
text = re.sub(r"(?m)^LEASE:.*$", line, text, count=1)
io.open(path, "w", encoding="utf-8").write(text)
print(u"\n".join(text.splitlines()[:3]))
