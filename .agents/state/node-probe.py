# -*- coding: utf-8 -*-
"""通用设计树探针：按树形缩进打印每个节点的几何/填充/文字/内边距。

用法: python .agents/state/node-probe.py <page-id> [out-suffix]
产出: .agents/state/<page-id>-nodes.txt
"""
import io
import json
import sys

PAGE = sys.argv[1]
TREE = ".calicat/raw/pages/%s/design.tree.json" % PAGE
OUT = ".agents/state/%s-nodes.txt" % PAGE
tree = json.load(io.open(TREE, encoding="utf-8"))
roots = tree if isinstance(tree, list) else [tree]
lines = []


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return "[" + ",".join(str(fmt(x)) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join("%s=%s" % (k, fmt(x)) for k, x in v.items()) + "}"
    if isinstance(v, float):
        return ("%.2f" % v).rstrip("0").rstrip(".")
    return str(v)


KEYS = ("id", "name", "type", "width", "height", "x", "y", "padding", "gap",
        "itemSpacing", "cornerRadius", "radius", "fills", "fill", "fontFill",
        "fontSize", "fontFamily", "stroke", "strokes", "strokeWidth", "layout",
        "alignItems", "justifyContent", "opacity", "shadow", "textAlign", "clip",
        "flexGrow", "visible")


def walk(n, depth=0):
    if not isinstance(n, dict):
        return
    parts = []
    for k in KEYS:
        v = n.get(k)
        if v is None or v == "" or v is False:
            continue
        parts.append("%s=%s" % (k, fmt(v)))
    txt = n.get("content")
    if isinstance(txt, str) and txt:
        parts.append("TEXT=%r" % txt)
    kids = n.get("children") or []
    parts.append("kids=%d" % len(kids))
    lines.append("%s%s" % ("  " * depth, " ".join(parts)))
    for c in kids:
        walk(c, depth + 1)


for r in roots:
    walk(r, 0)

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("lines=%d -> %s" % (len(lines), OUT))
