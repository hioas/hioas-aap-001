# -*- coding: utf-8 -*-
"""按节点 id 导出子树（含 fills/strokes/radius/fontSize/text），用于取色与间距。"""
import io
import json
import sys

TREE = ".calicat/raw/pages/page-6/design.tree.json"
tree = json.load(io.open(TREE, encoding="utf-8"))
roots = tree if isinstance(tree, list) else [tree]
want = set(sys.argv[1:])
out = []


def color(v):
    if isinstance(v, list):
        return [color(x) for x in v]
    if isinstance(v, dict):
        c = v.get("color") or v
        if isinstance(c, dict):
            r = c.get("r")
            g = c.get("g")
            b = c.get("b")
            a = c.get("a", 1)
            if r is not None:
                if isinstance(r, float) and r <= 1:
                    r, g, b = [round(x * 255) for x in (r, g, b)]
                return "#%02X%02X%02X" % (int(r), int(g), int(b)) + ("" if a in (1, None) else "@%.2f" % a)
        return json.dumps(v, ensure_ascii=False)[:80]
    return v


def walk(n, depth=0):
    if not isinstance(n, dict):
        return
    nid = n.get("id")
    in_scope = nid in want
    if in_scope:
        out.append(u"\n=== %s [%s] ===" % (nid, n.get("name")))
        _dump(n, 0)
        return
    for c in (n.get("children") or []):
        walk(c, depth + 1)


def _dump(n, d):
    keys = ("name", "type", "width", "height", "padding", "gap", "itemSpacing", "cornerRadius", "layout",
            "fills", "strokes", "strokeWidth", "fontSize", "fontWeight", "fontFill", "textAlign", "text", "content")
    info = {}
    for k in keys:
        v = n.get(k)
        if v in (None, "", [], {}):
            continue
        if k in ("fills", "strokes", "fontFill"):
            v = color(v)
        info[k] = v
    out.append(u"%s%s" % (u"  " * d, json.dumps(info, ensure_ascii=False)))
    for c in (n.get("children") or []):
        _dump(c, d + 1)


for r in roots:
    walk(r)

txt = u"\n".join(out)
io.open(".agents/state/page-6-subtree.txt", "w", encoding="utf-8").write(txt)
print("lines=%d" % len(out))
