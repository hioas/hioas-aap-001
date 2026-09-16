# -*- coding: utf-8 -*-
"""把序号 22（page-22-2「【工作台与我的】我的与用量概览 2」）判定的「非偏差」登记进 textleaf-accept.json。

判据优先级：①设计显式 height ②design PNG 的盒/带实测（含盒算术）③fs × lineHeight；②③冲突以 ② 为准。
本轮 9 条待判读全部判为**非偏差**（无需改源码），理由分三类：
  A. 内容驱动行的行盒由「PNG 行内容步进 + 卡高算术」定死为 18/20 —— 设计的 fs×lh1.2 是「声明模型」，
     与设计**渲染**行盒天然差 2.8~4.5px（CJK fit_content 自然行框），逐类墨迹实测 ±1。
  B. 定高盒内居中（成本合计行 41 = 10+21+10、明细入口卡 60 = 16+28+16、趋势标题行 20）→ 行盒不承重
     （居中盒里两个模型对墨迹同解，差 <0.3px）。
  C. trend__label 的设计声明自相矛盾（显式 h=11.3 vs lh1.31×fs10 = 13.1）：绝对定位不参与布局，
     实现取 13.1（载体页 trend.label.lh want 13.1 ± 0.3 早已绿）。

另有 **13 条「未渲染叶子」= 设计里的内联 SVG 图形**（4 网格线 + 折线 + 面积 + 6 点 r4 + 末点 r5）：
实现用同族画法（uni-image + SVG data-URI，mp-weixin 不能渲染内联 svg），本轮逐元素比对 13 ↔ 13 等价，
并在载体页新增 8 条硬断言锁死（trend.grid.ys / trend.grid.strokes / trend.line.pointCount /
trend.line.vsDesignX / trend.line.vsDesignY / trend.dots.radii / trend.dots.fills / trend.img.elemCount），
以源码变异测试证明有牙齿（改末条网格线色与末点半径 → 3 条红 → 还原 → 绿）。

用法: python .agents/state/accept-22-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
PAGE = 'page-22-2'
TAG = '22'
AT = '2026-09-16 21:00'
EVID = ('evidence/review-序号22-textleaf-报告.md + evidence/cmp-序号22-文本叶子-逐类带.txt'
        ' + evidence/cmp-序号22-趋势图区-设计SVGvs实现dataURI.txt + design-shots/page-22-2.png（430×1138）'
        ' + .agents/state/evidence/review-序号22-tl-run{1,2}.json + 20260916-2100-序22-用量概览-textleaf轮-h5-430宽.png')

PNG = 'design PNG（430×1138）'
ITEMS = [
    ('card__title',
     'fs14 × lh1.2 = 16.8（fit_content）', 'line-height 20',
     '判据②盒算术：四张卡的卡高都能反解出标题行 = 20 —— 汇总卡 228(PNG 108..336) = 20 + 标题行 + '
     '(16 + 2×72 + 8) + 20 ⇒ 20；趋势卡 222 = 20 + 20 + 12 + 150 + 20；模型卡 184 = 20 + 20 + '
     '(16 + 4×18 + 3×12) + 20；成本卡 207 = 20 + 20 + (16 + 3×18 + 3×12) + (12 + 41) + 20。'
     '若按声明 16.8 落地，四张卡各短 3.2px、与 ' + PNG + ' 的卡边界（108/348/582/778）全部冲突。'
     '逐类墨迹（4 处）：本月汇总 131..144 vs 132..145 · 近 7 日 371..384 vs 372..385 · '
     '模型用量分布 605..618 vs 606..619 · 成本构成 801..814 vs 802..815（各 +1 = H5 回退字体）。'
     '设计渲染行盒 = 20（fs14 CJK 自然行框），声明模型 16.8 属审计口径差。'),
    ('cost-total__label',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '判据①不承重 + ②盒算术：成本合计行 8e5874d9 = padding 10 + alignItems=center → 行高 41 = '
     '10 + 21 + 10（21 由同排「¥12,860」fs14 定；PNG 合计行 924..965 = 41 两侧相同）。标签在**居中**盒内，'
     '行盒 18（实现）与 14.4（声明）在居中盒里墨迹同解（差 <0.3px）→ 不承重。墨迹 设计 938..949 = '
     '实现 939..950（+1）。'),
    ('crow__label',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '判据②：成本项行 63cc9394（horizontal / align center / fit_content）只有两个 fs12 文本子节点 → '
     '行高 = 文本渲染行盒；PNG 行内容 837/867/897（步进 30 = 行 18 + 间距 12）、成本卡高 207 算术自洽 ⇒ 18。'
     '墨迹（3 行）：837..848 vs 838..848 · 867..878 vs 868..878 · 897..909 vs 897..908（±1）。'),
    ('crow__value',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '同 crow__label（同一行的右值节点）：行高由该行两个 fs12 文本的渲染行盒定（PNG 步进 30 ⇒ 18）。'
     '墨迹（3 行）：839..850 = 839..850 · 869..880 = 869..880 · 899..908 = 899..908（**逐值相同**）。'),
    ('detail__text',
     'fs13 × lh1.2 = 15.6（fit_content）', 'line-height 19.5',
     '判据②：明细入口卡 88ce181b = padding 16/20（PNG 997..1057 = 60 = 16 + 内容 28 + 16），'
     '内容 28 由同排 chevron 字形盒 22×28 定（见本页 checks 报告 §3）→ 文本在 align-center 行内**不承重**。'
     '墨迹：设计 1021..1034 = 实现 1021..1034（**逐值相同**）。'),
    ('legend__text',
     'fs10 × lh1.2 = 12.0（fit_content）', 'line-height 15',
     '判据②：趋势标题行 f0e3aec3（horizontal / align center / fit_content）高 20 —— 由 fs14 标题定，'
     '图例组 147a34ac（fit_content，container padding-left 4）内的 fs10 文本**不承重**。'
     '墨迹：设计 373..382 vs 实现 374..383（+1）；图例文字右界 394 两侧相同。'),
    ('mrow__name',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '判据②：模型行 69a339a5（align center）只有 fs12 名称 + 轨道(h10) + 百分比 → 行高 = 文本渲染行盒；'
     'PNG 行内容 638/668/698/728（步进 30 = 18 + 12）、模型卡 184 = 20 + 20 + (16 + 4×18 + 3×12) + 20 自洽 ⇒ 18。'
     '墨迹（4 行）：642..654 = 642..654 · 672..682 = 672..682 · 703..714 = 703..714 · 732..742 = 732..742'
     '（**逐值相同**）。'),
    ('mrow__pct',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '同 mrow__name（行内右值节点，同一步进 30 ⇒ 18）。墨迹（4 行）：643..652 = 643..652 · 673..682 = 673..682 '
     '· 703..712 = 703..712 · 733..742 = 733..742（**逐值相同**）。'),
    ('trend__label',
     '设计自身矛盾：显式 h=11.3 vs lh1.31×fs10 = 13.1', 'line-height 13.2（取 13.1 的落地值）',
     '判据①+设计自证：叶子 29522f0a 同时声明 height=11.3 与 lineHeight=1.31 —— 两者互斥（10×1.31 = 13.1）。'
     '实现取 13.1（载体页 trend.label.lh want 13.1 ± 0.3 早已绿，非本轮新增）；该叶子绝对定位（top 122.95）'
     '不参与布局，墨迹是唯一判据。墨迹（7 个标签，窗口取 ±1）：设计 525..533 vs 实现 526..534（+1）；'
     'x 段 106..126 vs 107..127 · 158..178 = 158..178 · 210..228 = 210..228 · 262..280 vs 261..280（±1）。'),
    ('trend__img',
     '设计 13 个内联 SVG 图形叶子（非文本）', 'uni-image + SVG data-URI（13 个元素）',
     '「未渲染叶子 13」= 设计把趋势图拆成 13 个内联 SVG 层（4 网格线 3×#F1F5F9 + 末条 #E2E8F0 · 折线 '
     '#2563EB sw3 `M 30 118 L 82 96 L 134 104 L 186 72 L 238 58 L 290 44 L 340 30` · 面积 '
     'rgba(191,219,254,.35) · 6 点 r4 #2563EB + 末点 r5 rgb(29,78,216)）。实现因 **mp-weixin 不能渲染内联 '
     'svg**（同序号 6 雷达图）改用 data-URI 交给 <image>，逐元素等价 13 ↔ 13（元素计数/色值/线宽/半径/填充'
     '全部相同，y 与设计路径经 Figma transform 映射后 |Δ| ≤ 0.79px）。像素侧：网格线行两侧同为 425/460'
     '（n=306/306、194/191）、点列中心 66..374.5 vs 66..373.5。已加 8 条 checks 锁死并以源码变异证明有牙齿。'),
]


def main():
    data = json.load(io.open(P, encoding='utf-8'))
    if '--reset' in sys.argv:
        before = len(data['items'])
        data['items'] = [it for it in data['items'] if it.get('page') != PAGE]
        print('清空 %s 旧条目 %d 条' % (PAGE, before - len(data['items'])))
    have = {(it.get('page'), (it.get('class') or '').lstrip('.')) for it in data['items']}
    added = 0
    for cls, declared, impl, reason in ITEMS:
        if (PAGE, cls) in have:
            print('已存在：%s（跳过）' % cls)
            continue
        data['items'].append({
            'page': PAGE, 'tag': TAG, 'class': cls, 'declared': declared, 'impl': impl,
            'verdict': 'not-a-deviation', 'reason': reason, 'evidence': EVID, 'at': AT,
        })
        added += 1
    print('新增 %d 条（合计 %d 条）' % (added, len(data['items'])))
    if '--dry' not in sys.argv:
        io.open(P, 'w', encoding='utf-8', newline='').write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print('已写盘 %s' % P)


main()
