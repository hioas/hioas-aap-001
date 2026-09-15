#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查 npm（npmmirror）上 uni-app 相关包的最新 dist-tags，用于钉版本。"""
import json
import urllib.request

PKGS = [
    "@dcloudio/uni-app", "@dcloudio/vite-plugin-uni", "@dcloudio/uni-mp-weixin",
    "@dcloudio/uni-h5", "@dcloudio/uni-components", "vue", "vite", "vitest",
    "@vue/test-utils", "sass", "typescript",
]

for name in PKGS:
    url = "https://registry.npmmirror.com/" + name.replace("/", "%2f")
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.load(r)
        tags = d.get("dist-tags", {})
        picked = ", ".join(f"{k}={v}" for k, v in list(tags.items())[:8])
        print(f"{name:<32} {picked}")
    except Exception as e:  # noqa: BLE001
        print(f"{name:<32} FAILED: {e}")
