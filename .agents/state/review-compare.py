#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""复核用：一页一次跑完「两次独立测量一致 + 与建页留证无漂移」的紧凑对比。

用法:
  python .agents/state/review-compare.py --tag 8 [--old .agents/state/evidence/measure-序号8-430宽.json]

读 .agents/state/evidence/review-序号<tag>-run{1,2}.json（review-measure.sh 的产物）。
phase 自动识别：值里带 innerWidth 的 dict 视为 phase；整个文件是扁平结构时按单段处理。
输出：每个 phase 一行「全等 N / 不一致 M」，并列出不一致的字段名（最多 8 个）。
"""
import io
import json
import os
import sys

tag = None
old = None
args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == "--tag":
        tag = args[i + 1]
        i += 2
    elif args[i] == "--old":
        old = args[i + 1]
        i += 2
    else:
        i += 1

EV = ".agents/state/evidence"
r1 = os.path.join(EV, "review-序号%s-run1.json" % tag)
r2 = os.path.join(EV, "review-序号%s-run2.json" % tag)


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


META = ("userAgent", "iframeHeightForShot", "iframeRect", "outerInnerWidth", "iframeRectForShot")


def phases(d):
    """dict 值各算一个分组；**顶层标量字段单独归入 flat**（否则会被 dict 分组掩盖而漏比）。"""
    groups = {k: v for k, v in d.items() if isinstance(v, dict) and k not in META}
    scalars = {k: v for k, v in d.items() if not isinstance(v, dict) and k not in META}
    if not groups:
        return {"flat": {k: v for k, v in d.items() if k not in META}}
    if scalars:
        groups["flat"] = scalars
    return groups


a, b = load(r1), load(r2)
pa, pb = phases(a), phases(b)
oldp = phases(load(old)) if old and os.path.isfile(old) else {}

ok = True
oldok = True
print("序号 %s · phases=%s" % (tag, ",".join(sorted(pa)) or "(none)"))
for ph in sorted(pa):
    if ph not in pb:
        print("  %-8s run2 缺该 phase → 不一致" % ph)
        ok = False
        continue
    xa, xb = pa[ph], pb[ph]
    keys = sorted(set(xa) | set(xb))
    diff2 = [k for k in keys if k not in ("userAgent", "iframeHeightForShot") and xa.get(k) != xb.get(k)]
    line = "  %-8s run1vsrun2: 全等 %d / 不一致 %d" % (ph, len(keys) - len(diff2), len(diff2))
    if diff2:
        line += " → " + ",".join(diff2[:8])
        ok = False
    print(line)
    if ph in oldp:
        xo = oldp[ph]
        keys3 = sorted(set(xo) | set(xa))
        diff3 = [k for k in keys3 if k not in ("userAgent", "iframeHeightForShot") and xo.get(k) != xa.get(k)]
        line = "  %-8s 留证vs本轮: 全等 %d / 不一致 %d" % (ph, len(keys3) - len(diff3), len(diff3))
        if diff3:
            line += " → " + ",".join(diff3[:8])
            oldok = False
        print(line)
    elif old:
        print("  %-8s 留证文件里没有该 phase（旧版探测项更少）" % ph)

print("结论: %s" % ("两次独立测量一致" + ("，且与建页留证无漂移" if oldp and oldok else "（留证对比见上）") if ok else "**存在不一致，需定位**"))
sys.exit(0 if ok else 1)
