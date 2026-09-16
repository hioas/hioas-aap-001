#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打印多相载体页实测 JSON（acc = {phase1:.., phase2:..}）每相的 checks 概览与失败清单。

用法:
  python .agents/state/show-phases.py <run.json> [out.txt] [--fails-only]
"""
import io
import json
import sys

p = sys.argv[1]
out = None
rest = [a for a in sys.argv[2:] if not a.startswith("--")]
fails_only = "--fails-only" in sys.argv
if rest:
    out = rest[0]

d = json.load(io.open(p, encoding="utf-8"))
lines = ["file: %s" % p]
for key in sorted(d.keys()):
    ph = d[key]
    if not isinstance(ph, dict):
        continue
    if "checkCount" in ph:
        lines.append("%s : scenario=%s state=%s checkCount=%s checkFailCount=%s overflowing=%s docH=%s docW=%s"
                     % (key, ph.get("scenario", "-"), ph.get("state", "-"), ph.get("checkCount"),
                        ph.get("checkFailCount"), ph.get("overflowingCount"),
                        ph.get("docScrollHeight"), ph.get("docScrollWidth")))
        for f in ph.get("checkFails") or []:
            lines.append("    FAIL %s: got %s want %s" % (f.get("k"), json.dumps(f.get("got"), ensure_ascii=False),
                                                          json.dumps(f.get("want"), ensure_ascii=False)))
        if not fails_only:
            lines.append("    missingTexts=%s" % (ph.get("missingTexts"),))
    else:
        lines.append("%s : %s" % (key, json.dumps(ph, ensure_ascii=False)[:400]))
text = "\n".join(lines)
print(text)
if out:
    io.open(out, "w", encoding="utf-8", newline="\n").write(text + "\n")
    print("-> %s (%d 行)" % (out, len(lines)))
