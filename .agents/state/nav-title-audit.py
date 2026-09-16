# -*- coding: utf-8 -*-
"""跨页核对：顶部栏「标题」的行盒 —— 设计声明 vs 实现 CSS line-height。

设计声明（want）：顶部栏子树里**标题文本叶子**（非 remixicon、字号最大的一条）的
  显式 height（数值优先）或 fontSize × lineHeight（设计 lh 恒为 1.2）。
实现（got）：该页样式里导航标题类（`.nav__title` / `.topbar__title` / `__nav-title`）的 line-height。
用途：同一视觉位置在不同帧里按同一声明实现（跨页一致性），逐帧核对而非套用某一页的倍数。

用法: python .agents/state/nav-title-audit.py [--out evidence/nav-title-audit.txt]
"""
import csv
import glob
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES = os.path.join(REPO, '.calicat', 'raw', 'pages')
SRC = os.path.join(REPO, 'aap-client', 'src')
LEDGER = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')
TOPBAR_RE = re.compile(r'顶部栏|顶部导航|顶部|用户头部')
FAMILY_FONT = re.compile(r'remixicon', re.I)


def find_bar(root):
    for c in root.get('children') or []:
        for g in c.get('children') or []:
            if TOPBAR_RE.search(g.get('name') or ''):
                return g
    return None


def title_leaf(bar):
    """标题 = 顶部栏子树里最大的非图标文本叶子（fs 最大；同 fs 取最靠前）。"""
    hits = []

    def walk(n, d):
        txt = n.get('content') or n.get('text')
        if txt is not None and not FAMILY_FONT.search(str(n.get('fontFamily') or '')):
            hits.append((float(n.get('fontSize') or 0), -d, n))
        for ch in n.get('children') or []:
            walk(ch, d + 1)
    walk(bar, 0)
    hits.sort(key=lambda t: (-t[0], t[1]))
    return hits[0][2] if hits else None


def declared_box(leaf):
    h = leaf.get('height')
    fs = float(leaf.get('fontSize') or 0)
    lh = leaf.get('lineHeight')
    if isinstance(h, (int, float)) or (isinstance(h, str) and re.match(r'^\d+(\.\d+)?$', h)):
        return float(h), 'height=%s' % h
    try:
        return round(fs * float(lh), 2), 'fs%s×lh%s' % (leaf.get('fontSize'), lh)
    except (TypeError, ValueError):
        return None, '无声明'


def _tokens():
    """读 tokens.scss 的 `$font-*: Npx;` 映射，用于把 `font-size: $font-2xl` 还原成数值。"""
    f = os.path.join(SRC, 'styles', 'tokens.scss')
    d = {}
    if os.path.exists(f):
        for m in re.finditer(r'(\$[\w-]+):\s*([\d.]+)px', io.open(f, encoding='utf-8').read()):
            d[m.group(1)] = float(m.group(2))
    return d


TOKENS = _tokens()


def impl_lineheight(route):
    """在 src 里找该路由页面文件（找不到则退到共用组件），取导航「标题」类的行盒声明。

    返回 (行盒数值或 None, 说明)。行盒 = 显式 line-height；为**无单位**倍数时按
    同一条规则里的 font-size（支持 tokens.scss 变量）换算，否则无法判读。
    """
    rel = route.strip('/')
    page_files = [f for f in glob.glob(os.path.join(SRC, 'pages', '**', '*.vue'), recursive=True)
                  if os.path.relpath(f, SRC).replace('\\', '/') == rel + '.vue']
    comp_files = glob.glob(os.path.join(SRC, 'components', '**', '*.vue'), recursive=True)
    # 只认「标题」类本身（`.nav__title` / `.topbar__title`），排除 `.nav__titles` 包装类与 `-wrap`
    pat = re.compile(r'\.(?:[\w-]+__)?title\s*\{([^}]*)\}')
    for files in (page_files, comp_files):
        for f in files:
            text = io.open(f, encoding='utf-8').read()
            m = pat.search(text)
            if not m:
                continue
            body = m.group(1)
            lh = re.search(r'line-height:\s*([^;]+);', body)
            if not lh:
                continue
            raw = lh.group(1).strip()
            where = '%s %s' % (os.path.relpath(f, SRC).replace('\\', '/'), m.group(0).split('{')[0].strip())
            mm = re.match(r'^([\d.]+)px$', raw)
            if mm:
                return float(mm.group(1)), '%s · line-height:%s' % (where, raw)
            fm = re.search(r'font-size:\s*([^;]+);', body)
            fsv = None
            if fm:
                fsraw = fm.group(1).strip()
                pm = re.match(r'^([\d.]+)px$', fsraw)
                if pm:
                    fsv = float(pm.group(1))
                elif fsraw in TOKENS:
                    fsv = TOKENS[fsraw]
            try:
                mult = float(raw)
            except ValueError:
                return None, '%s · line-height:%s（无法判读）' % (where, raw)
            if fsv is None:
                return None, '%s · line-height:%s×fs?（字号未解析）' % (where, raw)
            return round(fsv * mult, 2), '%s · line-height:%s × fs%s' % (where, raw, fsv)
    return None, '(未找到标题类)'


rows = []
for r in csv.DictReader(io.open(LEDGER, encoding='utf-8')):
    pid, route = r['页面ID'], r['目标路由']
    f = os.path.join(PAGES, pid, 'design.tree.json')
    if not os.path.exists(f):
        continue
    bar = find_bar(json.load(io.open(f, encoding='utf-8')))
    if bar is None:
        continue
    leaf = title_leaf(bar)
    if leaf is None:
        continue
    want, how = declared_box(leaf)
    gotnum, sel = impl_lineheight(route)
    flag = '' if (want is None or gotnum is None or abs(gotnum - want) < 0.5) else '  <<< 偏差'
    rows.append((r['序号'], pid, str(leaf.get('content'))[:20], how, want, gotnum, sel, flag))

print('%-7s %-12s %-20s %-14s %-8s %-8s %s' % ('序号', '页面', '标题文案', '设计声明', 'want', 'impl', '实现位置 / 判读'))
print('-' * 108)
for t in rows:
    print('%-7s %-12s %-20s %-14s %-8s %-8s %s%s' % (t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7]))
bad = [t for t in rows if t[7]]
print()
print('核对 %d 页 · 行盒不一致 %d 页' % (len(rows), len(bad)))
for t in bad:
    print('  偏差: 序号 %s（%s）设计 want=%s vs 实现行盒=%s' % (t[0], t[1], t[4], t[5]))
if '--out' in sys.argv:
    p = os.path.join(REPO, sys.argv[sys.argv.index('--out') + 1])
    lines = ['%-7s %-12s %-20s %-14s %-8s %-8s %s%s' % t for t in rows]
    lines.append('核对 %d 页 · 行盒不一致 %d 页' % (len(rows), len(bad)))
    for t in bad:
        lines.append('  偏差: 序号 %s（%s）设计 want=%s vs 实现行盒=%s' % (t[0], t[1], t[4], t[5]))
    io.open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('已写出 %s' % p)
