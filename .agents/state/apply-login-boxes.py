# -*- coding: utf-8 -*-
"""按**设计显式 height** 修正登录页文本行盒（RED→GREEN 的 GREEN 步）。

依据：`.calicat/raw/pages/page-1-2` 各文本叶子的显式 height（text-leaf audit 查出 10 处行盒偏小/偏大，
     design PNG 色带实测确认：品牌区累计短 8px）。
安全：每个 (父选择器, 子选择器) 必须**恰好命中 1 次**；命中块内若有 line-height 则替换，否则插入。
用法: python .agents/state/apply-login-boxes.py [--dry]
"""
import io
import re
import sys

PATH = 'E:/workspaces/hioas/hioas-aap-001/aap-client/src/pages/login/index.vue'

EDITS = [
    ('.brand', '&__name', '28px', '2774910e h=28（fs20）'),
    ('.brand', '&__en', '20px', '425a7e1c h=20（fs12）'),
    ('.brand', '&__title', '36px', '15a710ce h=36（fs26）'),
    ('.brand', '&__subtitle', '24px', 'b96e4f92 h=24（fs14）'),
    ('.card', '&__title', '28px', 'c127cbae h=28（fs20）'),
    ('.card', '&__hint', '20px', 'd6c0472f h=20（fs12）'),
    ('.field', '&__label', '18px', '125de7eb 等 3 处 h=18（fs13）'),
    ('.field', '&__placeholder', '16.8px', '3d537892 fs14×lh1.2 = 16.8（无显式 h）'),
    ('.field', '&__tip-text', '14.4px', '345fa279 fs12×lh1.2 = 14.4（无显式 h）'),
    ('.footer', '&__text', '18px', '页脚说明 h=18（fs11）'),
]

lines = io.open(PATH, encoding='utf-8').read().split('\n')


def parent_of(i):
    for j in range(i, -1, -1):
        m = re.match(r'^(\.[\w-]+)\s*\{', lines[j])
        if m:
            return m.group(1)
    return ''


plan = []
for parent, child, value, why in EDITS:
    hits = []
    for i, l in enumerate(lines):
        if l.strip() == child + ' {' and parent_of(i) == parent:
            hits.append(i)
    if len(hits) != 1:
        print('!! %s %s 命中 %d 次（要求 1）' % (parent, child, len(hits)))
        sys.exit(1)
    i = hits[0]
    close = next(k for k in range(i + 1, len(lines)) if lines[k].strip() == '}')
    lh_idx = next((k for k in range(i + 1, close) if lines[k].strip().startswith('line-height:')), None)
    plan.append((i, close, lh_idx, value, why, parent + ' ' + child))

plan.sort(key=lambda t: -t[0])
for i, close, lh_idx, value, why, sel in plan:
    if lh_idx is not None:
        old = lines[lh_idx]
        indent = old[:len(old) - len(old.lstrip())]
        lines[lh_idx] = '%sline-height: %s; /* 设计 %s */' % (indent, value, why)
        print('替换 %-24s %s → line-height: %s  (%s)' % (sel, old.strip(), value, why))
    else:
        fs_idx = next((k for k in range(i + 1, close) if lines[k].strip().startswith('font-size:')), i)
        indent = lines[fs_idx][:len(lines[fs_idx]) - len(lines[fs_idx].lstrip())]
        lines.insert(fs_idx + 1, '%sline-height: %s; /* 设计 %s */' % (indent, value, why))
        print('插入 %-24s line-height: %s  (%s)' % (sel, value, why))

if '--dry' in sys.argv:
    print('dry-run：未写文件')
    sys.exit(0)
io.open(PATH, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('已写入 %s' % PATH)
