# -*- coding: utf-8 -*-
"""任意页面的「交互切片先看红」取证：临时删掉 @tap/@change 绑定 → 跑测试看真红 → restore（SKILL §4.17）。

用法（在仓库根目录执行）:
  python .agents/state/strip-page-handlers.py strip  <页面相对路径>
  python .agents/state/strip-page-handlers.py restore <页面相对路径>

为什么需要它：页面写完再补交互测试必然一跑就绿（等于测试后写）——先删绑定跑出真红，再恢复。
snapshot 存到 %LOCALAPPDATA%/Temp/<文件名>-stripped-bak.vue。
"""
import os
import re
import shutil
import sys

mode = sys.argv[1] if len(sys.argv) > 1 else 'strip'
page = sys.argv[2] if len(sys.argv) > 2 else 'aap-client/src/pages/usage/index.vue'
# ⚠️ 快照名必须**含页面路径**（序号 23 踩坑：只用 basename 时 usage/index.vue 与 settings/index.vue 都叫
# `index-stripped-bak.vue`，restore 会把上一页的快照覆盖到本页 → 页面被写坏、13 例全红）。
bak = os.path.join(
    os.environ['LOCALAPPDATA'],
    'Temp',
    re.sub(r'[^0-9A-Za-z]+', '_', page).strip('_') + '.bak.vue'
)

# 需要临时摘掉的交互绑定：**正则匹配全部 @tap/@change（含 .stop 等修饰符）**，不再逐页维护清单
# （序号 22 起为硬编码清单；序号 23 改为正则，任意新页面直接可用）
BINDING_RE = re.compile(r'\s+@(?:tap|change)(?:\.\w+)*="[^"]*"')


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
        write(bak + '.src', page)
    writer = read(bak + '.src') if os.path.exists(bak + '.src') else ''
    if writer and writer != page:
        sys.exit('refuse: 快照 %s 属于 %s，不是 %s' % (bak, writer, page))
    stripped, count = BINDING_RE.subn('', src)
    write(page, stripped)
    print('strip: %s -> 摘掉 %d 处 @tap/@change（快照 %s）' % (page, count, bak))
elif mode == 'restore':
    if not os.path.exists(bak):
        sys.exit('refuse: 快照不存在 %s（先跑 strip，别手工恢复）' % bak)
    writer = read(bak + '.src') if os.path.exists(bak + '.src') else ''
    if writer and writer != page:
        sys.exit('refuse: 快照 %s 属于 %s，拒绝覆盖 %s' % (bak, writer, page))
    shutil.copyfile(bak, page)
    src = read(page)
    print('restore: %s -> @tap/@change %d 处（来自 %s）' % (page, len(BINDING_RE.findall(src)), bak))
else:
    print('usage: strip|restore <页面相对路径>')
