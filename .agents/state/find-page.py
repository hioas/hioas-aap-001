import json, sys, re

pat = sys.argv[1] if len(sys.argv) > 1 else "page-3"

def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + "/[%d]" % i)
    else:
        yield path, o

for f in sys.argv[2:] or [".calicat/inventory.json", ".calicat/raw/pages.json"]:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("SKIP", f, e)
        continue
    print("=== ", f, type(d).__name__)
    if isinstance(d, dict):
        print("keys:", list(d.keys())[:20])
    # find objects that smell like pages
    def find_pages(o, depth=0):
        out = []
        if isinstance(o, dict):
            if any(k in o for k in ("layer_id", "node_id", "sourceLayerId", "name")) and depth < 6:
                s = json.dumps(o, ensure_ascii=False)
                if pat in s:
                    out.append(o)
            for v in o.values():
                out += find_pages(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                out += find_pages(v, depth + 1)
        return out
    hits = find_pages(d)
    seen = set()
    for h in hits:
        s = json.dumps(h, ensure_ascii=False)
        if s in seen:
            continue
        seen.add(s)
        print(s[:900])
