# -*- coding: utf-8 -*-
"""把序号 12-v2（page-apikey「新增报价单-APIKey 下拉展开」）经设计 PNG + 盒算术判定的「非偏差」登记进 textleaf-accept.json。

判据优先级：①设计显式 height ②design PNG 的盒/带实测 ③fs × lineHeight；②③冲突以 ② 为准。
键名口径：`textleaf-audit.py` 的 class 键 = 叶子自身 class 链的第一个 token（一个键可覆盖多个变体）。

证据：evidence/cmp-序号12v2-文本叶子行盒-逐类带.txt · evidence/cmp-序号12v2-面板副行换行判读.txt

用法: python .agents/state/accept-12v2-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
EVID = 'evidence/cmp-序号12v2-文本叶子行盒-逐类带.txt + evidence/cmp-序号12v2-面板副行换行判读.txt'
AT = '2026-09-16 20:15'
PAGE = 'page-apikey'
TAG = '12-v2'

ITEMS = [
    ('label__text', 'fs13 × lh1.2 = 15.6', 'line-height 17',
     '盒算术定死 = 17（本帧两条独立链）：字段-报价单名称 = [字段标签行][container padTop 8 → 名称输入框 h48]；'
     '链1 输入框顶 196（PNG fill 197 −1）/ 标签墨迹 173 → L = 17；链2 只读盒顶 324 / 标签墨迹 301 → L = 17。'
     '与 12-v1 同组件、同声明结构，结论一致。'),
    ('label__star', 'fs13 × lh1.2 = 15.6', 'line-height 17',
     '与同行标签同盒（字段标签行 gap4 / align-center）；设计墨迹 173..178 = 实现 173..178。'),
    ('card__title', 'fs15 × lh1.2 = 18', 'line-height 20',
     '本帧两张卡的标题墨迹：基本信息 137..151（设计）= 137..151（实现）；模型列表 783..797（设计）= 782..796（实现，−1）。'
     '卡/头行几何与 12-v1 同组件（探针 272 条 checks 0 失败，含卡高）。设计渲染值 18~20（±1 不可分辨），不在此 churn。'),
    ('hint__text', 'fs11 × lh1.2 = 13.2', 'line-height 16.5',
     '与 12-v1 同组件同结构（字段 → container padTop 6 → 提示行）；本帧选择框下的蓝色提示行墨迹 715..727（设计，与选框描边带相连）'
     '= 713..727（实现，±2 = 字体墨迹 + 描边带合并）。'),
    ('bar__hint-text', 'fs11 × lh1.2 = 13.2', 'line-height 16.5',
     '底部操作条同 12-v1：说明行行高由同排图标字形盒（fs13 remixicon → 19.5）决定，文本在行内居中 → 行盒不承重；'
     '本帧墨迹 1027..1037（设计）= 1028..1038（实现，+1）。'),
    ('panel__title', 'fs14 × lh1.2 = 16.8', 'line-height 19',
     '判据①设计**显式 h=19**：0e3fde7a（测试环境密钥）与 3b424c06（数据标注专用）均为 w=fill_container h=19；'
     '首行 ecfecae1 为 fit_content、同为 19~20。墨迹：498..511（设计）= 498..511（实现）、608..621 = 608..621 逐值相同。'
     '16.8 会让选项行变 54（设计 55）。'),
    ('readonly-box__text', 'fs14 × lh1.2 = 16.8', 'line-height 21',
     '位于设计声明 h48 的只读盒内居中 → 行盒不承重；墨迹 342..355（设计）= 342..355（实现），逐值相同。'),
    ('rec-tag__text', 'fs9 × lh1.2 = 10.8', 'line-height 13.5',
     '设计 73297a26 fs9 SemiBold 白字（胶囊 h16 r8 #2563EB）；墨迹 500..508（设计）= 499..507（实现，−1）。'
     '胶囊高 16 由 .rec-tag 定高决定，行盒不承重。'),
    ('sample-pill__text', 'fs10 × lh1.2 = 12', 'line-height 15',
     '设计 106d1228 fs10；墨迹 344..353（设计）= 345..354（实现，+1）；与同页 fs10 一致。'),
    ('select__value', 'fs14 × lh1.2 = 16.8', 'line-height 21',
     '位于定高选择框内居中 → 行盒不承重；墨迹 449..462（设计）= 448..461（实现，−1）。'),
    ('tag__text', 'fs10 × lh1.2 = 12（chip 变体 fs11 → 13.2）', 'line-height 15 · chip 16.5',
     '系统生成（fs10）墨迹 302..311（设计）= 303..312（实现，+1）；待带出（tag__text--chip fs11）墨迹 784..794（设计）= 784..794（实现），'
     '带高与起点相同。面板内的「沙箱 / 专用」实为 env-tag__text（fs10，与设计 3291a0b7 / 9e2b7dbe 声明一致），不属本键。'),
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
