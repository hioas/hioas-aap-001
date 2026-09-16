# -*- coding: utf-8 -*-
"""跨页同族位置一致性核对：把 22 个载体页实测里的「顶部栏/导航区」字段拉成一张矩阵。

与 `.agents/state/topbar-matrix.py`（设计声明侧）配对使用：
  - 设计侧：.calicat/raw/pages/<page-id>/design.tree.json 的 顶部栏/顶部导航 声明值
  - 实现侧：.agents/state/evidence/review-序号cov-<tag>-run1.json 的 nav/topbar 类实测字段
用法: python .agents/state/nav-cross-matrix.py [--json out.json]
"""
import glob
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(REPO, '.agents', 'state', 'evidence')
DESIGN = os.path.join(REPO, '.calicat', 'raw', 'pages')
KEY = re.compile(r'(nav|topbar|header|用户头部|head)', re.I)


def design_family(pid):
    f = os.path.join(DESIGN, pid, 'design.tree.json')
    if not os.path.exists(f):
        return None, None, None
    root = json.load(io.open(f, encoding='utf-8'))
    for c in root.get('children') or []:
        for g in c.get('children') or []:
            if re.search(r'顶部栏|顶部导航|顶部|用户头部', g.get('name') or ''):
                return g.get('name'), g.get('padding'), g.get('effects')
    return None, None, None


def flat_phases(d):
    ph = [k for k in d if isinstance(d[k], dict) and 'checkCount' in d[k]]
    return {'flat': d} if (not ph and 'checkCount' in d) else d


files = sorted(glob.glob(os.path.join(EVD, 'review-序号cov-*-run1.json')))
order = {'1': 1, '2': 2, '3': 3, '4': 4, '4-v1': 5, '5': 6, '6': 7, '7': 8, '8': 9, '9': 10,
         '10': 11, '10.1': 12, '11': 13, '12': 14, '12-v1': 15, '12-v2': 16, '12-v3': 17,
         '15': 18, '20': 19, '21': 20, '22': 21, '23': 22}
rows = []
for f in files:
    tag = re.search(r'序号cov-(.+?)-run1\.json$', os.path.basename(f)).group(1)
    d = flat_phases(json.load(io.open(f, encoding='utf-8')))
    ph = [k for k in d if isinstance(d[k], dict)][0]
    body = d[ph]
    pid = None
    for cand in sorted(os.listdir(DESIGN)):
        pass
    nav = {k: v for k, v in body.items() if KEY.search(k) and k != 'userAgent'}
    rows.append({'tag': tag, 'phase': ph, 'navFields': nav,
                 'docH': body.get('docScrollHeight'), 'overflow': body.get('overflowingCount')})

rows.sort(key=lambda r: order.get(r['tag'], 99))
for r in rows:
    print('===== 序号 %s（相 %s）' % (r['tag'], r['phase']))
    for k, v in sorted(r['navFields'].items()):
        s = json.dumps(v, ensure_ascii=False)
        print('   %-26s %s' % (k, s[:200]))
print()
print('页数 %d' % len(rows))
if '--json' in sys.argv:
    p = os.path.join(REPO, sys.argv[sys.argv.index('--json') + 1])
    json.dump(rows, io.open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已写出 %s' % p)
