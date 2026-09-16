#!/usr/bin/env python
"""序号 6 像素对账（结构带版）：设计 PNG（430×5342）vs 实现 430 宽整页截图。

用法: python .agents/state/cmp-bands-6-design-vs-impl.py <设计PNG> <实现PNG> [out.txt]

方法：在 x=36..394（卡片内容区）逐行统计「与行主色不同的像素数」（ink），取出所有 ink≥3 的
连续行带起点；把设计侧每个带起点在实现侧 ±3 行内找同起点（实现可能因字体/换行略移），
命中记 HIT，否则列出（设计侧）供逐条判读。另打印两侧总带数、首末带、以及整页高度。
"""
import os
import sys
from importlib import import_module

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_png = import_module('png-cardmap')


def ink_bands(img, x0, x1, y0, y1, minink=3):
    w, h, rows = _png.read_png(img)
    starts = []
    inband = False
    for y in range(y0, min(y1, h)):
        row = rows[y]
        counts = {}
        for x in range(x0, min(x1, w)):
            px = (row[x * 4], row[x * 4 + 1], row[x * 4 + 2])
            counts[px] = counts.get(px, 0) + 1
        modal = max(counts.items(), key=lambda kv: kv[1])[0]
        ink = sum(v for k, v in counts.items() if k != modal)
        if ink >= minink:
            if not inband:
                starts.append(y)
                inband = True
        else:
            inband = False
    _png.read_png(img)  # keep the reader warm (no-op)
    return img[0], img[1], starts


def dims(path):
    w, h, _rows = _png.read_png(path)
    return w, h


def main():
    design_path, impl_path = sys.argv[1], sys.argv[2]
    tol = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    dw, dh = dims(design_path)
    iw, ih = dims(impl_path)
    out = ['序号 6 像素对账：设计 PNG %dx%d vs 实现 430 宽整页截图 %dx%d' % (dw, dh, iw, ih), '']
    total_hit = total_miss = 0
    for x0, x1, label in ((36, 394, '卡片内容区 x=36..394'), (194, 356, '明细条/进度条列 x=194..356')):
        _w, _h, dbands = ink_bands(design_path, x0, x1, 0, dh)
        _w2, _h2 = dims(impl_path)
        w2, h2, ibands = ink_bands(impl_path, x0, x1, 0, ih)
        hits, miss = [], []
        deltas = []
        for v in dbands:
            near = [u - v for u in ibands if abs(u - v) <= tol]
            if near:
                hits.append(v)
                deltas.append(min(near, key=abs))
            else:
                miss.append(v)
        total_hit += len(hits)
        total_miss += len(miss)
        out.append('--- %s ---' % label)
        out.append('  设计带起点 %d 个（首 %s 末 %s）' % (len(dbands), dbands[:3], dbands[-3:]))
        out.append('  实现带起点 %d 个（首 %s 末 %s）' % (len(ibands), ibands[:3], ibands[-3:]))
        if deltas:
            srt = sorted(deltas)
            out.append('  命中(±%d) %d / 未命中 %d' % (tol, len(hits), len(miss)))
            out.append('  命中处位移：中位 %d · 最小 %d · 最大 %d · 0 位移 %d 个'
                       % (srt[len(srt) // 2], srt[0], srt[-1], deltas.count(0)))
            # 分区间的位移概况（判「是整体平移还是局部漂移」）
            for lo, hi in ((0, 1000), (1000, 1425), (1425, 4400), (4400, 5342)):
                seg = [d for v, d in zip(hits, deltas) if lo <= v < hi]
                if seg:
                    out.append('    y %d..%d：%d 个命中，位移 min %d max %d 中位 %d'
                               % (lo, hi, len(seg), min(seg), max(seg), sorted(seg)[len(seg) // 2]))
        out.append('  未命中清单 → %s' % miss)
    out.append('')
    out.append('结构带未命中合计: %d（命中 %d）' % (total_miss, total_hit))
    text = '\n'.join(out) + '\n'
    print(text)
    if len(sys.argv) > 3:
        open(sys.argv[3], 'w', encoding='utf-8').write(text)
        print('-> ' + sys.argv[3])


if __name__ == '__main__':
    main()
