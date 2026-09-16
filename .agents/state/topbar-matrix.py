"""逐帧抽取「顶部栏 / 顶部导航 / 用户头部」节点的设计声明值，输出跨页对照矩阵。

口径：want 一律取 .calicat/raw/pages/<page-id>/design.tree.json（Calicat 当前画布重抓产物）。
用途：跨页同族位置（顶部栏/导航区）一致性核对——同一视觉模式在不同帧里是否声明一致、
实现是否落到同一套结构上。仅打印声明值，不做判读。

用法：
  python .agents/state/topbar-matrix.py                # 全部台账帧
  python .agents/state/topbar-matrix.py page-3 page-6  # 指定帧
  python .agents/state/topbar-matrix.py --json out.json
"""
import csv
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES = os.path.join(REPO, '.calicat', 'raw', 'pages')
LEDGER = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')

TOPBAR_RE = re.compile(r'顶部栏|顶部导航|顶部|用户头部|导航栏|topbar|nav', re.I)


def walk(node, depth=0, path=''):
    yield node, depth, path
    for i, c in enumerate(node.get('children') or []):
        yield from walk(c, depth + 1, '%s/%d' % (path, i))


def find_topbar(root):
    """顶部栏 = 页面容器/根节点的直接子节点里，名字匹配 或（首个横向布局且高 ≤ 120 的 frame）。"""
    cands = []
    for c in root.get('children') or []:
        for g in [c] + list(c.get('children') or [])[:0]:
            pass
    # 先按名字在整棵树里找（取最浅的一处）
    hits = [(d, n, p) for n, d, p in walk(root) if TOPBAR_RE.search(n.get('name') or '')]
    if hits:
        hits.sort(key=lambda t: t[0])
        return hits[0][1], hits[0][2]
    # 退路：页面容器的第一个横向 child
    for c in root.get('children') or []:
        for g in c.get('children') or []:
            if g.get('layout') == 'horizontal':
                return g, ''
    return None, ''


def loc(node):
    """一行摘要：几何/布局/内边距/间距/圆角/填充/描边/效果"""
    return 'w=%s h=%s layout=%s pad=%s gap=%s rad=%s fills=%s stroke=%s fx=%s' % (
        node.get('width'), node.get('height'), node.get('layout'), node.get('padding'),
        node.get('gap'), node.get('cornerRadius'), node.get('fills'),
        json.dumps(node.get('stroke'), ensure_ascii=False) if node.get('stroke') else None,
        json.dumps(node.get('effects'), ensure_ascii=False) if node.get('effects') else None)


def brief(node, depth=0):
    return '  ' * depth + '%-4s %-24s %-6s %s' % (
        (node.get('id') or '')[:4], (node.get('name') or '')[:24], node.get('type'), loc(node))


def main():
    args = [a for a in sys.argv[1:]]
    out_json = None
    if '--json' in args:
        i = args.index('--json')
        out_json = args[i + 1]
        del args[i:i + 2]
    ids = args or [r['页面ID'] for r in csv.DictReader(open(LEDGER, encoding='utf-8'))]
    matrix = {}
    for pid in ids:
        f = os.path.join(PAGES, pid, 'design.tree.json')
        if not os.path.exists(f):
            print('MISSING %s' % pid)
            continue
        root = json.load(open(f, encoding='utf-8'))
        bar, path = find_topbar(root)
        if not bar:
            print('== %-12s 未找到顶部栏节点' % pid)
            continue
        print('== %-12s 帧=%s' % (pid, (root.get('name') or '')[:44]))
        print('   顶部栏节点: %s  path=%s' % (bar.get('name'), path))
        print('   ' + loc(bar))
        kids = bar.get('children') or []
        print('   子节点 %d 个：' % len(kids))
        for k in kids:
            print('   ' + brief(k, 1))
            for kk in (k.get('children') or []):
                txt = kk.get('content') or kk.get('text') or ''
                extra = ''
                if kk.get('fontSize') or txt:
                    extra = ' // fs=%s fam=%s lh=%s text=%r' % (
                        kk.get('fontSize'), kk.get('fontFamily'), kk.get('lineHeight'), str(txt)[:40])
                print('   ' + brief(kk, 2) + extra)
        matrix[pid] = {'frame': root.get('name'), 'topbar': bar, 'path': path}
        print()
    if out_json:
        json.dump(matrix, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('已写出 %s（%d 帧）' % (out_json, len(matrix)))


if __name__ == '__main__':
    main()
