# -*- coding: utf-8 -*-
"""逐类「设计 PNG vs 实现 PNG」行墨迹带对账（文本叶子维度收口用）。

用法:
  python .agents/state/tl-bands.py <dump.json> <class 子串> [<class 子串> ...] [--impl PNG] [--design PNG] [--pad 14]
  python .agents/state/tl-bands.py <dump.json> --classes "a,b,c" [--impl PNG] [--design PNG]
  python .agents/state/tl-bands.py <dump.json> --all-pending [--impl PNG]      # 12-v1 的 17 类（历史用法）

窗口 = 该 DOM 叶子 rect 左右各 ±1、上下各 ±pad（默认 14）。
打印两图在该窗口里的 ink 带（与窗口主色不同的行，连续成带）。带起点相同 ⇒ 渲染行盒一致。
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

_png = import_module('png-cardmap')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DESIGN = os.path.join(REPO, '.agents', 'state', 'design-shots', 'page-26.png')
DEFAULT_IMPL = os.path.join(REPO, 'logs', 'screenshots',
                            '20260916-1945-序12v1-新增报价单初始态-checks轮-h5-430宽.png')


def bands(png, x0, y0, x1, y1, minink=2):
    w, h, rows = png
    x0, x1 = max(0, int(x0)), min(w, int(x1))
    y0, y1 = max(0, int(y0)), min(h, int(y1))
    out = []
    cur = None
    for y in range(y0, y1):
        row = rows[y]
        c = Counter()
        for x in range(x0, x1):
            c[(row[x * 4], row[x * 4 + 1], row[x * 4 + 2])] += 1
        _, n = c.most_common(1)[0]
        ink = (x1 - x0) - n
        if ink >= minink:
            if cur is None:
                cur = [y, y, ink]
            else:
                cur[1] = y
                cur[2] = max(cur[2], ink)
        else:
            if cur is not None:
                out.append(tuple(cur))
                cur = None
    if cur is not None:
        out.append(tuple(cur))
    return out


def fmt(bs):
    return ' | '.join('%d..%d(%d)' % b for b in bs) if bs else '(none)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dump')
    ap.add_argument('klass', nargs='*')
    ap.add_argument('--classes', default=None, help='逗号分隔的 class 子串列表')
    ap.add_argument('--impl', default=DEFAULT_IMPL)
    ap.add_argument('--design', default=DEFAULT_DESIGN)
    ap.add_argument('--pad', type=int, default=14)
    ap.add_argument('--all-pending', action='store_true')
    args = ap.parse_args()

    d = json.load(open(args.dump, encoding='utf-8'))
    leaves = d['leafs']
    des = _png.read_png(args.design)
    imp = _png.read_png(args.impl)
    print('design %s %dx%d  impl %s %dx%d' % (os.path.basename(args.design), des[0], des[1],
                                              os.path.basename(args.impl), imp[0], imp[1]))

    targets = list(args.klass)
    if args.classes:
        targets += [c.strip() for c in args.classes.split(',') if c.strip()]
    if args.all_pending:
        targets += PENDING

    for t in targets:
        rows = [lf for lf in leaves if t in (lf.get('ac') or '')]
        if not rows:
            print('\n--- %s: 无匹配叶子' % t)
            continue
        print('\n--- %s  (n=%d)' % (t, len(rows)))
        for lf in rows[:4]:
            x0 = lf['left'] - 1
            x1 = lf['left'] + lf['w'] + 1
            y0 = lf['top'] - args.pad
            y1 = lf['top'] + lf['h'] + args.pad
            db = bands(des, x0, y0, x1, y1)
            ib = bands(imp, x0, y0, x1, y1)
            print('  %-28s x=%d..%d impl y=%.1f..%.1f lh=%s' % (
                (lf['t'][:26] + '…') if len(lf['t']) > 27 else lf['t'],
                x0, x1, lf['top'], lf['top'] + lf['h'], lf['lh']))
            print('      design %s' % fmt(db))
            print('      impl   %s   %s' % (fmt(ib),
                                            'SAME' if [b[0] for b in db] == [b[0] for b in ib] else 'DIFF'))


PENDING = [
    'bar__hint-text', 'card__title--sm', 'card__title', 'counter__text', 'hint__text--blue',
    'hint__text', 'label__star', 'label__text', 'notice__no', 'notice__text',
    'readonly-box__text', 'required__text', 'sample-pill__text', 'select__value',
    'tag__text--chip', 'tag__text', 'input-box__placeholder',
]

main()
