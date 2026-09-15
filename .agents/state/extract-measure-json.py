# -*- coding: utf-8 -*-
"""从无头 Chrome 的 --dump-dom 输出里抽出 MEASURE_JSON 并落盘。

用法: python .agents/state/extract-measure-json.py <dump.html> <out.json>
"""
import io
import json
import re
import sys

dump = sys.argv[1]
out = sys.argv[2]
raw = io.open(dump, encoding="utf-8", errors="replace").read()
m = re.search(r"MEASURE_JSON:(\{.*?\})</pre>", raw, re.S)
if not m:
    m = re.search(r"MEASURE_JSON:(\{.*)", raw, re.S)
if not m:
    print("NO_MEASURE_JSON bytes=%d" % len(raw.encode("utf-8")))
    sys.exit(2)
text = m.group(1)
# 去掉尾随的 </pre> 等标签
text = text.split("</")[0].strip()
try:
    data = json.loads(text)
except Exception as exc:  # noqa: BLE001
    print("PARSE_FAIL %s ; head=%s" % (exc, text[:200]))
    sys.exit(3)
io.open(out, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
print("OK phases=%s -> %s" % (sorted(data.keys()), out))
