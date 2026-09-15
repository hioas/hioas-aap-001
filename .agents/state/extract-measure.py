import html
import io
import json
import re
import sys

raw = io.open(sys.argv[1], encoding="utf-8", errors="replace").read()
m = re.search(r"MEASURE_JSON:(\{.*?\})</pre>", raw, re.S)
if not m:
    print("NO MEASURE_JSON; tail:")
    print(raw[-1500:])
    sys.exit(1)
data = json.loads(html.unescape(m.group(1)))
out = sys.argv[2] if len(sys.argv) > 2 else None
if out:
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
print(json.dumps(data, ensure_ascii=False, indent=1))
keys = [
    "innerWidth", "innerHeight", "docScrollWidth", "docScrollHeight", "overflowingCount", "overflowing",
    "missingTexts", "titleText", "primaryChipText", "configuredChipText", "configuredChipBg",
    "aliasValue", "baseUrlValue", "apiKeyMaskText", "securityNoteText", "securityNoteBg", "securityNoteColor",
    "cardLabels", "cardCount", "selectedCountText", "vendorGroupCount", "modelRowCount", "checkedCount",
    "checkedBoxBg", "uncheckedBoxBorder", "catalogMoreText", "saveBtnText", "saveBtnBorder", "submitBtnText",
    "submitBtnBg", "bar", "barPinned", "barHeight", "cardW", "scrollYMax", "atBottom", "bodyBg", "topbarBg",
    "topbarPaddingTop", "emojiInText", "glyphCount"
]
print("=== SUMMARY ===")
print(json.dumps({k: data.get(k) for k in keys if k in data}, ensure_ascii=False, indent=1))
