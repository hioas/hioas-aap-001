# -*- coding: utf-8 -*-
"""任意页面的「交互切片先看红」取证：临时删掉 @tap/@change 绑定 → 跑测试看真红 → restore（SKILL §4.17）。

用法（在仓库根目录执行）:
  python .agents/state/strip-page-handlers.py strip  <页面相对路径>
  python .agents/state/strip-page-handlers.py restore <页面相对路径>

为什么需要它：页面写完再补交互测试必然一跑就绿（等于测试后写）——先删绑定跑出真红，再恢复。
snapshot 存到 %LOCALAPPDATA%/Temp/<文件名>-stripped-bak.vue。
"""
import os
import shutil
import sys

mode = sys.argv[1] if len(sys.argv) > 1 else 'strip'
page = sys.argv[2] if len(sys.argv) > 2 else 'aap-client/src/pages/usage/index.vue'
bak = os.path.join(os.environ['LOCALAPPDATA'], 'Temp', os.path.basename(page).replace('.vue', '') + '-stripped-bak.vue')

# 需要临时摘掉的交互绑定（出现即删，其余不动）
BINDINGS = [
    ' @tap="onBack"',
    ' @change="onMonthChange"',
    ' @tap="onDetailEntry"',
    ' @tap="onWithdraw"',
    ' @tap="onRowTap(row)"',
]


def read(p):
    with open(p, encoding='utf-8') as fh:
        return fh.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(s)


if mode == 'strip':
    src = read(page)
    if not os.path.exists(bak):
        shutil.copyfile(page, bak)
    for binding in BINDINGS:
        src = src.replace(binding, '')
    write(page, src)
    print('strip: %s -> @tap/@change 剩余 %d 处（快照 %s）' % (page, src.count('@tap') + src.count('@change'), bak))
elif mode == 'restore':
    shutil.copyfile(bak, page)
    src = read(page)
    print('restore: %s -> @tap/@change %d 处' % (page, src.count('@tap') + src.count('@change')))
else:
    print('usage: strip|restore <页面相对路径>')
