# -*- coding: utf-8 -*-
"""序号 8（报价单列表）checks 轮红/绿基线转录合成。

用法: python .agents/state/gen-8-checks-evidence.py
读 .agents/state/evidence/review-序号8-checks-red-run{1,2}.json（红）与
   .agents/state/evidence/review-序号8-final-run{1,2}.json（绿）
写 .agents/state/evidence/red-序号8-checks-设计期望值偏差.txt / green-序号8-checks-设计期望值.txt
   以及 requests 证据摘要。
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


def dump(tag, run1, run2, title, out):
    a = load(run1)
    b = load(run2)
    lines = [title, '=' * 78, '']
    for ph in phases(a):
        pa, pb = a[ph], b[ph]
        if not isinstance(pa, dict) or 'checkCount' not in pa:
            continue
        lines.append('%s : checkCount=%s checkFailCount=%s docH=%s docW=%s missingTexts=%s' % (
            ph, pa.get('checkCount'), pa.get('checkFailCount'), pa.get('docScrollHeight'),
            pa.get('docScrollWidth'), pa.get('missingTexts')))
        for f in pa.get('checkFails') or []:
            lines.append('    FAIL %s: got %s want %s' % (f['k'], json.dumps(f['got'], ensure_ascii=False), json.dumps(f['want'], ensure_ascii=False)))
        same = pa.get('checkFailCount') == pb.get('checkFailCount') and pa.get('checkFails') == pb.get('checkFails')
        lines.append('    [两轮独立测量一致? %s]' % ('是' if same else '否'))
        lines.append('')
    req = os.path.join(EVD, 'requests-序号%s-run1.txt' % tag)
    if os.path.exists(req):
        lines.append('serve 实收请求行（run1）:')
        lines.append(open(req, encoding='utf-8').read().strip() or '(空)')
    text = '\n'.join(lines) + '\n'
    with open(os.path.join(EVD, out), 'w', encoding='utf-8') as f:
        f.write(text)
    print('->', out)
    print(text[:400])


dump('8-checks-red', 'review-序号8-checks-red-run1.json', 'review-序号8-checks-red-run2.json',
     '序号 8「报价单列表」设计期望值 checks —— 红基线（修复前源码 + 本轮探针，同一份探针两轮）',
     'red-序号8-checks-设计期望值偏差.txt')
dump('8', 'review-序号8-run1.json', 'review-序号8-run2.json',
     '序号 8「报价单列表」设计期望值 checks —— 绿基线（全部修复后 + 两轮独立测量）',
     'green-序号8-checks-设计期望值.txt')
