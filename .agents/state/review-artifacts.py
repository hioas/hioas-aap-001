#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""复核用：按台账「目标路由」核对 mp-weixin 编译产物。

坑（本脚本已踩过，别重犯）：
- 产物路径是 dist/build/mp-weixin/<pages.json 里的 path>.<ext>（不是 <path>/index.<ext> 目录式）。
  即 pages/login/index → dist/.../pages/login/index.js；pages/quote-form/apikey → dist/.../pages/quote-form/apikey.js。
- wxss **只在有样式时**才产出（uni-app 对无 <style> 的页面不生成空 wxss），故 wxss 缺失不算缺陷，单独标注。
- 必备 = js + json + wxml 三件套。

用法: python .agents/state/review-artifacts.py [--root aap-client]
"""
import csv
import io
import json
import os
import sys

csv_path = ".agents/state/aap-feature-status.csv"
root = "aap-client"
for i, a in enumerate(sys.argv):
    if a == "--root" and i + 1 < len(sys.argv):
        root = sys.argv[i + 1]

dist = os.path.join(root, "dist", "build", "mp-weixin")
text = io.open(csv_path, encoding="utf-8-sig").read()
rows = list(csv.DictReader(io.StringIO(text)))

app_json_path = os.path.join(dist, "app.json")
app_pages = []
if os.path.isfile(app_json_path):
    app_pages = json.load(io.open(app_json_path, encoding="utf-8")).get("pages", [])

REQUIRED = ["js", "json", "wxml"]
bad = []
print("序号 | 路由 | js/json/wxml | wxss | 注册在app.json")
print("-----|------|--------------|------|---------------")
for r in rows:
    idx = (r.get("序号") or "").strip()
    route = (r.get("目标路由") or "").strip().lstrip("/")
    if not route:
        continue
    base = os.path.join(dist, route)
    miss = [e for e in REQUIRED if not os.path.isfile(base + "." + e)]
    wxss = os.path.isfile(base + ".wxss")
    registered = route in app_pages
    if miss or not registered:
        bad.append((idx, route, miss, registered))
    print("%s | /%s | %s | %s | %s" % (
        idx, route,
        "OK" if not miss else "缺" + ",".join(miss),
        "有" if wxss else "无(该页无样式)",
        "是" if registered else "**否**",
    ))

print()
print("dist 存在: %s · app.json 页面数: %d" % (os.path.isdir(dist), len(app_pages)))
if bad:
    print("存在问题 %d 条:" % len(bad))
    for b in bad:
        print("  - %s /%s 缺%s 注册=%s" % (b[0], b[1], b[2], b[3]))
else:
    print("总体: 台账全部路由的 mp-weixin 三件套齐备且已注册")
sys.exit(1 if bad else 0)
