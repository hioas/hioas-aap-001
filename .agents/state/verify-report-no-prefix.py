# -*- coding: utf-8 -*-
"""verify-report-no-prefix.py — 核定「报告编号」前缀口径（序号 6 vs 序号 7-2）。

背景：序号 7 台账备注⑩ 曾跨页断言「序号 6 顶部同样只渲染了号码、缺『报告编号』前缀（设计原文含前缀）
→ 序号 6 待回炉时一并修」。本脚本用**两条独立证据**核定该断言是否成立：

  ①设计树：两帧「顶部导航 → 报告编号」文本叶子的 content / width / fontSize；
  ②设计 PNG：顶部栏右侧区域的**墨迹包围盒宽度**（430 宽设计导出图，背景纯白）。

判据：fs11 的同一字体，单字符推进宽度相同 → 「含前缀」的串宽 ≈ 无前缀串宽 × (字符数比)。
      page-7-2 = 21 字符 / page-6 = 15 字符，若 page-6 也含前缀，其墨迹宽应 ≈ page-7-2 的墨迹宽。

用法: python .agents/state/verify-report-no-prefix.py
"""
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TMP = os.environ.get('LOCALAPPDATA', '.') + '/Temp'

TARGETS = [
    # (page-id, 设计 PNG, 顶部栏 y 范围, 说明)
    ('page-6', os.path.join(ROOT, '.agents/state/design-shots/page-6.png'), (0, 93), '序号 6 · 检测报告'),
    ('page-7-2', os.path.join(ROOT, '.agents/state/design-shots/page-7-2.png'), (0, 96), '序号 7 · 检测未通过报告'),
]


def find_leaf(node, prefix):
    """找「报告编号」文本叶子。

    两帧结构不同：page-6 的叶子包在名为「报告编号」的 frame 里；page-7-2 的前缀直接写在
    顶部导航下的叶子 content 中（无包装节点）→ 统一按**内容特征**匹配（DR-########-####）。
    """
    import re
    pat = re.compile(r'DR-\d{8}-\d{4}')
    out = []

    def walk(n):
        c = n.get('content') or ''
        if c and pat.search(c):
            out.append(n)
        for ch in n.get('children') or []:
            walk(ch)

    walk(node)
    return out


def ink_bbox(png, x0, y0, x1, y1):
    im = Image.open(png).convert('RGB')
    px = im.load()
    W, H = im.size
    x1 = min(x1, W)
    y1 = min(y1, H)
    # 背景 = 区域内众数色（顶部栏为纯白）
    from collections import Counter
    cnt = Counter()
    for y in range(y0, y1):
        for x in range(x0, x1):
            cnt[px[x, y]] += 1
    bg = cnt.most_common(1)[0][0]
    minx, miny, maxx, maxy, n = None, None, None, None, 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            p = px[x, y]
            if abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > 30:
                n += 1
                minx = x if minx is None else min(minx, x)
                maxx = x if maxx is None else max(maxx, x)
                miny = y if miny is None else min(miny, y)
                maxy = y if maxy is None else max(maxy, y)
    return {'bg': bg, 'ink': n, 'x': (minx, maxx), 'y': (miny, maxy),
            'w': (maxx - minx + 1) if minx is not None else 0,
            'h': (maxy - miny + 1) if miny is not None else 0}


def main():
    print('== 报告编号前缀核定（证据 ①/② 独立来源） ==')
    rows = []
    for page_id, png, (ty0, ty1), label in TARGETS:
        dj = os.path.join(ROOT, '.calicat/raw/pages', page_id, 'design.json')
        raw = json.load(open(dj, encoding='utf-8'))
        root = raw[0]['layer_data'] if isinstance(raw, list) else raw
        leaves = find_leaf(root, '报告编号')
        print('\n-- %s（%s）' % (page_id, label))
        print('   设计树 design.json = %s' % os.path.relpath(dj, ROOT))
        for lf in leaves:
            c = lf.get('content') or ''
            print('   ①叶子 id=%s content=%r w=%s h=%s fs=%s' % (
                (lf.get('id') or '')[:8], c, lf.get('width'), lf.get('height'), lf.get('fontSize')))
            rows.append({'page': page_id, 'content': c, 'chars': len(c),
                         'declaredW': lf.get('width'), 'fs': lf.get('fontSize')})
        if os.path.exists(png):
            bbox = ink_bbox(png, 200, ty0, 430, ty1)
            print('   ②设计 PNG 顶部栏右侧墨迹（x200..430, y%d..%d）: x=%s w=%d h=%d ink=%d bg=%s' % (
                ty0, ty1, bbox['x'], bbox['w'], bbox['h'], bbox['ink'], bbox['bg']))
            rows[-1]['inkW'] = bbox['w']
            rows[-1]['inkX'] = bbox['x']
        else:
            print('   ②设计 PNG 缺失: %s' % png)

    print('\n== 判据 ==')
    p6 = [r for r in rows if r['page'] == 'page-6']
    p7 = [r for r in rows if r['page'] == 'page-7-2']
    if p6 and p7:
        a, b = p6[0], p7[0]
        print('   page-6   : %d 字符 · 设计声明宽 %s · PNG 墨迹宽 %s' % (a['chars'], a['declaredW'], a.get('inkW')))
        print('   page-7-2 : %d 字符 · 设计声明宽 %s · PNG 墨迹宽 %s' % (b['chars'], b['declaredW'], b.get('inkW')))
        aw, bw = a.get('inkW') or 0, b.get('inkW') or 0
        if aw and bw:
            print('   墨迹宽比 page-6/page-7-2 = %.3f（字符数比 = %.3f）' % (aw / bw, a['chars'] / b['chars']))
        print('   单字符推进宽（设计声明）：page-6 %.2f px/char · page-7-2 %.2f px/char' % (
            a['declaredW'] / a['chars'], b['declaredW'] / b['chars']))
        has_prefix_6 = '报告编号' in a['content']
        has_prefix_7 = '报告编号' in b['content']
        print('   结论：序号 6 设计原文含前缀 = %s ；序号 7-2 设计原文含前缀 = %s' % (has_prefix_6, has_prefix_7))
        print('   → 序号 7 台账备注⑩「序号 6 缺前缀、待回炉修」= %s' % ('成立' if has_prefix_6 else '**误判**（序号 6 设计稿本就无前缀）'))
    return 0


if __name__ == '__main__':
    sys.exit(main())