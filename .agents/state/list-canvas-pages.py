#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打印 Calicat 画布全部页面名（用于判断某交互是否有目标页可导航，不臆造路由）。"""
import io, json

d = json.load(io.open(".calicat/inventory.json", encoding="utf-8"))
print("inventory keys:", list(d.keys()))

pages = d.get("pages") or []
if not pages and isinstance(d.get("canvas"), dict):
    pages = d["canvas"].get("pages") or []
print("page count:", len(pages))
for i, p in enumerate(pages, 1):
    if isinstance(p, dict):
        print("%2d  %s" % (i, p.get("name") or p.get("title") or json.dumps(p, ensure_ascii=False)[:80]))
    else:
        print("%2d  %s" % (i, p))
