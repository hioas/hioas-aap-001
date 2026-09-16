# -*- coding: utf-8 -*-
"""序号 12-v2 checks 轮证据合成：红基线 / 绿基线 / 两轮一致性 / 交互回放请求行 → evidence/*.txt

用法: python .agents/state/gen-12v2-checks-evidence.py
"""
import io
import json
import os
import subprocess

ROOT = '.agents/state'
EVD = os.path.join(ROOT, 'evidence')


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace').stdout


def load(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def phases_block(path, label):
    d = load(path)
    out = ['=== %s :: %s' % (label, path)]
    for k in sorted(d.keys()):
        if not k.startswith('phase'):
            continue
        p = d[k]
        if not isinstance(p, dict):
            continue
        if 'checkCount' in p:
            out.append('%-8s checkCount=%s checkFailCount=%s docScrollHeight=%s overflowing=%s missingTexts=%s' % (
                k, p.get('checkCount'), p.get('checkFailCount'), p.get('docScrollHeight'),
                p.get('overflowingCount'), p.get('missingTexts')))
            for f in p.get('checkFails', []):
                out.append('    FAIL %s: got %s want %s' % (f['k'], f['got'], f['want']))
        else:
            out.append('%-8s %s' % (k, json.dumps(p, ensure_ascii=False)))
    return '\n'.join(out) + '\n'


RED1 = os.path.join(EVD, 'review-序号12-v2-checks-red-run1.json')
RED2 = os.path.join(EVD, 'review-序号12-v2-checks-red-run2.json')
GRN1 = os.path.join(EVD, 'review-序号12-v2-checks-run1.json')
GRN2 = os.path.join(EVD, 'review-序号12-v2-checks-run2.json')
ACT1 = os.path.join(EVD, 'review-序号12-v2-checks-actions-run1.json')
ACT2 = os.path.join(EVD, 'review-序号12-v2-checks-actions-run2.json')
SET1 = os.path.join(EVD, 'review-序号12-v2-checks-settings-run1.json')
SET2 = os.path.join(EVD, 'review-序号12-v2-checks-settings-run2.json')
V1A = os.path.join(EVD, 'review-序号12-v1-recheck-run1.json')
V1B = os.path.join(EVD, 'review-序号12-v1-recheck-run2.json')

red = ['序号 12-v2「新增报价单-APIKey 下拉展开」载体页 checks 红基线（修复前源码 + 最终版探针；两轮独立测量）',
       '红基线口径：red = git stash 掉本轮源码改动（QuoteFormView.vue / quote-form-model.ts）后 build:h5 × 最终版 __measure-quote-apikey.html',
       '  → 最终版探针 272 条 · 红 6 条（探针自身期望值 bug 在红基线前已逐条修掉，见末尾「探针自身」段）',
       '  → 两轮独立测量完全一致（35/35 字段全等）→ 红基线可复现',
       '']
red.append(phases_block(RED1, 'RED run1'))
red.append(phases_block(RED2, 'RED run2'))
red.append('红基线 6 条分诊 —— 全部为**页面缺陷**（本轮已修，见 review-序号12v2-checks-报告.md §3）：')
red.append('  1) cred.value.color    展开态占位文案 #CBD5E1 → 设计 324d1612 #94A3B8（收起态 page-26 才是 #CBD5E1，逐帧不同）')
red.append('  2) panel.h             223 → 设计 225.5：选项行 54（设计 55，副行行盒 13.2 → 设计显式 h16）+ 面板用 border（占布局）')
red.append('  3) panel.ring          none → 设计 stroke 0.8 #2563EB + effects(0,12,24,rgba(15,23,42,0.1))（原用 border 实现，无投影）')
red.append('  4) row.w               352 → 设计 354（面板内容宽 = 366 − 2×6；border 0.8 挤掉 1.6px）')
red.append('  5) panel.actionIcon.w  13 → 设计图层 w17（盒 = 声明宽 17）')
red.append('  6) panel.actionIcon.h  13 → 22.5 = 字号 15 × 1.5（图标字形行盒）')
red.append('')
red.append('探针自身期望值 bug（已在探针内修正、不计页面账；修正后重跑红基线才有上面这 6 条）：')
red.append('  · nav.left.gap 断在 .nav__titles 的 columnGap（组件里标题块本身就是竖排容器）→ 改为断「标题 x − 返回右界」= 12')
red.append('  · cred.chevron.color / empty.glyph.color 读元素自身 color（D5 规定图标是 CSS 占位形状，颜色落在 ::before 的')
red.append('    border-color / background 上）→ 改用 chkP 读 ::before 的声明值')
red.append('  · row.h/panel.h 的容差与分帧口径：面板「首行选中态」是设计帧自身矛盾（选择框显占位、首行却画了底 #EFF6FF + 对勾）')
red.append('    → 不照抄，改断「三行都不高亮」+ 选中时由真实选择驱动（phase3 实测）')
io.open(os.path.join(EVD, 'red-序号12v2-checks-设计期望值偏差.txt'), 'w', encoding='utf-8').write('\n'.join(red))

green = ['序号 12-v2 载体页 checks 绿基线（修复后源码；两轮独立测量）', '']
green.append(phases_block(GRN1, 'GREEN run1'))
green.append(phases_block(GRN2, 'GREEN run2'))
green.append('两轮一致性（cmp-measure-runs.py phase1）：\n' + sh(
    'python .agents/state/cmp-measure-runs.py %s %s phase1' % (GRN1, GRN2)))
green.append('共用组件回归门（12-v1 同页初始态，同一份 QuoteFormView.vue）：\n' + sh(
    'python .agents/state/cmp-measure-runs.py %s %s phase1' % (V1A, V1B)))
green.append(phases_block(V1A, '12-v1 recheck run1'))
io.open(os.path.join(EVD, 'green-序号12v2-checks-设计期望值.txt'), 'w', encoding='utf-8').write('\n'.join(green))

act = ['序号 12-v2 交互回放（?scenario=actions，两轮）', '']
act.append(phases_block(ACT1, 'ACTIONS run1'))
act.append(phases_block(ACT2, 'ACTIONS run2'))
a1, a2 = load(ACT1), load(ACT2)
same = {k: (a1.get(k) == a2.get(k)) for k in ('phase2', 'phase3', 'phase3b', 'phase4')}
req1 = io.open(os.path.join(EVD, 'requests-序号12-v2-checks-actions-run1.txt'), encoding='utf-8').read()
req2 = io.open(os.path.join(EVD, 'requests-序号12-v2-checks-actions-run2.txt'), encoding='utf-8').read()
act.append('两轮一致性：' + ' · '.join('%s 逐字段相同 = %s' % (k, v) for k, v in same.items())
           + ' · serve 实收请求行逐字节相同 = %s' % (req1 == req2))
act.append('\n=== serve 实收请求行（run1 / run2）===')
for tag in ('run1', 'run2'):
    p = os.path.join(EVD, 'requests-序号12-v2-checks-actions-%s.txt' % tag)
    act.append('--- %s' % p)
    if os.path.exists(p):
        act.append(io.open(p, encoding='utf-8').read().strip())
act.append('\n纯测量轮（无 scenario）实收请求：1 行（仅首屏 GET /credentials）· 见 requests-序号12-v2-checks-run{1,2}.txt')
io.open(os.path.join(EVD, 'actions-序号12v2-交互回放.txt'), 'w', encoding='utf-8').write('\n'.join(act))

setg = ['序号 12-v2「前往「我的设置」新建凭证」落点（?scenario=settings，两轮）',
        '（台账旧备注写「序号 23 未实现 → hash 不变」——本轮实测 /pages/settings/index 已实现且注册在 pages.json，口径已改正）',
        '']
setg.append(phases_block(SET1, 'SETTINGS run1'))
setg.append(phases_block(SET2, 'SETTINGS run2'))
s1, s2 = load(SET1), load(SET2)
rq1 = io.open(os.path.join(EVD, 'requests-序号12-v2-checks-settings-run1.txt'), encoding='utf-8').read()
rq2 = io.open(os.path.join(EVD, 'requests-序号12-v2-checks-settings-run2.txt'), encoding='utf-8').read()
setg.append('两轮一致性：phase2 逐字段相同 = %s · serve 实收请求行逐字节相同 = %s'
            % (s1.get('phase2') == s2.get('phase2'), rq1 == rq2))
setg.append('\n=== serve 实收请求行 ===')
setg.append(rq1.strip())
io.open(os.path.join(EVD, 'settings-序号12v2-设置页落点.txt'), 'w', encoding='utf-8').write('\n'.join(setg))

print('wrote:')
for f in ('red-序号12v2-checks-设计期望值偏差.txt', 'green-序号12v2-checks-设计期望值.txt',
          'actions-序号12v2-交互回放.txt', 'settings-序号12v2-设置页落点.txt'):
    p = os.path.join(EVD, f)
    print('  %s  %d bytes' % (p, os.path.getsize(p)))
