# -*- coding: utf-8 -*-
"""清理本轮的两个冗余产物：audit-copies/ 目录与重复的 2030 截图（保留 2100 那张）。"""
import os
import shutil

REPO = r'E:/workspaces/hioas/hioas-aap-001'
d = os.path.join(REPO, '.agents', 'state', 'evidence', 'audit-copies')
if os.path.isdir(d):
    shutil.rmtree(d)
    print('removed dir', d)
p = os.path.join(REPO, '.agents', 'state', 'evidence', '20260916-2030-序22-用量概览-textleaf轮-h5-430宽.png')
if os.path.exists(p):
    os.remove(p)
    print('removed file', os.path.basename(p))
print('ok')
