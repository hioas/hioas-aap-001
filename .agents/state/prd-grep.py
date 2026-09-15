"""按 UTF-8 关键词文件在 .calicat/prd 中搜索（躲开 bash 中文参数 GBK 问题）。
用法: python .agents/state/prd-grep.py <keywords.txt> [目录..]
keywords.txt 每行一个关键词（UTF-8）。
"""
import os
import sys

kw_file = sys.argv[1]
roots = sys.argv[2:] or ['.calicat/prd']
kws = [l.strip() for l in open(kw_file, encoding='utf-8') if l.strip()]

files = []
for root in roots:
    if os.path.isfile(root):
        files.append(root)
        continue
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            if f.endswith('.md'):
                files.append(os.path.join(dp, f))

for kw in kws:
    print('=' * 8, kw)
    hits = 0
    for f in files:
        try:
            lines = open(f, encoding='utf-8').read().splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines, 1):
            if kw in ln:
                hits += 1
                if hits <= 40:
                    print('%s:%d: %s' % (os.path.basename(f), i, ln.strip()[:220]))
    print('-- hits:', hits)
