"""打印序号 5 measure JSON 的关键字段（cron 会话里 python -c 被拦，故落成脚本）。"""
import io
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else ".agents/state/evidence/measure-序号5-430宽.json"
d = json.load(io.open(path, encoding="utf-8"))

keys = [
    "innerWidth", "docScrollWidth", "docScrollHeight", "overflowingCount", "missingTexts",
    "rowCount", "chipLabels", "percentText", "fillWidthPct", "finishedText", "etaText",
    "totalCard", "bar", "fill", "barBg", "fillBg", "costBlock", "costBg", "probeBox",
    "probeBoxBgs", "probeChipBg", "probeChipTextColors", "probeChipRect", "rowRects",
    "tipCard", "tipBg", "historyBar", "historyBtn", "historyBtnBg", "historyBtnText",
    "pageBg", "topbarBg", "statusDotRect", "body", "topbar", "iframeHeightForShot",
]
for phase in ("phase1", "phase2"):
    p = d.get(phase)
    if not p:
        continue
    print("=== %s ===" % phase)
    for k in keys:
        if k in p:
            v = p[k]
            if isinstance(v, (list, dict)) and len(json.dumps(v, ensure_ascii=False)) > 400:
                print("  %s = %s" % (k, json.dumps(v, ensure_ascii=False)[:380] + " …"))
            else:
                print("  %s = %s" % (k, json.dumps(v, ensure_ascii=False)))
print("=== 一致性（phase1 vs phase2 关键数字） ===")
a, b = d.get("phase1", {}), d.get("phase2", {})
for k in ("docScrollWidth", "overflowingCount", "rowCount", "percentText", "finishedText", "etaText", "probeNames", "probeChips"):
    same = a.get(k) == b.get(k)
    print("  %s identical=%s (%s | %s)" % (k, same, json.dumps(a.get(k), ensure_ascii=False)[:60], json.dumps(b.get(k), ensure_ascii=False)[:60]))
print("iframeHeightForShot =", d.get("iframeHeightForShot"))
