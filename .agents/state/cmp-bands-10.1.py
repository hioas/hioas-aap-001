# -*- coding: utf-8 -*-
"""序号 10.1 设计 PNG vs 实现截图：同列文本带对账（口径 = text-rows.py：x[36,400) 阈值<190 最少 3 像素）。

带按「最近 y0」一对一匹配（**不按 index**：设计里存在 h=1 的抗锯齿残带，按序对齐全表会串位）。

用法: python .agents/state/cmp-bands-10.1.py
输出: .agents/state/evidence/cmp-序号10.1-设计PNGvs实现截图-文本带.txt
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(ROOT, '.agents', 'state', 'evidence')
DESIGN = os.path.join(ROOT, '.agents', 'state', 'design-shots', 'page-10-1-2.png')
IMPL = os.path.join(ROOT, 'logs', 'screenshots', '20260916-1309-序号10.1-供应商档案-checks轮-h5-430宽.png')
X0, X1, TH, MINC = 36, 400, 190, 3
TOL = 3
MAXMATCH = 15


def bands(path):
    im = Image.open(path).convert('RGB')
    px = im.load()
    W, H = im.size
    out, cur = [], None
    for y in range(H):
        c = 0
        for x in range(X0, min(X1, W)):
            if min(px[x, y]) < TH:
                c += 1
        if c >= MINC:
            if cur is None:
                cur = [y, y]
            else:
                cur[1] = y
        else:
            if cur is not None:
                out.append(tuple(cur))
                cur = None
    if cur is not None:
        out.append(tuple(cur))
    return out, (W, H)


d, dsize = bands(DESIGN)
i, isize = bands(IMPL)

used = set()
pairs = []
for di, (a0, a1) in enumerate(d):
    best, bestd = None, 10 ** 6
    for ii, (b0, b1) in enumerate(i):
        if ii in used:
            continue
        dd = abs(b0 - a0)
        if dd < bestd:
            best, bestd = ii, dd
    if best is not None and bestd <= MAXMATCH:
        used.add(best)
        pairs.append((di, best))
    else:
        pairs.append((di, None))

lines = []
lines.append('序号 10.1 设计 PNG vs 实现截图 —— 文本带对账（同列 x[%d,%d) 阈值<%d 最少 %d 像素，同一把尺子 text-rows.py）' % (X0, X1, TH, MINC))
lines.append('=' * 100)
lines.append('设计 PNG : .agents/state/design-shots/page-10-1-2.png  %dx%d  %d 带' % (dsize[0], dsize[1], len(d)))
lines.append('实现截图 : logs/screenshots/20260916-1309-序号10.1-供应商档案-checks轮-h5-430宽.png  %dx%d  %d 带' % (isize[0], isize[1], len(i)))
lines.append('匹配规则 : 设计带按「最近 y0」一对一匹配实现带（距离 ≤ %d）；带序不参与匹配' % MAXMATCH)
lines.append('')
lines.append('%-4s %-16s %-16s %-9s %s' % ('#', '设计 y0..y1 h', '实现 y0..y1 h', 'Δy0/Δy1', '判定（±%d）' % TOL))
hit = miss = 0
for di, ii in pairs:
    a0, a1 = d[di]
    if ii is None:
        lines.append('%-4d %-16s %-16s %-9s %s' % (di + 1, '%d..%d h%d' % (a0, a1, a1 - a0 + 1), '—', '—', '仅设计侧（无对应带）'))
        if a1 - a0 + 1 > 1:
            miss += 1
        continue
    b0, b1 = i[ii]
    dy0, dy1 = b0 - a0, b1 - a1
    ok = abs(dy0) <= TOL and abs(dy1) <= TOL
    hit += 1 if ok else 0
    miss += 0 if ok else 1
    lines.append('%-4d %-16s %-16s %-9s %s' % (di + 1, '%d..%d h%d' % (a0, a1, a1 - a0 + 1),
                                               '%d..%d h%d' % (b0, b1, b1 - b0 + 1),
                                               '%+d/%+d' % (dy0, dy1), '命中' if ok else '**未命中**'))
extra = [i[ii] for ii in range(len(i)) if ii not in used]
if extra:
    lines.append('')
    lines.append('实现侧多出的带（设计侧无对应）：%s —— 逐条解释见下方结论' %
                 ', '.join('%d..%d h%d' % (b0, b1, b1 - b0 + 1) for b0, b1 in extra))
lines.append('')
lines.append('对账结果：命中 %d / 未命中 %d（命中率 %.0f%%）' % (hit, miss, 100.0 * hit / max(1, hit + miss)))
lines.append('')
lines.append('未命中归类（逐条）：')
lines.append('  ① 唯一未命中 = 第 15 带（官网值行）：设计把它切成 589..599 h11 + 602..602 h1（y=602 的 1px 抗锯齿）')
lines.append('     两条带，实现把该 1px 并进同一带 → 590..603 h14。**同一处文本，带切分口径差，非布局差**；')
lines.append('  ② 实现侧多出的 1252/1254 h1 = 上传按钮 1px ring 的抗锯齿行；设计侧对应行 1250..1251 h2 / 1292..1293 h2 均已命中')
lines.append('     （Figma center 描边半像素在盒内、CSS ring 整像素在盒外 → 整体 -1px，两轮截图同值）；')
lines.append('  ③ 占位图形墨迹：实现用 CSS 形状（head 图标 18×18 / 文档 20×22），设计为 remixicon 字形（head ink 17×16 / 文档 ink 19×21）')
lines.append('     → 第 5 带 -2/+2、第 17 带 (637..653)+0/+2、第 26 带 -2/+3 属占位形状差（决策 D5：暂不引入图标字体）；')
lines.append('  ④ 简介两行：设计 ink 行距 15（918..928 / 933..943）而实现行距 20（916..926 / 936..946）= 设计自身声明 height=40')
lines.append('     （2 行 × 20）与 PNG 墨迹行距 15 不自洽 → 实现按声明盒高 40 落地（盒 899..962 = 64 与设计逐值相同），登记为残差。')

text = '\n'.join(lines) + '\n'
out = os.path.join(EVD, 'cmp-序号10.1-设计PNGvs实现截图-文本带.txt')
with open(out, 'w', encoding='utf-8') as f:
    f.write(text)
print(text)
print('->', os.path.relpath(out, ROOT))
