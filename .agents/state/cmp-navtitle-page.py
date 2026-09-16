# -*- coding: utf-8 -*-
"""对比「导航标题行盒」修正前后，载体页实测的标题矩形 / 导航矩形 / 整页高是否只动了行盒。

读 review-序号cov-<tag>-run1.json（改前）与 review-序号<tag>-navtitle-run1.json（改后），
打印 nav* / title* 相关字段的前后值。用法: python .agents/state/cmp-navtitle-page.py
"""
import json
import io
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(REPO, '.agents', 'state', 'evidence')
TAGS = ['8', '10', '10.1', '12', '22']
KEY = re.compile(r'(nav|topbar)', re.I)


def body(path):
    d = json.load(io.open(path, encoding='utf-8'))
    for k in d:
        if isinstance(d[k], dict) and 'checkCount' in d[k]:
            return d[k]
    return d


for tag in TAGS:
    a = body(os.path.join(EVD, 'review-序号cov-%s-run1.json' % tag))
    b = body(os.path.join(EVD, 'review-序号%s-navtitle-run1.json' % tag))
    print('===== 序号 %s' % tag)
    keys = sorted({k for k in list(a) + list(b) if KEY.search(k) and not k.startswith('userAgent')})
    for k in keys:
        x, y = a.get(k, '<无>'), b.get(k, '<无>')
        flag = '' if x == y else '   ← 变化'
        print('   %-24s 改前=%-58s 改后=%s%s' % (k, json.dumps(x, ensure_ascii=False)[:58],
                                               json.dumps(y, ensure_ascii=False)[:58], flag))
    for k in ('docScrollHeight', 'docScrollWidth', 'overflowingCount', 'checkFailCount'):
        x, y = a.get(k), b.get(k)
        print('   %-24s 改前=%-58s 改后=%s%s' % (k, x, y, '' if x == y else '   ← 变化'))
