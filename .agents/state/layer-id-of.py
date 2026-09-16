"""打印台账某序号的 layer_id / 帧名 / 目标路由（来源: .calicat/raw/pages.json + inventory.json）。

用法: python .agents/state/layer-id-of.py 10.1
"""
import json
import io
import os
import sys

REPO = r'E:/workspaces/hioas/hioas-aap-001'
tag = sys.argv[1] if len(sys.argv) > 1 else '10.1'

inv = json.load(io.open(os.path.join(REPO, '.calicat', 'inventory.json'), encoding='utf-8'))
items = inv.get('pages') or inv.get('items') or []
for it in items:
    s = json.dumps(it, ensure_ascii=False)
    if tag in s:
        print(json.dumps(it, ensure_ascii=False)[:600])
