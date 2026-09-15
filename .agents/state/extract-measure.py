import json, re, sys, html

raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
m = re.search(r"(?:MEASURE_JSON|PROBE_JSON):(\{.*?\})</pre>", raw, re.S)
if not m:
    print("NO MEASURE_JSON FOUND; tail of dump:")
    print(raw[-2000:])
    sys.exit(1)
txt = html.unescape(m.group(1))
data = json.loads(txt)
out = sys.argv[2] if len(sys.argv) > 2 else None
if out:
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(data, ensure_ascii=False, indent=1))
# 关键断言摘要（一眼可核）
keys = [
    "innerWidth", "innerHeight", "docScrollWidth", "docScrollHeight", "overflowingCount",
    "missingTexts", "chipTexts", "chipColors", "rowCount", "reportCount", "rowDotColors",
    "listTotal", "headTexts", "caption", "nameColW", "modelsColW", "statusColW", "viewColW",
    "tabbarPinned", "bodyBg", "topbarBg", "submitBg", "scrollYMax", "atBottom"
]
print("=== SUMMARY ===")
print(json.dumps({k: data.get(k) for k in keys if k in data}, ensure_ascii=False, indent=1))
