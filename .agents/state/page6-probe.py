# -*- coding: utf-8 -*-
"""page-6 设计树探针：导出长文本节点全文 + 容器几何（frame/rectangle 带 padding/gap/radius/fill）。"""
import io
import json
import sys

TREE = ".calicat/raw/pages/page-6/design.tree.json"
tree = json.load(io.open(TREE, encoding="utf-8"))
roots = tree if isinstance(tree, list) else [tree]
out = []


def text_of(n):
    for k in ("text", "content", "characters"):
        v = n.get(k)
        if isinstance(v, str) and v:
            return v
    for k in ("text", "content"):
        v = n.get(k)
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False)
    return ""


def walk(n, depth=0):
    if not isinstance(n, dict):
        return
    t = text_of(n)
    if t and len(t) > 34:
        out.append(u"[LONG len=%d] %s\n    %s" % (len(t), n.get("id", ""), t))
    kids = n.get("children") or []
    if kids:
        info = {
            "id": n.get("id"), "name": n.get("name"), "type": n.get("type"),
            "x": n.get("x"), "y": n.get("y"), "w": n.get("width"), "h": n.get("height"),
            "padding": n.get("padding"), "gap": n.get("gap") or n.get("itemSpacing"),
            "radius": n.get("cornerRadius") or n.get("radius"),
            "fill": n.get("fills") or n.get("fill"), "layout": n.get("layout"),
            "kids": len(kids),
        }
        out.append(u"[NODE d=%d] %s" % (depth, json.dumps(info, ensure_ascii=False)))
    for c in kids:
        walk(c, depth + 1)


for r in roots:
    walk(r)

top = roots[0] if roots else {}
out.append(u"[ROOT] %s" % json.dumps(
    {k: top.get(k) for k in ("id", "name", "type", "width", "height", "x", "y", "fills", "padding", "layout")},
    ensure_ascii=False))

with io.open(".agents/state/page-6-probe.txt", "w", encoding="utf-8") as f:
    f.write(u"\n".join(out))
print("lines=%d" % len(out))
