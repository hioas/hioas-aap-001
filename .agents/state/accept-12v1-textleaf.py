# -*- coding: utf-8 -*-
"""把序号 12-v1（page-26「新增报价单-初始态」）经设计 PNG + 盒算术判定的「非偏差」登记进 textleaf-accept.json。

判据优先级（与既有规则一致）：①设计显式 height ②design PNG 的盒/带实测 ③fs × lineHeight；②③冲突以 ② 为准。
本页新增的判法：**盒算术** —— 用设计树里已声明的 padding/height/gap 反推该文本所在行的行盒，
再与设计 PNG 的盒边界（scan-col）和墨迹带（png-textbands）对照；两边同时自洽才算核定。

⚠️ 键名口径：`textleaf-audit.py` 的 class 键 = 叶子**自身 class 链的第一个 token**
（`'hint__text hint__text--blue' → 'hint__text'`），所以一个键可能覆盖多个变体 —— 理由里必须写清覆盖了哪些。

证据：evidence/cmp-序号12v1-文本叶子行盒-逐类带.txt（逐类 ink 带）· evidence/cmp-序号12v1-行盒盒算术.txt（盒算术实测）。

用法: python .agents/state/accept-12v1-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
EVID = 'evidence/cmp-序号12v1-文本叶子行盒-逐类带.txt + evidence/cmp-序号12v1-行盒盒算术.txt'
AT = '2026-09-16 19:55'
PAGE = 'page-26'
TAG = '12-v1'

ITEMS = [
    ('label__text', 'fs13 × lh1.2 = 15.6', 'line-height 17',
     '盒算术定死 = 17：设计 字段-报价单名称(61760d8d) = [字段标签行 fit_content][container padTop 8 → 名称输入框 h=48]，'
     '输入框顶 − 8 − 标签行顶 = L、墨迹 = 标签行顶 + (L−13)/2；链1（报价单名称）输入框顶 277 / 墨迹 254 → L = 17；'
     '链2（报价单号）405 / 382 → L = 17。缩到 15.6 会把输入框整体上移 1.4px（PNG 实测输入框顶设计 277）。'
     '（同键覆盖 label--gap8 的「报价单号」行。）'),
    ('label__star', 'fs13 × lh1.2 = 15.6', 'line-height 17',
     '与同行「报价单名称」同盒（字段标签行 gap4 / align-center，行盒 = max(标签, 星号) = 17）；设计墨迹 254..259 = 实现 254..259。'),
    ('notice__text', 'fs12 × lh1.2 = 14.4', 'line-height 18',
     '盒算术定死 = 18：须知卡高 = 16 + 标题行 22 + (12+18) + (8+18) + (8+H3) + 16 = 118 + H3；'
     'PNG x=402 实测卡白区 945..1098（设计）= 947..1100（实现）→ 卡高两边同为 154 → H3 = 36 = 2 行 × 18。'
     '条目3 两行墨迹起点设计 1052/1067、实现 1054/1072（行盒同为 18，ink 起点差 = 设计字体与 H5 回退字体的字形墨迹差）。'),
    ('notice__no', 'fs10 × lh1.2 = 12', 'line-height 15',
     '数字位于设计声明 18×18 的序号点内（align-items:center）→ 行盒不承重；序号点列实测 995/1021/1047（设计）= 998/1024/1050（实现），'
     '点距两侧同为 26（= 点 18 + 条目间 padding 8）。'),
    ('card__title', 'fs15 × lh1.2 = 18（登记页的 sm 变体 fs13 → 15.6）', '主标题 line-height 20 · --sm line-height 18',
     '①主标题（fs15）：卡片头行竖条（803a0d01 5×16 #2563EB）居中 → 行高 = 2×(竖条中心 − 头行顶)；'
     'PNG 实测竖条 ink 217..232（设计）= 217..232（实现）⇒ 头行高一致；卡1 白区上界两边同为 200、卡1/卡2 之间 624..640 两边同界'
     '（探针 page.cardHeights [425,291,156] ±2 全绿）。设计渲染值在 18~20 之间（±1 不可分辨），本轮不在此 churn。'
     '②--sm（fs13「填写须知」）：须知卡标题行 T = 22（PNG 实测 卡内容顶 961 + 22 + 容器 padTop 12 = 序号点 995），'
     '由图标字形盒（fs16 remixicon 24）与文本行盒较大者决定；墨迹 966..978（设计）= 968..980（实现），+2 = 提示条 CJK 换行顺延。'),
    ('counter__text', 'fs11 × lh1.2 = 13.2', 'line-height 16.5',
     '与同页字数提示/提示行同族 11px 行盒；PNG 实测 x374..399：设计 316..325 + 334..344 = 实现 316..324 + 334..344（起点相同、带高相同）。'),
    ('hint__text', 'fs11 × lh1.2 = 13.2', 'line-height 16.5',
     '字段步进核对：字段2 → 字段3 的标签墨迹 382 → 513 = 131（设计）、383 → 514 = 131（实现）⇒ 提示行行盒不影响字段步进；'
     '墨迹：设计 462..473 = 实现 463..474（+1，H5 回退字体）。（同键覆盖 --blue 变体：设计 591..602 = 实现 593..604，+2 = 顺延，带高同为 12。）'),
    ('readonly-box__text', 'fs14 × lh1.2 = 16.8', 'line-height 21',
     '位于设计声明 h=48 的只读盒内（align-items:center）→ 行盒不承重；PNG 实测墨迹 423..436（设计）= 423..436（实现），逐值相同。'),
    ('required__text', 'fs11 × lh1.2 = 13.2', 'line-height 16.5',
     '位于卡片头行内（align-center，行高由竖条/标题决定）→ 不承重；墨迹 219..229（设计）= 220..230（实现），+1 = 顺延/字体。'),
    ('tag__text', 'fs10 × lh1.2 = 12', 'line-height 15',
     '标签胶囊高由内边距决定（设计声明胶囊带 379..397 = 实现 380..397）；同页 fs10（序号点 / 样例单号）同为 15。'
     '（同键覆盖 tag__text--chip「待带出」：墨迹 660..670（设计）= 660..670（实现），带高与起点均相同。）'),
    ('sample-pill__text', 'fs10 × lh1.2 = 12', 'line-height 15',
     '样例单号 QT-XXXXXXXX-XXXX：墨迹 425..434（设计）= 426..435（实现），+1 = 顺延；与同页 fs10 口径一致。'),
    ('select__value', 'fs14 × lh1.2 = 16.8', 'line-height 21',
     '位于定高选择框内居中 → 行盒不承重；墨迹 554..567（设计）= 553..566（实现），−1。'),
    ('uni-input-placeholder', 'fs14 × lh1.2 = 16.8', 'line-height 19.6',
     '位于设计声明 h=48 的输入框内居中 → 不承重；墨迹 295..309（设计）= 293..307（实现），−2 = H5 回退字体字形墨迹差'
     '（占位文本左右界与设计一致）。（叶子自身 class 为 `uni-input-placeholder input-box__placeholder`，审计键取第一个 token。）'),
    ('bar__hint-text', 'fs11 × lh1.2 = 13.2', 'line-height 16.5',
     '说明行行盒不承重：该行高由同排图标字形盒（05adee9c fs13 remixicon → 13×1.5 = 19.5）决定；'
     '条高 = 12 + 19.5 + 10(container padTop) + 48(按钮) + 28 = 118 ✓（PNG x=8 实测设计条顶 1120 / 实现 1122，条高 ±1）。'
     '文本在该行内居中 → 行盒 16.5 与 13.2 只差 ≤1px 墨迹（实测 1136..1146 设计 = 1139..1149 实现，+3 = 提示条 CJK 换行顺延）。'),
]

data = json.load(io.open(P, encoding='utf-8'))
if '--reset' in sys.argv:
    before = len(data['items'])
    data['items'] = [it for it in data['items'] if it.get('page') != PAGE]
    print('清空 page-26 旧条目 %d 条' % (before - len(data['items'])))
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
