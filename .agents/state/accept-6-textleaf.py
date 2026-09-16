# -*- coding: utf-8 -*-
"""把序号 6（page-6）经设计 PNG 逐类实测判定的「非偏差」登记进 textleaf-accept.json。

判据优先级（与既有规则一致）：①设计显式 height ②design PNG 的盒/带实测 ③fs × lineHeight；
②③冲突以 ② 为准。证据：evidence/cmp-序号6-设计PNGvs实现截图-行盒判读.txt（修前/设计）
与 …-修后.txt（设计 vs 实现同窗口 ink 带逐条相同）。

用法: python .agents/state/accept-6-textleaf.py [--dry]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
EVID = 'evidence/cmp-序号6-设计PNGvs实现截图-行盒判读-修后.txt + evidence/cmp-序号6-明细卡纵向对账-修后.txt'
AT = '2026-09-16 19:30'

ITEMS = [
    ('card__title', 'fs15 × lh1.2 = 18（封面卡 fs12 → 14.4）', "封面卡 18 / 其余卡 20",
     'design PNG 实测：综合检测结论 x56..134 → 设计 131..142 = 实现 131..142；关键指标 x46..112 → 设计 556..570 = 实现 556..570。'
     '行盒若缩到 18/14.4 会把卡高与卡间距拉离设计 PNG 的 pitch。'),
    ('metric__label', 'fs10.5 × lh1.2 = 12.6', 'line-height 15',
     'design PNG 实测 x45..124：设计 604..613 = 实现 604..613（模型指纹相似度行）。'),
    ('metric__sub', 'fs10 × lh1.2 = 12', 'line-height 14',
     'design PNG 实测 x229..308：设计 830..831 + 840..849 = 实现 830..831 + 840..849（30 分钟观测窗口行）。'),
    ('metric__value', 'fs19 × lh1.2 = 22.8', 'line-height 24',
     'design PNG 实测 x45..92：设计 612..613 + 625..640 = 实现同值（0.93 值行；Extrabold 19px 的自然行盒 24）。'),
    ('group__title', 'fs13 × lh1.2 = 15.6', 'line-height 18',
     'design PNG 实测 x46..214 七个组标题 ink：A 1508..1520 / B 1946..1958 / C 2341..2353 / D 2735..2748 / E 3217..3229 / '
     'F 3611..3624 / G 4006..4019 —— 实现修后逐条相同（修前整体 +8，根因是明细说明行盒，不是组标题）。'),
    ('score__meta-text', 'fs12 × lh1.2 = 14.4', 'line-height 17',
     'design PNG 实测 x93..148：设计 173..184 + 191..201 = 实现同值（综合评分 / 满分 100 两行）。'),
    ('radar__label', 'design 叶子 8c889494 自身 h=12.43 与 lh=1.31（11×1.31=14.41）互相矛盾', 'line-height 1.31（=14.41）',
     '设计树里该 paragraph 自己声明 lineHeight=1.31，实现按 1.31 落地；design PNG x204..232：设计 962..972 = 实现 962..972。'),
    ('report-page__no', 'fs11 × lh1.2 = 13.2', 'line-height 16',
     '该帧的顶部栏文本是 frame 5d860a4b 显式 h=16（叶子 202cd360 为 fill_container）→ 判据①显式 height 优先；'
     '2026-09-16 17:45 轮已按 design PNG 墨迹 x318..412 w95 核定并加口径锁（evidence/序号6-报告编号前缀核定.txt）。'),
    ('disclaimer__body', '设计叶子 h=51（块高，不是单行行盒）', 'line-height 17 · 块高 50',
     '51 = 3 行 × 17；实现块高 50（±1 = 设计小数坐标链取整）。审计把「多行块高」与「单行行盒」直接比较，属模型口径差。'),
    ('evidence-row__value', '设计叶子 h=32（块高）', 'line-height 16 · 块高 32',
     '32 = 2 行 × 16；实现块高 32（逐行相同）。'),
    ('finding__body', '设计叶子 h=34（块高）', 'line-height 17 · 块高 33',
     '34 = 2 行 × 17；实现块高 33（±1）。'),
    ('note-box', '设计叶子 h=48（块高）', 'line-height 16 · 块高 72',
     '48 = 3 行 × 16；实现 3 行 × 16 + padding 12×2 = 72（design 104230be frame = 同值）。'),
    ('verdict-box__text', '设计叶子 h=38（块高）', 'line-height 19 · 块高 36',
     '38 = 2 行 × 19；实现块高 36（±2 = 设计小数坐标 + H5 回退字体），17:45 轮已逐行核对墨迹。'),
    ('detail-summary', 'fs11 × lh1.2 = 13.2', 'line-height 16（本轮按设计 frame 修正）',
     'design 明细说明 8485b93b frame h=24 = padding-top 8 + 行盒 16 → 行盒 16；design PNG 1476..1486 = 实现 1476..1486。'),
    ('dim__text', 'fs12 × lh1.2 = 14.4', 'line-height 16',
     'design PNG 实测 x46..120 六行维度名 ink：设计 1208..1219 / 1236..1247 / 1264..1275 / 1292..1303 / 1320..1331 / 1348..1359 '
     '= 实现逐行相同（行距 28 = 行盒 16 + 12；缩到 14.4 会破坏 28 的行距）。'),
    ('dim__score', 'fs12 × lh1.2 = 14.4', 'line-height 16',
     'design PNG 实测 x366..400 六行分值 ink：设计 1210..1219 / 1238..1247 / 1266..1275 / 1294..1303 / 1322..1331 / 1350..1359 '
     '= 实现逐行相同（与维度名列同一行盒）。'),
]

data = json.load(io.open(P, encoding='utf-8'))
have = {(it.get('page'), (it.get('class') or '').lstrip('.')) for it in data['items']}
added = 0
for cls, declared, impl, reason in ITEMS:
    if ('page-6', cls) in have:
        print('已存在：%s（跳过）' % cls)
        continue
    data['items'].append({
        'page': 'page-6', 'tag': '6', 'class': cls, 'declared': declared, 'impl': impl,
        'verdict': 'not-a-deviation', 'reason': reason, 'evidence': EVID, 'at': AT,
    })
    added += 1
print('新增 %d 条（合计 %d 条）' % (added, len(data['items'])))
if '--dry' not in sys.argv:
    io.open(P, 'w', encoding='utf-8', newline='').write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('已写盘 %s' % P)
