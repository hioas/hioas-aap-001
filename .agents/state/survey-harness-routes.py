# -*- coding: utf-8 -*-
"""列出每个载体页 __measure-*.html 的 iframe 目标路由（对齐台账序号用）。"""
import glob
import io
import os
import re

root = r'E:\workspaces\hioas\hioas-aap-001\.agents\state\h5-measure'
for f in sorted(glob.glob(os.path.join(root, '__measure*.html'))):
    s = io.open(f, encoding='utf-8', errors='replace').read()
    m = re.search(r'src="(/index\.html#/pages/[^"]+)"', s)
    route = m.group(1) if m else '(none)'
    title = re.search(r'<title>(.*?)</title>', s)
    print('%-34s %-46s %s' % (os.path.basename(f), route, title.group(1) if title else ''))
