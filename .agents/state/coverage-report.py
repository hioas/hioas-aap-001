# -*- coding: utf-8 -*-
"""汇总全量复跑（coverage-rerun.sh）的结果：逐页逐相 checks 数 / 失败数 / 两轮不一致 / docH / 溢出。

用法: python .agents/state/coverage-report.py [--json out.json] [--dir .agents/state/evidence]
证据文件名约定：review-序号cov-<tag>-run{1,2}.json
"""
import glob
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(REPO, '.agents', 'state', 'evidence')
if '--dir' in sys.argv:
    EVD = os.path.join(REPO, sys.argv[sys.argv.index('--dir') + 1])
SKIP = {'userAgent', 'iframeHeightForShot'}

rows, problems = [], []
for f1 in sorted(glob.glob(os.path.join(EVD, 'review-序号cov-*-run1.json'))):
    tag = re.search(r'序号cov-(.+?)-run1\.json$', os.path.basename(f1)).group(1)
    f2 = f1.replace('-run1.json', '-run2.json')
    if not os.path.exists(f2):
        problems.append('%s: 缺 run2' % tag)
        continue
    a = json.load(io.open(f1, encoding='utf-8'))
    b = json.load(io.open(f2, encoding='utf-8'))
    phases = [k for k in a if isinstance(a[k], dict) and 'checkCount' in a[k]]
    if not phases and 'checkCount' in a:
        # 扁平单段测量（早期载体页只写一个 MEASURE_JSON，没有 phase 分组）
        a, b, phases = {'flat': a}, {'flat': b}, ['flat']
    for ph in phases:
        pa, pb = a[ph], b.get(ph, {})
        keys = set(pa) | set(pb)
        diff = [k for k in sorted(keys) if k not in SKIP and pa.get(k, '<MISSING>') != pb.get(k, '<MISSING>')]
        fails = pa.get('checkFails') or []
        rows.append({
            'tag': tag, 'phase': ph,
            'checks': pa.get('checkCount'), 'fail': pa.get('checkFailCount'),
            'phaseDiff': len(diff), 'diffKeys': diff[:8],
            'docH': pa.get('docScrollHeight'), 'docW': pa.get('docScrollWidth'),
            'overflow': pa.get('overflowingCount'), 'missingTexts': pa.get('missingTexts'),
            'failedList': [f if isinstance(f, str) else json.dumps(f, ensure_ascii=False) for f in fails][:6],
        })

print('%-7s %-8s %6s %5s %9s %8s %7s %6s' % ('序号', '相', 'checks', '失败', '两轮差异', 'docH', '溢出', '缺文案'))
print('-' * 70)
bad = 0
for r in rows:
    flag = ''
    if (r['fail'] or 0) > 0 or r['phaseDiff'] > 0 or (r['overflow'] or 0) > 0 or r['missingTexts']:
        flag = '  <<<'
        bad += 1
    print('%-7s %-8s %6s %5s %9s %8s %7s %6s%s' % (
        r['tag'], r['phase'], r['checks'], r['fail'], r['phaseDiff'], r['docH'],
        r['overflow'], len(r['missingTexts'] or []), flag))
    if flag:
        if r['failedList']:
            print('        失败项: %s' % '; '.join(r['failedList'])[:220])
        if r['diffKeys']:
            print('        两轮差异键: %s' % ', '.join(r['diffKeys']))

print()
print('相数 %d · 页数 %d · 有问题的相 %d' % (len(rows), len({r['tag'] for r in rows}), bad))
if problems:
    print('PROBLEM: %s' % '; '.join(problems))

out = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
if out:
    json.dump(rows, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已写出 %s' % out)
