# -*- coding: utf-8 -*-
"""打印设计树所有文本叶子的 fontSize/lineHeight/w/h/文案；--geom 时打印每个节点的 x/y/宽高。

用法: python .agents/state/text-lineheight.py <page-id> [--geom]
"""
import io
import json
import os
import sys

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
pid = sys.argv[1]
geom = "--geom" in sys.argv
tree = json.load(io.open(os.path.join(ROOT, ".calicat/raw/pages", pid, "design.tree.json"), encoding="utf-8"))


def walk(d, depth=0):
    kids = d.get("children") or []
    if geom:
        print("%s%-9s %-24s %-9s x=%-7s y=%-7s w=%-8s h=%-10s pad=%s" % (
            "  " * depth, str(d.get("id"))[:8], str(d.get("name"))[:24], d.get("type"),
            d.get("x"), d.get("y"), d.get("width"), d.get("height"), d.get("padding")))
    elif not kids and d.get("fontSize") is not None:
        print("%-9s %-22s %-9s fs=%-4s lh=%-5s w=%-7s h=%-7s fill=%-24s %s" % (
            str(d.get("id"))[:8], str(d.get("name"))[:22], d.get("type"), d.get("fontSize"),
            d.get("lineHeight"), d.get("width"), d.get("height"), d.get("fontFill"), str(d.get("content"))[:30]))
    for k in kids:
        walk(k, depth + 1)


walk(tree)
