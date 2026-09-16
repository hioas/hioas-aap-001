# -*- coding: utf-8 -*-
"""跨页审计：设计**文本叶子**的声明行盒 / 字号 / 字重 vs 实现 DOM 的 computed 值。

数据源：
  设计侧 = .calicat/raw/pages/<page-id>/design.tree.json（文本叶子 = 有 content/text 且字体非 remixicon）
  实现侧 = .agents/state/evidence/textleaf-<序号>.json（textleaf-scan.py 产出的全页文本叶子 DOM dump）

匹配口径：**按渲染文案精确匹配**（去空白），所以设计叶子必须真的渲染出来才会被比对；
         未匹配到的叶子单独计数（不当作偏差 —— 它们受 mock 数据/条件分支影响）。

want（声明行盒）：显式数值 height 优先；否则 fontSize × lineHeight（设计 lh 多为 1.2）。
                  lineHeight 缺失 / 'normal' / 'auto' → 记为「无声明」，不比对。
got：computed line-height（px）。'normal' → 判读不了，单列。
另比 fontSize 与 fontFamily→字重（SemiBold 600 / Medium 500 / Bold 700 / Regular 400）。

用法:
  python .agents/state/textleaf-audit.py [序号 ...] [--out evidence/textleaf-audit.txt] [--all-classes]
  默认只打印「有偏差的 class」聚合行；--all-classes 打印全部比对过的 class。
"""
import csv
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = os.path.join(REPO, '.agents', 'state')
PAGES = os.path.join(REPO, '.calicat', 'raw', 'pages')
EVD = os.path.join(STATE, 'evidence')
FAMILY_ICON = re.compile(r'remixicon', re.I)
WEIGHT_BY_NAME = [('extrabold', 800), ('semibold', 600), ('demibold', 600), ('black', 900),
                  ('bold', 700), ('medium', 500), ('light', 300), ('regular', 400), ('normal', 400)]


def fam_weight(fam):
    f = (fam or '').lower()
    for k, w in WEIGHT_BY_NAME:
        if k in f:
            return w
    return None


def num(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        m = re.match(r'^(\d+(\.\d+)?)\s*px$', s)
        if m:
            return float(m.group(1))
        if re.match(r'^\d+(\.\d+)?$', s):
            return float(s)
    return None


def declared_box(leaf):
    fs = num(leaf.get('fontSize'))
    h = num(leaf.get('height'))
    lh = num(leaf.get('lineHeight'))
    if h is not None:
        return h, 'h=%s' % leaf.get('height')
    if fs is not None and lh is not None:
        return round(fs * lh, 2), 'fs%s×lh%s' % (leaf.get('fontSize'), leaf.get('lineHeight'))
    return None, '无声明'


def design_leaves(pid):
    f = os.path.join(PAGES, pid, 'design.tree.json')
    if not os.path.exists(f):
        return []
    out = []

    def walk(n):
        if not isinstance(n, dict):
            return
        txt = n.get('content')
        if txt is None:
            txt = n.get('text')
        if txt is not None and str(txt).strip() and not FAMILY_ICON.search(str(n.get('fontFamily') or '')):
            out.append(n)
        for ch in n.get('children') or []:
            walk(ch)
    walk(json.load(io.open(f, encoding='utf-8')))
    return out


def norm_text(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def main():
    av = sys.argv[1:]
    flag_vals = set()
    for i, a in enumerate(av):
        if a in ('--out',) and i + 1 < len(av):
            flag_vals.add(av[i + 1])
    args = [a for a in av if not a.startswith('--') and a not in flag_vals]
    flags = [a for a in av if a.startswith('--')]
    out_path = None
    if '--out' in sys.argv:
        out_path = os.path.join(REPO, sys.argv[sys.argv.index('--out') + 1])
    all_classes = '--all-classes' in flags

    rows = list(csv.DictReader(io.open(os.path.join(STATE, 'aap-feature-status.csv'), encoding='utf-8')))
    if args:
        rows = [r for r in rows if r['序号'] in set(args)]
    accept = {}
    acc_f = os.path.join(STATE, 'textleaf-accept.json')
    if os.path.exists(acc_f):
        for it in json.load(io.open(acc_f, encoding='utf-8')).get('items') or []:
            accept[(it.get('page'), str(it.get('class') or '').split(' ')[0].lstrip('.'))] = it

    lines = []
    total_leaves = total_matched = total_dev = total_unmatched = total_ambig = 0
    accepted = 0
    for r in rows:
        tag, pid = r['序号'], r['页面ID']
        dom_f = os.path.join(EVD, 'textleaf-%s.json' % tag)
        if not os.path.exists(dom_f):
            lines.append('== 序号 %-7s %-12s （无 DOM dump，先跑 textleaf-scan.py）' % (tag, pid))
            continue
        dom = json.load(io.open(dom_f, encoding='utf-8'))
        bytext = {}
        for lf in dom.get('leafs') or []:
            if (lf.get('tg') or '') in ('title', 'meta', 'style', 'script', 'link'):
                continue
            bytext.setdefault(norm_text(lf.get('t')), []).append(lf)
        dls = design_leaves(pid)
        total_leaves += len(dls)
        # 文案索引：同一文案在**多个设计叶子**且声明值不同 → 无法唯一归属，整条跳过（避免自造偏差）
        by_design_text = {}
        for d in dls:
            t = norm_text(d.get('content') if d.get('content') is not None else d.get('text'))
            w, _h = declared_box(d)
            by_design_text.setdefault(t, set()).add((num(d.get('fontSize')), w, fam_weight(d.get('fontFamily'))))
        ambiguous = sorted(t for t, s in by_design_text.items() if len(s) > 1)
        total_ambig += len(ambiguous)
        agg = {}
        unmatched = []
        skipped = 0
        for d in dls:
            want, how = declared_box(d)
            t = norm_text(d.get('content') if d.get('content') is not None else d.get('text'))
            hits = bytext.get(t) or []
            if t in ambiguous:
                if hits:
                    skipped += 1
                continue
            if not hits:
                unmatched.append(t)
                continue
            total_matched += 1
            dfs = num(d.get('fontSize'))
            dfw = fam_weight(d.get('fontFamily'))
            did = (d.get('id') or '')[:8]
            for h in hits:
                cls = h.get('c') or ((h.get('ch') or [''])[0]) or h.get('tg')
                key = (cls, want, dfs, dfw)
                rec = agg.setdefault(key, {'n': 0, 'want': want, 'how': how, 'got': set(), 'fs_want': dfs,
                                           'fs_got': set(), 'fw_want': dfw, 'fw_got': set(), 'sample': t,
                                           'al': set(), 'chain': h.get('ac'), 'ids': set()})
                rec['n'] += 1
                rec['ids'].add(did)
                lh = h.get('lh')
                got = num(lh)
                rec['got'].add('normal' if lh == 'normal' else got)
                rec['fs_got'].add(num(h.get('fs')))
                rec['fw_got'].add(int(h.get('fw')) if str(h.get('fw')).isdigit() else h.get('fw'))
                rec['al'].add(h.get('al'))
        total_unmatched += len(unmatched)
        devs = []
        for key, rec in sorted(agg.items(), key=lambda kv: str(kv[0])):
            cls = key[0]
            kinds = []
            if rec['want'] is not None:
                bad = [g for g in rec['got'] if isinstance(g, float) and abs(g - rec['want']) > 0.5]
                if bad:
                    kinds.append('行盒 want=%s(%s) got=%s' % (rec['want'], rec['how'], sorted(str(g) for g in rec['got'])))
            elif rec['got'] and rec['got'] != {None}:
                kinds.append('行盒 want=无声明 got=%s' % sorted(str(g) for g in rec['got']))
            if rec['fs_want'] is not None and rec['fs_got'] - {rec['fs_want']}:
                kinds.append('字号 want=%s got=%s' % (rec['fs_want'], sorted(str(g) for g in rec['fs_got'])))
            if rec['fw_want'] is not None and rec['fw_got'] - {rec['fw_want']}:
                kinds.append('字重 want=%s got=%s' % (rec['fw_want'], sorted(str(g) for g in rec['fw_got'])))
            if kinds:
                acc = accept.get((pid, cls.split(' ')[0]))
                if acc and acc.get('verdict') == 'not-a-deviation':
                    devs.append((cls, rec, ['已核定(非偏差): %s' % acc.get('reason', '')[:80]]))
                    accepted += 1
                else:
                    devs.append((cls, rec, kinds))
            elif all_classes:
                devs.append((cls, rec, ['OK']))
        total_dev += len(devs)
        lines.append('== 序号 %-7s %-12s 文本叶子 %d · 匹配 %d · 未渲染 %d · 待判读 class %d · 已核定 %d'
                     % (tag, pid, len(dls), sum(v['n'] for v in agg.values()), len(unmatched),
                        len([d for d in devs if not str(d[2][0]).startswith('已核定')]), accepted))
        for cls, rec, kinds in devs:
            lines.append('   %-34s n=%-3s %s' % (cls[:34], rec['n'], ' | '.join(kinds)))
            if kinds != ['OK']:
                lines.append('   %-34s   leaf=%s sample=%r al=%s fs=%s%s' % (
                    '', sorted(rec['ids']), rec['sample'][:40], sorted(str(a) for a in rec['al']), rec['fs_want'],
                    (' chain=' + str(rec['chain'])[:70]) if rec.get('chain') else ''))
        if unmatched:
            lines.append('   未渲染叶子(%d): %s' % (len(unmatched), ' / '.join(unmatched[:8])))
        if skipped:
            lines.append('   口径跳过(文案在设计里多义，%d 条): %s' % (len(ambiguous), ' / '.join(ambiguous[:10])))
    lines.append('')
    lines.append('合计: 设计文本叶子 %d · 匹配 %d · 未渲染 %d · 有偏差 class %d'
                 % (total_leaves, total_matched, total_unmatched, total_dev))
    text = '\n'.join(lines)
    print(text)
    if out_path:
        io.open(out_path, 'w', encoding='utf-8').write(text + '\n')
        print('\n已写出 %s' % out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
