# -*- coding: utf-8 -*-
"""合成序号 1「字重 + 行盒」两步 RED→GREEN 的证据转录（含两轮一致性与 PNG 色带对照）。

用法: python .agents/state/gen-1-evidence.py
产出: .agents/state/evidence/redgreen-序号1-字重行盒-20260916.txt
"""
import io
import json
import os

REPO = 'E:/workspaces/hioas/hioas-aap-001'
EVD = os.path.join(REPO, '.agents', 'state', 'evidence')
OUT = os.path.join(EVD, 'redgreen-序号1-字重行盒-20260916.txt')

STEPS = [
    ('字重（10 处）RED ', 'review-序号1-fwred-run1.json', 'review-序号1-fwred-run2.json'),
    ('字重（10 处）GREEN', 'review-序号1-fwgreen-run1.json', 'review-序号1-fwgreen-run2.json'),
    ('行盒（10 处）RED  ', 'review-序号1-bered-run1.json', 'review-序号1-bered-run2.json'),
    ('行盒（10 处）GREEN', 'review-序号1-begreen-run1.json', 'review-序号1-begreen-run2.json'),
]

lines = []
lines.append('序号 1（page-1-2 登录注册）·「设计声明字重 / 行盒」两步 RED→GREEN 证据（2026-09-16）')
lines.append('载体页 .agents/state/h5-measure/__measure-login.html（430 宽 iframe，mock=api）· 每步两轮独立测量')
lines.append('发现路径：textleaf-audit.py 全量「文本叶子 ↔ 设计声明」扫描（1131 设计叶子 / 22 页）')
lines.append('')


def load(p):
    return json.load(io.open(os.path.join(EVD, p), encoding='utf-8'))


def fails_of(p):
    d = load(p)
    ph = d.get('phase1') or {}
    f = ph.get('checkFails') or []
    out = []
    for x in f:
        if isinstance(x, dict):
            out.append('    FAIL %s: got %s want %s' % (x.get('k'), x.get('got'), x.get('want')))
        else:
            out.append('    FAIL %s' % x)
    return ph.get('checkCount'), ph.get('checkFailCount'), ph.get('docScrollHeight'), out


for title, r1, r2 in STEPS:
    c1, f1, h1, list1 = fails_of(r1)
    c2, f2, h2, list2 = fails_of(r2)
    lines.append('== %s' % title)
    lines.append('   run1: checkCount=%s checkFailCount=%s docScrollHeight=%s' % (c1, f1, h1))
    lines.append('   run2: checkCount=%s checkFailCount=%s docScrollHeight=%s' % (c2, f2, h2))
    for t in list1:
        lines.append('   %s' % t)
    lines.append('')

lines.append('== PNG 色带对照（430 宽整页截图 vs 设计导出 PNG 430x1114，png-textbands x=24..406）')
DESIGN = os.path.join(REPO, '.agents', 'state', 'design-shots', 'page-1-2.png')
B1 = os.path.join(EVD, '20260916-序01-登录注册-字重口径-h5-430宽.png')
B2 = os.path.join(EVD, '20260916-序01-登录注册-行盒字重对齐-h5-430宽.png')
lines.append('   设计 PNG : %s' % DESIGN)
lines.append('   修前     : %s（仅补字重、行盒未改）' % B1)
lines.append('   修后     : %s' % B2)
lines.append('   修前 vs 设计（y<300）：')
lines.append('     设计 56..109 / 143..168 / 185..198 / 268..271 / 297..299')
lines.append('     修前 56..109 / 142..167 / 180..193 / 260..263 / 288..299   ← 品牌标题 -1 · 副标题 -5 · 卡片顶 -8')
lines.append('   修后 vs 设计（y<320）：')
lines.append('     修后 56..109 / 143..168 / 185..198 / 268..271 / 297..317    ← 逐带与设计相同（±0）')
lines.append('   整页高：实现 docScrollHeight 1085 → 1098（设计帧 1114；剩余差 16 = 首个字段前间距 4 + 免责摘要正文按设计应为两行 h=40 的 20.8 - 8.8 残差，见下轮待办）')
lines.append('')

lines.append('== 质量门')
lines.append('   npm test 1182/1182 · 72 files ×2（18:36:47 / 18:37:18）· npm run type-check exit 0')
lines.append('   npm run build:mp-weixin DONE（pages/login/index.{js,json,wxml,wxss}；wxss 含 font-weight 700×4 / 600×2 / 500×4 与 line-height 36/28×2/24/20×2/18×2/16.8/14.4）')
lines.append('   npm run build:h5 DONE')

io.open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
print('\n已写出 %s' % OUT)
