import json, sys

tree = json.load(open(".calicat/raw/pages/page-3/design.tree.json", encoding="utf-8"))
want = set(sys.argv[1:])


def walk(n):
    nid = n.get("id") or ""
    if nid in want:
        small = {k: v for k, v in n.items() if k != "children"}
        print(json.dumps(small, ensure_ascii=False, indent=1))
        print("---")
    for c in (n.get("children") or []):
        walk(c)


for r in (tree if isinstance(tree, list) else [tree]):
    walk(r)
