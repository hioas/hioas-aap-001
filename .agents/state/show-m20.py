#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""序号 20（站内信列表 / page-20-2）H5 取数速览。

用法：
  python .agents/state/show-m20.py <measure.json>                # 打印 phase1 全量摘要
  python .agents/state/show-m20.py <measure.json> cmp            # 比 phase1 / phase2（若 phase2 含全量）
  python .agents/state/show-m20.py <measure.json> phase2         # 打印 phase2 原始
"""
import io
import json
import sys

path = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "phase1"

with io.open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

if mode == "raw":
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(0)

if mode == "phase2":
    print(json.dumps(data.get("phase2"), ensure_ascii=False, indent=2))
    sys.exit(0)

if mode == "cmp":
    a = data.get("phase1") or {}
    b = data.get("phase2") or {}
    diffs = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            diffs.append("%s: phase1=%s | phase2=%s" % (k, json.dumps(a.get(k), ensure_ascii=False)[:160], json.dumps(b.get(k), ensure_ascii=False)[:160]))
    print("字段数 %d · 差异 %d" % (len(a), len(diffs)))
    for d in diffs:
        print("  " + d)
    sys.exit(0)

p = data.get("phase1") or {}
print("innerWidth=%s docScrollWidth=%s docScrollHeight=%s 溢出=%s" % (p.get("innerWidth"), p.get("docScrollWidth"), p.get("docScrollHeight"), p.get("overflowingCount")))
print("iframeHeightForShot=%s" % data.get("iframeHeightForShot"))
print("missingTexts=%s" % json.dumps(p.get("missingTexts"), ensure_ascii=False))
print("overflowing=%s" % json.dumps(p.get("overflowing"), ensure_ascii=False)[:600])
print("--- 骨架 ---")
for k in ("page", "nav", "filters", "list", "tabbar"):
    print("%-9s %s" % (k, json.dumps(p.get(k), ensure_ascii=False)))
print("navPad=%s listPad=%s filtersPad=%s tabbarPad=%s pagePadBottom=%s" % (p.get("navPad"), p.get("listPad"), p.get("filtersPad"), p.get("tabbarPad"), p.get("pagePadBottom")))
print("pageBg=%s tabbarPos=%s" % (p.get("pageBg"), p.get("tabbarPos")))
print("--- 顶部导航 ---")
print("title=%s navStyle=%s" % (p.get("title"), json.dumps(p.get("navTitleStyle"), ensure_ascii=False)))
print("badge=%s text=%s bg=%s radius=%s" % (json.dumps(p.get("badge"), ensure_ascii=False), p.get("badgeText"), p.get("badgeBg"), p.get("badgeRadius")))
print("badgeTextStyle=%s" % json.dumps(p.get("badgeTextStyle"), ensure_ascii=False))
print("readAll=%s text=%s icon=%s" % (json.dumps(p.get("readAll"), ensure_ascii=False), p.get("readAllText"), json.dumps(p.get("readAllIcon"), ensure_ascii=False)))
print("readAllTextStyle=%s" % json.dumps(p.get("readAllTextStyle"), ensure_ascii=False))
print("--- 筛选行 ---")
print("chips=%s" % json.dumps(p.get("chips"), ensure_ascii=False))
print("chipTexts=%s chipActive=%s radius=%s" % (json.dumps(p.get("chipTexts"), ensure_ascii=False), p.get("chipActiveText"), p.get("chipRadius")))
print("chipBgs=%s" % json.dumps(p.get("chipBgs"), ensure_ascii=False))
print("chipTextColors=%s" % json.dumps(p.get("chipTextColors"), ensure_ascii=False))
print("--- 消息列表 ---")
print("rowCount=%s cardPads=%s radius=%s shadow=%s" % (p.get("rowCount"), p.get("cardPads"), p.get("cardRadius"), p.get("cardShadow")))
print("cards=%s" % json.dumps(p.get("cards"), ensure_ascii=False))
print("cardGaps=%s" % json.dumps(p.get("cardGaps"), ensure_ascii=False))
print("icons=%s" % json.dumps(p.get("icons"), ensure_ascii=False))
print("iconBgs=%s iconRadius=%s" % (json.dumps(p.get("iconBgs"), ensure_ascii=False), p.get("iconRadius")))
print("glyphs=%s" % json.dumps(p.get("glyphs"), ensure_ascii=False))
print("glyphBgs=%s" % json.dumps(p.get("glyphBgs"), ensure_ascii=False))
print("bodyPadLeft=%s" % p.get("bodyPadLeft"))
print("titles=%s" % json.dumps(p.get("titles"), ensure_ascii=False))
print("titleRects=%s" % json.dumps(p.get("titleRects"), ensure_ascii=False))
print("titleColors=%s msgTitleStyle=%s" % (json.dumps(p.get("titleColors"), ensure_ascii=False), json.dumps(p.get("msgTitleStyle"), ensure_ascii=False)))
print("contents=%s" % json.dumps(p.get("contents"), ensure_ascii=False))
print("contentRects=%s contentColors=%s" % (json.dumps(p.get("contentRects"), ensure_ascii=False), json.dumps(p.get("contentColors"), ensure_ascii=False)))
print("contentStyle=%s" % json.dumps(p.get("contentStyle"), ensure_ascii=False))
print("times=%s timeRects=%s" % (json.dumps(p.get("times"), ensure_ascii=False), json.dumps(p.get("timeRects"), ensure_ascii=False)))
print("timeColors=%s timeStyle=%s" % (json.dumps(p.get("timeColors"), ensure_ascii=False), json.dumps(p.get("timeStyle"), ensure_ascii=False)))
print("dots=%s count=%s bg=%s" % (json.dumps(p.get("dots"), ensure_ascii=False), p.get("dotCount"), p.get("dotBg")))
print("targets=%s" % json.dumps(p.get("targets"), ensure_ascii=False))
print("--- TabBar ---")
print("tabbarCount=%s items=%s" % (p.get("tabbarCount"), json.dumps(p.get("tabItems"), ensure_ascii=False)))
print("labels=%s colors=%s active=%s" % (json.dumps(p.get("tabLabels"), ensure_ascii=False), json.dumps(p.get("tabLabelColors"), ensure_ascii=False), p.get("tabActiveLabel")))
print("glyphBgs=%s" % json.dumps(p.get("tabGlyphBgs"), ensure_ascii=False))
print("inputCount=%s" % p.get("inputCount"))
