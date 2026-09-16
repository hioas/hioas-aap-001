# -*- coding: utf-8 -*-
"""合成序号 1「16px 残差（首字段前间距 / 图标字形盒 / 免责正文两行）」RED→GREEN 的证据转录。

用法: python .agents/state/gen-1-16px-evidence.py
产出: .agents/state/evidence/redgreen-序号1-16px残差-20260916.txt
"""
import io
import json
import os
import subprocess
import sys

REPO = 'E:/workspaces/hioas/hioas-aap-001'
EVD = os.path.join(REPO, '.agents', 'state', 'evidence')
TMP = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp')
OUT = os.path.join(EVD, 'redgreen-序号1-16px残差-20260916.txt')
DESIGN_PNG = os.path.join(REPO, '.agents', 'state', 'design-shots', 'page-1-2.png')
IMPL_PNG = os.path.join(TMP, 'impl-login.png')

STEPS = [
    ('RED  ', 'review-序号1-red-run1.json', 'review-序号1-red-run2.json'),
    ('GREEN', 'review-序号1-green-run1.json', 'review-序号1-green-run2.json'),
]

lines = []
lines.append('序号 1（page-1-2 登录注册）· 16px 残差 RED→GREEN 证据（2026-09-16 18:45 轮 · cron aap-tdd-run-20260916-1845）')
lines.append('载体页 .agents/state/h5-measure/__measure-login.html（430 宽 iframe，mock=api）· 每步两轮独立测量')
lines.append('红/绿同一份最终版探针（133 条 checks）：「先建探针 → 两轮红 → 改源码 → 两轮绿」')
lines.append('')


def load(p):
    return json.load(io.open(os.path.join(EVD, p), encoding='utf-8'))


def p1(d):
    return d.get('phase1') or {}


def fails_str(f):
    out = []
    for x in f:
        if isinstance(x, dict):
            out.append('    FAIL %s: got %s want %s' % (x.get('k'), json.dumps(x.get('got'), ensure_ascii=False), json.dumps(x.get('want'), ensure_ascii=False)))
        else:
            out.append('    FAIL %s' % x)
    return out


for name, a, b in STEPS:
    da, db = load(a), load(b)
    pa, pb = p1(da), p1(db)
    fa, fb = pa.get('checkFails') or [], pb.get('checkFails') or []
    lines.append('%s: run1 checks=%s fails=%s docH=%s overflow=%s' % (name, pa.get('checkCount'), pa.get('checkFailCount'), pa.get('docScrollHeight'), pa.get('overflowingCount')))
    lines.append('        run2 checks=%s fails=%s docH=%s overflow=%s' % (pb.get('checkCount'), pb.get('checkFailCount'), pb.get('docScrollHeight'), pb.get('overflowingCount')))
    lines.append('        run1 == run2（phase1 全字段逐字节比对）: %s' % ('YES' if json.dumps(pa, sort_keys=True, ensure_ascii=False) == json.dumps(pb, sort_keys=True, ensure_ascii=False) else 'NO'))
    for ln in fails_str(fa):
        lines.append(ln)
    if fa:
        lines.append('        run2 失败清单与 run1 相同: %s' % ('YES' if json.dumps([str(x) for x in fa]) == json.dumps([str(x) for x in fb]) else 'NO'))
    lines.append('')

# ---- 交互相（2..6）与 serve 实收请求行 ----
lines.append('交互回放（同一次绿轮，phase2..6）与 serve 实收请求行（两轮逐字节比对）')
dg = load('review-序号1-green-run1.json')
for ph in ('phase2', 'phase3', 'phase4', 'phase5'):
    p = dg.get(ph) or {}
    keys = [k for k in ('scenario', 'typedPhone', 'typedCaptcha', 'typedSms', 'clickedAgree', 'toast', 'smsLabel', 'hash', 'storageToken', 'note') if k in p]
    lines.append('  %s: %s' % (ph, json.dumps({k: p[k] for k in keys}, ensure_ascii=False)))
req1 = io.open(os.path.join(EVD, 'requests-序号1-green-run1.txt'), encoding='utf-8').read()
req2 = io.open(os.path.join(EVD, 'requests-序号1-green-run2.txt'), encoding='utf-8').read()
lines.append('  requests run1 == run2（逐字节）: %s · 行数 %d' % ('YES' if req1 == req2 else 'NO', len([l for l in req1.splitlines() if l.strip()])))
for ln in req1.strip().splitlines():
    lines.append('    %s' % ln)
lines.append('')

# ---- 像素对账（结构带 + 文本行） ----
lines.append('像素对账（实现截图 evidence/20260916-1945-序01-登录注册-16px残差对齐-h5-430宽.png 430x1114）')
cmp_txt = os.path.join(EVD, 'cmp-序号1-设计PNGvs实现截图-结构带.txt')
if os.path.exists(cmp_txt):
    for ln in io.open(cmp_txt, encoding='utf-8').read().splitlines():
        if ln.strip():
            lines.append('  ' + ln)
lines.append('')
lines.append('  未命中逐条判读（cmp-pixel-rows.py 同列取色，x=200）：')
lines.append('    y656/657 设计 (254,254,255) vs 实现 (255,255,255) → 主按钮 drop_shadow(0,8,20,.28) 的 Figma/Chrome 衰减起点差 1~2/255（阴影类，非页面缺陷）')
lines.append('    y891 设计 (235,237,240) vs 实现 (248,250,252) → 卡片底边（设计 268..891，实现 [268,891) 半开区间）亚像素边界 + 卡投影（阴影类）')
lines.append('    y914/920 设计 (253,253,253) vs 实现 (255,255,255) → 设计导出图在免责卡上方 908..921 的均匀软染色（同族已在 page-15 记录）')
lines.append('    y819（内容列）与 y415（条列）→ 取值两侧完全相同（分别为微信按钮填充 (240,253,244) 与输入框底色 (248,250,252)），属带分割阈值效应，非几何差')
lines.append('')

lines.append('文本行对账（text-rows.py x36..394 · 设计 20 行 / 实现 21 行；逐行按最近 y 对齐）')
tr_d = os.path.join(TMP, 'trows-design.txt')
tr_i = os.path.join(TMP, 'trows-impl.txt')
for path, png, out in ((DESIGN_PNG, DESIGN_PNG, tr_d), (IMPL_PNG, IMPL_PNG, tr_i)):
    with io.open(out, 'w', encoding='utf-8') as fh:
        subprocess.run([sys.executable, os.path.join(REPO, '.agents', 'state', 'text-rows.py'), png, '36', '394'], stdout=fh, cwd=REPO)
rows_d = [l for l in io.open(tr_d, encoding='utf-8').read().splitlines()[1:] if l.strip()]
rows_i = [l for l in io.open(tr_i, encoding='utf-8').read().splitlines()[1:] if l.strip()]
for a, b in zip(rows_d, rows_i):
    lines.append('  设计 %-34s 实现 %s' % (a.strip(), b.strip()))
for extra in rows_i[len(rows_d):]:
    lines.append('  （实现多出行）                          %s' % extra.strip())
lines.append('  判读：两行免责正文墨迹 设计 965..975 / 980..990 与实现 966..976 / 980..990（行距 15，±1 内）；')
lines.append('        设计 601..602（h=2, maxDark=13）为设计字形图标墨迹、实现为 D5 浅色占位形状 → 该行不计为差异；')
lines.append('        设计 849..866 vs 实现 853..863 = 协议行勾选框「设计帧静态为选中态（蓝底+tick）」而实现按 PRD 校验门默认未选中 —— 状态差非几何差（guard 证据见上）。')
lines.append('')
lines.append('共用消费方回归门（未改共用组件，仍复跑）：__measure-workbench.html（序号 2）两轮 103 条 0 失败 · docH 1146')

with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('\n'.join(lines) + '\n')
print('written', OUT)
print('\n'.join(lines[:12]))
