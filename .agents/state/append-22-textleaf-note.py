# -*- coding: utf-8 -*-
"""回写台账 `aap-feature-status.csv` 序号 22 行的 备注 列（追加一段：文本叶子维度收口）。

用法: python .agents/state/append-22-textleaf-note.py [--dry]
"""
import csv
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')
SEQ = '22'
NOTE = (
    '队列 8 · 文本叶子维度（2026-09-16 20:30 轮 · cron `aap-tdd-run-20260916-2030`）：'
    '`textleaf-scan.py 22`（mock api-22 · leafs 344 · docH 1137）→ `textleaf-audit.py 22` 红基线 '
    '**待判读 class 9 + 未渲染叶子 13**（evidence/red-序号22-textleaf-待判读.txt）→ 逐条判读 → 复跑 '
    '**待判读 0 · 已核定 9**（green-序号22-textleaf-待判读0.txt）。**本轮无源码改动**（9 条全为非偏差）：'
    '①`card__title` 的行盒 20 由**卡高盒算术**定死（汇总卡 228 = 20+20+(16+2×72+8)+20 · 趋势卡 222 · 模型卡 184 · 成本卡 207）'
    '，设计渲染行盒 = 20 ≠ 声明模型 16.8；'
    '②`crow__label/crow__value/mrow__name/mrow__pct` 行盒 18 由 PNG 行内容步进 30 = 18+12 定死（墨迹**逐值相同**）；'
    '③`cost-total__label`（合计行 41 = 10+21+10 居中盒）· `detail__text`（明细卡 60 = 16+28+16，28 由 chevron 字形盒定）'
    '· `legend__text`（趋势标题行 20 由 fs14 标题定）三处**不承重**（居中盒里两模型对墨迹同解）；'
    '④`trend__label` 设计**自相矛盾**（显式 h=11.3 vs lh1.31×fs10 = 13.1）：绝对定位不参与布局，实现取 13.1（载体页 want 13.1±0.3 早已绿）。'
    '**13 条「未渲染叶子」= 设计的内联 SVG 图形层**（4 网格线 3×#F1F5F9+末条#E2E8F0 · 折线 #2563EB sw3 · 面积 rgba(191,219,254,.35) · '
    '6 点 r4 #2563EB + 末点 r5 rgb(29,78,216)）：实现因 mp-weixin 不能渲染内联 svg → data-URI 交 uni-image（同序号 6 雷达图），'
    '**逐元素 13 ↔ 13 等价**（色值/线宽/半径/填充全同；y 与设计 path 经 Figma transform 映射后 |Δ| ≤ 0.79px；'
    'x 侧设计步距 52/52/52/52/52/50 非等距而实现取等距 51.33 → 第 6 点 |Δ| ≤ 1.84px，理由是**设计自己的横轴标签就是等距**（56/107/…/364），'
    '照抄设计点距会让数据点与标签错开 2px，已登记为已知残差）。'
    '为此在载体页**新增 8 条硬断言**（267 → **275** 条：trend.grid.ys / grid.strokes / line.pointCount / line.vsDesignX（want = 实测残差表，容差 0.35）/ '
    'line.vsDesignY / dots.radii / dots.fills / img.elemCount），并用**源码变异测试**证明有牙齿（临时改末条网格线色 + 末点半径/色 → 3 条红 → 还原 → 绿）。'
    '回归门：载体页 **275 条 0 失败 ×2**（docH 1138 = 设计帧高 · 50 字段全等 · requests 两轮逐字节相同 = 1 行只读 GET）· '
    '430 宽整页截图与 16:05 轮**逐字节相同** · 像素结构带对账 39 命中/8 未命中（与 16:05 轮完全一致）· '
    '`npm test` **1185/1185 · 72 files 连跑两轮** · `type-check` exit 0 · 未重跑 build（无 src 改动）· '
    '设计帧重抓（design.json sha256 `63d7ce0c…` **逐字节相同**，无漂移）。'
    '证据：evidence/{red,green}-序号22-textleaf-*.txt · evidence/cmp-序号22-文本叶子-逐类带.txt · '
    'evidence/cmp-序号22-趋势图区-设计SVGvs实现dataURI.txt · evidence/red-序号22-trendchecks-变异测试.txt · '
    'evidence/review-序号22-textleaf-报告.md · .agents/state/evidence/review-序号22-{tl,tlmut,tlcheck}-run{1,2}.json'
    '（+ requests-序号22-tl-run{1,2}.txt）· 截图 logs/screenshots/20260916-2100-序22-用量概览-textleaf轮-h5-430宽.png（430×1138）。'
)

raw = io.open(P, encoding='utf-8', newline='').read()
rows = list(csv.reader(io.StringIO(raw)))
head = rows[0]
n = len(head)
hit = 0
for r in rows[1:]:
    if r and r[0].strip() == SEQ:
        while len(r) < n:
            r.append('')
        r[10] = (r[10] + ' ｜ ' + NOTE) if r[10].strip() else NOTE
        hit += 1
if hit != 1:
    raise SystemExit('序号 %s 命中 %d 行（要求恰好 1）→ 不写盘' % (SEQ, hit))
out = io.StringIO()
csv.writer(out, lineterminator='\r\n').writerows(rows)
print('命中 1 行 · 备注列 +%d 字' % len(NOTE))
if '--dry' not in sys.argv:
    io.open(P, 'w', encoding='utf-8', newline='').write(out.getvalue())
    print('已写盘 %s' % P)
