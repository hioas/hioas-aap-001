# -*- coding: utf-8 -*-
"""从 dump-dom 里按关键字抓上下文片段（排查 uni-app H5 的真实 DOM 结构）。

用法: python .agents/state/grep-dump.py <dump.html> <keyword> [窗口字符数] [命中数]
"""
import io
import re
import sys

path = sys.argv[1]
kw = sys.argv[2]
win = int(sys.argv[3]) if len(sys.argv) > 3 else 400
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 3

raw = io.open(path, encoding="utf-8", errors="replace").read()
hits = [m.start() for m in re.finditer(re.escape(kw), raw)]
print("hits=%d" % len(hits))
for i, pos in enumerate(hits[:limit]):
    print("--- [%d] ---" % i)
    print(raw[max(0, pos - win // 2):pos + win // 2].replace("\n", " ")[:win])
