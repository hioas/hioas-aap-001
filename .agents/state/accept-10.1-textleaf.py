# -*- coding: utf-8 -*-
"""把序号 10.1（page-10-1-2「供应商档案」）判定的「非偏差」登记进 textleaf-accept.json。

判据优先级：①设计显式 height ②design PNG 的盒/带实测 ③fs × lineHeight；②③冲突以 ② 为准。
本轮据设计 PNG 与盒算术统一了本页的多行文本模型：
  设计里 fs12 文本的「块高」= n × 18（自然 CJK 行框，或显式声明），
  而字形行按 lh1.2 = 14.4 排布并在块内垂直居中
  （1 行：块 18 → 墨迹 636..648；2 行：块 36 → 墨迹 202..214 / 217..228 —— 两种 n 同解）。
=> 本页 2 处真偏差按此模型先红后绿改源码（.intro-box__text 与 .gate__text：块高保留、行高改 14.4 + 盒内居中）；
   其余待判读 class 判为非偏差（固定高胶囊/定高按钮内的单行文本不承重）。

证据：evidence/cmp-序号10.1-文本叶子-逐类带.txt · evidence/red-序号10.1-textleaf-简介行盒.txt
      · evidence/redgreen-序号10.1-textleaf-行盒.txt · .agents/state/design-shots/page-10-1-2.png（430×1414）
      · 实现截图 logs/screenshots/20260916-2035-序10.1-文本叶子维度收口-h5-430宽.png

用法: python .agents/state/accept-10.1-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
EVID = ('evidence/cmp-序号10.1-文本叶子-逐类带.txt + evidence/redgreen-序号10.1-textleaf-行盒.txt'
        ' + design-shots/page-10-1-2.png + logs/screenshots/20260916-2035-序10.1-文本叶子维度收口-h5-430宽.png')
AT = '2026-09-16 20:15'
PAGE = 'page-10-1-2'
TAG = '10.1'

ITEMS = [
    ('intro-box__text',
     'h=40（设计显式 height，2 行块高）', '行高 14.4px + 块高 40 + 盒内居中（本轮已改）',
     '本轮真偏差，已先红后绿：design 234362e0 显式 height=40 是【块高】（2 行）；行盒按判据②设计 PNG 渲染实测 = '
     'fs12 × lh1.2 = 14.4（设计墨迹 917..929 / 932..943，行距 15）。修前实现 line-height 20 → 墨迹 915..927 / 936..946'
     '（行距 21，第 2 行低 4px）；改后 918..930 / 933..943 = 逐行 ±1（H5 回退字体）。盒 899..962 = 64 两侧逐值相同、'
     'docScrollHeight 1414 = 设计帧高不变。同族口径 = 序号 1 .disclaimer__body。audit 的 want=40 是「显式 height 当行盒」的'
     '模型口径差 => 登记为已核定。'),
    ('gate__text',
     'fs12 × lh1.2 = 14.4', '行高 14.4px + 块高 36 + 盒内居中（本轮已改）',
     '本轮真偏差，已先红后绿：闸门提示 87815f1d padding 12 的 #FFFBEB 填充盒在 x=215 列实测 —— 设计 186..245 = 实现 '
     '186..245（两侧同为 60 = 12 + 36 + 12 => 块高 36；图标行框 27 不承重，图标墨迹中心两侧同为 211.5 => 盒 198..225 = 27 高，'
     '与全站「字号×1.5」一致）。块内字形行按设计渲染实测 14.4 排 + 垂直居中：改后实现墨迹 203..214 / 218..228 = 设计 '
     '202..214 / 217..228（±1）；修前 line-height 18 → 220..230（第 2 行低 3px）。盒高与整页几何不变（docH 1414）。'),
    ('btn-upload__text',
     'fs13 × lh1.2 = 15.6', 'line-height 18',
     '判据①不承重：上传新资质按钮 f79c7824 height=44 + alignItems=center，叶子在定高居中盒内 => 行盒变动只移动墨迹 ≤1px。'
     '判据②墨迹：设计 1266..1278 = 实现 1266..1278（逐值相同）；按钮盒 1250..1293(44) 两侧相同。'),
    ('completeness__text',
     'fs11 × lh1.2 = 13.2', 'line-height 24',
     '判据①不承重：顶部「完整度 72%」胶囊 c440ccf2 height=24 + padding 0/8 + alignItems=center => 叶子在定高胶囊内。'
     '判据②墨迹：设计 60..70 vs 实现 61..71（+1，胶囊上下边带 54/77 两侧相同）。'),
    ('lock-badge__text',
     'fs11 × lh1.2 = 13.2', 'line-height 14',
     '判据①不承重：锁定标签 a957abfa height=22 + padding 0/8 + alignItems=center。判据②墨迹：设计 306..316 vs 实现 '
     '307..317（+1）；胶囊边带 300/322 两侧相同。'),
    ('qual-row__badge-text',
     'fs11 × lh1.2 = 13.2', 'line-height 14',
     '覆盖两个变体（--success「已通过」与 --warning「条件必传」）：判据①不承重 —— 角标 f01c05c7 / 0eb1d1a0 height=20 + '
     'padding 0/8 + alignItems=center。判据②墨迹：设计 1076..1086 / 1140..1150 vs 实现 1077..1087 / 1141..1151（各 +1）；'
     '角标边带 1072/1091 与 1136/1155 两侧同高（实现边带 6px vs 设计 3px = ring 与中心描边的 AA 宽度差，非几何差）。'),
    ('type-chip__text',
     'fs11 × lh1.2 = 13.2', 'line-height 14',
     '判据①不承重：类型胶囊 c2cd28be height=24 + padding 0/12 + alignItems=center。判据②墨迹：设计 479..489 vs 实现 '
     '480..490（+1）；胶囊上下边带 461..462 两侧逐值相同。'),
    ('note__text',
     'fs12 × lh1.2 = 14.4', 'line-height 18',
     '单行文本：设计的「块高 = n × 18 自然行框 + 字形行 14.4 居中」模型给出块 18 => 墨迹 636..648；实现（行盒 18、块顶对齐）'
     '实测 636..648 = 设计逐值相同（两模型对 n=1 同解，差 <1px）=> 不承重、无需改动。（与 gate__text 同页同族对照：n=2 时'
     '两模型才分叉 3px，故只改 2 行块。）'),
    ('head-line__percent',
     'fs14 × lh1.2 = 16.8', 'line-height 20',
     '判据②：完整度标题行 8f58bea7（fit_content = 标题 + spacer + 72%），行高由文本自然行框定（fs14 CJK ≈ 20~21，非 16.8）。'
     '墨迹：设计 132..143 vs 实现 133..144（+1），同行「档案完整度」同为 +1；卡1 高 158 = 设计 158（PNG 实测）=> 行盒等价。'),
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
