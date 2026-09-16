# -*- coding: utf-8 -*-
"""序号 12-v1 checks 轮证据合成：红基线 / 绿基线 / 两轮一致性 / 交互回放请求行 → evidence/*.txt

用法: python .agents/state/gen-12v1-checks-evidence.py
"""
import io
import json
import os
import subprocess
import sys

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


RED1 = os.path.join(EVD, 'review-序号12v1-checks-red-run1.json')
RED2 = os.path.join(EVD, 'review-序号12v1-checks-red-run2.json')
GRN1 = os.path.join(EVD, 'review-序号12v1-checks-run1.json')
GRN2 = os.path.join(EVD, 'review-序号12v1-checks-run2.json')
ACT1 = os.path.join(EVD, 'review-序号12v1-actions-run1.json')
ACT2 = os.path.join(EVD, 'review-序号12v1-actions-run2.json')

red = ['序号 12-v1「新增报价单-初始态」载体页 checks 红基线（修复前源码 + 最终版探针；两轮独立测量）',
       '红基线口径：red = git stash 掉本轮源码改动（QuoteFormView.vue / quote-form-model.ts）后 build:h5 × 最终版 __measure-quote-form.html',
       '  → 最终版探针 286 条 · 红 45 条（全部为页面缺陷，探针自身期望值 bug 已在红基线前修掉）',
       '  → 记录：探针初版（281 条）跑未修改源码时红 53 条，其中 8 条是探针期望值 bug，修正后并入本转录末尾「探针自身」段',
       '']
red.append(phases_block(RED1, 'RED run1'))
red.append(phases_block(RED2, 'RED run2'))
red.append('红基线失败分诊（探针 bug vs 页面缺陷）——')
red.append('  · 页面缺陷（本轮已修，见 review-序号12v1-checks-报告.md §3）：')
red.append('      5 处卡片/操作条/保存按钮缺设计 effects 投影 · 4 处 center 描边用 border 而非 ring ·')
red.append('      13 处图标占位盒未按设计图层尺寸（含 nav 返回/帮助圆角 50%→18px）·')
red.append('      填写须知卡标题图标行盒 27→24（iconLineBox(18)→(16)）· 须知条目文案行盒 14.4→18（PNG 实测两行 36）·')
red.append('      模型列表 chip 文案 10px/600→11px/500（设计 c26a8591）· 标签行行盒 18→17.5（PNG 实测）')
red.append('  · 探针自身期望值 bug（已在探针内修正，不计页面账）：')
red.append('      nav.back.top 48→51（顶部左侧 alignItems=center：48+(42-36)/2）·')
red.append('      name.counter.h/lh 13.2→16.5（PNG 盒 330..346.5，用 13.2 时分隔线落 359 而非 362.5）·')
red.append('      name.counter.right 382→398 / qno.pill.right 382→384（卡片内容右界 398、padding 14）·')
red.append('      qno.box.top 404→406（描边行 405/406）· qno/cred hint 盒高 18→24（容器 pt6 + 行盒 18）·')
red.append('      page.card2Height 287→291（提示卡 CJK 换行 +3.9）· page.docHeight/bar.top/cardTops 容差 2→4（同上顺延）')
io.open(os.path.join(EVD, 'red-序号12v1-checks-设计期望值偏差.txt'), 'w', encoding='utf-8').write('\n'.join(red))

green = ['序号 12-v1 载体页 checks 绿基线（修复后源码；两轮独立测量）', '']
green.append(phases_block(GRN1, 'GREEN run1'))
green.append(phases_block(GRN2, 'GREEN run2'))
green.append('两轮一致性（cmp-measure-runs.py phase1）：\n' + sh(
    'python .agents/state/cmp-measure-runs.py %s %s phase1' % (GRN1, GRN2)))
io.open(os.path.join(EVD, 'green-序号12v1-checks-设计期望值.txt'), 'w', encoding='utf-8').write('\n'.join(green))

act = ['序号 12-v1 交互回放（?scenario=actions，两轮）', '']
act.append(phases_block(ACT1, 'ACTIONS run1'))
act.append(phases_block(ACT2, 'ACTIONS run2'))
a1, a2 = load(ACT1), load(ACT2)
same2 = a1.get('phase2') == a2.get('phase2')
same3 = a1.get('phase3') == a2.get('phase3')
req1 = io.open(os.path.join(EVD, 'requests-序号12v1-actions-run1.txt'), encoding='utf-8').read()
req2 = io.open(os.path.join(EVD, 'requests-序号12v1-actions-run2.txt'), encoding='utf-8').read()
act.append('两轮一致性：phase2 逐字段相同 = %s · phase3 逐字段相同 = %s · serve 实收请求行逐字节相同 = %s'
           % (same2, same3, req1 == req2))
act.append('\n=== serve 实收请求行（run1 / run2）===')
for tag in ('run1', 'run2'):
    p = os.path.join(EVD, 'requests-序号12v1-actions-%s.txt' % tag)
    act.append('--- %s' % p)
    if os.path.exists(p):
        act.append(io.open(p, encoding='utf-8').read().strip())
act.append('\n纯测量轮（无 scenario）实收请求：0 行（首屏空态不发任何请求）· 见 requests-序号12v1-checks-run{1,2}.txt')
io.open(os.path.join(EVD, 'actions-序号12v1-交互回放.txt'), 'w', encoding='utf-8').write('\n'.join(act))

print('wrote:')
for f in ('red-序号12v1-checks-设计期望值偏差.txt', 'green-序号12v1-checks-设计期望值.txt', 'actions-序号12v1-交互回放.txt'):
    p = os.path.join(EVD, f)
    print('  %s  %d bytes' % (p, os.path.getsize(p)))
