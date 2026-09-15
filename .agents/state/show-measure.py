#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印 measure JSON 的关键字段（cron 会话里 python -c 被拦，故落成脚本）。

用法：
    python .agents/state/show-measure.py <measure.json>                # 平坦结构：打印默认键
    python .agents/state/show-measure.py <measure.json> empty|filled   # 两段式结构：打印该段
    python .agents/state/show-measure.py <measure.json> filled key1 key2
"""
import io
import json
import sys

DEFAULT_KEYS = [
    "innerWidth",
    "innerHeight",
    "docScrollWidth",
    "docScrollHeight",
    "overflowingCount",
    "overflowing",
    "missingTexts",
    "titleText",
    "subtitleText",
    "sectionTitles",
    "fieldLabels",
    "starCount",
    "starColor",
    "nativePlaceholders",
    "placeholderTexts",
    "inputBoxRect",
    "inputBoxBg",
    "inputBoxBorder",
    "inputBoxRadius",
    "cardCount",
    "cards",
    "cardGap",
    "cardShadow",
    "cardRadius",
    "typeChips",
    "chipChecked",
    "chipBg",
    "chipTextColors",
    "chipRect",
    "uploadTipText",
    "uploadMainText",
    "uploadLimitText",
    "uploadRect",
    "uploadBorderStyle",
    "uploadBorderColor",
    "uploadIconRect",
    "uploadIconBg",
    "fileRowCount",
    "fileNameText",
    "fileSizeText",
    "fileRowRect",
    "fileDelRect",
    "remarkBoxRect",
    "remarkBoxBg",
    "submitBtnText",
    "submitBtnRect",
    "submitBtnBg",
    "submitBtnShadow",
    "footnoteText",
    "topbarRect",
    "topbarBg",
    "pageBg",
    "contentPadding",
    "contentGap",
    "hasTabbar",
    "glyphCount",
    "emojiInText",
    "injectError",
]

path = sys.argv[1]
args = sys.argv[2:]
d = json.load(io.open(path, encoding="utf-8"))
phase = ""
if args and args[0] in ("empty", "filled"):
    phase = args.pop(0)
    d = d.get(phase, {"__missing__": phase})
keys = args or DEFAULT_KEYS
if phase:
    print("== phase: %s ==" % phase)
for k in keys:
    print("%-20s = %s" % (k, json.dumps(d.get(k, "<缺失>"), ensure_ascii=False)))
