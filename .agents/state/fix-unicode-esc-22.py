# -*- coding: utf-8 -*-
"""修掉证据文件里被 echo 原样写出的 \\uXXXX 转义（只在指定文件里替换，安全）。"""
import io
import os

REPO = r'E:/workspaces/hioas/hioas-aap-001'
names = ['evidence/cmp-序号22-趋势图区-设计SVGvs实现dataURI.txt']
REPL = {'\\u0394': 'Δ', '\\u2264': '≤', '\\u2194': '↔'}
for n in names:
    p = os.path.join(REPO, n)
    t = io.open(p, encoding='utf-8').read()
    for k, v in REPL.items():
        t = t.replace(k, v)
    io.open(p, 'w', encoding='utf-8', newline='').write(t)
    print('%s: %d 处转义已修' % (n, sum(t.count(v) for v in REPL.values())))
