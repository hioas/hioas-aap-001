# -*- coding: utf-8 -*-
"""画布「全新版本」覆盖核对：当前画布帧列表 vs 台账（已实现范围）vs 未覆盖帧的性质。

口径（状态文件 §1 C）：「全新版本」= Calicat 文件 2095515676955668480 / 画布 2095515676976640000
的**当前状态**。本脚本回答三个问题并留证：
  1. 台账里每一行是否仍指向**当前画布**上存在、且 layer_id 一致的帧（台账是否过期/指错帧）；
  2. 当前画布上是否存在**报价端 · 小程序**的帧未被台账覆盖（= 有页面没实现）；
  3. 未被台账覆盖的帧分别是什么（应全部是管理端 / 画布根容器，范围外）。

用法: python .agents/state/canvas-coverage-check.py [--out evidence/画布覆盖核对.txt]
"""
import csv
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = os.path.join(REPO, '.calicat', 'raw', 'pages.json')
INV = os.path.join(REPO, '.calicat', 'inventory.json')
LEDGER = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')

live = json.load(io.open(LIVE, encoding='utf-8'))['page_list']
inv = json.load(io.open(INV, encoding='utf-8'))
layer_of = {p['id']: p.get('sourceLayerId') for p in inv['pages']}
name_of = {p['id']: p.get('name') for p in inv['pages']}
live_by_layer = {p['layer_id']: p['name'] for p in live}

rows = list(csv.DictReader(io.open(LEDGER, encoding='utf-8')))
out = []
out.append('画布帧数 %d · 台账行数 %d · inventory 帧数 %d' % (len(live), len(rows), len(inv['pages'])))
out.append('')

bad = 0
covered_layers = set()
out.append('--- ① 台账每行 ↔ 当前画布 ---')
for r in rows:
    pid = r['页面ID']
    layer = layer_of.get(pid)
    name = name_of.get(pid)
    if layer not in live_by_layer:
        out.append('FAIL 序号 %-6s %-12s layer_id %s 不在当前画布上' % (r['序号'], pid, layer))
        bad += 1
        continue
    if live_by_layer[layer] != name:
        out.append('FAIL 序号 %-6s %-12s 帧名漂移: 台账=%r 画布=%r' % (r['序号'], pid, name, live_by_layer[layer]))
        bad += 1
        continue
    covered_layers.add(layer)
    out.append('OK   序号 %-6s %-12s %-44s %s' % (r['序号'], pid, name[:44], layer[:8]))
out.append('')

out.append('--- ②③ 未被台账覆盖的当前画布帧 ---')
report_side = re.compile('报价端')
uncovered_quote = []
for p in live:
    if p['layer_id'] in covered_layers:
        continue
    is_quote = bool(report_side.search(p['name'] or ''))
    tag = '未覆盖·报价端❗' if is_quote else '未覆盖·范围外'
    out.append('%-14s %-46s %s' % (tag, (p['name'] or '')[:46], p['layer_id']))
    if is_quote:
        uncovered_quote.append(p)

out.append('')
out.append('结论: 台账失配 %d · 未覆盖的报价端帧 %d' % (bad, len(uncovered_quote)))
if uncovered_quote:
    out.append('❗ 画布上存在未被实现的报价端帧：%s' % '; '.join(p['name'] for p in uncovered_quote))

text = '\n'.join(out)
print(text)
out_path = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
if out_path:
    p = out_path if os.path.isabs(out_path) else os.path.join(REPO, out_path)
    io.open(p, 'w', encoding='utf-8').write(text + '\n')
    print('\n已写出 %s' % p)
