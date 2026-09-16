# -*- coding: utf-8 -*-
"""序号 10.1（供应商档案）checks 轮证据合成。

读 .agents/state/evidence/review-序号10.1-checks-red-run{1,2}.json（红：修复前源码 + 同一份探针两轮）
   .agents/state/evidence/review-序号10.1-checks-run{1,2}.json（绿：修复后两轮独立测量）
写 red-序号10.1-checks-设计期望值偏差.txt / green-序号10.1-checks-设计期望值.txt
   / green-序号10.1-checks-交互回放.txt
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(ROOT, '.agents', 'state', 'evidence')


def load(name):
    with open(os.path.join(EVD, name), encoding='utf-8') as f:
        return json.load(f)


def phases(d):
    return [k for k in d if k.startswith('phase')]


def dump(tag, run1, run2, title, out, quiet_phases=('phase2', 'phase3', 'phase4')):
    a, b = load(run1), load(run2)
    lines = [title, '=' * 78, '']
    for ph in phases(a):
        pa, pb = a[ph], b[ph]
        if not isinstance(pa, dict) or 'checkCount' not in pa:
            continue
        lines.append('%s : checkCount=%s checkFailCount=%s docH=%s docW=%s overflowing=%s missingTexts=%s' % (
            ph, pa.get('checkCount'), pa.get('checkFailCount'), pa.get('docScrollHeight'),
            pa.get('docScrollWidth'), len(pa.get('overflowing') or []), pa.get('missingTexts')))
        for f in pa.get('checkFails') or []:
            lines.append('    FAIL %s: got %s want %s' % (
                f['k'], json.dumps(f['got'], ensure_ascii=False), json.dumps(f['want'], ensure_ascii=False)))
        same = pa.get('checkFailCount') == pb.get('checkFailCount') and pa.get('checkFails') == pb.get('checkFails')
        lines.append('    [两轮独立测量一致? %s]' % ('是' if same else '否'))
        lines.append('')
    for ph in phases(a):
        if ph not in quiet_phases:
            continue
        lines.append('%s: %s' % (ph, json.dumps(a[ph], ensure_ascii=False)))
        lines.append('%s(run2): %s' % (ph, json.dumps(b[ph], ensure_ascii=False)))
        lines.append('')
    req = os.path.join(EVD, 'requests-序号%s-run1.txt' % tag)
    if os.path.exists(req):
        lines.append('serve 实收请求行（run1，写请求带 body）:')
        lines.append(open(req, encoding='utf-8').read().strip() or '(空)')
    text = '\n'.join(lines) + '\n'
    with open(os.path.join(EVD, out), 'w', encoding='utf-8') as f:
        f.write(text)
    print('->', out)


dump('10.1-checks-red', 'review-序号10.1-checks-red-run1.json', 'review-序号10.1-checks-red-run2.json',
     '序号 10.1「供应商档案」设计期望值 checks —— 红基线（修复前源码 + 同一份探针两轮）',
     'red-序号10.1-checks-设计期望值偏差.txt', quiet_phases=())
dump('10.1-checks', 'review-序号10.1-checks-run1.json', 'review-序号10.1-checks-run2.json',
     '序号 10.1「供应商档案」设计期望值 checks —— 绿基线（全部修复后 + 两轮独立测量）',
     'green-序号10.1-checks-设计期望值.txt', quiet_phases=())
dump('10.1-checks', 'review-序号10.1-checks-run1.json', 'review-序号10.1-checks-run2.json',
     '序号 10.1「供应商档案」交互回放（phase2 保存 / phase3 四个入口 / phase4 返回）+ 设计期望值 checks',
     'green-序号10.1-checks-交互回放.txt', quiet_phases=('phase1',))
