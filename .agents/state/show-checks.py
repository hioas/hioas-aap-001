# -*- coding: utf-8 -*-
"""打印某轮载体页实测的 checks 概览与失败清单（RED/GREEN 基线转录用）。

用法: python .agents/state/show-checks.py <run.json> [out.txt]
"""
import io
import json
import sys

p = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None
d = json.load(io.open(p, encoding="utf-8"))
lines = []
lines.append("file: %s" % p)
lines.append("checkCount=%s checkFailCount=%s overflowingCount=%s docScrollWidth=%s innerWidth=%s"
             % (d.get("checkCount"), d.get("checkFailCount"), d.get("overflowingCount"),
                d.get("docScrollWidth"), d.get("innerWidth")))
lines.append("missingTexts=%s" % (d.get("missingTexts"),))
fails = d.get("checkFails") or []
for f in fails:
    lines.append("FAIL %-28s got=%s want=%s" % (f.get("k"), f.get("got"), f.get("want")))
lines.append("共 %d 条 check，其中 %d 条与设计稿不符" % (d.get("checkCount") or 0, len(fails)))
text = "\n".join(lines)
print(text)
if out:
    io.open(out, "w", encoding="utf-8").write(text + "\n")
