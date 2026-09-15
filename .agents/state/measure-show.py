#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打印测量 JSON 里若干关键字段（列表/标量），避免 grep 截断。"""
import io
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else ".agents/state/evidence/measure-序号4.json"
keys = sys.argv[2:] or [
    "innerWidth", "docScrollWidth", "overflowingCount", "missingTexts", "docScrollHeight",
    "aliasValue", "baseUrlValue", "apiKeyMaskText", "selectedCountText", "titleText",
    "primaryChipText", "configuredChipText", "catalogMoreText", "saveBtnText", "submitBtnText",
    "cardLabels", "cardCount", "vendorGroupCount", "modelRowCount", "checkedCount", "barPinned",
    "bar", "firstCard", "firstModelRow", "atBottom", "scrollYMax", "emojiInText", "iframeRect"
]
data = json.load(io.open(path, encoding="utf-8"))
for k in keys:
    print("%-20s %s" % (k, json.dumps(data.get(k, "<absent>"), ensure_ascii=False)))
