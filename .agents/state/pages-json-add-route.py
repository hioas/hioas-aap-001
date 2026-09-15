#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""向 aap-client/src/pages.json 追加上一个页面路由（保留原 CRLF 行尾）。"""
import io, json, sys, os

path = os.path.join("aap-client", "src", "pages.json")
raw = io.open(path, "rb").read().decode("utf-8")
data = json.loads(raw.replace("\r\n", "\n"))

new_path = sys.argv[1]
new_title = sys.argv[2]

if any(p.get("path") == new_path for p in data["pages"]):
    print("already present:", new_path)
else:
    data["pages"].append({"path": new_path, "style": {"navigationStyle": "custom", "navigationBarTitleText": new_title}})
    crlf = "\r\n" if "\r\n" in raw else "\n"
    out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    out = out.replace("\n", crlf)
    io.open(path, "wb").write(out.encode("utf-8"))
    print("added:", new_path)

for p in json.loads(io.open(path, "rb").read().decode("utf-8").replace("\r\n", "\n"))["pages"]:
    print(" -", p["path"])
