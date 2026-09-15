#!/usr/bin/env python
"""打印 inventory.json 中指定 page-id 的条目（含 sourceLayerId）。用法: show-page.py page-15-2"""
import json
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
inv = os.path.join(ROOT, ".calicat", "inventory.json")
d = json.load(open(inv, encoding="utf-8"))

want = sys.argv[1:] or None


def walk(node, path=""):
    if isinstance(node, dict):
        pid = node.get("pageId") or node.get("page_id") or node.get("id")
        if pid and (not want or str(pid) in want):
            keys = [k for k in node.keys()]
            print("=== ", pid, " path=", path)
            print(json.dumps({k: node[k] for k in keys if not isinstance(node[k], (list, dict))}, ensure_ascii=False, indent=2))
            for k in ("layers", "pages", "children"):
                if k in node:
                    print(f"  [{k}]:", json.dumps(node[k], ensure_ascii=False)[:600])
        for k, v in node.items():
            walk(v, path + "/" + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + f"[{i}]")


print("top keys:", list(d.keys()) if isinstance(d, dict) else f"list({len(d)})")
walk(d)
