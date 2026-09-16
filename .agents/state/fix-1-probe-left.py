# -*- coding: utf-8 -*-
"""fix-1-probe-left.py — 修正载体页新增 checks 里 rects() 的键名（本探针 rects() 返回 x，不是 left）。

用法: python .agents/state/fix-1-probe-left.py [--dry]
"""
import io
import sys

P = 'E:/workspaces/hioas/hioas-aap-001/.agents/state/h5-measure/__measure-login.html'
dry = '--dry' in sys.argv
src = io.open(P, encoding='utf-8', newline='').read()

EDITS = [
    ("chk('fieldBox.contentLeft', marks.length ? Math.round(marks[0].left) : null, 48)",
     "chk('fieldBox.contentLeft', marks.length ? marks[0].x : null, 48)"),
    ("chk('mark.lefts', marks.map(function (r) { return r.left }).join(','), '48,48,48')",
     "chk('mark.lefts', marks.map(function (r) { return r.x }).join(','), '48,48,48')"),
    ("chk('input.lefts', inputs.map(function (r) { return r.left }).join(','), '119,76,76')",
     "chk('input.lefts', inputs.map(function (r) { return r.x }).join(','), '119,76,76')"),
]

out = src
problems = []
for old, new in EDITS:
    n = out.count(old)
    if n != 1:
        problems.append('anchor hit %d: %r' % (n, old[:70]))
        continue
    out = out.replace(old, new)
if problems:
    print('ABORT')
    for p in problems:
        print(' -', p)
    raise SystemExit(1)
print('ok %d edits' % len(EDITS))
if not dry:
    io.open(P, 'w', encoding='utf-8', newline='').write(out)
    print('written')
