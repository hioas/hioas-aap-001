#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Print one page record from .calicat/inventory.json. Usage: show-inv-page.py <page-id>"""
import io, json, sys

want = sys.argv[1]
d = json.load(io.open('.calicat/inventory.json', encoding='utf-8'))
for p in d['pages']:
    if p.get('id') == want or p.get('pageId') == want:
        print(json.dumps(p, ensure_ascii=False, indent=2))
