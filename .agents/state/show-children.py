"""Print a design node's direct children (name/id/type/width/height/padding) — used to
read the layout skeleton of a row without dumping the whole subtree."""
import json
import sys

path = sys.argv[1]
want = sys.argv[2]

with open(path, encoding="utf-8") as fh:
    tree = json.load(fh)


def walk(node):
    if isinstance(node, dict):
        if node.get("name") == want:
            kids = node.get("children") or []
            print("== %s (%s) w=%s h=%s pad=%s layout=%s ==" % (
                node.get("name"), node.get("id"), node.get("width"), node.get("height"),
                node.get("padding"), node.get("layout")))
            for kid in kids:
                print("  - %-16s id=%-10s %-10s w=%-14s h=%-12s pad=%-16s fills=%s fs=%s text=%s" % (
                    kid.get("name"), str(kid.get("id"))[:8], kid.get("type"), kid.get("width"),
                    kid.get("height"), kid.get("padding"), kid.get("fills"), kid.get("fontSize"),
                    (kid.get("content") or "")[:14]))
                for gk in (kid.get("children") or []):
                    print("      . %-14s id=%-10s %-10s w=%-14s h=%-12s pad=%-16s fills=%s fs=%s text=%s" % (
                        gk.get("name"), str(gk.get("id"))[:8], gk.get("type"), gk.get("width"),
                        gk.get("height"), gk.get("padding"), gk.get("fills"), gk.get("fontSize"),
                        (gk.get("content") or "")[:14]))
        for value in node.values():
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)


walk(tree)
