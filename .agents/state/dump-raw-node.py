import json, sys

p = sys.argv[1] if len(sys.argv) > 1 else ".calicat/raw/pages/page-11/design.tree.json"
t = json.load(open(p, encoding="utf-8"))
nid = sys.argv[2] if len(sys.argv) > 2 else None

def walk(n, depth=0, path=""):
    if nid and n.get("id") != nid:
        for c in n.get("children") or []:
            walk(c, depth + 1, path)
        return
    print(json.dumps(n, ensure_ascii=False)[:3000])
    if nid:
        return

print("keys:", sorted(t.keys()))
walk(t)
