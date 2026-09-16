# -*- coding: utf-8 -*-
"""序号 11（【报价管理】模型定价-详情）checks 轮红/绿基线转录合成。

用法: python .agents/state/gen-11-checks-evidence.py
读 .agents/state/evidence/review-序号11-checks-red-run{1,2}.json（红：修复前源码 + 同一份探针）
   .agents/state/evidence/review-序号11-checks-run{1,2}.json（绿：修复后 + 同一份探针）
   .agents/state/evidence/requests-序号11-checks{,-red}-run{1,2}.txt（serve 实收请求）
写 .agents/state/evidence/red-序号11-checks-设计期望值偏差.txt
   .agents/state/evidence/green-序号11-checks-设计期望值.txt
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(ROOT, '.agents', 'state', 'evidence')


def load(name):
    with open(os.path.join(EVD, name), encoding='utf-8') as f:
        return json.load(f)


def req_text(name):
    p = os.path.join(EVD, name)
    if not os.path.exists(p):
        return ['(缺 %s)' % name]
    with open(p, encoding='utf-8') as f:
        return [l.rstrip('\n') for l in f]


def phases(d):
    return [k for k in d if k.startswith('phase')]


def dump(title, runs, reqs, out):
    a, b = load(runs[0]), load(runs[1])
    lines = [title, '=' * 78, '']
    for ph in phases(a):
        pa, pb = a[ph], b[ph]
        lines.append('%s : %s' % (ph, json.dumps(pa, ensure_ascii=False)[:1500]))
        if isinstance(pb, dict) and pa != pb:
            lines.append('    [run2 与 run1 不一致] %s' % json.dumps(pb, ensure_ascii=False)[:800])
        if isinstance(pa, dict) and 'checkCount' in pa:
            same = pa.get('checkFailCount') == pb.get('checkFailCount') and pa.get('checkFails') == pb.get('checkFails')
            lines.append('    [两轮独立测量一致? %s]' % ('是' if same else '否'))
            lines.append('    checkCount=%s checkFailCount=%s docH=%s docW=%s overflowing=%s missingTexts=%s' % (
                pa.get('checkCount'), pa.get('checkFailCount'), pa.get('docScrollHeight'),
                pa.get('docScrollWidth'), pa.get('overflowingCount'), pa.get('missingTexts')))
            for f in pa.get('checkFails') or []:
                lines.append('    FAIL %s: got %s want %s' % (
                    f['k'], json.dumps(f['got'], ensure_ascii=False), json.dumps(f['want'], ensure_ascii=False)))
    for r in reqs:
        lines.append('')
        lines.append('serve 实收（%s）：' % r)
        lines.extend('    ' + l for l in req_text(r))
    text = '\n'.join(lines) + '\n'
    with open(os.path.join(EVD, out), 'w', encoding='utf-8') as f:
        f.write(text)
    print('wrote', out, len(text), 'bytes')


dump('序号 11 红基线（修复前源码 + 新探针，同一份探针跑两轮）— 设计期望值 checks 偏差',
     ['review-序号11-checks-red-run1.json', 'review-序号11-checks-red-run2.json'],
     ['requests-序号11-checks-red-run1.txt', 'requests-序号11-checks-red-run2.txt'],
     'red-序号11-checks-设计期望值偏差.txt')

dump('序号 11 绿（修复后 + 同一份探针，两轮独立测量）— 设计期望值 checks',
     ['review-序号11-checks-run1.json', 'review-序号11-checks-run2.json'],
     ['requests-序号11-checks-run1.txt', 'requests-序号11-checks-run2.txt'],
     'green-序号11-checks-设计期望值.txt')
