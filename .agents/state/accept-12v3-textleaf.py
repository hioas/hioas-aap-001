# -*- coding: utf-8 -*-
"""把序号 12-v3（page-29「新增报价单-保存成功」）经设计 PNG + 盒算术判定的「非偏差」登记进 textleaf-accept.json。

判据优先级：①设计显式 height ②design PNG 的盒/带实测 ③fs × lineHeight；②③冲突以 ② 为准。
键名口径：`textleaf-audit.py` 的 class 键 = 叶子自身 class 链的第一个 token（一个键覆盖多个变体：
本页 `card__title` 覆盖 fs15 与 --sm fs14 两条、`tag__text` 覆盖 --on/--off 两条）。

证据：evidence/cmp-序号12v3-文本叶子行盒-逐类带.txt（逐类 ink 带，设计与实现同窗口）
      evidence/cmp-序号12v3-分区并排对账.txt（整页 4 区、24/25 命中）
      设计 PNG .agents/state/design-shots/page-29.png（430×1018）· 实现截图 20:12 轮同尺寸

用法: python .agents/state/accept-12v3-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
EVID = ('evidence/cmp-序号12v3-文本叶子行盒-逐类带.txt + evidence/cmp-序号12v3-分区并排对账.txt'
        ' + design-shots/page-29.png')
AT = '2026-09-16 20:15'
PAGE = 'page-29'
TAG = '12-v3'

ITEMS = [
    ('btn__text', 'fs14 × lh1.2 = 16.8', 'line-height 18',
     '判据①设计显式 h=48：次按钮 26d36f5b height=48（主按钮同）+ textAlignVertical=middle → 文本行盒不承重。'
     'PNG：继续设置模型报价 设计 901..915 = 实现 901..915；返回报价单列表 设计 959..972 vs 实现 960..973（+1，H5 回退字体墨迹）。'),
    ('card__title', 'fs15 × lh1.2 = 18（--sm 变体 fs14 → 16.8）', 'line-height 20（--sm 18）',
     '两条独立依据：①--sm 变体（已带出模型）同行有 remixicon 字形层 f6b7fbbd fs16 → 字形行盒 24 定行高（同本页 12-v3 checks 轮：'
     '卡3 标题行 fs16→24 使卡3 恰 132）⇒ 文本行盒不承重；②结果摘要标题行 c0b98aa4 子节点只有 标题竖条 h16 + 文本，行高由文本定，'
     'PNG 卡2 全部 ink 起点 408/453/488/526/568/604 设计与实现逐值相同、卡2 区带 8/8 命中（docH 1018 = 设计帧高）。'
     '墨迹：结果摘要 409..423 = 409..423；已带出模型 677..690 vs 678..691（+1）。'),
    ('count-chip__text', 'fs10 × lh1.2 = 12', 'line-height 18',
     '判据①设计显式 h=18：模型数标 22acf5bc height=18 + padding [0,8,0,8] + textAlignVertical=middle → 胶囊内居中、行盒不承重。'
     'PNG：胶囊上下边界 526 / 543 与墨迹 530..539 设计与实现逐值相同（含 526/543 两行 AA 带的墨迹量）。'),
    ('env-chip__text', 'fs10 × lh1.2 = 12', 'line-height 18',
     '判据①设计显式 h=18：环境小标 2a6f28d0 height=18 + padding [0,8,0,8] → 行盒不承重。'
     'PNG：胶囊边界 488 / 505 与墨迹 492..501 逐值相同。'),
    ('no-bar__copy-text', 'fs12 × lh1.2 = 14.4', 'line-height 16',
     '判据①设计显式 h=32：复制按钮 6bb5859a height=32 + padding [0,12,0,12] → 行盒不承重。'
     'PNG：复制 设计 309..320（24 列墨迹）= 实现 309..320。'),
    ('srow__label', 'fs13 × lh1.2 = 15.6', 'line-height 18',
     '盒算术（判据②）：摘要行 fba2ebb8/11050f12/bb193b6b/dd3a795d 均 padding [10,0,10,0] + alignItems=center，'
     '相邻行同字号标签的墨迹起点差 = 行高 ⇒ PNG 实测 453→491 = **38 = 10 + 行盒 + 10**（若 15.6 则行距 ≈37，与实测不符）⇒ 行盒 = 18。'
     '四行标签墨迹 453/491/529/568 设计与实现逐值相同；卡2 区带 8/8 命中。'),
    ('srow__value', 'fs13 × lh1.2 = 15.6', 'line-height 18',
     '与同行标签同盒（摘要行双方共用行高 38 = 10 + 18 + 10）。PNG 墨迹：2024Q3 主线路报价 453..466 = 453..466；'
     'sk-prod-••2f9a 491..504 = 491..504；QT-20240615-0007 569..581 vs 569..581（墨迹宽 94 vs 91 = H5 回退字体数字字距）。'),
    ('status-chip__text', 'fs11 × lh1.2 = 13.2', 'line-height 20',
     '判据①设计显式 h=20：状态标 c9fda041 height=20 + padding [0,8,0,8] → 行盒不承重。'
     'PNG：胶囊边界 604 / 623 逐值相同；墨迹 608..618 vs 609..619（+1）。'),
    ('tag__text', 'fs12 × lh1.2 = 14.4', 'line-height 16',
     '判据①设计显式 h=28：模型标签 1f778b64（--off）与 5290721b（--on）height=28 + padding [0,12,0,12] → 行盒不承重。'
     'PNG：胶囊边界 708 / 735 与 734..772 逐值相同，墨迹 gpt-4o / gpt-4o-mini / claude-3-5 / gemini-1.5-pro 逐值相同'
     '（claude-3-5 下沿 AA 708..709 vs 708、gemini 分隔 743 vs 743..744 = 亚像素取整）。'),
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
