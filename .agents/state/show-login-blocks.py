# -*- coding: utf-8 -*-
"""打印登录页样式块里若干选择器的**当前声明**（为行盒修正取准数）。

用法: python .agents/state/show-login-blocks.py
"""
import io
import re

PATH = 'E:/workspaces/hioas/hioas-aap-001/aap-client/src/pages/login/index.vue'
src = io.open(PATH, encoding='utf-8').read()

WANT = ['&__name', '&__en', '&__title', '&__subtitle', '&__hint', '&__label', '&__placeholder',
        '&__tip-text', '&__text']
lines = src.split('\n')
# 找出所有含目标选择器的行，并打印其后 6 行（含所属父选择器上下文：往上找最近的顶层 .xxx {）
for i, l in enumerate(lines):
    s = l.strip()
    if s not in [w + ' {' for w in WANT]:
        continue
    parent = ''
    for j in range(i, -1, -1):
        pj = lines[j]
        if re.match(r'^\.[\w-]+\s*\{', pj):
            parent = pj.strip()
            break
    print('--- %s  (父 %s)  行 %d' % (s, parent, i + 1))
    for k in range(i + 1, min(i + 7, len(lines))):
        print('   %s' % lines[k])
