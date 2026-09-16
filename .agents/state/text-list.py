# -*- coding: utf-8 -*-
"""列出 design.tree.json 里所有文本图层（TEXT= 的值），用于载体页 needText 清单。

用法: python .agents/state/text-list.py .calicat/raw/pages/page-1-2/design.tree.json
"""
import json
import sys

path = sys.argv[1]
tree = json.load(open(path, encoding="utf-8"))
out = []


def walk(node, depth=0):
    if not isinstance(node, dict):
        return
    t = node.get("TEXT") or node.get("text") or node.get("content")
    if isinstance(t, str) and t.strip():
        out.append((depth, node.get("name", ""), t.strip()))
    for ch in node.get("children") or []:
        walk(ch, depth + 1)


walk(tree)
for d, name, t in out:
    print("%s[%s] %s" % ("  " * d, name, t))
print("--- total %d ---" % len(out))
