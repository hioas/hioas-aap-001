# -*- coding: utf-8 -*-
"""列出当前全部 textleaf-*.json 的 route/docH/leaf 数（判「dump 是否取到数据后的状态」）。"""
import glob
import io
import json
import os

EVD = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   '.agents', 'state', 'evidence')
for f in sorted(glob.glob(os.path.join(EVD, 'textleaf-*.json'))):
    try:
        d = json.load(io.open(f, encoding='utf-8'))
    except Exception as e:  # noqa: BLE001
        print('%-24s PARSE FAIL %s' % (os.path.basename(f), e))
        continue
    print('%-24s route=%-34s docH=%-6s leafs=%-4s tries=%s' % (
        os.path.basename(f), d.get('route'), d.get('docH'), len(d.get('leafs') or []), d.get('tries')))
