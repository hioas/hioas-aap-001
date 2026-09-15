# -*- coding: utf-8 -*-
"""切片 5 取证：临时删掉页面里的 @tap 绑定与交互 handler → 先看红（SKILL §4.14）。
用法: strip-mine-handlers.py strip|restore
"""
import os
import shutil
import sys

PAGE = 'src/pages/mine/index.vue'
BAK = os.path.join(os.environ['LOCALAPPDATA'], 'Temp', 'mine-index-slice5-bak.vue')


def read(p):
    return open(p, encoding='utf-8').read()


def write(p, s):
    open(p, 'w', encoding='utf-8').write(s)


mode = sys.argv[1]
if mode == 'strip':
    s = read(PAGE)
    s = s.replace(' data-testid="wallet-withdraw" @tap="onWithdraw"', ' data-testid="wallet-withdraw"')
    s = s.replace(' :data-testid="`row-${row.key}`" @tap="onRowTap(row)"', ' :data-testid="`row-${row.key}`"')
    write(PAGE, s)
    print('strip: remaining @tap =', s.count('@tap'))
elif mode == 'restore':
    shutil.copyfile(BAK, PAGE)
    print('restore: @tap =', read(PAGE).count('@tap'))
else:
    print('usage: strip|restore')
