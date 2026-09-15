"""从 design.tree.json 导出扁平图层清单：id / 名称 / 类型 / 尺寸 / 填充 / 字体 / 文本 / 圆角。

用法: python .agents/state/design-text.py <tree.json> [out.txt]
"""
import json
import sys

TEXT_KEYS = ("content", "text", "characters", "value")
lines = []


def fmt(v):
    if v is None or v == "":
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)[:120]
    return str(v)


def walk(node, depth=0):
    if not isinstance(node, dict):
        return
    nid = node.get("id", "")
    name = node.get("name", "")
    ntype = node.get("type", "")
    parts = [f"{'  ' * depth}[{ntype}] {name!r} id={nid}"]
    for k in ("width", "height", "x", "y"):
        if k in node:
            parts.append(f"{k}={fmt(node[k])}")
    for k in ("fills", "strokes", "stroke", "strokeWidth", "fontFill", "cornerRadius", "radius", "padding", "gap",
              "layout", "alignItems", "justifyContent", "opacity", "clip", "borderRadius"):
        if k in node:
            parts.append(f"{k}={fmt(node[k])}")
    text = None
    for k in TEXT_KEYS:
        if isinstance(node.get(k), str) and node[k].strip():
            text = node[k]
            break
    if text and not text.strip().startswith("<svg"):
        parts.append(f"TEXT={text!r}")
    for k in ("fontSize", "fontWeight", "fontFamily", "color", "fill", "lineHeight", "textAlign", "letterSpacing"):
        if k in node:
            parts.append(f"{k}={fmt(node[k])}")
    st = node.get("style")
    if isinstance(st, dict):
        for k in ("fontSize", "fontWeight", "color", "lineHeight", "textAlign", "borderRadius", "backgroundColor"):
            if k in st:
                parts.append(f"style.{k}={fmt(st[k])}")
    lines.append(" ".join(parts))
    for c in node.get("children") or []:
        walk(c, depth + 1)


tree = json.load(open(sys.argv[1], encoding="utf-8"))
walk(tree)
txt = "\n".join(lines)
if len(sys.argv) > 2:
    open(sys.argv[2], "w", encoding="utf-8").write(txt)
print(f"{len(lines)} 行图层")
print(txt)
