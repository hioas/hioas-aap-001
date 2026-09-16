# -*- coding: utf-8 -*-
"""跨页「导航标题行盒」口径修正的红/绿转录合成。

读 review-序号<tag>-navtitle-red-run{1,2}.json（改前）与 review-序号<tag>-navtitle-run{1,2}.json（改后），
输出每个页面的：checks 数 / 失败数 / 失败项 / 两轮独立测量差异字段数 / docH / 溢出。
用法: python .agents/state/gen-navtitle-evidence.py
"""
import io
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(REPO, '.agents', 'state', 'evidence')
TAGS = ['8', '10', '10.1', '12', '22']
SKIP = {'userAgent', 'iframeHeightForShot'}


def phases(d):
    ph = [k for k in d if isinstance(d[k], dict) and 'checkCount' in d[k]]
    return {'flat': d} if (not ph and 'checkCount' in d) else d


def load(tag, suffix, run):
    p = os.path.join(EVD, 'review-序号%s-navtitle%s-run%d.json' % (tag, suffix, run))
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else None


def summarize(d, label, out):
    d = phases(d)
    for ph in d:
        b = d[ph]
        if not isinstance(b, dict) or 'checkCount' not in b:
            continue
        out.append('  %s %-8s checks=%-5s 失败=%-3s docH=%-6s 溢出=%-5s 缺文案=%s' % (
            label, ph, b.get('checkCount'), b.get('checkFailCount'), b.get('docScrollHeight'),
            b.get('overflowingCount'), len(b.get('missingTexts') or [])))
        for f in (b.get('checkFails') or [])[:6]:
            out.append('        FAIL %s' % (f if isinstance(f, str) else json.dumps(f, ensure_ascii=False)))


out = ['跨页「导航标题行盒」口径修正 —— 设计声明 vs 实现（红/绿 + 两轮独立测量）',
       'want 一律取 .calicat/raw/pages/<page-id>/design.tree.json 的标题文本叶子：显式 height 优先，否则 fontSize × lineHeight(1.2)。', '']
for tag in TAGS:
    out.append('===== 序号 %s' % tag)
    red = load(tag, '-red', 1)
    gr1, gr2 = load(tag, '', 1), load(tag, '', 2)
    if red:
        out.append('  改前（红基线 · 探针期望值先改、源码后改）:')
        summarize(red, 'RED', out)
    if gr1:
        out.append('  改后（绿）:')
        summarize(gr1, 'GREEN', out)
    if gr1 and gr2:
        a, b = phases(gr1), phases(gr2)
        for ph in [k for k in a if k in b and isinstance(a[k], dict) and 'checkCount' in a[k]]:
            keys = set(a[ph]) | set(b[ph])
            diff = [k for k in sorted(keys) if k not in SKIP and a[ph].get(k, '<MISSING>') != b[ph].get(k, '<MISSING>')]
            out.append('  两轮独立测量 %s: 差异字段 %d %s' % (ph, len(diff), diff[:6] if diff else ''))
    out.append('')

text = '\n'.join(out)
io.open(os.path.join(EVD, 'redgreen-导航标题行盒-20260916-1800.txt'), 'w', encoding='utf-8').write(text + '\n')
print(text)
