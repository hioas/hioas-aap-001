# -*- coding: utf-8 -*-
"""把序号 7（page-7-2「检测未通过报告」）经设计声明值 + 设计 PNG 盒/带实测判定的「非偏差」登记进 textleaf-accept.json。

判据优先级：①设计显式 height ②design PNG 的盒/带实测 ③fs × lineHeight；②③冲突以 ② 为准。
键名口径：`textleaf-audit.py` 的 class 键 = 叶子自身 class 链的第一个 token（一个键覆盖多个变体：
本页 `dim__label` / `dim__score` 各覆盖 8 条、`card__label` / `card__sub` 同属封面顶行）。

证据：evidence/cmp-序号7-文本叶子行盒-逐类带.txt（逐字墨迹带，设计与实现同窗口）
      evidence/cmp-序号7-设计PNGvs实现截图-结构带.txt（整页结构带 53/57 命中 · 位移中位 +1）
      设计 PNG .agents/state/design-shots/page-7-2.png（430×1110）· 实现截图 20:23 轮（430×1180）

用法: python .agents/state/accept-7-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
EVID = ('evidence/cmp-序号7-文本叶子行盒-逐类带.txt + evidence/cmp-序号7-设计PNGvs实现截图-结构带.txt'
        ' + design-shots/page-7-2.png')
AT = '2026-09-16 20:40'
PAGE = 'page-7-2'
TAG = '7'

ITEMS = [
    ('card__label', 'fs12 × lh1.2 = 14.4', 'line-height 18',
     '判据②盒算术：封面顶行 1093d116（horizontal · alignItems=center · fit_content，子节点只有两个文本叶子）→ 行高即文本行盒；'
     '未通过封面卡 07b82bea padding 20 使行顶 = 卡顶 108 + 20 = 128，设计墨迹 131 ⇒ 偏移 3 = (L−12)/2 ⇒ **L = 18**。'
     'PNG：综合检测结论 设计 131..142 = 实现 131..142（逐值相同）。'),
    ('card__sub', 'fs12 × lh1.2 = 14.4', 'line-height 18',
     '与 card__label 同一行（封面顶行），行盒同解 = 18；PNG：华南备线路 · 备用通道 设计 131..142 = 实现 131..142。'),
    ('detail__title', 'fs14 × lh1.2 = 16.8', 'line-height 20',
     'D2标题行 b2bba46b（fit_content，子节点 = 标题文本 + spacer + 分值文本）→ 行高由文本行盒定；'
     'PNG：D2 鉴权有效性 · 详情 设计 791..804 vs 实现 793..806（**+2 = 14px 拉丁/数字混排的回退字体墨迹偏移**，同页结构带 19/19 命中、卡片边界 ±1）。'),
    ('detail__score', 'fs14 × lh1.2 = 16.8', 'line-height 20',
     '与 detail__title 同一行（D2标题行），两侧同 +2（相对差 0）⇒ 行盒一致、差为字体墨迹：设计 791..804 = 实现 793..806。'),
    ('dim__label', 'fs12 × lh1.2 = 14.4', 'line-height 18',
     '评分项行 df5c9dfc（fit_content，子节点 = 标签 + 进度条 h8 + 分值）→ 行高由文本定；'
     'PNG 四行标签墨迹起点 设计 436/466/496/526 = 实现 437/467/497/527：**行距两侧同为 30**（+1 常量偏移）⇒ 行盒一致。'),
    ('dim__score', 'fs12 × lh1.2 = 14.4', 'line-height 18',
     '与 dim__label 同行（分值列）：设计 437..446 / 467..475 / 497..506 / 527..536 = 实现 438..447 / 468..476 / 498..507 / 528..537（+1、带高 9~10 相同）。'),
    ('score', 'fs38 × lh1.2 = 45.6', 'line-height 57',
     '判据②：38px ExtraBold 数字「54」—— 实现 span 实测 163..218（55 高 · lh 57px），设计墨迹 175..204（30 行）与实现 178..207（30 行）'
     '**带高相同、起点 +3**（38px 下 3px ≈ 8% em，属回退字体数字基线偏移）；结构带 x=36..394 列 34/38 命中'
     '（未命中 4 条 = 376/379/385 封面卡投影 AA + 707 换行）。57 由本页 checks 轮按设计 PNG 定（`.score` 行高 57px = 38×1.5，'
     '见 evidence/review-序号7-checks-报告.md §5）：同卡结论胶囊设计边界 176/203 = 实现 177/204 反证块高 57 —— '
     '若按 45.6 则块矮 11px、其下全部内容上移约 11px。'),
    ('verdict-row__text', 'fs12 × lh1.2 = 14.4', 'line-height 18',
     '两行块：设计 310..323 / 326..336 vs 实现 310..323 / 329..339 —— **第 1 行逐值相同**，第 2 行差来自**换行点不同**'
     '（设计 line2 墨迹 75 列 vs 实现 86 列，H5 回退字体换行）。行盒由同卡内一票否决条的填充盒直证（见 veto-box__text）；'
     '封面卡边界与卡2 顶在结构带里 ±1。'),
    ('veto-box__text', 'fs12 × lh1.2 = 14.4', 'line-height 18',
     '判据②（决定性）：一票否决条 c93a930a padding 12 的**填充盒**（#FEF2F2）在 x=200 列实测 —— 设计 234..293 = 实现 235..294，'
     '**盒高两侧同为 60 = 12 + 2×18 + 12 ⇒ 12px 行盒 = 18**（声明模型 14.4 会给出 52.8）。'
     '墨迹：设计 250..262 / 266..276 vs 实现 250..261 / 269..279（第 1 行 −1、第 2 行 +3 = 换行/字体墨迹）。'),
    ('weight-box__text', 'h=36（设计**显式 height**）', 'line-height 18',
     '判据①设计显式 h=36：权重说明 def3b414 padding 12 内的叶子 18dda7b2 **height=36 = 2 × 18**（append 声明 w=fill_container h=36 · fs11）'
     '⇒ 行盒 18 = 实现值；实现 2 行块高 = 2 × 18 = 36 ✓。墨迹 设计 694..705 / 707..717 vs 实现 693..704 / 711..721（第 1 行 −1、'
     '第 2 行差为换行点不同：设计 line2 墨迹 25 列 vs 实现 14 列）。'),
]

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
