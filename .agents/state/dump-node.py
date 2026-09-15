import json, sys

page = "page-4-2"
args = sys.argv[1:]
if args and args[0].startswith("--page="):
    page = args[0].split("=", 1)[1]
    args = args[1:]
tree = json.load(open(".calicat/raw/pages/%s/design.tree.json" % page, encoding="utf-8"))
want = set(args)


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
