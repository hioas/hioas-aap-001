# -*- coding: utf-8 -*-
"""把序号 1（page-1-2「登录注册」）剩余的 disclaimer__body 登记为「非偏差」（审计模型口径差）。

口径：审计把**块高**（设计显式 height 40 = 2 行）与**单行行盒**（实现 line-height 14.4）直接比较 ——
两者不是同一个量。判据①「设计显式 height 优先」在本例里指的就是块高 40，实现同时满足块高 40 与
每行墨迹位置（设计两行 965..975 / 980..990 = 实现 966..976 / 980..990，18:45 轮已逐行核对）。

证据：evidence/review-序号1-16px-checks-报告.md §3（免责正文 38→40 的修复与墨迹核对）·
      evidence/20260916-序01-登录注册-16px残差收口-h5-430宽.png。

用法: python .agents/state/accept-1-textleaf.py [--dry]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
EVID = 'evidence/review-序号1-16px-checks-报告.md §3 + evidence/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png'
AT = '2026-09-16 20:00'
PAGE = 'page-1-2'

ITEMS = [
    ('disclaimer__body', '设计叶子 8485…/e5e24331 显式 h=40（块高，不是单行行盒）', 'line-height 14.4 · 块高 40（flex 垂直居中，两行）',
     '审计把「块高 40 = 2 行」与「单行行盒」直接比较，属模型口径差：设计该叶子是高 40 的两行容器，'
     '实现用 height:40px + line-height:14.4px + align-items:center 落地 —— 两行墨迹位置与设计逐行相同'
     '（设计 965..975 / 980..990 = 实现 966..976 / 980..990，18:45 轮实测）。'),
]

data = json.load(io.open(P, encoding='utf-8'))
have = {(it.get('page'), (it.get('class') or '').lstrip('.')) for it in data['items']}
added = 0
for cls, declared, impl, reason in ITEMS:
    if (PAGE, cls) in have:
        print('已存在：%s（跳过）' % cls)
        continue
    data['items'].append({
        'page': PAGE, 'tag': '1', 'class': cls, 'declared': declared, 'impl': impl,
        'verdict': 'not-a-deviation', 'reason': reason, 'evidence': EVID, 'at': AT,
    })
    added += 1
print('新增 %d 条（合计 %d 条）' % (added, len(data['items'])))
if '--dry' not in sys.argv:
    io.open(P, 'w', encoding='utf-8', newline='').write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('已写盘 %s' % P)
