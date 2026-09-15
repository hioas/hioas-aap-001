#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 design.tree.json 抽取设计 token：所有 fills/bg/radius/fontSize/fontWeight 去重计数。

用法：python .agents/state/extract-tokens.py .calicat/raw/pages/page-1-2/design.tree.json
"""
import argparse
import json
import re
from collections import Counter


def walk(n, acc):
    for k in ("fills", "backgroundColor", "fill"):
        v = n.get(k)
        if isinstance(v, str):
            acc[k][v] += 1
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, str):
                    acc[k][it] += 1
                elif isinstance(it, dict):
                    c = it.get("color") or it.get("hex")
                    if c:
                        acc[k][str(c)] += 1
    for k in ("fontSize", "fontWeight", "borderRadius", "padding", "layout", "type"):
        v = n.get(k)
        if v not in (None, ""):
            acc[k][json.dumps(v, ensure_ascii=False)] += 1
    for c in n.get("children") or []:
        walk(c, acc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    a = ap.parse_args()
    d = json.load(open(a.path, encoding="utf-8"))
    acc = {k: Counter() for k in ("fills", "backgroundColor", "fill", "fontSize", "fontWeight",
                                  "borderRadius", "padding", "layout", "type")}
    roots = d if isinstance(d, list) else [d]
    for r in roots:
        walk(r, acc)

    hex_rgb = re.compile(r"rgba?\((\d+),\s*(\d+),\s*(\d+)")
    print("== 颜色（原值 -> hex -> 出现次数） ==")
    for group in ("fills", "backgroundColor"):
        for val, n in acc[group].most_common():
            m = hex_rgb.match(val)
            hexv = "#%02X%02X%02X" % (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else val
            print(f"  {group:<16} {val:<24} {hexv:<9} x{n}")
    print("== 字号 ==", dict(acc["fontSize"].most_common()))
    print("== 字重 ==", dict(acc["fontWeight"].most_common()))
    print("== 圆角 ==", dict(acc["borderRadius"].most_common()))
    print("== 内边距 ==", dict(acc["padding"].most_common(8)))
    print("== 布局 ==", dict(acc["layout"].most_common()))
    print("== 图层类型 ==", dict(acc["type"].most_common(10)))


if __name__ == "__main__":
    main()
