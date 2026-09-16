# -*- coding: utf-8 -*-
"""打印测量 JSON 的某相（默认全部）为 pretty JSON。用法: python show-json.py <file.json> [phaseKey] [--keys a,b]"""
import io
import json
import sys

path = sys.argv[1]
data = json.load(io.open(path, encoding='utf-8'))
key = None
for a in sys.argv[2:]:
    if not a.startswith('--'):
        key = a
if key:
    data = {key: data.get(key)}
print(json.dumps(data, ensure_ascii=False, indent=1))
