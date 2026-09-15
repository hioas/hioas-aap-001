#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Calicat design.json 压成"可读排版摘要"，供实现 UI 时对照（不要把原始 payload 贴进对话）。

用法：
    python .agents/state/design-summary.py .calicat/raw/pages/page-1-2/design.json
    python .agents/state/design-summary.py <design.json> --text-only     # 只列文字与样式
    python .agents/state/design-summary.py <design.json> --max-depth 6
"""
import argparse
import json
import sys

KEEP_STYLE = ["fontFamily", "fontSize", "fontWeight", "color", "fills", "backgroundColor",
              "borderRadius", "padding", "opacity", "textAlign", "lineHeight", "layoutMode",
              "itemSpacing", "border"]


def px(v):
    if isinstance(v, (int, float)):
        return f"{v:g}"
    if isinstance(v, dict):
        for k in ("value", "x", "left"):
            if k in v and isinstance(v[k], (int, float)):
                return f"{v[k]:g}"
    return str(v) if v is not None else ""


def color_of(node):
    fills = node.get("fills") or node.get("fill")
    if isinstance(fills, list) and fills:
        c = fills[0]
        if isinstance(c, dict):
            return c.get("color") or c.get("hex") or c.get("value") or ""
    if isinstance(fills, dict):
        return fills.get("color") or fills.get("hex") or ""
    return ""


def style_brief(n):
    bits = []
    for k in ("fontSize", "fontWeight", "textAlign", "lineHeight", "borderRadius", "layoutMode", "itemSpacing"):
        if n.get(k) not in (None, ""):
            bits.append(f"{k}={n[k]}")
    c = color_of(n)
    if c:
        bits.append(f"color={c}")
    b = n.get("backgroundColor")
    if b:
        bits.append(f"bg={b}")
    return " ".join(str(x) for x in bits)


def walk(n, depth, max_depth, out, text_only):
    name = n.get("name", "?")
    typ = n.get("type", "")
    x, y = px(n.get("x")), px(n.get("y"))
    w, h = px(n.get("width")), px(n.get("height"))
    text = (n.get("characters") or n.get("text") or n.get("content") or "")
    if isinstance(text, str):
        text = text.replace("\n", "\\n")
    sb = style_brief(n)
    is_text = bool(text) or typ.lower() in ("text", "textnode")
    if text_only and not is_text:
        pass
    else:
        line = f"{'  ' * depth}{typ:<10} {name[:46]:<46} pos=({x},{y}) size={w}x{h}"
        if text:
            line += f'  TEXT="{text[:80]}"'
        if sb:
            line += f"  [{sb}]"
        out.append(line)
    if depth >= max_depth:
        return
    for c in (n.get("children") or []):
        walk(c, depth + 1, max_depth, out, text_only)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--max-depth", type=int, default=8)
    ap.add_argument("--text-only", action="store_true")
    a = ap.parse_args()
    with open(a.path, encoding="utf-8") as f:
        d = json.load(f)
    roots = d if isinstance(d, list) else (d.get("nodes") or d.get("layers") or d.get("children") or [d])
    out = []
    for r in roots:
        walk(r, 0, a.max_depth, out, a.text_only)
    print("\n".join(out))
    print(f"--- {len(out)} 行（--text-only={a.text_only}） ---", file=sys.stderr)


if __name__ == "__main__":
    main()
