import json

d = json.load(open(".calicat/raw/pages.json", encoding="utf-8"))
pl = d["page_list"] if isinstance(d, dict) else d
print("count:", len(pl))
for p in pl:
    if isinstance(p, dict):
        print(p.get("id"), "|", p.get("name"), "|", p.get("sourceLayerId"), "|", p.get("width"), p.get("height"))
    else:
        print(p)
