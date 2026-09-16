#!/usr/bin/env python
"""Print inventory/raw page metadata for a page id (layer_id, name, screenshot)."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
pid = sys.argv[1] if len(sys.argv) > 1 else "page-4-2"

inv = json.loads((root / ".calicat" / "inventory.json").read_text(encoding="utf-8"))
print("inventory keys:", list(inv.keys()))
pages = inv.get("pages") or inv.get("items") or []
for p in pages:
    if p.get("id") == pid or p.get("pageId") == pid or pid in json.dumps(p, ensure_ascii=False):
        print(json.dumps(p, ensure_ascii=False, indent=1))

raw = root / ".calicat" / "raw" / "pages.json"
if raw.exists():
    data = json.loads(raw.read_text(encoding="utf-8"))
    blob = data if isinstance(data, list) else (data.get("pages") or data.get("layers") or data)
    for p in blob:
        if pid in json.dumps(p, ensure_ascii=False):
            print("RAW:", json.dumps(p, ensure_ascii=False)[:1200])

pd = root / ".calicat" / "raw" / "pages" / pid
print("capture files:", sorted(x.name for x in pd.glob("*")) if pd.exists() else "MISSING")
