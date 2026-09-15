import json
d = json.load(open(".calicat/inventory.json", encoding="utf-8"))
for i, p in enumerate(d["pages"], 1):
    print("%2d | %-12s | %-52s | %s" % (i, p["id"], p["name"][:52], p.get("sourceLayerId", "")[:8]))
