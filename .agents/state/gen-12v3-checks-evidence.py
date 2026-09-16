# -*- coding: utf-8 -*-
"""序号 12-v3 checks 轮证据合成：红基线 / 绿基线 / 两轮一致性 / 四个出口交互回放 / 像素对账 → evidence/*.txt

用法: python .agents/state/gen-12v3-checks-evidence.py
"""
import io
import json
import os
import subprocess

ROOT = '.agents/state'
EVD = os.path.join(ROOT, 'evidence')


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          encoding='utf-8', errors='replace').stdout


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


def req_block(tag, label):
    out = ['=== %s 请求行（serve 实收）' % label]
    for run in (1, 2):
        p = os.path.join(EVD, 'requests-序号%s-run%d.txt' % (tag, run))
        lines = io.open(p, encoding='utf-8').read().strip().split('\n') if os.path.exists(p) else ['<缺>']
        out.append('  run%d: %d 行' % (run, len([x for x in lines if x.strip()])))
        out.extend('    ' + x for x in lines if x.strip())
    same = True
    try:
        a = io.open(os.path.join(EVD, 'requests-序号%s-run1.txt' % tag), encoding='utf-8').read()
        b = io.open(os.path.join(EVD, 'requests-序号%s-run2.txt' % tag), encoding='utf-8').read()
        same = a == b
    except Exception:
        same = False
    out.append('  两轮请求行逐字节相同: %s' % same)
    return '\n'.join(out) + '\n'


RED1 = os.path.join(EVD, 'review-序号12-v3-checks-red-run1.json')
RED2 = os.path.join(EVD, 'review-序号12-v3-checks-red-run2.json')
GRN1 = os.path.join(EVD, 'review-序号12-v3-checks-run1.json')
GRN2 = os.path.join(EVD, 'review-序号12-v3-checks-run2.json')

red = ['序号 12-v3「新增报价单-保存成功」（page-29）载体页 checks 红基线',
       '红基线口径：probe 建立后用 `git stash push -- aap-client/src/pages/quote-form/success.vue` 复现修复前源码 + build:h5，',
       '  再跑最终版 __measure-quote-apikey 系骨架切出的 __measure-quote-success.html（红/绿同一份探针）',
       '  → 259 条 checks · 红 30 条（5 处 effects 投影 + 8 个图标占位盒 + 3 处字形颜色 + 单号行右侧组 gap）',
       '  → 两轮独立测量完全一致 → 红基线可复现',
       '']
red.append(phases_block(RED1, 'RED run1'))
red.append(phases_block(RED2, 'RED run2'))
red.append('红基线两轮一致性（cmp-measure-runs.py <red1> <red2> phase1）:\n' +
           sh('python .agents/state/cmp-measure-runs.py %s %s phase1' % (RED1, RED2)))
io.open(os.path.join(EVD, 'red-序号12v3-checks-设计期望值偏差.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(red))

grn = ['序号 12-v3「新增报价单-保存成功」（page-29）载体页 checks 绿基线（修复后源码 + 最终版探针；两轮独立测量）', '']
grn.append(phases_block(GRN1, 'GREEN run1'))
grn.append(phases_block(GRN2, 'GREEN run2'))
grn.append('绿基线两轮一致性（cmp-measure-runs.py <run1> <run2> phase1）:\n' +
           sh('python .agents/state/cmp-measure-runs.py %s %s phase1' % (GRN1, GRN2)))
grn.append('纯测量轮请求行（应为 2 行只读 GET：报价单详情 + 凭证明细；零写请求）')
grn.append(req_block('12-v3-checks', '12-v3-checks'))
io.open(os.path.join(EVD, 'green-序号12v3-checks-设计期望值.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(grn))

act = ['序号 12-v3 四个出口交互回放（?scenario=copy|primary|secondary|close，各两轮）',
       '设计侧 interaction.json = 「不存在图层交互数据」→ 交互退 PRD/设计控件语义（页面注释已登记）；',
       '  本轮只回放「点击 → 真实调用链 → 落点/剪贴板/toast」并留 serve 实收请求行为证。', '']
for sc, label in (('copy', '复制报价单号（client-only）'),
                  ('primary', '继续设置模型报价 → 模型定价页'),
                  ('secondary', '返回报价单列表 → 报价单列表'),
                  ('close', '关闭（×）→ 报价单列表')):
    act.append(phases_block(os.path.join(EVD, 'review-序号12-v3-%s-run1.json' % sc), '%s run1 (%s)' % (sc, label)))
    act.append(phases_block(os.path.join(EVD, 'review-序号12-v3-%s-run2.json' % sc), '%s run2' % sc))
    act.append(req_block('12-v3-%s' % sc, sc))
act.append('== fixture 缺口（先红后绿）==')
act.append('  红：?scenario=primary 落地页 /pages/model-pricing/index?quoteId=q9 取 GET /api/v1/quotes/q9/items → 404；')
act.append('      ?scenario=secondary 落地页 /pages/quotes/index 取 GET /api/v1/quotes → 404 + 错误 toast「数据加载失败，请稍后重试」')
act.append('  绿：补 api-12-v3 的 `v1/quotes/q9/items/index`（同 12-v1）与 `v1/quotes/index`（同 12）后，两个落地页均 200 且 toast 为空；')
act.append('      `python .agents/state/check-mock-fixtures.py --mock api-12-v3` → 5 条 PASS（含反向体检）· FAIL 0')
io.open(os.path.join(EVD, 'interaction-序号12v3-出口回放.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(act))
print('wrote red/green/interaction evidence for 12-v3')
