import json, sys

d = json.load(open(".calicat/raw/pages.json", encoding="utf-8"))
lst = d["page_list"]
key = sys.argv[1] if len(sys.argv) > 1 else None
for p in lst:
    name = p.get("name") or p.get("title") or ""
    pid = p.get("id")
    layer = p.get("layer_id") or p.get("source_layer_id") or p.get("layerId")
    if key and key not in str(name):
        continue
    print("|", pid, "|", layer, "|", name, "|", sorted(p.keys()))
