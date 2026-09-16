# -*- coding: utf-8 -*-
"""序号 6（page-6 / 检测报告）载体页补「文本叶子 ↔ 设计声明」维度 checks。

改动（全部按设计声明值 / 设计 PNG 实测）：
  ① card4.summary.h  24 → 16   （design 明细说明 8485b93b frame h=24 = pad-top 8 + 行盒 16）
  ② card5.finding.title.fw 700 → 600（design 2ba0333a SourceHanSans-SemiBold）
  ③ card4.groupPitch 437 → 438（design PNG 组标题 ink 间距 438；旧值 437 是「421+16」的自洽算术，
     漏了 design 在每组之间还有 1px 分隔线 分隔线A–F）
  ④ 新增 17 条 tl.* checks（字重 / 字号 / 行盒 / 组间分隔线 / 组标题 top / cardTops 逐项）

用法: python .agents/state/apply-6-textleaf-probe.py [--dry]
幂等：新键已存在则整体不写（避免 §5.20 的重复插入）。
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'h5-measure', '__measure-report.html')
src = io.open(P, encoding='utf-8').read()
orig = src

EDITS = [
    # (old, new, 说明)
    ("chkC('card4.summary.h', '.detail-summary', 'height', 24)",
     "chkC('card4.summary.h', '.detail-summary', 'height', 16)\n"
     "        /* design 明细说明 8485b93b：frame h=24 = padding-top 8 + 行盒 16（叶子 068c8976 fs11） */",
     "summary.h"),
    ("chkC('card5.finding.title.fw', '.finding__title', 'fontWeight', 700)",
     "chkC('card5.finding.title.fw', '.finding__title', 'fontWeight', 600)",
     "finding fw"),
    ("})(), 437, 2) /* = 组高 421（16+18+14+9 项 373）+ 组间间隔 16 */",
     "})(), 438, 1) /* = 组高 421 + spacer 16 + 分隔线 1（design 分隔线A；PNG 实测组标题 ink 间距 438） */",
     "group pitch"),
    ("        /* ---------- 整页 ---------- */",
     """        /* ---------- 文本叶子维度（设计叶子声明值 ↔ 实现 computed；审计 27 class 收口） ---------- */
        /* want 来源：page-6 design.tree.json 的 fontFamily→字重 / fontSize / 显式 height；
           行盒另有设计 PNG 实测（.agents/state/design-shots/page-6.png vs 实现截图），
           逐类对账见 evidence/cmp-序号6-设计PNGvs实现截图-行盒判读.txt 与 …明细卡纵向对账.txt */
        chkC('tl.ghostExport.fw', '.action__ghost-text', 'fontWeight', 500)   /* design a3023014 Medium */
        chkC('tl.findingTitle.fw', '.finding__title', 'fontWeight', 600)      /* design 2ba0333a SemiBold */
        chkC('tl.dimText.fw', '.dim__text', 'fontWeight', 500)                /* design 177b7f5f Medium */
        chkC('tl.dimScore.fw', '.dim__score', 'fontWeight', 700)              /* design 0947f700 Bold */
        chkC('tl.pillStatus.fs', '.item__pill:not(.item__pill--value) .item__pill-text', 'fontSize', 10)
        chkC('tl.pillStatus.fw', '.item__pill:not(.item__pill--value) .item__pill-text', 'fontWeight', 600)
        /* design e247efe0「未申报」/ 66800e15「不可测」/ 1b3c9a9f「仅证据」= fs10 + SemiBold（状态标签 pill） */
        chkC('tl.pillValue.fs', '.item__pill--value .item__pill-text', 'fontSize', 11)
        chkC('tl.pillValue.fw', '.item__pill--value .item__pill-text', 'fontWeight', 400)
        /* design ef69fd0e「20.42.xx.xx · AS8075 Azure」= fs11 w142（G 组的值 pill，是数据不是标签） */
        chkC('tl.summary.lh', '.detail-summary', 'lineHeight', 16)
        chkR('tl.summary.boxH', '.detail-summary', 24, 1)                     /* = pad-top 8 + 行盒 16（design frame h=24） */
        chk('tl.groupSep.count', doc.querySelectorAll('.group__sep').length, 6) /* design 分隔线A–F（G 之后无） */
        chkC('tl.groupSep.h', '.group__sep', 'height', 1)
        chkC('tl.groupSep.bg', '.group__sep', 'backgroundColor', 'rgb(238, 242, 247)')
        chkR('tl.groupTitle.top', '.group__title', 1504, 1)                   /* design PNG A 组标题 ink 1508 → 盒顶 1504 */
        chkArr('tl.cardTops', cardTops, [105, 533, 896, 1425, 4400, 4822, 5120], 1)

        /* ---------- 整页 ---------- */""",
     "tl block"),
    ("        function chkR(key, sel, want, tol) { return chk(key, rectField(sel, key), want, tol) }",
     "        function chkArr(key, got, want, tol) {\n"
     "          checks++\n"
     "          var t = tol == null ? 0 : tol\n"
     "          var ok = got && want && got.length === want.length && want.every(function (w, i) { return Math.abs(got[i] - w) <= t })\n"
     "          if (!ok) fails.push({ k: key, got: got ? got.join(',') : null, want: want.join(','), tol: t })\n"
     "          return got ? got.join(',') : null\n"
     "        }\n"
     "        function chkR(key, sel, want, tol) { return chk(key, rectField(sel, key), want, tol) }",
     "chkArr helper"),
]

if "tl.ghostExport.fw" in src:
    print('已包含 tl.* checks —— 幂等跳过（未写盘）')
    sys.exit(0)

for old, new, tag in EDITS:
    n = src.count(old)
    if n != 1:
        print('锚点命中 %d 次（必须恰好 1 次）: %s' % (n, tag))
        sys.exit(2)
    src = src.replace(old, new)
    print('OK  %-14s 锚点唯一，已替换' % tag)

if '--dry' in sys.argv:
    print('--dry：未写盘。新增 %d 条 tl.* checks。' % src.count('chk'))
    sys.exit(0)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已写盘 %s（校验：tl.* 键 %d 个）' % (P, src.count("'tl.")))
